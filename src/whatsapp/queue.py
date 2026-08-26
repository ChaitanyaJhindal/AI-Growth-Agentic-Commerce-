import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union
from bson import ObjectId
from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.server_api import ServerApi
from src import config

E164_REGEX = re.compile(r'^\+[1-9]\d{7,14}$')

def validate_e164_phone(phone: str) -> str:
    """
    Validates and normalizes a phone number to international E.164 format.
    Example: '+919876543210', '+14155552671'
    """
    if not phone or not isinstance(phone, str):
        raise ValueError("Recipient phone number is required.")
    
    # Remove any whitespace, dashes, dots, or parentheses
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone.strip())
    
    # Ensure it starts with '+'
    if not cleaned.startswith('+'):
        # If 10-12 digits without '+', reject or require explicit '+'
        raise ValueError(f"Phone number '{phone}' must include international '+' prefix (e.g. +919876543210).")
    
    if not E164_REGEX.match(cleaned):
        raise ValueError(
            f"Invalid E.164 phone number format: '{phone}'. "
            "Must be '+' followed by 8 to 15 digits without special characters."
        )
    
    return cleaned

def mask_phone_number(phone: str) -> str:
    """
    Masks middle digits of a phone number for privacy in logs & public API responses.
    Example: '+919876543210' -> '+9198****3210'
    """
    if not phone or len(phone) < 8:
        return "+******"
    prefix = phone[:5]
    suffix = phone[-4:]
    return f"{prefix}****{suffix}"

class WhatsAppQueue:
    """
    Persistent, atomic MongoDB message queue for WhatsApp messages.
    Supports atomic locking, automatic retry with backoff, stale lock reclamation,
    and E.164 recipient validation.
    """

    def __init__(self, db=None, max_attempts: Optional[int] = None):
        self.max_attempts = max_attempts or config.WHATSAPP_MAX_ATTEMPTS
        
        if db is not None:
            self.db = db
        else:
            try:
                from src.agents.base import get_search_engine
                engine = get_search_engine()
                self.db = engine.collection.database
            except Exception:
                connection_uri = config.MONGODB_URI or os.getenv("MONGODB_URI")
                if not connection_uri and os.getenv("MONGODB_PASSWORD"):
                    import urllib.parse
                    connection_uri = config.DEFAULT_URI_TEMPLATE.format(
                        password=urllib.parse.quote_plus(os.getenv("MONGODB_PASSWORD", ""))
                    )
                if not connection_uri:
                    raise ValueError("MONGODB_URI or MONGODB_PASSWORD is required for WhatsApp queue.")
                self.client = MongoClient(connection_uri, server_api=ServerApi('1'))
                self.db = self.client[config.DB_NAME]

        self.collection: Collection = self.db[config.WHATSAPP_QUEUE_COLLECTION]
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Creates indexes for fast atomic queue polling and status lookups."""
        try:
            self.collection.create_index([("status", 1), ("created_at", 1)])
            self.collection.create_index([("recipient_phone", 1)])
            self.collection.create_index([("updated_at", 1)])
        except Exception as e:
            print(f"Notice on WhatsApp queue index creation: {e}")

    def enqueue(
        self,
        recipient_phone: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validates and enqueues a WhatsApp message into MongoDB with status 'pending'.
        Does NOT send the message immediately.
        """
        normalized_phone = validate_e164_phone(recipient_phone)
        
        if not message or not isinstance(message, str) or not message.strip():
            raise ValueError("Message body cannot be empty.")
        
        clean_message = message.strip()
        now = datetime.now(timezone.utc)

        doc = {
            "recipient_phone": normalized_phone,
            "message": clean_message,
            "status": "pending",
            "attempts": 0,
            "max_attempts": self.max_attempts,
            "created_at": now,
            "updated_at": now,
            "sent_at": None,
            "last_error": None,
            "metadata": metadata or {}
        }

        result = self.collection.insert_one(doc)
        message_id = str(result.inserted_id)

        return {
            "success": True,
            "message_id": message_id,
            "status": "pending",
            "recipient_phone": mask_phone_number(normalized_phone),
            "created_at": now.isoformat()
        }

    def get_message(self, message_id: str, unmask: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieves a message document by ID. Phone number is masked unless explicitly unmasked.
        """
        try:
            oid = ObjectId(message_id) if isinstance(message_id, str) and len(message_id) == 24 else message_id
            doc = self.collection.find_one({"_id": oid})
            if not doc:
                return None
            return self._serialize_doc(doc, unmask=unmask)
        except Exception:
            return None

    def claim_next_pending(self, stale_timeout_seconds: int = 300) -> Optional[Dict[str, Any]]:
        """
        Atomically claims one pending message (or recovers a stalled 'processing' message).
        Transitions status from 'pending' -> 'processing'.
        """
        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(seconds=stale_timeout_seconds)

        claimed_doc = self.collection.find_one_and_update(
            filter={
                "$or": [
                    {"status": "pending", "attempts": {"$lt": self.max_attempts}},
                    {"status": "processing", "updated_at": {"$lt": stale_cutoff}, "attempts": {"$lt": self.max_attempts}}
                ]
            },
            update={
                "$set": {
                    "status": "processing",
                    "updated_at": now
                }
            },
            sort=[("created_at", 1)],
            return_document=ReturnDocument.AFTER
        )

        if claimed_doc:
            return self._serialize_doc(claimed_doc, unmask=True)
        return None

    def mark_sent(self, message_id: str, provider_meta: Optional[Dict[str, Any]] = None) -> bool:
        """
        Transitions message status to 'sent' with timestamp.
        """
        now = datetime.now(timezone.utc)
        oid = ObjectId(message_id) if isinstance(message_id, str) and len(message_id) == 24 else message_id
        
        update_fields: Dict[str, Any] = {
            "status": "sent",
            "sent_at": now,
            "updated_at": now,
            "last_error": None
        }
        if provider_meta:
            update_fields["provider_meta"] = provider_meta

        res = self.collection.update_one(
            {"_id": oid},
            {"$set": update_fields}
        )
        return res.modified_count > 0

    def mark_failed_or_retry(self, message_id: str, error_msg: str) -> Dict[str, Any]:
        """
        Increments attempts and marks message either as 'pending' for retry
        or 'failed' if max_attempts has been reached.
        """
        now = datetime.now(timezone.utc)
        oid = ObjectId(message_id) if isinstance(message_id, str) and len(message_id) == 24 else message_id
        
        # Read current document
        doc = self.collection.find_one({"_id": oid})
        if not doc:
            return {"status": "not_found", "attempts": 0}

        current_attempts = doc.get("attempts", 0) + 1
        max_attempts = doc.get("max_attempts", self.max_attempts)
        new_status = "failed" if current_attempts >= max_attempts else "pending"

        self.collection.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": new_status,
                    "last_error": str(error_msg)[:500],
                    "updated_at": now
                },
                "$inc": {"attempts": 1}
            }
        )

        return {
            "status": new_status,
            "attempts": current_attempts,
            "max_attempts": max_attempts
        }

    def get_stats(self) -> Dict[str, Any]:
        """Returns real-time queue metrics."""
        counts = {
            "pending": self.collection.count_documents({"status": "pending"}),
            "processing": self.collection.count_documents({"status": "processing"}),
            "sent": self.collection.count_documents({"status": "sent"}),
            "failed": self.collection.count_documents({"status": "failed"})
        }
        counts["total"] = sum(counts.values())
        return counts

    def _serialize_doc(self, doc: Dict[str, Any], unmask: bool = False) -> Dict[str, Any]:
        """Converts MongoDB document to JSON-safe dictionary."""
        serialized = dict(doc)
        serialized["_id"] = str(doc.get("_id", ""))
        serialized["message_id"] = serialized["_id"]
        
        if not unmask:
            serialized["recipient_phone"] = mask_phone_number(doc.get("recipient_phone", ""))
        
        for k in ["created_at", "updated_at", "sent_at"]:
            if isinstance(serialized.get(k), datetime):
                serialized[k] = serialized[k].isoformat()

        return serialized


# Shared singleton instance
_whatsapp_queue = None

def get_whatsapp_queue() -> WhatsAppQueue:
    global _whatsapp_queue
    if _whatsapp_queue is None:
        _whatsapp_queue = WhatsAppQueue()
    return _whatsapp_queue
