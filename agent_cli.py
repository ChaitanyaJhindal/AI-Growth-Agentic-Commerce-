import sys
import uuid
from tabulate import tabulate
from src.agents.workflow import agent_app

def display_product_table(products: list, title: str = "Search Results"):
    if not products:
        print(f"\n[{title}] No products found.")
        return

    rows = []
    for i, p in enumerate(products, 1):
        pid = p.get("product_id", "N/A")
        name = p.get("name", "N/A")[:32]
        brand = p.get("brand", "N/A")
        cat = f"{p.get('gender', '')} / {p.get('article_type', '')}"
        color = p.get("base_color", "N/A")
        price = f"${p.get('price', 0):.2f}"
        rating = f"{p.get('rating', 0):.1f} ({p.get('review_count', 0)})"
        rrf = p.get("rrf_score", "-")
        rows.append([i, pid, name, brand, cat, color, price, rating, rrf])

    headers = ["#", "ID", "Name", "Brand", "Gender/Type", "Color", "Price", "Rating", "RRF Score"]
    print(f"\n--- {title} ({len(products)} items) ---")
    print(tabulate(rows, headers=headers, tablefmt="grid"))


def display_upsell_table(upsell_items: list):
    if not upsell_items:
        return

    print("\n" + "=" * 80)
    print("  AI Fashion Stylist Outfit Pairings (Upsell & Cross-Sell)")
    print("=" * 80)

    for i, item in enumerate(upsell_items, 1):
        print(f"\n[Pairing #{i}] {item.get('name')} (${item.get('price', 0):.2f}) - {item.get('base_color')} {item.get('article_type')}")
        if item.get("compatibility_reason"):
            print(f"  * Style Match: {item.get('compatibility_reason')}")
        if item.get("stylist_note"):
            print(f"  * Stylist Tip: {item.get('stylist_note')}")


def run_interactive_session():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    session_id = str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": session_id}}

    print("=" * 80)
    print(f"  🛍️  LangGraph Multi-Turn Fashion Shopping Assistant [Session: {session_id}]")
    print("  (Type your request, refine with follow-ups, select items, or type 'exit')")
    print("=" * 80)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

        if not user_input or user_input.lower() == "exit":
            print("Thank you for shopping! Goodbye.")
            break

        print("\n[AI Agent] Thinking & searching...")

        state_input = {
            "current_query": user_input
        }

        # Run through LangGraph with persistent thread_id checkpointer
        state = agent_app.invoke(state_input, config=config)

        # Handle follow-up clarification if needed
        if state.get("needs_clarification") and state.get("clarification_question"):
            print(f"\n🤖 Context Agent:")
            print(f"   \"{state['clarification_question']}\"")
            continue

        # Display results of the turn
        print(f"\n[Turn Summary] Intent: {state.get('intent')} | Active Filters: {state.get('filters')}")
        val_res = state.get("validation_result", {})
        if val_res.get("explanation"):
            print(f"[Quality Check] {val_res.get('explanation')}")

        if state.get("selected_product"):
            sel = state['selected_product']
            print(f"\n⭐ Selected Product: [{sel.get('product_id')}] {sel.get('name')} (${sel.get('price')})")

        display_product_table(state.get("search_results", []), title="Matching Products")
        display_upsell_table(state.get("upsell_results", []))

if __name__ == "__main__":
    run_interactive_session()
