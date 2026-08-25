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
    llm = get_llm()
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
