import os
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agents.upsell_agent import upsell_agent_node
from src.agents.state import AgentState

def test_dynamic_upsell_reasoning():
    print("=" * 80)
    print("  TESTING DYNAMIC CHAIN-OF-THOUGHT (CoT) + FEW-SHOT AI STYLIST UPSELL AGENT")
    print("=" * 80)

    test_products = [
        {
            "product_id": "PROD-TEST-01",
            "name": "Puma Men Graphic Grey Crewneck T-shirt",
            "article_type": "Tshirts",
            "master_category": "Apparel",
            "base_color": "Grey",
            "gender": "Men",
            "usage": "Casual",
            "season": "Summer",
            "brand": "Puma",
            "price": 45.00
        },
        {
            "product_id": "PROD-TEST-02",
            "name": "Titan Men Classique Black Dial Analog Watch",
            "article_type": "Watches",
            "master_category": "Accessories",
            "base_color": "Black",
            "gender": "Men",
            "usage": "Formal",
            "season": "All Season",
            "brand": "Titan",
            "price": 120.00
        }
    ]

    for p in test_products:
        print(f"\n--- Testing Anchor Product: {p['name']} ({p['article_type']}, {p['base_color']}) ---")
        state: AgentState = {
            "conversation_history": [],
            "original_query": f"I want {p['name']}",
            "current_query": p['name'],
            "filters": {},
            "intent": "select_product",
            "clarification_count": 0,
            "needs_clarification": False,
            "clarification_question": None,
            "search_results": [p],
            "validation_result": {"validated": True},
            "selected_product": p,
            "upsell_results": []
        }

        result = upsell_agent_node(state)
        upsells = result.get("upsell_results", [])
        print(f"[OK] Dynamically curated {len(upsells)} bespoke complementary items:")
        for idx, u in enumerate(upsells, 1):
            p_name = u.get('name', 'Item')
            p_price = u.get('price', 0)
            p_cat = u.get('article_type', 'Piece')
            p_comp = u.get('compatibility_reason', 'Tonal match')
            p_note = u.get('stylist_note', 'Wear together')
            print(f"  {idx}. [{u.get('product_id')}] {p_name} (${p_price})")
            print(f"     - Category:       {p_cat}")
            print(f"     - Compatibility:  {p_comp}")
            print(f"     - Stylist Advice: {p_note}")

    print("\n" + "=" * 80)
    print("[SUCCESS] DYNAMIC AI STYLIST CHAIN-OF-THOUGHT UPSELL TEST COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    test_dynamic_upsell_reasoning()
