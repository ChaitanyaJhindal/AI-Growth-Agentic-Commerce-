import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pymongo.collection import Collection
from src import config
from src.agents.campaign_agent import get_campaign_agent, CampaignAgent
from src.whatsapp.queue import WhatsAppQueue, get_whatsapp_queue, validate_e164_phone, mask_phone_number

# Available system coupons
VALID_COUPONS = {
    "AURA20": {"discount_percent": 20, "description": "20% Exclusive Concierge Privilege"},
    "AURA25": {"discount_percent": 25, "description": "25% VIP Autumn Selection"},
    "VIP20": {"discount_percent": 20, "description": "20% VIP Atelier Discount"},
    "WELCOME10": {"discount_percent": 10, "description": "10% Welcome Patron Gift"},
    "RUNWAY30": {"discount_percent": 30, "description": "30% Runway Special Preview"}
}

def validate_coupon_code(code: str, subtotal: float = 0.0) -> Dict[str, Any]:
    """
    Validates a coupon code and calculates savings and discounted total.
    """
    clean_code = (code or "").strip().upper()
    if not clean_code:
        return {"valid": False, "error": "Please enter a promo code."}

    coupon = VALID_COUPONS.get(clean_code)
    if not coupon:
        return {
            "valid": False,
            "error": f"Invalid or expired code '{clean_code}'. Try 'AURA20' or 'AURA25'."
        }

    percent = coupon["discount_percent"]
    savings = round(subtotal * (percent / 100.0), 2)
    final_total = max(0.0, round(subtotal - savings, 2))

    return {
        "valid": True,
        "code": clean_code,
        "discount_percent": percent,
        "description": coupon["description"],
        "savings": savings,
        "final_total": final_total
    }

class CartCampaignAutomationManager:
    """
    Automated pipeline that identifies users with active/abandoned shopping bags in MongoDB,
    generates hyper-personalized promotional copy via CampaignAgent (openai/gpt-oss-20b),
    and enqueues messages to the WhatsApp persistent queue.
    """

    def __init__(self, db=None, queue: Optional[WhatsAppQueue] = None, agent: Optional[CampaignAgent] = None):
        if db is not None:
            self.db = db
        else:
            try:
                from src.agents.base import get_search_engine
                engine = get_search_engine()
                self.db = engine.collection.database
            except Exception:
                from src.auth import UserManager
                self.db = UserManager().db

        self.users_collection: Collection = self.db["users"]
        self.queue = queue or get_whatsapp_queue(db=self.db)
        self.agent = agent or get_campaign_agent()

    def get_abandoned_cart_users(self, min_items: int = 1, user_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Finds all registered users who currently have items in their shopping bag.
        """
        query = {
            "bag": {"$exists": True, "$not": {"$size": 0}}
        }
        if user_email:
            query["email"] = user_email.strip().lower()

        users = list(self.users_collection.find(query, {"password_hash": 0, "password_salt": 0}))
        results = []
        for u in users:
            bag = u.get("bag", [])
            if len(bag) >= min_items:
                total_val = sum(float(i.get("price", 0)) for i in bag)
                results.append({
                    "user_id": str(u["_id"]),
                    "name": u.get("name", "Customer"),
                    "email": u.get("email"),
                    "phone": u.get("phone"),
                    "bag_items_count": len(bag),
                    "bag_total_value": round(total_val, 2),
                    "bag_items": bag,
                    "bag_updated_at": u.get("bag_updated_at"),
                    "last_campaign_sent_at": u.get("last_campaign_sent_at")
                })
        return results

    def trigger_abandoned_cart_campaign(
        self,
        coupon_code: str = "AURA20",
        tone: str = "witty_hinglish",
        cooldown_hours: float = 1.0,
        override_phone: Optional[str] = None,
        max_users: int = 20,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end automation pipeline:
        1. Queries users with active/abandoned carts.
        2. Applies cooldown filter to avoid repeat messaging.
        3. Synthesizes personalized copy using CampaignAgent (openai/gpt-oss-20b).
        4. Enqueues messages to MongoDB whatsapp_messages queue for the background worker to dispatch.
        """
        abandoned_users = self.get_abandoned_cart_users(min_items=1, user_email=user_email)
        now = datetime.now(timezone.utc)
        cooldown_delta = timedelta(hours=cooldown_hours)

        processed = []
        skipped = []

        for u in abandoned_users[:max_users]:
            user_phone = override_phone or u.get("phone")
            if not user_phone:
                skipped.append({
                    "user": u.get("name"),
                    "email": u.get("email"),
                    "reason": "Missing phone number"
                })
                continue

            # Check cooldown
            last_sent_str = u.get("last_campaign_sent_at")
            if last_sent_str and not override_phone:
                try:
                    last_sent_dt = datetime.fromisoformat(last_sent_str.replace("Z", "+00:00"))
                    if (now - last_sent_dt) < cooldown_delta:
                        skipped.append({
                            "user": u.get("name"),
                            "email": u.get("email"),
                            "reason": f"Cooldown active (last sent {last_sent_str})"
                        })
                        continue
                except Exception:
                    pass

            # 1. Generate AI Copy
            try:
                campaign_res = self.agent.generate_message(
                    customer_name=u.get("name", "Patron"),
                    bag_items=u.get("bag_items", []),
                    channel="whatsapp",
                    discount_code=coupon_code,
                    tone=tone
                )
                msg_text = campaign_res.get("message", "")
                if not msg_text:
                    raise RuntimeError("No message produced by campaign agent.")

                # 2. Enqueue in WhatsApp persistent queue
                enq_res = self.queue.enqueue(
                    recipient_phone=user_phone,
                    message=msg_text,
                    metadata={
                        "user_email": u.get("email"),
                        "customer_name": u.get("name"),
                        "campaign_type": "abandoned_cart",
                        "headline": campaign_res.get("headline"),
                        "coupon_code": coupon_code,
                        "bag_items_count": u.get("bag_items_count"),
                        "bag_total": u.get("bag_total_value"),
                        "source": "abandoned_cart_automation"
                    }
                )

                # 3. Update user doc with campaign timestamp
                self.users_collection.update_one(
                    {"email": u.get("email")},
                    {"$set": {"last_campaign_sent_at": now.isoformat()}}
                )

                processed.append({
                    "email": u.get("email"),
                    "user_email": u.get("email"),
                    "customer_name": u.get("name"),
                    "phone": user_phone,
                    "recipient_phone": mask_phone_number(enq_res.get("recipient_phone", user_phone)),
                    "message_id": enq_res.get("message_id"),
                    "headline": campaign_res.get("headline"),
                    "preview": campaign_res.get("formatted_message") or campaign_res.get("headline"),
                    "coupon_code": coupon_code,
                    "status": enq_res.get("status")
                })
            except Exception as ex:
                skipped.append({
                    "user": u.get("name"),
                    "email": u.get("email"),
                    "reason": f"Campaign synthesis/queue failed: {str(ex)}"
                })

        return {
            "success": True,
            "message": f"Successfully processed {len(abandoned_users)} cart(s) and enqueued {len(processed)} recovery campaign(s).",
            "total_abandoned_found": len(abandoned_users),
            "processed_count": len(processed),
            "enqueued_count": len(processed),
            "skipped_count": len(skipped),
            "processed_campaigns": processed,
            "details": processed,
            "skipped_details": skipped,
            "triggered_at": now.isoformat()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Calculates real-time abandoned cart metrics for Admin portal."""
        abandoned_users = self.get_abandoned_cart_users(min_items=1)
        total_items = sum(u["bag_items_count"] for u in abandoned_users)
        total_value = sum(u["bag_total_value"] for u in abandoned_users)
        with_phone = sum(1 for u in abandoned_users if u.get("phone"))

        # Queue metrics
        queue_stats = self.queue.get_stats()

        return {
            "abandoned_carts_count": len(abandoned_users),
            "abandoned_items_count": total_items,
            "abandoned_total_value": round(total_value, 2),
            "reachable_via_whatsapp": with_phone,
            "queue": queue_stats,
            "active_users": abandoned_users[:10]
        }

_automation_mgr = None

def get_automation_manager(db=None) -> CartCampaignAutomationManager:
    """Returns singleton instance of CartCampaignAutomationManager."""
    global _automation_mgr
    if _automation_mgr is None:
        _automation_mgr = CartCampaignAutomationManager(db=db)
    return _automation_mgr
