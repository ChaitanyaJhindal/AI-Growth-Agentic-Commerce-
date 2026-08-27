from typing import Dict, Any
from src.agents.state import AgentState
from src.agents.base import get_search_engine

def search_node(state: AgentState) -> Dict[str, Any]:
    """
    Search Node: Deterministic Hybrid Search Executor with Price & Budget Intelligence
    Executes hybrid search against MongoDB Atlas with smart price boundary detection.
    """
    if state.get("selected_product") and state.get("intent") == "select_product":
        return {
            "search_results": state.get("search_results", []),
            "price_analysis": state.get("price_analysis")
        }

    query = state.get("current_query") or state.get("original_query", "")
    filters = state.get("filters", {})

    engine = get_search_engine()
    results, price_analysis = engine.hybrid_search_with_price_intelligence(
        query=query,
        filter_dict=filters,
        limit=15
    )

    return {
        "search_results": results,
        "price_analysis": price_analysis
    }
