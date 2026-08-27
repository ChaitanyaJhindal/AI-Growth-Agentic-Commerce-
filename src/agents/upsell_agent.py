import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.agents.state import AgentState, UpsellAnalysis, UpsellRecommendation
from src.agents.base import get_llm, get_search_engine

# Deprecated placeholder maintained for backward compatibility
COMPLEMENTARY_MAP: Dict[str, List[str]] = {}


# =====================================================================
# Pydantic Schemas for Stylist Chain-of-Thought & Ideation
# =====================================================================

class StylistQueryTarget(BaseModel):
    category_or_article: str = Field(description="Target complementary article or category (e.g. Slim Track Pants, Minimalist Leather Watch, Oxford Shirt)")
    search_query: str = Field(description="Semantic hybrid search query to retrieve this piece from catalog (e.g. 'black slim tapered track pants', 'classic silver dial watch')")
    styling_intent: str = Field(description="Why this specific item type enhances the look and balances the silhouette")

class StylistIdeation(BaseModel):
    aesthetic_vibe: str = Field(description="The overarching fashion aesthetic (e.g. 'Refined Scandinavian Athleisure', 'Monochrome Street Luxury', 'Riviera Smart Casual')")
    color_and_tonal_strategy: str = Field(description="Tonal balance and color matching philosophy")
    chain_of_thought: str = Field(description="Step-by-step reasoning on what pieces complete the silhouette and occasion")
    pairing_targets: List[StylistQueryTarget] = Field(description="2 to 3 target complementary pieces to search for in the catalog")


def safe_parse_json(text: str) -> Dict[str, Any]:
    """Robustly extracts and parses a JSON object from model output text."""
    clean = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    match_brace = re.search(r"(\{.*\})", clean, re.DOTALL)
    if match_brace:
        return json.loads(match_brace.group(1))
    return json.loads(clean)


# =====================================================================
# Few-Shot Dynamic Ideation Prompt Template (JSON Format)
# =====================================================================

IDEATION_SYSTEM_PROMPT = """You are an Haute Couture Personal Fashion Stylist and Creative Director for AURA Luxury Concierge.
Given an anchor fashion product, analyze its silhouette, fabric, color, brand, gender, and usage.
Use Chain-of-Thought (CoT) reasoning to devise an editorial outfit and specify 2 to 3 search queries to retrieve complementary items.

You MUST respond strictly with a valid JSON object matching this schema:
{
  "aesthetic_vibe": "string",
  "color_and_tonal_strategy": "string",
  "chain_of_thought": "string detailing 1. Silhouette Balance 2. Occasion & Season 3. Tonal Harmony 4. Footwear & Accessories",
  "pairing_targets": [
    {
      "category_or_article": "string",
      "search_query": "string (semantic search query for catalog)",
      "styling_intent": "string"
    }
  ]
}

--- FEW-SHOT EXAMPLES ---

[Example 1: Casual Grey T-Shirt]
Input: Name: Puma Men Grey Crewneck Tee | Category: Tshirts | Color: Grey | Gender: Men | Usage: Casual
Output JSON:
{
  "aesthetic_vibe": "Refined Casual Monochrome",
  "color_and_tonal_strategy": "Heather grey anchor with deep charcoal/black base and optical white contrast",
  "chain_of_thought": "1. Upper is soft and relaxed. Lower half needs tailored structure. 2. Black slim tapered track pants or dark jeans anchor the silhouette. 3. Clean white low-top sneakers elevate from loungewear to street style. 4. A minimalist steel watch finishes the look.",
  "pairing_targets": [
    {
      "category_or_article": "Track Pants",
      "search_query": "black slim tapered casual track pants",
      "styling_intent": "Structured lower silhouette to balance the relaxed jersey top"
    },
    {
      "category_or_article": "Casual Shoes",
      "search_query": "white minimalist leather low top sneakers",
      "styling_intent": "Crisp optical footwear contrast"
    },
    {
      "category_or_article": "Watches",
      "search_query": "silver stainless steel analog casual watch",
      "styling_intent": "Luxe understated metallic wrist accent"
    }
  ]
}

[Example 2: Sports Running Shoes]
Input: Name: Nike Men Air Max Running Shoes | Category: Sports Shoes | Color: White/Blue | Gender: Men | Usage: Sports
Output JSON:
{
  "aesthetic_vibe": "High-Performance Technical Athleisure",
  "color_and_tonal_strategy": "Crisp athletic white and electric blue grounded by matte black performance fabrics",
  "chain_of_thought": "1. Footwear is dynamic and technical. 2. Ergonomic ribbed socks prevent chafing and bridge shoe-to-pant transition. 3. Breathable tapered track pants maintain aerodynamic line. 4. A moisture-wicking active tee completes the training look.",
  "pairing_targets": [
    {
      "category_or_article": "Socks",
      "search_query": "white ribbed athletic training socks",
      "styling_intent": "Ergonomic cushioning and clean ankle transition"
    },
    {
      "category_or_article": "Track Pants",
      "search_query": "black breathable lightweight training pants",
      "styling_intent": "Tapered athletic silhouette that highlights the sneakers"
    },
    {
      "category_or_article": "Tshirts",
      "search_query": "blue moisture wicking performance athletic t-shirt",
      "styling_intent": "Harmonizes with blue sneaker detailing"
    }
  ]
}
"""


RANKING_SYSTEM_PROMPT = """You are AURA's Lead Fashion Curator.
Review the retrieved catalog products and select the top 2-3 most harmonious pieces that complete the outfit with the customer's Anchor Piece.

You MUST respond strictly with a valid JSON object matching this schema:
{
  "recommendations": [
    {
      "complementary_product_id": "string (MUST exactly match a candidate product_id)",
      "compatibility_reason": "string (why this specific color/fabric/piece pairs well)",
      "stylist_note": "string (bespoke styling advice: tucking, cuffing, layering, accessories)"
    }
  ]
}

--- FEW-SHOT EXAMPLE ---
Output JSON:
{
  "recommendations": [
    {
      "complementary_product_id": "PROD-12345",
      "compatibility_reason": "The matte black tapered fit provides clean structural grounding against the grey crewneck.",
      "stylist_note": "Tuck the front of the tee loosely and pair with clean white sneakers for an effortless weekend silhouette."
    },
    {
      "complementary_product_id": "PROD-67890",
      "compatibility_reason": "The silver bezel introduces a refined metallic highlight that elevates the casual monochrome palette.",
      "stylist_note": "Wear with a pushed-up sleeve to showcase the watch as an intentional statement piece."
    }
  ]
}
"""


# =====================================================================
# Main Upsell Agent Node
# =====================================================================

def upsell_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Dynamic AI Fashion Stylist & Outfit Engine.
    Uses Chain-of-Thought (CoT) + Few-Shot Prompting (Temperature 0.9) to:
    1. Dynamically ideate the aesthetic, tonal harmony, and complementary pieces for ANY item.
    2. Formulate semantic queries and retrieve matching catalog candidates via Hybrid Search.
    3. Curate and write bespoke stylist editorial notes for the final ensemble.
    """
    selected = state.get("selected_product")
    if not selected:
        results = state.get("search_results", [])
        selected = results[0] if results else None

    if not selected:
        return {"upsell_results": []}

    name = selected.get("name", "Fashion Piece")
    category = selected.get("article_type") or selected.get("master_category", "Apparel")
    color = selected.get("base_color", "Neutral")
    gender = selected.get("gender", "Unisex")
    usage = selected.get("usage", "Casual")
    season = selected.get("season", "All Season")
    brand = selected.get("brand", "Studio")

    # -----------------------------------------------------------------
    # Step 1: Dynamic Ideation & Chain-of-Thought (Temp = 0.9 - Key 3)
    # -----------------------------------------------------------------
    llm_creative = get_llm(temperature=0.9, agent_name="upsell")

    user_ideation_msg = f"""Anchor Product Details:
- Name: {name}
- Category: {category}
- Color: {color}
- Gender: {gender}
- Usage: {usage}
- Season: {season}
- Brand: {brand}

Generate your Chain-of-Thought reasoning, Aesthetic Vibe, Color Strategy, and 2-3 precise Pairing Search Targets in JSON format."""

    try:
        response = llm_creative.invoke([
            {"role": "system", "content": IDEATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_ideation_msg}
        ])
        parsed = safe_parse_json(response.content)
        ideation = StylistIdeation.model_validate(parsed)
    except Exception as e:
        print(f"Notice on stylist ideation parsing: {e}")
        ideation = StylistIdeation(
            aesthetic_vibe=f"Modern {usage} Capsule",
            color_and_tonal_strategy=f"Harmonious tonal pairing with {color}",
            chain_of_thought=f"Curating balanced contemporary pieces for {name}.",
            pairing_targets=[
                StylistQueryTarget(category_or_article="Bottoms", search_query=f"{gender} pants trousers jeans", styling_intent="Foundation piece"),
                StylistQueryTarget(category_or_article="Footwear", search_query=f"{gender} casual shoes sneakers", styling_intent="Footwear grounding"),
                StylistQueryTarget(category_or_article="Accessories", search_query=f"{gender} watch belt socks", styling_intent="Finishing touch")
            ]
        )

    # -----------------------------------------------------------------
    # Step 2: Dynamic Hybrid Search Retrieval from Catalog
    # -----------------------------------------------------------------
    engine = get_search_engine()
    candidates: List[Dict[str, Any]] = []
    seen_ids = {selected.get("product_id")}

    for target in ideation.pairing_targets[:3]:
        cat_filters = engine.build_filter(
            gender=gender if gender in ["Men", "Women"] else None,
            in_stock=True
        )
        found = engine.hybrid_search(
            query=f"{gender} {target.search_query}".strip(),
            filter_dict=cat_filters,
            limit=4
        )
        for item in found:
            p_id = item.get("product_id")
            if p_id and p_id not in seen_ids:
                seen_ids.add(p_id)
                candidates.append(item)

    if not candidates:
        return {"upsell_results": []}

    # -----------------------------------------------------------------
    # Step 3: Stylist Selection & Editorial Ranking (Temp = 0.9)
    # -----------------------------------------------------------------
    candidate_lines = []
    for c in candidates:
        raw_p = c.get('price') or 0
        candidate_lines.append(
            f"product_id: {c.get('product_id')} | Name: {c.get('name')} | Category: {c.get('article_type')} | "
            f"Color: {c.get('base_color')} | Brand: {c.get('brand')} | Price: ₹{int(raw_p * 50):,}"
        )
    candidate_text = "\n".join(candidate_lines)

    user_ranking_msg = f"""Anchor Piece:
- Name: {name} ({category}, Color: {color}, Gender: {gender}, Usage: {usage})

Stylist Aesthetic:
- Vibe: {ideation.aesthetic_vibe}
- Strategy: {ideation.color_and_tonal_strategy}

Available Retrieved Candidates:
{candidate_text}

Select the top 2-3 most harmonious pieces and output your recommendations in JSON format."""

    try:
        rank_response = llm_creative.invoke([
            {"role": "system", "content": RANKING_SYSTEM_PROMPT},
            {"role": "user", "content": user_ranking_msg}
        ])
        rank_parsed = safe_parse_json(rank_response.content)
        analysis = UpsellAnalysis.model_validate(rank_parsed)

        upsell_list = []
        cand_map = {c.get("product_id"): c for c in candidates}

        for rec in analysis.recommendations:
            prod = cand_map.get(rec.complementary_product_id)
            if prod:
                item_data = prod.copy()
                item_data["compatibility_reason"] = rec.compatibility_reason
                item_data["stylist_note"] = rec.stylist_note
                item_data["aesthetic_vibe"] = ideation.aesthetic_vibe
                upsell_list.append(item_data)

        if not upsell_list:
            upsell_list = candidates[:3]

        updated_history = list(state.get("conversation_history", []))
        summary = f"Curated {len(upsell_list)} bespoke outfit pairings under aesthetic '{ideation.aesthetic_vibe}'."
        updated_history.append({"role": "assistant", "content": summary})

        return {
            "upsell_results": upsell_list,
            "conversation_history": updated_history
        }

    except Exception as e:
        print(f"Notice on stylist ranking parsing: {e}")
        return {"upsell_results": candidates[:3]}
