import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agents.campaign_agent import get_campaign_agent

def run_campaign_tests():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 80)
    print("  TESTING AI CAMPAIGN & PROMOTIONAL RE-ENGAGEMENT AGENT (openai/gpt-oss-20b)")
    print("=" * 80)

    agent = get_campaign_agent()
    print(f"\n1. Initialized Campaign Agent with model: {agent.model}")

    sample_bag = [
        {"name": "Puma Nitro Carbon White Running Shoes", "article_type": "Sports Shoes", "price": 85.0},
        {"name": "Nike Tech Fleece Black Track Pants", "article_type": "Track Pants", "price": 60.0}
    ]

    # Test 1: WhatsApp Witty Hinglish Promotional Message
    print("\n2. Testing WhatsApp Witty Hinglish Promotional Copy for 'Rahul'...")
    res_whatsapp = agent.generate_message(
        customer_name="Rahul",
        bag_items=sample_bag,
        channel="whatsapp",
        discount_code="AURA20",
        tone="witty_hinglish"
    )
    assert res_whatsapp.get("success"), "WhatsApp campaign generation failed"
    print(f"✓ Headline: {res_whatsapp.get('headline')}")
    print(f"✓ Body Copy:\n   \"{res_whatsapp.get('message')}\"")
    print(f"✓ Call To Action: {res_whatsapp.get('call_to_action')}")

    # Test 2: Push Notification Copy for 'Priya'
    print("\n3. Testing Push Notification Copy for 'Priya'...")
    sample_bag_2 = [
        {"name": "Turtle Check Navy Blue Linen Shirt", "article_type": "Shirts", "price": 52.0}
    ]
    res_push = agent.generate_message(
        customer_name="Priya",
        bag_items=sample_bag_2,
        channel="push",
        discount_code="STYLE15",
        tone="playful_urgency"
    )
    assert res_push.get("success"), "Push notification generation failed"
    print(f"✓ Push Title: {res_push.get('headline')}")
    print(f"✓ Push Body: \"{res_push.get('message')}\"")

    # Test 3: Multiple Creative A/B Variations
    print("\n4. Testing A/B Campaign Variations...")
    variations = agent.generate_campaign_variations(
        customer_name="Aryan",
        bag_items=sample_bag,
        count=3,
        discount_code="DROP25"
    )
    assert len(variations) == 3, f"Expected 3 variations, got {len(variations)}"
    for idx, var in enumerate(variations, 1):
        print(f"   [Variant {idx} ({var.get('channel')})] {var.get('headline')} -> \"{var.get('message')[:75]}...\"")

    print("\n" + "=" * 80)
    print("🎉 ALL AI CAMPAIGN AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_campaign_tests()
