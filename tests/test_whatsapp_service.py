import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.whatsapp.queue import (
    WhatsAppQueue,
    get_whatsapp_queue,
    validate_e164_phone,
    mask_phone_number
)
from src.whatsapp.worker import WhatsAppWorker
from src.whatsapp.baileys_client import BaileysClient
from src.agents.campaign_agent import get_campaign_agent

def run_whatsapp_tests():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 80)
    print("  TESTING LIGHTWEIGHT WHATSAPP MESSAGE QUEUE & BAILEYS WORKER")
    print("=" * 80)

    # 1. Test Phone Validation & Masking
    print("\n1. Testing E.164 Phone Number Validation & Masking...")
    valid_india = validate_e164_phone("+91 98765 43210")
    assert valid_india == "+919876543210", f"Unexpected phone: {valid_india}"
    
    valid_us = validate_e164_phone("+1 (415) 555-2671")
    assert valid_us == "+14155552671", f"Unexpected phone: {valid_us}"

    masked = mask_phone_number("+919876543210")
    assert masked == "+9198****3210", f"Unexpected masked output: {masked}"
    print(f"✓ Validated +91 98765 43210 -> {valid_india}")
    print(f"✓ Masked phone privacy -> {masked}")

    # Test invalid phones raise ValueError
    try:
        validate_e164_phone("9876543210") # missing '+'
        assert False, "Should have failed missing '+'"
    except ValueError:
        print("✓ Successfully rejected invalid phone without '+' prefix.")

    # 2. Test MongoDB Queue Enqueue & Retrieval
    print("\n2. Testing MongoDB Queue Enqueue & Atomic Claiming...")
    queue = get_whatsapp_queue()
    # Clean previous test docs for isolation
    queue.collection.delete_many({"recipient_phone": {"$in": ["+919876543210", "+919988776655"]}})

    test_phone = "+919876543210"
    test_msg = "Hey Rahul, your luxury Puma sneakers are waiting in your bag! Use code AURA20."

    enq_res = queue.enqueue(
        recipient_phone=test_phone,
        message=test_msg,
        metadata={"test": True, "customer": "Rahul"}
    )
    assert enq_res.get("success"), "Failed to enqueue message"
    message_id = enq_res.get("message_id")
    assert message_id, "Missing message_id"
    print(f"✓ Enqueued message: {message_id} (Status: {enq_res.get('status')}, Masked: {enq_res.get('recipient_phone')})")

    # Read back message
    fetched = queue.get_message(message_id)
    assert fetched and fetched.get("status") == "pending", "Message status is not pending"
    print(f"✓ Retrieved message by ID: Status = {fetched.get('status')}")

    # 3. Test Atomic Claiming
    print("\n3. Testing Atomic Claiming (`pending` -> `processing`)...")
    claimed = queue.claim_next_pending(stale_timeout_seconds=300)
    assert claimed is not None, "Failed to claim pending message"
    claimed_id = claimed.get("message_id")
    assert claimed.get("status") == "processing", f"Expected processing status, got {claimed.get('status')}"
    print(f"✓ Atomically claimed message {claimed_id} (New Status: {claimed.get('status')})")

    # 4. Test Error Handling & Retry Backoff
    print("\n4. Testing Retry Mechanism & Max Attempts...")
    retry_res = queue.mark_failed_or_retry(claimed_id, error_msg="Temporary network timeout")
    assert retry_res.get("status") == "pending", f"Expected pending, got {retry_res.get('status')}"
    assert retry_res.get("attempts") >= 1, "Expected attempts to increment"
    print(f"✓ Failed attempt recorded: {retry_res.get('attempts')}/{retry_res.get('max_attempts')} (Status: {retry_res.get('status')})")

    # Re-claim and mark sent
    claimed_again = queue.claim_next_pending(stale_timeout_seconds=300)
    assert claimed_again is not None, "Failed to reclaim for retry"
    marked_sent = queue.mark_sent(claimed_again.get("message_id"), provider_meta={"provider": "baileys_test"})
    assert marked_sent, "Failed to mark sent"

    final_doc = queue.get_message(claimed_again.get("message_id"))
    assert final_doc.get("status") == "sent", "Final status should be sent"
    assert final_doc.get("sent_at") is not None, "sent_at timestamp should be present"
    print(f"✓ Successfully transitioned to status 'sent' with sent_at timestamp: {final_doc.get('sent_at')}")

    # 5. Test Campaign Agent -> WhatsApp Queue Integration
    print("\n5. Testing Campaign Agent Integration with WhatsApp Queue...")
    campaign_agent = get_campaign_agent()
    sample_bag = [
        {"name": "Puma Nitro Carbon White Running Shoes", "article_type": "Sports Shoes", "price": 85.0}
    ]
    campaign_copy = campaign_agent.generate_message(
        customer_name="Aarav",
        bag_items=sample_bag,
        channel="whatsapp",
        discount_code="AURA25",
        tone="witty_hinglish"
    )
    print(f"✓ Generated Campaign Headline: \"{campaign_copy.get('headline')}\"")

    campaign_enq = queue.enqueue(
        recipient_phone="+919988776655",
        message=campaign_copy.get("message"),
        metadata={
            "customer_name": "Aarav",
            "campaign_headline": campaign_copy.get("headline"),
            "discount_code": "AURA25"
        }
    )
    assert campaign_enq.get("success"), "Failed to enqueue campaign copy"
    print(f"✓ Campaign message enqueued: {campaign_enq.get('message_id')} for {campaign_enq.get('recipient_phone')}")

    # 6. Test Worker Process Execution
    print("\n6. Testing Lightweight Worker Execution in Dry-Run Mode...")
    os.environ["WHATSAPP_DRY_RUN"] = "true"
    worker = WhatsAppWorker(queue=queue, client=BaileysClient())
    processed = worker.process_one_message()
    assert processed, "Worker should process the enqueued campaign message"
    print("✓ Worker claimed and delivered message successfully.")

    # 7. Queue Realtime Stats
    stats = queue.get_stats()
    print(f"\n✓ Real-Time Queue Metrics: Pending={stats.get('pending')}, Processing={stats.get('processing')}, Sent={stats.get('sent')}, Failed={stats.get('failed')}")

    print("\n" + "=" * 80)
    print("🎉 ALL WHATSAPP QUEUE & BAILEYS WORKER TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_whatsapp_tests()
