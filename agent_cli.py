import sys
import os
from tabulate import tabulate
from dotenv import load_dotenv

load_dotenv()

from agent_graph import agent_app
from agent_state import AgentState

def display_product_table(products: list, title: str = "Search Results"):
    if not products:
        print(f"\n[{title}] No products found.")
        return

    rows = []
    for i, p in enumerate(products, 1):
        pid = p.get("product_id", "N/A")
        name = p.get("name", "N/A")[:30]
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
    print("  AI Fashion Stylist Outfit Recommendations (Upsell & Cross-Sell)")
    print("=" * 80)

    for i, item in enumerate(upsell_items, 1):
        print(f"\n[Look #{i}] {item.get('name')} (${item.get('price', 0):.2f}) - {item.get('base_color')} {item.get('article_type')}")
        if item.get("compatibility_reason"):
            print(f"  * Compatibility: {item.get('compatibility_reason')}")
        if item.get("stylist_note"):
            print(f"  * Stylist Tip:   {item.get('stylist_note')}")


def run_interactive_session():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 80)
    print("  🛍️  LangGraph E-Commerce Fashion Agent System (Groq gpt-oss-120b)")
    print("=" * 80)

    state: AgentState = {
        "original_query": "",
        "current_query": "",
        "filters": {},
        "intent": "",
        "clarification_count": 0,
        "needs_clarification": False,
        "clarification_question": None,
        "search_results": [],
        "validation_result": {},
        "selected_product": None,
        "upsell_results": []
    }

    initial_query = input("\nEnter your shopping request (or 'exit' to quit): ").strip()
    if not initial_query or initial_query.lower() == "exit":
        return

    state["original_query"] = initial_query
    state["current_query"] = initial_query

    # Run LangGraph workflow loop
    while True:
        print("\n[LangGraph] Processing agent pipeline...")
        state = agent_app.invoke(state)

        # Check if Context Agent needs clarification from user
        if state.get("needs_clarification") and state.get("clarification_question"):
            print(f"\n🤖 Context Agent Follow-up:")
            print(f"   \"{state['clarification_question']}\"")
            user_reply = input("\nYour answer: ").strip()
            if not user_reply or user_reply.lower() == "exit":
                break

            # Append context and re-invoke
            state["current_query"] = f"{state['current_query']} {user_reply}"
            state["needs_clarification"] = False
            state["clarification_question"] = None
            continue
        else:
            break

    # Display final results
    print("\n" + "=" * 80)
    print("  FINAL AGENT PIPELINE RESULTS")
    print("=" * 80)
    print(f"Intent Extracted:   {state.get('intent')}")
    print(f"Parsed Search Term: '{state.get('current_query')}'")
    print(f"Active Filters:     {state.get('filters')}")
    
    val_res = state.get("validation_result", {})
    print(f"Validation Status:  {'PASSED' if val_res.get('validated') else 'RETRY LIMIT REACHED'}")
    if val_res.get("explanation"):
        print(f"Validation Notes:   {val_res.get('explanation')}")

    display_product_table(state.get("search_results", []), title="Validated Search Results")
    display_upsell_table(state.get("upsell_results", []))

if __name__ == "__main__":
    run_interactive_session()
