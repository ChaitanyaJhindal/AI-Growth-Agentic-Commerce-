from typing import Dict, Any
from src.agents.state import AgentState
from src.agents.base import get_search_engine

def search_node(state: AgentState) -> Dict[str, Any]:
    """
    Search Node: Deterministic Hybrid Search Executor
    Executes hybrid search against MongoDB Atlas without LLM hallucination.
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
