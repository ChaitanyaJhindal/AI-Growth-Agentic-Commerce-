import os
import sys
import hmac
import hashlib
import uuid

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import config
from src.payments import (
    get_razorpay_client,
    create_razorpay_order,
    verify_razorpay_signature
)
from src.auth import UserManager

def run_razorpay_tests():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 80)
    print("  RUNNING RAZORPAY STANDARD WEB CHECKOUT INTEGRATION TESTS")
    print("=" * 80)

    # 1. Test Client Authentication
    print("\n--- 1. Testing Razorpay Client Authentication ---")
    client = get_razorpay_client()
    assert client is not None, "Razorpay client failed to initialize"
    print(f"✓ Razorpay client initialized with Key ID: {config.RAZORPAY_KEY_ID}")

    # 2. Test Order Creation via Razorpay API
    print("\n--- 2. Testing Razorpay Order Creation API ---")
    test_amount_paise = 50000  # 500.00 INR
    order = create_razorpay_order(
        amount_in_paise=test_amount_paise,
        currency="INR",
        receipt=f"test_rcpt_{uuid.uuid4().hex[:6]}"
    )
    assert order.get("order_id") is not None, "Order ID missing in response"
    assert order.get("amount") == test_amount_paise, "Order amount mismatch"
    assert order.get("currency") == "INR", "Order currency mismatch"
    print(f"✓ Order created successfully on Razorpay:")
    print(f"  - Order ID: {order['order_id']}")
    print(f"  - Amount:   {order['amount']} paise ({order['amount']/100:.2f} {order['currency']})")

    # 2b. Test Minimum Amount Validation (< 100 paise)
    print("\nTesting minimum amount validation (< 100 paise)...")
    try:
        create_razorpay_order(amount_in_paise=50)
        assert False, "Should have raised ValueError for amount < 100 paise"
    except ValueError:
        print("✓ Minimum amount boundary (< 100 paise) correctly enforced.")

    # 3. Test HMAC-SHA256 Signature Verification
    print("\n--- 3. Testing Payment Signature Verification ---")
    test_order_id = order["order_id"]
    test_payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    
    # Compute valid signature using KEY_SECRET
    payload = f"{test_order_id}|{test_payment_id}".encode("utf-8")
    valid_signature = hmac.new(
        config.RAZORPAY_KEY_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Verify valid signature
    is_valid = verify_razorpay_signature(
        razorpay_order_id=test_order_id,
        razorpay_payment_id=test_payment_id,
        razorpay_signature=valid_signature
    )
    assert is_valid is True, "Valid signature verification failed"
    print("✓ Valid signature verified successfully.")

    # Verify tampered signature is rejected
    invalid_signature = "tampered_signature_hex_12345"
    is_invalid_rejected = not verify_razorpay_signature(
        razorpay_order_id=test_order_id,
        razorpay_payment_id=test_payment_id,
        razorpay_signature=invalid_signature
    )
    assert is_invalid_rejected is True, "Tampered signature should have been rejected"
    print("✓ Tampered signature correctly rejected.")

    # 4. Test MongoDB Order Record with Payment ID
    print("\n--- 4. Testing MongoDB Order Storage with Payment ID ---")
    user_mgr = UserManager()
    test_email = f"razorpay_user_{uuid.uuid4().hex[:6]}@example.com"
    user_mgr.signup(name="Razorpay Customer", email=test_email, password="TestPassword123")

    mock_items = [{"product_id": "PROD-999", "name": "Silk Blazer", "price": 500.00}]
    order_record = user_mgr.create_order(
        email=test_email,
        items=mock_items,
        total=500.00,
        payment_id=test_payment_id,
        razorpay_order_id=test_order_id,
        payment_status="Paid (Razorpay)"
    )
    assert order_record["success"] is True
    print(f"✓ Recorded paid order in MongoDB (Internal ID: {order_record['order_id']}, Payment ID: {order_record['payment_id']})")

    # Cleanup
    user_mgr.users_collection.delete_one({"email": test_email})
    user_mgr.db["orders"].delete_one({"order_id": order_record["order_id"]})
    print("✓ Cleaned up test database records.")

    print("\n" + "=" * 80)
    print("🎉 ALL RAZORPAY INTEGRATION & SIGNATURE VERIFICATION TESTS PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    run_razorpay_tests()
