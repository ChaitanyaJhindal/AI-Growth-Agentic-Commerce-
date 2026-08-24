import os
from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq
from dotenv import load_dotenv

import config
from hybrid_search import ProductHybridSearchEngine
from agent_state import (
    AgentState,
    QueryAnalysis,
    ContextEvaluation,
    ValidationDecision,
    UpsellAnalysis
)

load_dotenv()

_groq_api_key = os.getenv("GROQ_API_KEY")
if not _groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable is missing. Please set it in .env")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.1,
    api_key=_groq_api_key
)

_search_engine = None

def get_search_engine() -> ProductHybridSearchEngine:
    global _search_engine
    if _search_engine is None:
        _search_engine = ProductHybridSearchEngine()
    return _search_engine


# =====================================================================
# 1. Query Agent (with Context-Aware Filter Management)
# =====================================================================

def query_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Parses user input using conversational history context.
    Properly resets filters on new searches while preserving them on refinements.
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
    structured_llm = llm.with_structured_output(QueryAnalysis)
    analysis: QueryAnalysis = structured_llm.invoke(prompt)

    # Build fresh filters for the current query
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

    # Clean filter management: Only merge previous filters if user is refining
    if analysis.intent in ["filter_refinement", "refinement"] and prev_filters:
        merged_filters = prev_filters.copy()
        merged_filters.update(new_filters)
    else:
        merged_filters = new_filters

    # Handle selected product if user picked an item
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


# =====================================================================
# 2. Context Agent
# =====================================================================

def context_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates whether enough information exists to execute a targeted search.
    If critically vague and clarification_count < 2, asks 1 concise question.
    """
    clarification_count = state.get("clarification_count", 0)
    current_query = state.get("current_query", "")
    filters = state.get("filters", {})

    if state.get("selected_product"):
        return {
            "needs_clarification": False,
            "clarification_question": None,
            "current_query": current_query,
            "filters": filters
        }

    if clarification_count >= 2:
        return {
            "needs_clarification": False,
            "clarification_question": None,
            "current_query": current_query,
            "filters": filters
        }

    prompt = f"""You are an E-Commerce Fashion Context Evaluator.
Determine if the shopping request has sufficient specificity to return relevant fashion products.

User Query: "{current_query}"
Current Filters: {filters}
Clarification Rounds So Far: {clarification_count}/2

Rules:
1. If the request has clear intent (e.g. "women running shoes", "casual blue shirt", "black watch"), set has_sufficient_context = True.
2. If the request is severely vague with zero specifics (e.g. just "I want clothes", "give me something"):
   - Set has_sufficient_context = False.
   - Generate exactly ONE concise follow-up question.
3. If the user mentions a category (e.g. "watch", "shoes", "jeans"), it IS sufficient to perform an initial search unless completely meaningless.
"""
    structured_llm = llm.with_structured_output(ContextEvaluation)
    eval_result: ContextEvaluation = structured_llm.invoke(prompt)

    updated_history = list(state.get("conversation_history", []))

    if not eval_result.has_sufficient_context and clarification_count < 2:
        if eval_result.clarification_question:
            updated_history.append({"role": "assistant", "content": eval_result.clarification_question})

        return {
            "needs_clarification": True,
            "clarification_question": eval_result.clarification_question,
            "clarification_count": clarification_count + 1,
            "conversation_history": updated_history
        }
    else:
        merged = filters.copy()
        if eval_result.inferred_filters:
            merged.update(eval_result.inferred_filters)

        return {
            "needs_clarification": False,
            "clarification_question": None,
            "current_query": eval_result.final_search_query or current_query,
            "filters": merged,
            "conversation_history": updated_history
        }


# =====================================================================
# 3. Search Node (Deterministic Tool / Node)
# =====================================================================

def search_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes hybrid search against MongoDB Atlas.
    Deterministic execution without LLM hallucination.
    """
    if state.get("selected_product") and state.get("intent") == "select_product":
        return {"search_results": state.get("search_results", [])}

    query = state.get("current_query") or state.get("original_query", "")
    filters = state.get("filters", {})

    engine = get_search_engine()
    results = engine.hybrid_search(
        query=query,
        filter_dict=filters,
        limit=15
    )

    return {
        "search_results": results
    }


# =====================================================================
# 4. Validation Agent
# =====================================================================

def validation_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Validates retrieved products against user criteria.
    If mismatched, rewrites query and retries (max 2 retries).
    """
    original_query = state.get("original_query", "")
    current_query = state.get("current_query", "")
    results = state.get("search_results", [])
    val_state = state.get("validation_result", {})
    retry_count = val_state.get("retry_count", 0)

    if not results:
        if retry_count < 2:
            return {
                "validation_result": {
                    "validated": False,
                    "explanation": "No products found matching filters, relaxing constraints.",
                    "retry_count": retry_count + 1
                },
                "current_query": original_query,
                "filters": {}
            }
        else:
            return {
                "validation_result": {
                    "validated": True,
                    "explanation": "Search complete with available matches.",
                    "retry_count": retry_count
                }
            }

    product_summaries = []
    for p in results[:4]:
        product_summaries.append(
            f"- [{p.get('product_id')}] {p.get('name')} | Brand: {p.get('brand')} | Gender: {p.get('gender')} | "
            f"Type: {p.get('article_type')} | Price: ${p.get('price')}"
        )
    catalog_snippet = "\n".join(product_summaries)

    prompt = f"""You are an E-Commerce Product Quality Validator.
Verify if the retrieved products satisfy the user's request.

Original Request: "{original_query}"
Current Search Term: "{current_query}"
Top Products:
{catalog_snippet}

Tasks:
1. If products are relevant to the request, set validated = True.
2. If completely unrelated, set validated = False and rewrite query.
"""
    structured_llm = llm.with_structured_output(ValidationDecision)
    decision: ValidationDecision = structured_llm.invoke(prompt)

    if decision.validated or retry_count >= 2:
        return {
            "validation_result": {
                "validated": True,
                "explanation": decision.explanation,
                "retry_count": retry_count
            }
        }
    else:
        return {
            "validation_result": {
                "validated": False,
                "explanation": decision.explanation,
                "retry_count": retry_count + 1
            },
            "current_query": decision.rewritten_query or original_query,
            "filters": {}
        }


# =====================================================================
# 5. Upsell Agent
# =====================================================================

COMPLEMENTARY_MAP = {
    "Casual Shoes": ["Socks", "Track Pants", "Jeans", "Tshirts"],
    "Sports Shoes": ["Socks", "Track Pants", "Tshirts", "Shorts"],
    "Shirts": ["Trousers", "Jeans", "Watches", "Belts"],
    "Tshirts": ["Jeans", "Track Pants", "Casual Shoes", "Sunglasses"],
    "Jeans": ["Tshirts", "Shirts", "Belts", "Casual Shoes"],
    "Watches": ["Shirts", "Wallets", "Belts", "Trousers"],
    "Dresses": ["Handbags", "Watches", "Accessories", "Heels"],
    "Jackets": ["Jeans", "Tshirts", "Mufflers", "Casual Shoes"]
}

def upsell_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Recommends stylish complementary products for selected or top item.
    Retrieves candidates via hybrid search and uses LLM to rank outfit pairings.
    """
    selected = state.get("selected_product")
    if not selected:
        results = state.get("search_results", [])
        selected = results[0] if results else None

    if not selected:
        return {"upsell_results": []}

    article_type = selected.get("article_type", "")
    gender = selected.get("gender", "")
    color = selected.get("base_color", "")
    season = selected.get("season", "")
    usage = selected.get("usage", "")

    complementary_categories = COMPLEMENTARY_MAP.get(article_type, ["Watches", "Belts", "Accessories", "Socks"])
    
    engine = get_search_engine()
    candidates = []
    for cat in complementary_categories[:2]:
        cat_filters = engine.build_filter(
            gender=gender if gender in ["Men", "Women"] else None,
            in_stock=True
        )
        cat_query = f"{usage} {season} {cat}".strip()
        found = engine.hybrid_search(query=cat_query, filter_dict=cat_filters, limit=3)
        candidates.extend(found)

    if not candidates:
        return {"upsell_results": []}

    candidate_lines = []
    for c in candidates:
        candidate_lines.append(
            f"ID: {c.get('product_id')} | Name: {c.get('name')} | Category: {c.get('article_type')} | Color: {c.get('base_color')} | Price: ${c.get('price')}"
        )
    candidate_text = "\n".join(candidate_lines)

    prompt = f"""You are an Expert AI Fashion Stylist.
Recommend the best complementary items to complete an outfit with the customer's selected item.

Selected Item:
- Name: {selected.get('name')}
- Category: {article_type}
- Color: {color}
- Gender: {gender}
- Usage: {usage}

Candidate Items:
{candidate_text}

Task:
Select the top 2-3 most harmonious complementary products and provide stylist reasoning.
"""
    structured_llm = llm.with_structured_output(UpsellAnalysis)
    try:
        analysis: UpsellAnalysis = structured_llm.invoke(prompt)
        
        upsell_list = []
        cand_map = {c.get("product_id"): c for c in candidates}
        for rec in analysis.recommendations:
            prod = cand_map.get(rec.complementary_product_id)
            if prod:
                item_data = prod.copy()
                item_data["compatibility_reason"] = rec.compatibility_reason
                item_data["stylist_note"] = rec.stylist_note
                upsell_list.append(item_data)

        updated_history = list(state.get("conversation_history", []))
        summary = f"Found {len(state.get('search_results', []))} products and {len(upsell_list)} stylist outfit pairings."
        updated_history.append({"role": "assistant", "content": summary})

        return {
            "upsell_results": upsell_list,
            "conversation_history": updated_history
        }
    except Exception as e:
        print(f"Notice on upsell analysis: {e}")
        return {"upsell_results": candidates[:2]}
