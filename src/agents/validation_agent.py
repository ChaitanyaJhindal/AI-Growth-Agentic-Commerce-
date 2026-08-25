from typing import Dict, Any
from src.agents.state import AgentState, ValidationDecision
from src.agents.base import get_llm

def validation_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Validation Agent: Quality Assurance & Retry Controller
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
    llm = get_llm()
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
