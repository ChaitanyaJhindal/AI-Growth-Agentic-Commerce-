"""
AURA Autonomous AI Buyer Simulation Agent (A2A Commerce)
Demonstrates end-to-end Machine-to-Machine commerce:
1. Manifest Discovery (AP2 / MCP)
2. Agent-Readable Catalog Search
3. Automated Quote Negotiation (with voucher AURA20)
4. Strict Spending Gating Violation & Recovery
5. Programmatic Order Execution & Cryptographic Verification
"""
import sys
import os
import json
import hmac
import hashlib
import time
import urllib.request
import urllib.error

# Ensure root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src import config

API_BASE = "http://127.0.0.1:8000"
BUYER_AGENT_ID = "Agent_Executive_Shopper_007"
SHOPPER_EMAIL = "patron_aarav@aurafashion.com"

def log_step(step_num: int, title: str):
    print("\n" + "=" * 70)
    print(f"  [STEP {step_num}] {title}")
    print("=" * 70)

def post_json(endpoint: str, payload: dict) -> dict:
    url = f"{API_BASE}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode("utf-8"))

def get_json(endpoint: str) -> dict:
    url = f"{API_BASE}{endpoint}"
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode("utf-8"))

def run_ai_buyer_simulation():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("🤖 STARTING AUTONOMOUS AI BUYER AGENT SIMULATION")
    print(f"• Calling Agent ID: {BUYER_AGENT_ID}")
    print(f"• Beneficiary Patron: {SHOPPER_EMAIL}")
    print(f"• Merchant Protocol Target: {API_BASE}")

    # -------------------------------------------------------------
    # 1. DISCOVERY & CAPABILITIES
    # -------------------------------------------------------------
    log_step(1, "DISCOVERING MERCHANT AP2 / MCP PROTOCOL MANIFEST")
    try:
        manifest = get_json("/.well-known/agent-protocol.json")
        print("✓ Merchant Discovered:", manifest.get("merchant_name"))
        print(f"✓ Protocol Version: {manifest.get('protocol_version')}")
        print(f"✓ Currency: {manifest.get('currency')} (1 USD = {manifest.get('usd_to_inr_rate')} INR)")
        print(f"✓ Supported Capabilities: {', '.join(manifest.get('capabilities', []))}")
    except Exception as e:
        print(f"Error fetching manifest: {e}. Ensure local server is running.")
        return

    # -------------------------------------------------------------
    # 2. AGENTIC SEMANTIC CATALOG SEARCH
    # -------------------------------------------------------------
    log_step(2, "AI BUYER QUERIES CATALOG: 'men running shoes under ₹3000'")
    query_payload = {
        "query": "men running shoes",
        "gender": "Men",
        "max_budget_inr": 3000.0,
        "limit": 3
    }
    search_res = post_json("/protocol/v1/catalog/query", query_payload)
    products = search_res.get("products", [])
    print(f"✓ Retrieved {len(products)} machine-readable candidate pieces:")
    
    selected_items = []
    for idx, p in enumerate(products, 1):
        print(f"   [{idx}] {p['name']} ({p['brand']}) - ₹{p['price_inr']:,} INR (Status: {p['stock_status']})")
        if idx <= 2:
            selected_items.append({
                "product_id": p["product_id"],
                "name": p["name"],
                "price_inr": p["price_inr"],
                "brand": p.get("brand"),
                "article_type": p.get("article_type"),
                "image_url": p.get("image_url")
            })

    if not selected_items:
        print("No items selected. Simulation terminating.")
        return

    # -------------------------------------------------------------
    # 3. EXPLAINABLE QUOTE & VOUCHER NEGOTIATION
    # -------------------------------------------------------------
    log_step(3, "NEGOTIATING EXPLAINABLE QUOTE WITH PROMO VOUCHER 'AURA20'")
    quote_payload = {
        "buyer_agent_id": BUYER_AGENT_ID,
        "items": selected_items,
        "coupon_code": "AURA20"
    }
    quote_res = post_json("/protocol/v1/quote", quote_payload)
    subtotal = quote_res["subtotal_inr"]
    discount = quote_res["discount_inr"]
    final_payable = quote_res["final_payable_inr"]
    print(f"✓ Subtotal: ₹{subtotal:,.0f} INR")
    print(f"✓ Voucher Applied: {quote_res['applied_promo']['code']} (-{quote_res['applied_promo']['discount_percent']}%, Savings: ₹{discount:,.0f} INR)")
    print(f"✓ Guaranteed Final Payable: ₹{final_payable:,.0f} INR")
    print(f"✓ Merchant Explainability String:\n   \"{quote_res['explainability']}\"")

    # -------------------------------------------------------------
    # 4. TESTING THE BAR: SPENDING GATING VIOLATION & RECOVERY
    # -------------------------------------------------------------
    log_step(4, "THE BAR: TESTING BUDGET GATING VIOLATION (FAILURE HANDLED GRACEFULLY)")
    print(f"• Actual Order Total is: ₹{final_payable:,.0f} INR")
    print("• Simulating Buyer attempting checkout with insufficient budget cap: ₹500.00 INR...")

    bad_checkout_payload = {
        "buyer_agent_id": BUYER_AGENT_ID,
        "shopper_email": SHOPPER_EMAIL,
        "items": selected_items,
        "coupon_code": "AURA20",
        "max_authorized_budget_inr": 500.0 # Strict Violation!
    }

    try:
        url = f"{API_BASE}/protocol/v1/order/checkout"
        data = json.dumps(bad_checkout_payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as res:
            print("❌ Unexpected: Order passed when it should have been gated!")
    except urllib.error.HTTPError as err:
        error_data = json.loads(err.read().decode("utf-8"))
        print(f"✓ [GATING SUCCESS] Merchant Gate Rejected Request (HTTP {err.code}):")
        print(f"   Error Code: {error_data['detail']['error_code']}")
        print(f"   Reason: {error_data['detail']['message']}")
        print(f"   Gating Status: {error_data['detail']['gating_status']}")

    # -------------------------------------------------------------
    # 5. EXECUTING BOUNDED & GATED CHECKOUT (WITHIN LIMITS)
    # -------------------------------------------------------------
    log_step(5, "EXECUTING BOUNDED & GATED CHECKOUT (AUTHORIZED LIMIT ₹4,000 INR)")
    valid_checkout_payload = {
        "buyer_agent_id": BUYER_AGENT_ID,
        "shopper_email": SHOPPER_EMAIL,
        "items": selected_items,
        "coupon_code": "AURA20",
        "max_authorized_budget_inr": 4000.0 # Valid limit!
    }
    order_res = post_json("/protocol/v1/order/checkout", valid_checkout_payload)
    order_id = order_res["order_id"]
    rzp_order_id = order_res["razorpay_order_id"]
    print(f"✓ Status: {order_res['status']}")
    print(f"✓ Order Reference: {order_id}")
    print(f"✓ Razorpay Order ID: {rzp_order_id}")
    print(f"✓ Amount in Paise: {order_res['amount_in_paise']} paise (₹{order_res['final_payable_inr']} INR)")
    print(f"✓ Gating Proof: {order_res['gating_proof']['budget_compliance']} (Authorized limit: ₹{order_res['gating_proof']['authorized_ceiling_inr']:,.0f})")

    # -------------------------------------------------------------
    # 6. PROGRAMMATIC PAYMENT SIGNATURE & VERIFICATION
    # -------------------------------------------------------------
    log_step(6, "SIMULATING CRYPTOGRAPHIC RAZORPAY TEST PAYMENT SETTLEMENT")
    simulated_payment_id = f"pay_test_{secrets.token_hex(6)}"
    
    # Compute valid HMAC-SHA256 test signature using RAZORPAY_KEY_SECRET
    payload_str = f"{rzp_order_id}|{simulated_payment_id}"
    signature = hmac.new(
        config.RAZORPAY_KEY_SECRET.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    verify_payload = {
        "buyer_agent_id": BUYER_AGENT_ID,
        "shopper_email": SHOPPER_EMAIL,
        "order_id": order_id,
        "razorpay_order_id": rzp_order_id,
        "razorpay_payment_id": simulated_payment_id,
        "razorpay_signature": signature,
        "items": selected_items,
        "total_inr": final_payable,
        "coupon_code": "AURA20",
        "discount_inr": discount
    }

    verify_res = post_json("/protocol/v1/order/verify", verify_payload)
    print(f"✓ Transaction Status: {verify_res['status']}")
    print(f"✓ Settlement ID: {verify_res['payment_id']}")
    print(f"✓ Settled Amount: ₹{verify_res['amount_settled_inr']:,.0f} INR")
    print(f"✓ Cryptographic Protocol Receipt:")
    print(f"   * Signature Verified: {verify_res['protocol_receipt']['signature_verified']}")
    print(f"   * Algorithm: {verify_res['protocol_receipt']['algorithm']}")
    print(f"   * Audit Ledger: {verify_res['protocol_receipt']['ledger']}")

    # -------------------------------------------------------------
    # 7. A2A TELEMETRY VERIFICATION
    # -------------------------------------------------------------
    log_step(7, "FETCHING A2A MERCHANT TELEMETRY")
    telemetry = get_json("/protocol/v1/telemetry")
    print(f"✓ Total Autonomous A2A Orders: {telemetry.get('total_a2a_orders')}")
    print(f"✓ Total A2A Volume: ₹{telemetry.get('total_a2a_gmv_inr', 0):,.0f} INR")
    print(f"✓ Active AI Buyers: {', '.join(telemetry.get('active_ai_buyers', []))}")

    print("\n" + "=" * 70)
    print("🎉 AI BUYER AGENT-TO-AGENT COMMERCE SIMULATION COMPLETE & VERIFIED!")
    print("=" * 70)

if __name__ == "__main__":
    run_ai_buyer_simulation()
