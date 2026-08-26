import os
import json
import base64
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.server_api import ServerApi
from src import config

class MongoWhatsAppSessionStore:
    """
    Persists WhatsApp multi-device authentication & session keys in MongoDB
    `whatsapp_sessions` collection so Render ephemeral restarts never require
    re-scanning the WhatsApp QR code.
    """

    def __init__(self, db=None, session_id: str = "default_session"):
        self.session_id = session_id
        if db is not None:
            self.db = db
        else:
            connection_uri = config.MONGODB_URI
            if not connection_uri:
                raise ValueError("MONGODB_URI is required for session store.")
            self.client = MongoClient(connection_uri, server_api=ServerApi('1'))
            self.db = self.client[config.DB_NAME]

        self.collection: Collection = self.db[config.WHATSAPP_SESSION_COLLECTION]
        self._ensure_indexes()

    def _ensure_indexes(self):
        try:
            self.collection.create_index([("session_id", 1), ("key", 1)], unique=True)
        except Exception as e:
            print(f"Notice on session store index creation: {e}")

    def save_session_data(self, key: str, data: Any) -> bool:
        """Saves an authentication key (e.g. creds, pre-keys, app-state) into MongoDB."""
        now = datetime.now(timezone.utc)
        payload = json.dumps(data) if not isinstance(data, str) else data
        
        self.collection.update_one(
            {"session_id": self.session_id, "key": key},
            {
                "$set": {
                    "session_id": self.session_id,
                    "key": key,
                    "data": payload,
                    "updated_at": now
                }
            },
            upsert=True
        )
        return True

    def get_session_data(self, key: str) -> Optional[Any]:
        """Retrieves an authentication key from MongoDB."""
        doc = self.collection.find_one({"session_id": self.session_id, "key": key})
        if not doc:
            return None
        raw = doc.get("data")
        try:
            return json.loads(raw)
        except Exception:
            return raw

    def remove_session_data(self, key: str) -> bool:
        """Deletes an authentication key from MongoDB."""
        res = self.collection.delete_one({"session_id": self.session_id, "key": key})
        return res.deleted_count > 0

    def clear_all_session_keys(self) -> int:
        """Clears all session keys for this session ID."""
        res = self.collection.delete_many({"session_id": self.session_id})
        return res.deleted_count

    def has_active_session(self) -> bool:
        """Checks if valid credentials exist in MongoDB."""
        creds = self.get_session_data("creds")
        return creds is not None and isinstance(creds, dict) and bool(creds.get("me"))
