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

    prompt = f"""You are an Expert Conversational E-Commerce Fashion & Budget Parser for a luxury atelier.
Analyze the user's latest message in light of the ongoing conversation history and extract precise semantic search criteria, metadata filters, and budget constraints.

{dialogue_context}
{results_context}
Active Filters from Previous Turn: {prev_filters}

Latest User Message: "{user_query}"

Catalog Knowledge & Taxonomies:
- Master Categories: Apparel, Footwear, Accessories, Personal Care
- Genders: Men, Women, Unisex, Boys, Girls
- Articles: Tshirts, Shirts, Jeans, Casual Shoes, Sports Shoes, Watches, Handbags, Wallets, Belts, Sunglasses, Track Pants, Jackets, Kurtas, Tops, Heels, Flats, Sandals, Flip Flops, Socks, etc.
- Colors: Black, Blue, Navy Blue, White, Grey, Red, Green, Silver, Gold, Brown, Beige, Olive, Charcoal, etc.

Critical Parsing & Reasoning Guidelines:
1. **Intent Determination**:
   - Set intent = 'search' if user initiates a new search or product category inquiry.
   - Set intent = 'filter_refinement' if user modifies/filters previous results (e.g. "under $50", "show only blue", "in Nike", "cheaper ones").
   - Set intent = 'select_product' if user selects or asks about a specific item (e.g. "I like the 2nd one", "style product #1").
2. **Budget & Money Filter Extraction ($1 USD = ₹50 INR Conversion)**:
   - Catalog baseline data is indexed where $1 USD = ₹50 INR (e.g. $40 = ₹2,000 INR; $20 = ₹1,000 INR; $100 = ₹5,000 INR).
   - If the user provides an amount in Indian Rupees / INR / ₹ / Rs (e.g. "under ₹2000", "below 1500 rs", "budget 2500 inr", "max 1000 rupees"), DIVIDE by 50 to extract the filter in catalog units (e.g. ₹2000 / 50 = 40.0; ₹1500 / 50 = 30.0; ₹1000 / 50 = 20.0; ₹5000 / 50 = 100.0).
   - If the user specifies a plain number > 150 (e.g. "under 2000", "below 1500", "between 1000 and 3000"), interpret it as INR and divide by 50 (e.g. 2000 -> 40.0).
   - If the user specifies a dollar sign (e.g. "under $50", "below $40"), use the direct number (e.g. 50.0, 40.0).
   - Extract `max_price` for ceilings ("under ₹2000", "below 1500"), `min_price` for floors ("above ₹4000"), and both for ranges ("between ₹1500 and ₹3000").
3. **Cleaned Search Query Formulation**:
   - `cleaned_query` must contain the core fashion attributes, style, brand, gender, and category WITHOUT the explicit price numbers (e.g. for "puma running shoes under $50", output cleaned_query: "puma running shoes").
   - For filter refinements on existing context (e.g. user previously searched for watches and now says "under $100"), preserve the subject: "watches".
4. **Brand & Gender Precision**:
   - Extract explicit brand (Nike, Puma, Titan, Tommy Hilfiger, Peter England, Fossil, Fastrack, etc.).
   - Extract explicit gender (Men, Women, Unisex, Boys, Girls).
"""
    llm = get_llm(temperature=0.1, agent_name="query")
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
