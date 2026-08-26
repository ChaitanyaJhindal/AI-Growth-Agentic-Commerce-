import unittest
import os
import sys

# Ensure root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.whatsapp.automation import validate_coupon_code, VALID_COUPONS, get_automation_manager
from src.auth import get_user_manager


class TestCouponAndAutomation(unittest.TestCase):

    def test_coupon_validation(self):
        """Verifies promo code validation and discount calculations."""
        # Test valid 20% coupon
        res1 = validate_coupon_code("AURA20", 100.0)
        self.assertTrue(res1["valid"])
        self.assertEqual(res1["discount_percent"], 20)
        self.assertEqual(res1["savings"], 20.0)
        self.assertEqual(res1["final_total"], 80.0)

        # Test valid 25% coupon (case-insensitive & trimmed)
        res2 = validate_coupon_code(" aura25  ", 200.0)
        self.assertTrue(res2["valid"])
        self.assertEqual(res2["discount_percent"], 25)
        self.assertEqual(res2["savings"], 50.0)
        self.assertEqual(res2["final_total"], 150.0)

        # Test valid 30% coupon
        res3 = validate_coupon_code("RUNWAY30", 50.0)
        self.assertTrue(res3["valid"])
        self.assertEqual(res3["discount_percent"], 30)
        self.assertEqual(res3["savings"], 15.0)
        self.assertEqual(res3["final_total"], 35.0)

        # Test invalid coupon
        res_bad = validate_coupon_code("FAKEDISCOUNT99", 100.0)
        self.assertFalse(res_bad["valid"])
        self.assertIn("Invalid or expired code", res_bad["error"])

    def test_user_manager_cart_and_coupon(self):
        """Verifies user bag syncing, bag_updated_at timestamp, phone update, and order with discount."""
        mgr = get_user_manager()
        test_email = f"test_patron_{os.urandom(4).hex()}@example.com"
        test_phone = "+919876543210"

        # 1. Signup
        signup_res = mgr.signup("Automation Patron", test_email, "Password123!", phone=test_phone)
        self.assertTrue(signup_res["success"])
        self.assertEqual(signup_res["user"]["phone"], test_phone)

        # 2. Sync cart items into bag
        cart_items = [
            {"product_id": "item_101", "name": "Cashmere Knit Sweater", "price": 120.0, "brand": "AURA Studio"},
            {"product_id": "item_102", "name": "Minimalist Tailored Trouser", "price": 95.0, "brand": "AURA Studio"}
        ]
        sync_res = mgr.sync_user_data(test_email, bag=cart_items)
        self.assertTrue(sync_res["success"])

        # 3. Check profile in Mongo has non-empty bag and bag_updated_at
        user_prof = mgr.get_user_profile(test_email)
        self.assertIsNotNone(user_prof)
        self.assertEqual(len(user_prof.get("bag", [])), 2)
        self.assertIn("bag_updated_at", user_prof)

        # 4. Check automation manager finds this user
        auto_mgr = get_automation_manager()
        stats = auto_mgr.get_stats()
        self.assertGreaterEqual(stats["abandoned_carts_count"], 1)
        self.assertGreater(stats["abandoned_total_value"], 0)

        # 5. Place order with coupon discount
        order_res = mgr.create_order(
            email=test_email,
            items=cart_items,
            total=172.0,
            coupon_code="AURA20",
            discount_amount=43.0,
            subtotal=215.0,
            payment_status="Paid (Razorpay)"
        )
        self.assertTrue(order_res["success"])
        self.assertEqual(order_res["coupon_code"], "AURA20")
        self.assertEqual(order_res["discount_amount"], 43.0)

        # 6. Verify user bag is now cleared in MongoDB
        user_prof_after = mgr.get_user_profile(test_email)
        self.assertEqual(len(user_prof_after.get("bag", [])), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
