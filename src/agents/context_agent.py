from typing import Dict, Any
from src.agents.state import AgentState, ContextEvaluation
from src.agents.base import get_llm

def context_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Context Agent: Evaluator & Clarification Generator
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

    prompt = f"""You are an Expert E-Commerce Fashion Context Evaluator for a luxury atelier.
Determine if the shopping request or budget refinement has sufficient specificity to execute a targeted catalog search.

User Query: "{current_query}"
Current Filters: {filters}
Clarification Rounds So Far: {clarification_count}/2

Evaluation Rules:
1. If the request has clear intent, category, or budget parameter (e.g. "women running shoes", "casual blue shirt", "black watch", "under ₹2000", "under $50", "from ₹4000", "yes show from ₹4000"), set has_sufficient_context = True.
2. If the user's message is answering a previous budget or category question (e.g. "from ₹4000", "make it ₹3500", "for men"), incorporate that into final_search_query / inferred_filters and set has_sufficient_context = True.
3. If the request is severely vague with zero specifics (e.g. just "I want clothes", "give me something", "help"):
   - Set has_sufficient_context = False.
   - Generate exactly ONE concise, luxury concierge follow-up question.
4. If a category is mentioned (e.g. "shoes", "watches", "tshirts"), it IS sufficient to perform a curated search.
"""
    llm = get_llm(temperature=0.1, agent_name="context")
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
