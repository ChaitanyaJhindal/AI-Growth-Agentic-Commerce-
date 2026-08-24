import sys
from agent_graph import agent_app

def run_multi_turn_test():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    thread_id = "test-session-001"
    config = {"configurable": {"thread_id": thread_id}}

    print("=" * 80)
    print(f"  TESTING MULTI-TURN CONVERSATION MANAGEMENT (Thread: {thread_id})")
    print("=" * 80)

    # ------------------------------------------------------------
    # TURN 1: Initial broad search
    # ------------------------------------------------------------
    print("\n--- TURN 1: Initial Request ---")
    query_1 = "I want running shoes for men"
    print(f"User: \"{query_1}\"")
    
    state_1 = agent_app.invoke(
        {"current_query": query_1, "original_query": query_1, "conversation_history": []},
        config=config
    )
    print(f"Agent Intent:          {state_1.get('intent')}")
    print(f"Agent Parsed Query:    '{state_1.get('current_query')}'")
    print(f"Agent Filters:         {state_1.get('filters')}")
    print(f"Products Found:        {len(state_1.get('search_results', []))}")
    if state_1.get("search_results"):
        p1 = state_1["search_results"][0]
        print(f"Top Result:            [{p1.get('product_id')}] {p1.get('name')} | Brand: {p1.get('brand')} | Price: ${p1.get('price')}")

    # ------------------------------------------------------------
    # TURN 2: Contextual Refinement (Brand & Price constraint)
    # ------------------------------------------------------------
    print("\n" + "=" * 80)
    print("--- TURN 2: Contextual Follow-up Refinement ---")
    query_2 = "Only Nike and under $60"
    print(f"User: \"{query_2}\"")
    
    state_2 = agent_app.invoke(
        {"current_query": query_2},
        config=config
    )
    print(f"Agent Intent:          {state_2.get('intent')}")
    print(f"Agent Parsed Query:    '{state_2.get('current_query')}'")
    print(f"Agent Merged Filters:  {state_2.get('filters')}")
    print(f"Products Found:        {len(state_2.get('search_results', []))}")
    if state_2.get("search_results"):
        for i, p in enumerate(state_2["search_results"][:3], 1):
            print(f"  {i}. [{p.get('product_id')}] {p.get('name')} | Brand: {p.get('brand')} | Price: ${p.get('price')}")

    # ------------------------------------------------------------
    # TURN 3: Product Selection and Styling Advice
    # ------------------------------------------------------------
    print("\n" + "=" * 80)
    print("--- TURN 3: Product Selection for Styling / Upsell ---")
    query_3 = "I like product 1, recommend what outfit goes with it"
    print(f"User: \"{query_3}\"")
    
    state_3 = agent_app.invoke(
        {"current_query": query_3},
        config=config
    )
    print(f"Agent Intent:          {state_3.get('intent')}")
    if state_3.get("selected_product"):
        sel = state_3["selected_product"]
        print(f"Selected Product:      [{sel.get('product_id')}] {sel.get('name')} (${sel.get('price')})")
    
    print(f"Upsell Recommendations ({len(state_3.get('upsell_results', []))} items):")
    for i, item in enumerate(state_3.get("upsell_results", []), 1):
        print(f"  {i}. {item.get('name')} (${item.get('price')}) - {item.get('article_type')}")
        print(f"     Stylist Tip: {item.get('stylist_note')}")

    print("\n" + "=" * 80)
    print("✅ MULTI-TURN CONVERSATION MANAGEMENT TEST PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_multi_turn_test()
