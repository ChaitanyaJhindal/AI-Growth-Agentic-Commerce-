from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

# ==========================================
# 1. Pydantic Structured Output Models
# ==========================================

class QueryAnalysis(BaseModel):
    """Structured extraction from the user's query and conversation history."""
    intent: str = Field(
        description="The user intent: 'search', 'filter_refinement', 'select_product', 'browse', 'ask_question'."
    )
    product_category: Optional[str] = Field(
        None, description="Target product category or article type (e.g. 'Shoes', 'Shirts', 'Watches', 'Jeans')."
    )
    attributes: Optional[List[str]] = Field(
        default_factory=list,
        description="Fashion attributes (colors, style, material, season, usage)."
    )
    brand: Optional[str] = Field(
        None, description="Explicit brand mentioned (e.g. 'Nike', 'Puma', 'Peter England', 'Titan')."
    )
    gender: Optional[str] = Field(
        None, description="Target gender ('Men', 'Women', 'Unisex', 'Boys', 'Girls')."
    )
    min_price: Optional[float] = Field(
        None, description="Minimum price in USD."
    )
    max_price: Optional[float] = Field(
        None, description="Maximum price in USD."
    )
    min_rating: Optional[float] = Field(
        None, description="Minimum rating (e.g. 4.0)."
    )
    in_stock_only: bool = Field(
        False, description="True if only in-stock items requested."
    )
    selected_product_index: Optional[int] = Field(
        None, description="If user refers to a specific product number (e.g. 'I like the 2nd one', 'recommend outfit for product #1'), the 1-based index."
    )
    cleaned_query: str = Field(
        description="Context-aware refined search query string incorporating previous conversation turns."
    )


class ContextEvaluation(BaseModel):
    """Evaluation of whether enough information exists to execute a high-quality search."""
    has_sufficient_context: bool = Field(
        description="True if query has enough clarity to search; False if too vague."
    )
    clarification_question: Optional[str] = Field(
        None, description="1 concise follow-up question if information is missing."
    )
    final_search_query: str = Field(
        description="Refined search query string incorporating full dialogue context."
    )
    inferred_filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured MongoDB filters."
    )


class ValidationDecision(BaseModel):
    """Validation of retrieved products against user criteria."""
    validated: bool = Field(
        description="True if products satisfy requirements; False otherwise."
    )
    explanation: str = Field(
        description="Short rationale of validation decision."
    )
    rewritten_query: Optional[str] = Field(
        None, description="Rewritten search query if validation failed."
    )
    adjusted_filters: Optional[Dict[str, Any]] = Field(
        None, description="Adjusted metadata filters if validation failed."
    )


class UpsellRecommendation(BaseModel):
    """Ranked complementary product recommendation."""
    complementary_product_id: str = Field(description="Product ID of complementary item.")
    compatibility_reason: str = Field(description="Why this item pairs well.")
    stylist_note: str = Field(description="Fashion advice on wearing them together.")


class UpsellAnalysis(BaseModel):
    """Ranked upsell/cross-sell recommendations."""
    recommendations: List[UpsellRecommendation] = Field(
        default_factory=list,
        description="Top complementary products ranked by style harmony."
    )


# ==========================================
# 2. Typed LangGraph State with Conversation Memory
# ==========================================

class AgentState(TypedDict):
    """The central state dictionary with full multi-turn conversation memory."""
    conversation_history: List[Dict[str, str]]  # [{"role": "user"/"assistant", "content": "..."}]
    original_query: str
    current_query: str
    filters: Dict[str, Any]
    intent: str
    clarification_count: int
    needs_clarification: bool
    clarification_question: Optional[str]
    search_results: List[Dict[str, Any]]
    validation_result: Dict[str, Any]
    selected_product: Optional[Dict[str, Any]]
    upsell_results: List[Dict[str, Any]]
