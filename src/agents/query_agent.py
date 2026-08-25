from typing import Dict, Any, List
from src.agents.state import AgentState, QueryAnalysis
from src.agents.base import get_llm, get_search_engine

def query_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Query Agent: Context-Aware Filter & Intent Parser
    Parses user input in context of conversation history.
    Identifies new searches vs. filter refinements and extracts criteria.
    """
    user_query = state.get("current_query") or state.get("original_query", "")
    history = state.get("conversation_history", [])
    prev_results = state.get("search_results", [])
    prev_filters = state.get("filters", {})

    dialogue_context = ""
    if history:
        formatted_turns = [f"{turn.get('role', 'user').capitalize()}: {turn.get('content', '')}" for turn in history[-4:]]
        dialogue_context = "\nRecent Conversation History:\n" + "\n".join(formatted_turns)

    results_context = ""
    if prev_results:
        summary_lines = [f"{i}. [{p.get('product_id')}] {p.get('name')} (${p.get('price')})" for i, p in enumerate(prev_results[:4], 1)]
        results_context = "\nPrevious Search Results Visible to User:\n" + "\n".join(summary_lines)

    prompt = f"""You are an Expert Conversational E-Commerce Fashion Parser.
Analyze the user's latest message in light of the ongoing conversation history.

{dialogue_context}
{results_context}
Active Filters from Previous Turn: {prev_filters}

Latest User Message: "{user_query}"

Catalog Knowledge:
- Master Categories: Apparel, Footwear, Accessories, Personal Care
- Genders: Men, Women, Unisex, Boys, Girls
- Articles: Tshirts, Shirts, Jeans, Casual Shoes, Sports Shoes, Watches, Bags, Track Pants, Jackets, Socks, etc.
- Colors: Black, Blue, Navy Blue, White, Grey, Red, Green, Silver, etc.

Critical Instructions:
1. Determine if this message is a **new_search** (user is searching for a new item/category) OR a **refinement** (user is modifying the existing search like "only blue", "under 50", "show in Nike").
2. Set intent = 'search' if it is a new search, or 'filter_refinement' if modifying the previous search.
3. If it is a new search, DO NOT carry over unrelated filters from the previous turn.
4. Output a standalone cleaned search query.
"""
    llm = get_llm()
    structured_llm = llm.with_structured_output(QueryAnalysis)
    try:
        analysis: QueryAnalysis = structured_llm.invoke(prompt)
    except Exception as e:
        print(f"Notice on query parsing: {e}")
        # Robust fallback analysis
        analysis = QueryAnalysis(
            intent="search",
            cleaned_query=user_query,
            in_stock_only=False
        )

    engine = get_search_engine()
    new_filters = engine.build_filter(
        brand=analysis.brand,
        gender=analysis.gender,
        master_category=analysis.product_category if analysis.product_category in ["Apparel", "Footwear", "Accessories", "Personal Care"] else None,
        article_type=analysis.product_category if analysis.product_category not in ["Apparel", "Footwear", "Accessories", "Personal Care"] else None,
        min_price=analysis.min_price,
        max_price=analysis.max_price,
        min_rating=analysis.min_rating,
        in_stock=analysis.in_stock_only
    )

    if analysis.intent in ["filter_refinement", "refinement"] and prev_filters:
        merged_filters = prev_filters.copy()
        merged_filters.update(new_filters)
    else:
        merged_filters = new_filters

    selected_prod = state.get("selected_product")
    if analysis.selected_product_index and prev_results:
        idx = analysis.selected_product_index - 1
        if 0 <= idx < len(prev_results):
            selected_prod = prev_results[idx]

    updated_history = list(history)
    updated_history.append({"role": "user", "content": user_query})

    return {
        "intent": analysis.intent,
        "current_query": analysis.cleaned_query or user_query,
        "filters": merged_filters,
        "selected_product": selected_prod,
        "conversation_history": updated_history
    }
