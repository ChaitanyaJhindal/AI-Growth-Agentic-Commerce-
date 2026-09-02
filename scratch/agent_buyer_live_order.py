"""
Autonomous AI Buyer Agent Script
Acting as the AI Buyer to discover, quote, and place a verified order via the A2A Protocol.
"""
import json
import secrets
import hmac
import hashlib
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from server import app
from src import config

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

client = TestClient(app)
BUYER_AGENT_ID = "Antigravity_Autonomous_AI_Buyer_v1"
PATRON_EMAIL = "chaitanya_vip@aurafashion.com"

print("=" * 70)
print("1. DISCOVERING MCP TOOLS & AGENT PROTOCOL MANIFEST")
print("=" * 70)

res_manifest = client.get("/.well-known/agent-protocol.json")
print("Manifest Response (HTTP", res_manifest.status_code, "):")
print(json.dumps(res_manifest.json(), indent=2))

res_mcp = client.get("/.well-known/mcp.json")
print("\nMCP Tool Definitions (HTTP", res_mcp.status_code, "):")
tools = res_mcp.json().get("tools", [])
for t in tools:
    print(f" • Tool: {t['name']} - {t['description'][:60]}...")

print("\n" + "=" * 70)
print("2. EXECUTING MCP TOOL: aura_search_catalog")
print("=" * 70)

search_query = {
    "query": "Puma casual t-shirt",
    "gender": "Men",
    "max_budget_inr": 2500.0,
    "limit": 3
}
res_search = client.post("/protocol/v1/catalog/query", json=search_query)
search_data = res_search.json()
products = search_data.get("products", [])
print(f"Found {len(products)} products matching '{search_query['query']}':")
for p in products:
    print(f" • [{p['product_id']}] {p['name']} | Brand: {p['brand']} | Price: ₹{p['price_inr']:,} INR")

if not products:
    print("Fallback to generic search")
    res_search = client.post("/protocol/v1/catalog/query", json={"query": "shirt", "limit": 2})
    products = res_search.json().get("products", [])

selected_product = products[0]
print(f"\nAI Buyer Selected Piece: {selected_product['name']} (ID: {selected_product['product_id']}, Price: ₹{selected_product['price_inr']:,} INR)")

print("\n" + "=" * 70)
print("3. EXECUTING MCP TOOL: aura_get_quote (Applying Voucher: AURA20)")
print("=" * 70)

cart_items = [{
    "product_id": selected_product["product_id"],
    "name": selected_product["name"],
    "price_inr": selected_product["price_inr"],
    "brand": selected_product.get("brand"),
    "article_type": selected_product.get("article_type"),
    "image_url": selected_product.get("image_url")
}]

quote_payload = {
    "buyer_agent_id": BUYER_AGENT_ID,
    "items": cart_items,
    "coupon_code": "AURA20"
}
res_quote = client.post("/protocol/v1/quote", json=quote_payload)
quote_data = res_quote.json()
print("Quote Breakdown:")
print(f" • Subtotal: ₹{quote_data['subtotal_inr']:,} INR")
print(f" • Applied Voucher: {quote_data['applied_promo']['code']} (-{quote_data['applied_promo']['discount_percent']}%)")
print(f" • Savings: ₹{quote_data['discount_inr']:,} INR")
print(f" • Final Payable: ₹{quote_data['final_payable_inr']:,} INR")
print(f" • Explainability: {quote_data['explainability']}")

print("\n" + "=" * 70)
print("4. EXECUTING MCP TOOL: aura_execute_checkout (Bounded at ₹3,000 INR)")
print("=" * 70)

checkout_payload = {
    "buyer_agent_id": BUYER_AGENT_ID,
    "shopper_email": PATRON_EMAIL,
    "items": cart_items,
    "coupon_code": "AURA20",
    "max_authorized_budget_inr": 3000.0
}
res_checkout = client.post("/protocol/v1/order/checkout", json=checkout_payload)
checkout_data = res_checkout.json()
print("Razorpay Intent Created:")
print(f" • Order ID: {checkout_data['order_id']}")
print(f" • Razorpay Order Ref: {checkout_data['razorpay_order_id']}")
print(f" • Amount in Paise: {checkout_data['amount_in_paise']} paise (₹{checkout_data['final_payable_inr']} INR)")
print(f" • Gating Status: {checkout_data['gating_proof']['budget_compliance']}")

print("\n" + "=" * 70)
print("5. VERIFYING & COMMITTING ORDER WITH CRYPTOGRAPHIC PROOF")
print("=" * 70)

rzp_order_id = checkout_data["razorpay_order_id"]
simulated_payment_id = f"pay_agentic_{secrets.token_hex(6)}"

# Generate valid HMAC-SHA256 test signature
payload_str = f"{rzp_order_id}|{simulated_payment_id}"
signature = hmac.new(
    config.RAZORPAY_KEY_SECRET.encode("utf-8"),
    payload_str.encode("utf-8"),
    hashlib.sha256
).hexdigest()

verify_payload = {
    "buyer_agent_id": BUYER_AGENT_ID,
    "shopper_email": PATRON_EMAIL,
    "order_id": checkout_data["order_id"],
    "razorpay_order_id": rzp_order_id,
    "razorpay_payment_id": simulated_payment_id,
    "razorpay_signature": signature,
    "items": cart_items,
    "total_inr": checkout_data["final_payable_inr"],
    "coupon_code": "AURA20",
    "discount_inr": quote_data["discount_inr"]
}
res_verify = client.post("/protocol/v1/order/verify", json=verify_payload)
verify_data = res_verify.json()

print("Settlement Confirmation:")
print(f" • Status: {verify_data['status']}")
print(f" • Confirmed Order ID: {verify_data['order_id']}")
print(f" • Razorpay Payment ID: {verify_data['payment_id']}")
print(f" • Settled Amount: ₹{verify_data['amount_settled_inr']:,} INR")
print(f" • Audit Ledger: {verify_data['protocol_receipt']['ledger']}")

print("\n" + "=" * 70)
print("6. VERIFYING TELEMETRY STREAM IN ADMIN LEDGER")
print("=" * 70)
res_telem = client.get("/protocol/v1/telemetry")
print(json.dumps(res_telem.json(), indent=2))
