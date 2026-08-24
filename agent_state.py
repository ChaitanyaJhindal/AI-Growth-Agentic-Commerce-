from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

# ==========================================
# 1. Pydantic Structured Output Models
# ==========================================

class QueryAnalysis(BaseModel):
    """Structured extraction from the user's initial query."""
    intent: str = Field(
        description="The primary user intent (e.g., 'search', 'browse', 'find_specific_item', 'compare')."
    )
    product_category: Optional[str] = Field(
        None, description="Target product category or article type (e.g. 'Shoes', 'Shirts', 'Watches', 'Jeans')."
    )
    attributes: List[str] = Field(
        default_factory=list,
        description="Extracted fashion attributes (e.g., colors, style, material, season, occasion, usage)."
    )
    brand: Optional[str] = Field(
        None, description="Explicit brand mentioned if any (e.g. 'Nike', 'Puma', 'Peter England', 'Titan')."
    )
    gender: Optional[str] = Field(
        None, description="Target gender if mentioned or inferred ('Men', 'Women', 'Unisex', 'Boys', 'Girls')."
    )
    min_price: Optional[float] = Field(
        None, description="Minimum price constraint in USD."
    )
    max_price: Optional[float] = Field(
        None, description="Maximum price constraint in USD."
    )
    min_rating: Optional[float] = Field(
        None, description="Minimum star rating (e.g., 4.0)."
    )
    in_stock_only: bool = Field(
        False, description="True if the user specifically requested available/in-stock items."
    )
    cleaned_query: str = Field(
        description="A concise semantic search query optimized for vector/keyword search."
    )


class ContextEvaluation(BaseModel):
    """Evaluation of whether enough information exists to execute a high-quality search."""
    has_sufficient_context: bool = Field(
        description="True if the query has enough clarity to perform a targeted product search; False if too vague."
    )
    clarification_question: Optional[str] = Field(
        None, description="1 concise follow-up question if information is missing (e.g. budget, gender, or category)."
    )
    final_search_query: str = Field(
        description="Refined search query string incorporating all available context."
    )
    inferred_filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured MongoDB filters (e.g., {'gender': 'Men', 'price': {'$lte': 50}})."
    )


class ValidationDecision(BaseModel):
    """Validation of retrieved products against the user's requirements."""
    validated: bool = Field(
        description="True if the retrieved products satisfy the user's criteria; False if irrelevant or missing key constraints."
    )
    explanation: str = Field(
        description="Short rationale of why the products passed or failed validation."
    )
    rewritten_query: Optional[str] = Field(
        None, description="If validation failed, a rewritten query to improve search precision."
    )
    adjusted_filters: Optional[Dict[str, Any]] = Field(
        None, description="If validation failed, adjusted metadata filters to fix the mismatch."
    )


class UpsellRecommendation(BaseModel):
    """Ranked complementary product recommendation for a selected item."""
    complementary_product_id: str = Field(description="Product ID of the complementary item.")
    compatibility_reason: str = Field(description="Why this item pairs well in terms of color, style, usage, and occasion.")
    stylist_note: str = Field(description="Actionable fashion advice on wearing them together.")


class UpsellAnalysis(BaseModel):
    """Set of ranked upsell/cross-sell recommendations."""
    recommendations: List[UpsellRecommendation] = Field(
        default_factory=list,
        description="Top complementary products ranked by style and color harmony."
    )


# ==========================================
# 2. Typed LangGraph State
# ==========================================

class AgentState(TypedDict):
    """The central state dictionary passed across LangGraph nodes."""
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
