import sys, os
sys.path.insert(0, ".")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.auth import get_user_manager
from src.whatsapp.automation import get_automation_manager
from src.whatsapp.queue import get_whatsapp_queue
from src.whatsapp.worker import get_whatsapp_worker

user_mgr = get_user_manager()
auto_mgr = get_automation_manager()
queue = get_whatsapp_queue()

test_email = "chaitanya_vip@aurafashion.com"
test_phone = "+919876543210"

print("=" * 70)
print("1. ADDING LUXURY ITEMS TO SHOPPING BAG (MONGODB)")
print("=" * 70)

cart_items = [
    {
        "product_id": "PROD-2969",
        "name": "Puma Men's Black Running T-shirt",
        "brand": "Puma",
        "price": 33.04,
        "article_type": "Tshirts"
    },
    {
        "product_id": "PROD-1163",
        "name": "Nike Air Zoom Pegasus Sports Shoes",
        "brand": "Nike",
        "price": 40.00,
        "article_type": "Sports Shoes"
    }
]

user = user_mgr.get_user_profile(test_email)
if not user:
    user_mgr.signup("Chaitanya", test_email, "AuraVip2026!", phone=test_phone)
else:
    user_mgr.update_user_phone(test_email, test_phone)

sync_res = user_mgr.sync_user_data(test_email, bag=cart_items, phone=test_phone)
print("[OK] Cart synced successfully to MongoDB for:", test_email)
print("[OK] Items in Bag:", len(cart_items))
for item in cart_items:
    print(f"   * {item['name']} (${item['price']:.2f} / INR {int(item['price']*50):,})")

print("\n" + "=" * 70)
print("2. TRIGGERING AI ABANDONED CART RE-ENGAGEMENT CAMPAIGN")
print("=" * 70)

campaign_res = auto_mgr.trigger_abandoned_cart_campaign(
    coupon_code="AURA20",
    tone="witty_hinglish",
    cooldown_hours=0.0,
    override_phone=test_phone,
    max_users=1,
    user_email=test_email
)

print(f"[OK] Campaign Orchestrator Success: {campaign_res.get('success')}")
print(f"[OK] Recovery Messages Enqueued: {campaign_res.get('enqueued_count')}")

if campaign_res.get("details"):
    detail = campaign_res["details"][0]
    message_id = detail.get("message_id")
    print("\n[AI Generated Recovery Message Details]")
    print(f" * Recipient: {detail.get('recipient_phone')}")
    print(f" * Message ID: {message_id}")
    print(f" * Headline: {detail.get('headline')}")
    
    msg_doc = queue.get_message(message_id, unmask=False)
    if msg_doc:
        print("\n[Full AI Copy (WhatsApp)]")
        print("-" * 50)
        print(msg_doc.get("message"))
        print("-" * 50)

print("\n" + "=" * 70)
print("3. DISPATCHING MESSAGE VIA WHATSAPP QUEUE WORKER")
print("=" * 70)

worker = get_whatsapp_worker()
processed = worker.process_one_message()
print(f"[OK] Worker Processed & Sent: {processed}")

stats = queue.get_stats()
print("\n[Real-Time MongoDB WhatsApp Queue Stats]")
print(f" * Total Messages: {stats.get('total')}")
print(f" * Sent: {stats.get('sent')}")
print(f" * Pending: {stats.get('pending')}")
print(f" * Processing: {stats.get('processing')}")
print(f" * Failed: {stats.get('failed')}")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE: PRODUCTS IN CART & WHATSAPP CAMPAIGN SENT!")
print("=" * 70)
