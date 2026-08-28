"""
Unit & Integration Tests for AI Buyer Protocol (AP2 / MCP / A2A Commerce).
Verifies discovery, machine search, explainable quotes, budget gating, and HMAC verification.
"""
import unittest
import os
import sys
import hmac
import hashlib
import secrets
from fastapi.testclient import TestClient

# Ensure root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from server import app
from src import config

class TestAgentProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.buyer_id = "Agent_Test_Buyer_001"
        cls.shopper_email = "test_ai_buyer@aurafashion.com"

    def test_01_agent_protocol_manifest_discovery(self):
        """Tests that machine-readable discovery manifest is accessible and compliant."""
        res = self.client.get("/.well-known/agent-protocol.json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("protocol_version"), "AP2/1.0")
        self.assertEqual(data.get("currency"), "INR")
        self.assertIn("capabilities", data)
        self.assertIn("endpoints", data)

    def test_02_mcp_manifest_discovery(self):
        """Tests that Model Context Protocol (MCP) tool declarations are valid."""
        res = self.client.get("/.well-known/mcp.json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("server_name"), "aura-commerce-mcp")
        tools = [t["name"] for t in data.get("tools", [])]
        self.assertIn("aura_search_catalog", tools)
        self.assertIn("aura_get_quote", tools)
        self.assertIn("aura_execute_checkout", tools)

    def test_03_protocol_catalog_query(self):
        """Tests structured catalog discovery with INR budget normalization."""
        payload = {
            "query": "running shoes",
            "gender": "Men",
            "max_budget_inr": 4000.0,
            "limit": 4
        }
        res = self.client.post("/protocol/v1/catalog/query", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        self.assertGreaterEqual(data.get("results_count", 0), 1)
        products = data.get("products", [])
        for p in products:
            self.assertIn("price_inr", p)
            self.assertIn("stock_status", p)

    def test_04_protocol_quote_explainability(self):
        """Tests automated quote calculation with voucher discount and explainability."""
        payload = {
            "buyer_agent_id": self.buyer_id,
            "items": [
                {"product_id": "1163", "name": "Nike Men Running Shoes", "price_inr": 2000.0},
                {"product_id": "1164", "name": "Puma Sport Socks", "price_inr": 500.0}
            ],
            "coupon_code": "AURA20"
        }
        res = self.client.post("/protocol/v1/quote", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("subtotal_inr"), 2500.0)
        self.assertEqual(data.get("discount_inr"), 500.0) # 20% of 2500
        self.assertEqual(data.get("final_payable_inr"), 2000.0)
        self.assertTrue(len(data.get("explainability", "")) > 0)

    def test_05_budget_gating_violation_rejection(self):
        """
        THE BAR: Tests strict spending gating.
        Rejects order with HTTP 422 BUDGET_GATING_VIOLATION when total exceeds authorized limit.
        """
        payload = {
            "buyer_agent_id": self.buyer_id,
            "shopper_email": self.shopper_email,
            "items": [
                {"product_id": "1163", "name": "Nike Men Running Shoes", "price_inr": 3500.0}
            ],
            "max_authorized_budget_inr": 1000.0 # Violation: 3500 > 1000!
        }
        res = self.client.post("/protocol/v1/order/checkout", json=payload)
        self.assertEqual(res.status_code, 422)
        err = res.json()
        self.assertEqual(err["detail"]["error_code"], "BUDGET_GATING_VIOLATION")
        self.assertEqual(err["detail"]["gating_status"], "REJECTED_BY_MERCHANT_GATE")

    def test_06_bounded_checkout_and_verification(self):
        """Tests successful bounded checkout and HMAC-SHA256 test payment verification."""
        # 1. Checkout
        checkout_payload = {
            "buyer_agent_id": self.buyer_id,
            "shopper_email": self.shopper_email,
            "items": [
                {"product_id": "1163", "name": "Nike Men Running Shoes", "price_inr": 2000.0}
            ],
            "coupon_code": "AURA20",
            "max_authorized_budget_inr": 2500.0
        }
        checkout_res = self.client.post("/protocol/v1/order/checkout", json=checkout_payload)
        self.assertEqual(checkout_res.status_code, 200)
        order_data = checkout_res.json()
        self.assertEqual(order_data.get("status"), "PAYMENT_INTENT_CREATED")
        self.assertEqual(order_data.get("final_payable_inr"), 1600.0) # 2000 - 20% (400)
        self.assertIn("razorpay_order_id", order_data)

        rzp_order_id = order_data["razorpay_order_id"]
        order_id = order_data["order_id"]
        simulated_payment_id = f"pay_test_{secrets.token_hex(6)}"

        # 2. Compute HMAC-SHA256 signature
        payload_str = f"{rzp_order_id}|{simulated_payment_id}"
        signature = hmac.new(
            config.RAZORPAY_KEY_SECRET.encode("utf-8"),
            payload_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # 3. Verify Payment
        verify_payload = {
            "buyer_agent_id": self.buyer_id,
            "shopper_email": self.shopper_email,
            "order_id": order_id,
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": simulated_payment_id,
            "razorpay_signature": signature,
            "items": checkout_payload["items"],
            "total_inr": 1600.0,
            "coupon_code": "AURA20",
            "discount_inr": 400.0
        }
        verify_res = self.client.post("/protocol/v1/order/verify", json=verify_payload)
        self.assertEqual(verify_res.status_code, 200)
        verify_data = verify_res.json()
        self.assertEqual(verify_data.get("status"), "TRANSACTION_SETTLED")
        self.assertTrue(verify_data["protocol_receipt"]["signature_verified"])

    def test_07_protocol_telemetry(self):
        """Tests telemetry endpoint aggregating A2A volume and active agent buyers."""
        res = self.client.get("/protocol/v1/telemetry")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("total_a2a_orders", data)
        self.assertIn("active_ai_buyers", data)


if __name__ == "__main__":
    unittest.main()
