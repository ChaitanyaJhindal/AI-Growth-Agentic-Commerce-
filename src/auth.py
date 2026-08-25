import os
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.server_api import ServerApi
from src import config

def hash_password(password: str) -> Tuple[str, str]:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with a cryptographically random salt.
    Returns (salt_hex, hash_hex).
    """
    salt = secrets.token_bytes(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        hash_name='sha256',
        password=password.encode('utf-8'),
        salt=salt,
        iterations=100000
    )
    return salt.hex(), hash_bytes.hex()

def verify_password(password: str, salt_hex: str, expected_hash_hex: str) -> bool:
    """
    Verifies a password against the stored salt and hash using constant-time comparison.
    """
    try:
        salt = bytes.fromhex(salt_hex)
        hash_bytes = hashlib.pbkdf2_hmac(
            hash_name='sha256',
            password=password.encode('utf-8'),
            salt=salt,
            iterations=100000
        )
        return secrets.compare_digest(hash_bytes.hex(), expected_hash_hex)
    except Exception:
        return False

class UserManager:
    """Manages user registration, authentication, and MongoDB persistence."""

    def __init__(self, uri: Optional[str] = None):
        connection_uri = uri or config.MONGODB_URI
        if not connection_uri:
            raise ValueError("MONGODB_URI or MONGODB_PASSWORD environment variable is required.")
        self.client = MongoClient(connection_uri, server_api=ServerApi('1'))
        self.db = self.client[config.DB_NAME]
        self.users_collection: Collection = self.db["users"]
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Ensures unique index on user email."""
        try:
            self.users_collection.create_index("email", unique=True)
        except Exception as e:
            print(f"Notice on user collection index creation: {e}")

    def signup(self, name: str, email: str, password: str) -> Dict[str, Any]:
        """Registers a new user in MongoDB."""
        clean_email = email.strip().lower()
        clean_name = name.strip()

        if not clean_email or "@" not in clean_email:
            return {"success": False, "error": "Invalid email address format."}
        if not password or len(password) < 6:
            return {"success": False, "error": "Password must be at least 6 characters."}
        if not clean_name:
            clean_name = clean_email.split("@")[0].capitalize()

        existing = self.users_collection.find_one({"email": clean_email})
        if existing:
            return {"success": False, "error": "An account with this email already exists."}

        salt_hex, hash_hex = hash_password(password)
        now = datetime.now(timezone.utc).isoformat()

        user_doc = {
            "name": clean_name,
            "email": clean_email,
            "password_salt": salt_hex,
            "password_hash": hash_hex,
            "created_at": now,
            "wardrobe": [],
            "bag": [],
            "preferences": {}
        }

        result = self.users_collection.insert_one(user_doc)
        user_id = str(result.inserted_id)

        return {
            "success": True,
            "user": {
                "id": user_id,
                "name": clean_name,
                "email": clean_email,
                "wardrobe": [],
                "bag": [],
                "created_at": now
            }
        }

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticates an existing user and returns their profile and collections."""
        clean_email = email.strip().lower()

        if not clean_email or not password:
            return {"success": False, "error": "Email and password are required."}

        user_doc = self.users_collection.find_one({"email": clean_email})
        if not user_doc:
            return {"success": False, "error": "Invalid email or password."}

        salt_hex = user_doc.get("password_salt", "")
        expected_hash = user_doc.get("password_hash", "")

        if not verify_password(password, salt_hex, expected_hash):
            return {"success": False, "error": "Invalid email or password."}

        return {
            "success": True,
            "user": {
                "id": str(user_doc["_id"]),
                "name": user_doc.get("name", clean_email.split("@")[0].capitalize()),
                "email": clean_email,
                "wardrobe": user_doc.get("wardrobe", []),
                "bag": user_doc.get("bag", []),
                "created_at": user_doc.get("created_at", "")
            }
        }

    def get_user_profile(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieves user profile and saved items."""
        clean_email = email.strip().lower()
        user_doc = self.users_collection.find_one({"email": clean_email})
        if not user_doc:
            return None
        return {
            "id": str(user_doc["_id"]),
            "name": user_doc.get("name", ""),
            "email": clean_email,
            "wardrobe": user_doc.get("wardrobe", []),
            "bag": user_doc.get("bag", []),
            "created_at": user_doc.get("created_at", "")
        }

    def sync_user_data(self, email: str, wardrobe: Optional[List[Dict[str, Any]]] = None, bag: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Synchronizes user's saved wardrobe and shopping bag items into MongoDB."""
        clean_email = email.strip().lower()
        update_fields = {}
        if wardrobe is not None:
            update_fields["wardrobe"] = wardrobe
        if bag is not None:
            update_fields["bag"] = bag

        if not update_fields:
            return {"success": True, "message": "Nothing to update."}

        res = self.users_collection.update_one(
            {"email": clean_email},
            {"$set": update_fields}
        )

        return {
            "success": res.matched_count > 0,
            "updated": res.modified_count > 0
        }

    def create_order(
        self,
        email: str,
        items: List[Dict[str, Any]],
        total: float,
        payment_id: Optional[str] = None,
        razorpay_order_id: Optional[str] = None,
        payment_status: str = "Paid"
    ) -> Dict[str, Any]:
        """Places a verified paid order in MongoDB for a registered user."""
        clean_email = email.strip().lower()
        user = self.users_collection.find_one({"email": clean_email})
        if not user:
            return {"success": False, "error": "User account not found."}

        order_id = f"ORD-{secrets.token_hex(4).upper()}"
        now = datetime.now(timezone.utc).isoformat()

        order_doc = {
            "order_id": order_id,
            "user_email": clean_email,
            "user_name": user.get("name", "Customer"),
            "items": items,
            "total_amount": round(float(total), 2),
            "payment_id": payment_id,
            "razorpay_order_id": razorpay_order_id,
            "status": payment_status,
            "created_at": now
        }

        orders_collection = self.db["orders"]
        orders_collection.insert_one(order_doc)

        # Clear user's active bag and append order to user's history
        self.users_collection.update_one(
            {"email": clean_email},
            {
                "$set": {"bag": []},
                "$push": {"orders": {
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "items_count": len(items),
                    "total": order_doc["total_amount"],
                    "created_at": now
                }}
            }
        )

        return {
            "success": True,
            "order_id": order_id,
            "payment_id": payment_id,
            "total": order_doc["total_amount"],
            "created_at": now
        }

    def get_user_orders(self, email: str) -> List[Dict[str, Any]]:
        """Retrieves all full order documents for a specific user, sorted newest first."""
        clean_email = email.strip().lower()
        orders = list(self.db["orders"].find({"user_email": clean_email}, {"_id": 0}).sort("created_at", -1))
        return orders

    def get_all_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves all placed orders across the platform, sorted newest first."""
        orders = list(self.db["orders"].find({}, {"_id": 0}).sort("created_at", -1).limit(limit))
        return orders

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Retrieves user directory with statistics."""
        users_cursor = self.users_collection.find({}, {"_id": 0, "password_salt": 0, "password_hash": 0}).sort("created_at", -1)
        users_list = []
        for u in users_cursor:
            orders = u.get("orders", [])
            total_spent = sum(o.get("total", 0.0) for o in orders)
            users_list.append({
                "name": u.get("name", "Patron"),
                "email": u.get("email"),
                "created_at": u.get("created_at", ""),
                "wardrobe_count": len(u.get("wardrobe", [])),
                "orders_count": len(orders),
                "total_spent": round(total_spent, 2)
            })
        return users_list

    def get_admin_metrics(self) -> Dict[str, Any]:
        """Calculates executive dashboard analytics and metrics."""
        orders_col = self.db["orders"]
        all_orders = list(orders_col.find({}, {"_id": 0}))

        total_orders = len(all_orders)
        gross_volume = sum(o.get("total_amount", 0.0) for o in all_orders)
        avg_order_val = (gross_volume / total_orders) if total_orders > 0 else 0.0
        total_users = self.users_collection.count_documents({})
        total_products = self.db["products"].count_documents({})

        # Category sales breakdown
        categories: Dict[str, int] = {}
        for o in all_orders:
            for item in o.get("items", []):
                cat = item.get("master_category") or item.get("article_type") or "Accessories"
                categories[cat] = categories.get(cat, 0) + 1

        recent_orders = list(orders_col.find({}, {"_id": 0}).sort("created_at", -1).limit(6))

        return {
            "gross_volume": round(gross_volume, 2),
            "total_orders": total_orders,
            "total_users": total_users,
            "total_products": total_products,
            "average_order_value": round(avg_order_val, 2),
            "category_breakdown": categories,
            "recent_orders": recent_orders
        }

    def update_order_status(self, order_id: str, new_status: str) -> bool:
        """Updates fulfillment status for an order."""
        res = self.db["orders"].update_one(
            {"order_id": order_id},
            {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return res.modified_count > 0

_user_manager: Optional[UserManager] = None

def get_user_manager() -> UserManager:
    """Returns or initializes the global UserManager singleton."""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager


