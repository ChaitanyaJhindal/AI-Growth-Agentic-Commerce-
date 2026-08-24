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

# Initialize Groq LLM (openai/gpt-oss-120b)
_groq_api_key = os.getenv("GROQ_API_KEY")
if not _groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable is missing. Please set it in .env")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.1,
    api_key=_groq_api_key
)

# Search Engine Singleton
_search_engine = None

def get_search_engine() -> ProductHybridSearchEngine:
    global _search_engine
    if _search_engine is None:
        _search_engine = ProductHybridSearchEngine()
    return _search_engine


# =====================================================================
# 1. Query Agent
# =====================================================================

def query_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes the user query and extracts intent, product category,
    fashion attributes, and explicit constraints into structured filters.
    """
    user_query = state.get("current_query") or state.get("original_query", "")
    
    prompt = f"""You are an expert E-Commerce Fashion Query Parser.
Analyze the user's shopping request and extract structured details.

Catalog Knowledge:
- Master Categories: Apparel, Footwear, Accessories, Personal Care
- Genders: Men, Women, Unisex, Boys, Girls
- Common Articles: Tshirts, Shirts, Jeans, Casual Shoes, Sports Shoes, Watches, Bags, Track Pants, Jackets, Socks, etc.
- Colors: Black, Blue, Navy Blue, White, Grey, Red, Green, Silver, etc.

User Request: "{user_query}"

Extract all intent, attributes, and constraints cleanly.
"""
    structured_llm = llm.with_structured_output(QueryAnalysis)
    analysis: QueryAnalysis = structured_llm.invoke(prompt)

    # Compile structured filters for MongoDB
    engine = get_search_engine()
    filters = engine.build_filter(
        brand=analysis.brand,
        gender=analysis.gender,
        master_category=analysis.product_category if analysis.product_category in ["Apparel", "Footwear", "Accessories", "Personal Care"] else None,
        article_type=analysis.product_category if analysis.product_category not in ["Apparel", "Footwear", "Accessories", "Personal Care"] else None,
        min_price=analysis.min_price,
        max_price=analysis.max_price,
        min_rating=analysis.min_rating,
        in_stock=analysis.in_stock_only
    )

    # Merge any existing state filters
    existing_filters = state.get("filters", {})
    if existing_filters:
        filters.update(existing_filters)

    return {
        "intent": analysis.intent,
        "current_query": analysis.cleaned_query or user_query,
        "filters": filters
    }


# =====================================================================
# 2. Context Agent
# =====================================================================

def context_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates whether enough information exists to perform a targeted search.
    If critically vague and clarification_count < 2, asks 1 concise question.
    """
    clarification_count = state.get("clarification_count", 0)
    current_query = state.get("current_query", "")
    filters = state.get("filters", {})

    # If we have reached 2 clarification rounds, proceed directly with whatever context exists
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
1. If the request is specific enough (e.g. "men running shoes under $80", "blue denim shirt", "silver watch"), mark has_sufficient_context = True.
2. If the request is severely vague or ambiguous (e.g. "I want sneakers", "clothes for party", "something to wear"):
   - Set has_sufficient_context = False.
   - Generate exactly ONE concise, helpful follow-up question (e.g. "What is your preferred budget?", "Are you shopping for Men or Women?").
3. Do NOT ask unnecessary questions if the intent and category are clear.
"""
    structured_llm = llm.with_structured_output(ContextEvaluation)
    eval_result: ContextEvaluation = structured_llm.invoke(prompt)

    if not eval_result.has_sufficient_context and clarification_count < 2:
        return {
            "needs_clarification": True,
            "clarification_question": eval_result.clarification_question,
            "clarification_count": clarification_count + 1
        }
    else:
        merged_filters = filters.copy()
        if eval_result.inferred_filters:
            merged_filters.update(eval_result.inferred_filters)

        return {
            "needs_clarification": False,
            "clarification_question": None,
            "current_query": eval_result.final_search_query or current_query,
            "filters": merged_filters
        }


# =====================================================================
# 3. Search Node (Deterministic Tool / Node)
# =====================================================================

def search_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes hybrid search against MongoDB Atlas.
    Deterministic execution without LLM hallucination.
    """
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
    Validates retrieved products against original user requirements.
    If mismatched, rewrites the query and triggers retry (max 2 retries).
    """
    original_query = state.get("original_query", "")
    current_query = state.get("current_query", "")
    results = state.get("search_results", [])
    val_state = state.get("validation_result", {})
    retry_count = val_state.get("retry_count", 0)

    # Empty results check
    if not results:
        if retry_count < 2:
            return {
                "validation_result": {
                    "validated": False,
                    "explanation": "No products found with current constraints.",
                    "retry_count": retry_count + 1
                },
                "current_query": original_query,
                "filters": {}  # Relax filters on retry
            }
        else:
            return {
                "validation_result": {
                    "validated": True,
                    "explanation": "Max retries reached with 0 results.",
                    "retry_count": retry_count
                }
            }

    # Format top products summary for LLM validator
    product_summaries = []
    for p in results[:5]:
        product_summaries.append(
            f"- [{p.get('product_id')}] {p.get('name')} | Brand: {p.get('brand')} | Gender: {p.get('gender')} | "
            f"Type: {p.get('article_type')} | Color: {p.get('base_color')} | Price: ${p.get('price')} | Rating: {p.get('rating')}"
        )
    catalog_snippet = "\n".join(product_summaries)

    prompt = f"""You are an E-Commerce Product Quality Validator.
Verify if the retrieved catalog products satisfy the user's original request and constraints.

Original User Query: "{original_query}"
Current Search Query: "{current_query}"
Retrieved Top Products:
{catalog_snippet}

Evaluate:
1. Do the products match the intended category, gender, and attributes?
2. If yes, set validated = True.
3. If no (e.g. wrong gender, irrelevant category, or strict constraint violated), set validated = False, explain why, and provide a rewritten_query and adjusted_filters.
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
        # Prepare for retry
        new_filters = state.get("filters", {}).copy()
        if decision.adjusted_filters:
            new_filters.update(decision.adjusted_filters)

        return {
            "validation_result": {
                "validated": False,
                "explanation": decision.explanation,
                "retry_count": retry_count + 1
            },
            "current_query": decision.rewritten_query or original_query,
            "filters": new_filters
        }


# =====================================================================
# 5. Upsell Agent
# =====================================================================

# Complementary category mapping for fashion recommendations
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
    Recommends stylish complementary products for the selected/primary product.
    Retrieves candidates via hybrid search and uses LLM to rank outfit pairings.
    """
    # Identify target product
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

    # Look up complementary categories
    complementary_categories = COMPLEMENTARY_MAP.get(article_type, ["Watches", "Belts", "Accessories", "Socks"])
    
    # Retrieve candidates using hybrid search tool
    engine = get_search_engine()
    candidates = []
    for cat in complementary_categories[:2]:
        cat_filters = engine.build_filter(
            gender=gender if gender in ["Men", "Women"] else None,
            in_stock=True
        )
        cat_query = f"{usage} {season} {cat}"
        found = engine.hybrid_search(query=cat_query, filter_dict=cat_filters, limit=3)
        candidates.extend(found)

    if not candidates:
        return {"upsell_results": []}

    # Format candidates for LLM compatibility judge
    candidate_lines = []
    for c in candidates:
        candidate_lines.append(
            f"ID: {c.get('product_id')} | Name: {c.get('name')} | Category: {c.get('article_type')} | Color: {c.get('base_color')} | Price: ${c.get('price')}"
        )
    candidate_text = "\n".join(candidate_lines)

    prompt = f"""You are an Expert AI Fashion Stylist.
Recommend the best complementary items to complete an outfit with the customer's selected item.

Selected Product:
- ID: {selected.get('product_id')}
- Name: {selected.get('name')}
- Category: {article_type}
- Color: {color}
- Gender: {gender}
- Season: {season}
- Usage: {usage}
- Price: ${selected.get('price')}

Available Candidate Items:
{candidate_text}

Task:
Select the top 2-3 most harmonious complementary products.
Explain why their color, style, usage, and category pair perfectly.
"""
    structured_llm = llm.with_structured_output(UpsellAnalysis)
    try:
        analysis: UpsellAnalysis = structured_llm.invoke(prompt)
        
        # Attach full product metadata to recommendations
        upsell_list = []
        cand_map = {c.get("product_id"): c for c in candidates}
        for rec in analysis.recommendations:
            prod = cand_map.get(rec.complementary_product_id)
            if prod:
                item_data = prod.copy()
                item_data["compatibility_reason"] = rec.compatibility_reason
                item_data["stylist_note"] = rec.stylist_note
                upsell_list.append(item_data)

        return {"upsell_results": upsell_list}
    except Exception as e:
        print(f"Notice on upsell analysis: {e}")
        return {"upsell_results": candidates[:2]}
