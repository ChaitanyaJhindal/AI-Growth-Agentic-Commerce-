import hmac
import hashlib
import secrets
from typing import Dict, Any, Optional
import razorpay
from src import config

def get_razorpay_client() -> razorpay.Client:
    """Initializes and returns the Razorpay client using environment credentials."""
    key_id = config.RAZORPAY_KEY_ID
    key_secret = config.RAZORPAY_KEY_SECRET
    if not key_id or not key_secret:
        raise ValueError("RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET is missing. Please configure .env")
    return razorpay.Client(auth=(key_id, key_secret))

def create_razorpay_order(
    amount_in_paise: int,
    currency: str = "INR",
    receipt: Optional[str] = None,
    notes: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Creates a new order on Razorpay API.
    Amount must be specified in the smallest currency sub-unit (e.g., paise for INR).
    Minimum amount is 100 paise (1 INR).
    """
    if amount_in_paise < 100:
        raise ValueError("Amount must be at least 100 paise (1.00 INR)")

    client = get_razorpay_client()
    receipt_id = receipt or f"rcpt_{secrets.token_hex(4)}"

    data = {
        "amount": amount_in_paise,
        "currency": currency.upper(),
        "receipt": receipt_id,
        "notes": notes or {}
    }

    order = client.order.create(data=data)
    return {
        "order_id": order.get("id"),
        "amount": order.get("amount"),
        "currency": order.get("currency"),
        "receipt": order.get("receipt")
    }

def verify_razorpay_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
) -> bool:
    """
    Verifies Razorpay payment signature using HMAC-SHA256.
    Algorithm: HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET).
    Returns True only if signatures match.
    """
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return False

    key_secret = config.RAZORPAY_KEY_SECRET
    if not key_secret:
        return False

    try:
        # 1. Native HMAC-SHA256 signature verification
        payload = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
        generated_signature = hmac.new(
            key_secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        return secrets.compare_digest(generated_signature, razorpay_signature)
    except Exception:
        return False
