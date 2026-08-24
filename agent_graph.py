from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agent_state import AgentState
from agents import (
    query_agent_node,
    context_agent_node,
    search_node,
    validation_agent_node,
    upsell_agent_node
)

# ==========================================
# Conditional Routing Functions
# ==========================================

def route_after_context(state: AgentState) -> Literal["search_node", "__end__"]:
    """
    Decides whether to proceed to search or pause to ask clarification from user.
    """
    if state.get("needs_clarification", False):
        return "__end__"
    return "search_node"


def route_after_validation(state: AgentState) -> Literal["upsell_agent", "search_node"]:
    """
    Decides whether validation passed (proceed to upsell/complete)
    or failed and needs a search retry.
    """
    val_res = state.get("validation_result", {})
    is_valid = val_res.get("validated", True)
    retry_count = val_res.get("retry_count", 0)

    if is_valid or retry_count >= 2:
        return "upsell_agent"
    return "search_node"


# ==========================================
# Build LangGraph StateGraph with MemorySaver Checkpointer
# ==========================================

memory_checkpointer = MemorySaver()

def create_ecommerce_agent_graph(checkpointer = memory_checkpointer):
    workflow = StateGraph(AgentState)

    # 1. Add Nodes
    workflow.add_node("query_agent", query_agent_node)
    workflow.add_node("context_agent", context_agent_node)
    workflow.add_node("search_node", search_node)
    workflow.add_node("validation_agent", validation_agent_node)
    workflow.add_node("upsell_agent", upsell_agent_node)

    # 2. Set Entry Point
    workflow.set_entry_point("query_agent")

    # 3. Add Edges
    workflow.add_edge("query_agent", "context_agent")

    # Conditional Branch after Context Agent:
    workflow.add_conditional_edges(
        "context_agent",
        route_after_context,
        {
            "search_node": "search_node",
            "__end__": END
        }
    )

    workflow.add_edge("search_node", "validation_agent")

    # Conditional Branch after Validation Agent:
    workflow.add_conditional_edges(
        "validation_agent",
        route_after_validation,
        {
            "upsell_agent": "upsell_agent",
            "search_node": "search_node"
        }
    )

    workflow.add_edge("upsell_agent", END)

    return workflow.compile(checkpointer=checkpointer)


# Global compiled app with conversation checkpointing
agent_app = create_ecommerce_agent_graph()
