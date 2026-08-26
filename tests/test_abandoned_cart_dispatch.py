import unittest
import os
import sys

# Ensure root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.whatsapp.automation import get_automation_manager
from src.whatsapp.queue import get_whatsapp_queue
from src.auth import get_user_manager


class TestAbandonedCartPipeline(unittest.TestCase):

    def test_full_abandoned_cart_campaign_pipeline(self):
        """
        Creates a test user with a non-empty bag and a valid phone number,
        triggers the CartCampaignAutomationManager with CampaignAgent (openai/gpt-oss-20b),
        and asserts that a hyper-personalized message is synthesized and enqueued into MongoDB.
        """
        mgr = get_user_manager()
        auto_mgr = get_automation_manager()
        queue = get_whatsapp_queue()

        test_email = f"vip_patron_{os.urandom(4).hex()}@example.com"
        test_phone = "+919876543210"

        # 1. Register patron with phone
        signup_res = mgr.signup("Aarav Mehta", test_email, "SecurePass123!", phone=test_phone)
        self.assertTrue(signup_res["success"])

        # 2. Add luxury items to shopping bag
        cart_items = [
            {"product_id": "aura_shoe_1", "name": "Puma Velocity Nitro 3 Running Shoes", "price": 130.0, "brand": "Puma"},
            {"product_id": "aura_tee_2", "name": "Merino Wool Knit Tee", "price": 75.0, "brand": "AURA Studio"}
        ]
        mgr.sync_user_data(test_email, bag=cart_items)

        # 3. Trigger Abandoned Cart Re-Engagement Campaign with CampaignAgent
        res = auto_mgr.trigger_abandoned_cart_campaign(
            coupon_code="AURA25",
            tone="witty_hinglish",
            cooldown_hours=0.0,  # immediate test
            override_phone=test_phone,
            max_users=1,
            user_email=test_email
        )

        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["enqueued_count"], 1)
        self.assertEqual(len(res["details"]), 1)

        detail = res["details"][0]
        self.assertEqual(detail["email"], test_email)
        self.assertIn(detail["status"], ["pending", "enqueued"])
        self.assertIn("preview", detail)
        try:
            print("\n[Synthesized AI Recovery Copy]:", detail["preview"])
        except Exception:
            print("\n[Synthesized AI Recovery Copy]:", detail["preview"].encode("ascii", "replace").decode("ascii"))

        # 4. Check Queue Status in MongoDB
        q_stats = queue.get_stats()
        self.assertGreaterEqual(q_stats["total"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
