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

    price_info = state.get("price_analysis") or {}
    price_gap_note = ""
    if price_info.get("price_gap_detected"):
        req_p = price_info.get("requested_max_price")
        min_p = price_info.get("catalog_min_price")
        cat = price_info.get("category_name", "this category")
        price_gap_note = f"""
Notice on Budget:
The patron requested items under ${req_p:.2f}, but curated pieces in {cat} begin at ${min_p:.2f}.
We have retrieved the finest entry-level pieces starting at ${min_p:.2f}.
In your explanation, politely and professionally acknowledge this entry baseline (e.g. "Curated {cat} selections begin at ${min_p:.2f}; presenting our most accessible luxury pieces with superior craftsmanship.") and validate the results.
"""

    product_summaries = []
    for p in results[:4]:
        product_summaries.append(
            f"- [{p.get('product_id')}] {p.get('name')} | Brand: {p.get('brand')} | Gender: {p.get('gender')} | "
            f"Type: {p.get('article_type')} | Price: ${p.get('price')}"
        )
    catalog_snippet = "\n".join(product_summaries)

    prompt = f"""You are a Luxury Fashion Quality & Concierge Validator.
Verify if the retrieved catalog pieces satisfy the user's intent, aesthetic criteria, and budget expectations.

Original Request: "{original_query}"
Current Search Term: "{current_query}"
{price_gap_note}
Top Retrieved Products:
{catalog_snippet}

Tasks & Reasoning Rules:
1. If products are relevant to the fashion category/style, set validated = True.
2. If a budget gap was noted (the catalog minimum is higher than requested price), provide an intelligent, honest concierge explanation explaining the entry-level baseline starting price and validate the curated pieces.
3. If products are completely unrelated (e.g. wrong category entirely), set validated = False and rewrite query.
"""
    llm = get_llm(temperature=0.1, agent_name="validation")
    structured_llm = llm.with_structured_output(ValidationDecision)
    try:
        decision: ValidationDecision = structured_llm.invoke(prompt)
    except Exception as e:
        print(f"Validation invocation notice: {e}")
        decision = ValidationDecision(
            validated=True,
            explanation=f"Curated {len(results)} exquisite selections tailored to your inquiry."
        )

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
