import sys
import json
from agent_graph import agent_app
from agent_state import AgentState

def run_automated_agent_tests():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 80)
    print("  RUNNING AUTOMATED LANGGRAPH AGENT LAYER TESTS")
    print("=" * 80)

    # ---------------------------------------------------------
    # TEST 1: Specific Query (Direct Search + Validation + Upsell)
    # ---------------------------------------------------------
    print("\n--- TEST 1: Specific Query Flow ---")
    query_1 = "casual blue shirts for men under 60"
    state_1: AgentState = {
        "original_query": query_1,
        "current_query": query_1,
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

    result_1 = agent_app.invoke(state_1)
    print(f"Query:                 '{query_1}'")
    print(f"Extracted Intent:      {result_1.get('intent')}")
    print(f"Extracted Filters:     {result_1.get('filters')}")
    print(f"Needs Clarification:   {result_1.get('needs_clarification')}")
    print(f"Search Results Found:  {len(result_1.get('search_results', []))}")
    print(f"Validation Status:     {result_1.get('validation_result', {}).get('validated')}")
    print(f"Validation Notes:      {result_1.get('validation_result', {}).get('explanation')}")
    print(f"Upsell Items Created:  {len(result_1.get('upsell_results', []))}")
    if result_1.get("upsell_results"):
        top_upsell = result_1["upsell_results"][0]
        print(f"Sample Upsell Item:    {top_upsell.get('name')} (${top_upsell.get('price')})")
        print(f"Stylist Note:          {top_upsell.get('stylist_note')}")

    # ---------------------------------------------------------
    # TEST 2: Clarification Flow (Vague Query -> Context Follow-up -> Search)
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("--- TEST 2: Clarification Flow ---")
    vague_query = "I want sneakers"
    state_2: AgentState = {
        "original_query": vague_query,
        "current_query": vague_query,
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

    # Step 2a: First invoke with vague query
    step_2a = agent_app.invoke(state_2)
    print(f"Initial Vague Query:   '{vague_query}'")
    print(f"Needs Clarification:   {step_2a.get('needs_clarification')}")
    print(f"Clarification Question: \"{step_2a.get('clarification_question')}\"")
    print(f"Clarification Count:   {step_2a.get('clarification_count')}")

    # Step 2b: User answers the follow-up
    user_clarification = "Men's running sneakers under $80"
    print(f"\nUser Provides Answer:  \"{user_clarification}\"")
    step_2a["current_query"] = f"{vague_query} {user_clarification}"
    step_2a["needs_clarification"] = False
    step_2a["clarification_question"] = None

    # Step 2c: Resume LangGraph workflow
    step_2c = agent_app.invoke(step_2a)
    print(f"Resolved Search Term:  '{step_2c.get('current_query')}'")
    print(f"Resolved Filters:      {step_2c.get('filters')}")
    print(f"Search Results Found:  {len(step_2c.get('search_results', []))}")
    print(f"Validation Status:     {step_2c.get('validation_result', {}).get('validated')}")
    print(f"Upsell Items Created:  {len(step_2c.get('upsell_results', []))}")

    # ---------------------------------------------------------
    # TEST 3: Direct Selected Product Upsell
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("--- TEST 3: Selected Product Upsell Recommendation ---")
    mock_selected_product = {
        "product_id": "PROD-54796",
        "name": "Peter England Men Blue Jeans",
        "brand": "Peter England",
        "gender": "Men",
        "article_type": "Jeans",
        "base_color": "Blue",
        "season": "Summer",
        "usage": "Casual",
        "price": 56.37
    }

    state_3: AgentState = {
        "original_query": "blue jeans",
        "current_query": "blue jeans",
        "filters": {"gender": "Men"},
        "intent": "search",
        "clarification_count": 0,
        "needs_clarification": False,
        "clarification_question": None,
        "search_results": [mock_selected_product],
        "validation_result": {"validated": True, "retry_count": 0},
        "selected_product": mock_selected_product,
        "upsell_results": []
    }

    result_3 = agent_app.invoke(state_3)
    print(f"Selected Product:      {mock_selected_product['name']} (${mock_selected_product['price']})")
    print(f"Upsell Recommendations ({len(result_3.get('upsell_results', []))} items):")
    for i, item in enumerate(result_3.get("upsell_results", []), 1):
        print(f"  {i}. {item.get('name')} (${item.get('price')}) - {item.get('article_type')}")
        print(f"     Stylist Advice: {item.get('stylist_note')}")

    print("\n" + "=" * 80)
    print("🎉 ALL LANGGRAPH AGENT LAYER TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_automated_agent_tests()
