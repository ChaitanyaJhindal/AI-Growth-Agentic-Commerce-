from typing import Dict, Any, List
from src.agents.state import AgentState, UpsellAnalysis
from src.agents.base import get_llm, get_search_engine

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
    Upsell Agent: AI Fashion Stylist Outfit Engine
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
    llm = get_llm()
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
