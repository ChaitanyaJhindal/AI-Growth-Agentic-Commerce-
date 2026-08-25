import json
import random
import time
import urllib.request
from typing import List, Dict, Any, Generator, AsyncGenerator
from src import config

# Curated Simple, Natural & Catalog-Grounded Search Prompts
DEFAULT_CATALOG_PROMPTS = [
    "Minimal black running sneakers under $80...",
    "Blue casual cotton shirt for dinner...",
    "White summer linen dress under $60...",
    "Men slim fit black formal trousers...",
    "Classic silver chronograph watch under $100...",
    "Navy blue hooded sweatshirt for winter...",
    "Women casual floral print top under $45...",
    "Puma breathable sports running shoes...",
    "Beige tailored semi-formal blazer...",
    "Black leather crossbody handbag...",
    "Olive green casual cargo pants...",
    "Red round neck cotton t-shirt under $30...",
    "Brown formal leather shoes for office...",
    "Unisex vintage black sunglasses..."
]

# Dynamic, Engaging Pipeline Thoughts (Replaces Dry Static Text)
DYNAMIC_PIPELINE_SETS = [
    [
        {"step": 1, "agent": "Query Agent", "thought": "Decoding silhouette proportions & aesthetic vibe..."},
        {"step": 2, "agent": "Context Agent", "thought": "Cross-referencing runway trends & seasonal occasion..."},
        {"step": 3, "agent": "Search Node", "thought": "Deep-mining 44,000+ luxury pieces with Voyage AI 512-dim vectors..."},
        {"step": 4, "agent": "Validation Agent", "thought": "Quality-assuring fabric drape, color harmony & rating score..."},
        {"step": 5, "agent": "Stylist Agent", "thought": "Curating bespoke capsule pairings & editorial styling advice..."}
    ],
    [
        {"step": 1, "agent": "Query Agent", "thought": "Dissecting streetwear drip, fit profile & color harmony..."},
        {"step": 2, "agent": "Context Agent", "thought": "Analyzing subtle style constraints & price-to-luxury ratio..."},
        {"step": 3, "agent": "Search Node", "thought": "Fusing Atlas Vector Search + Keyword Rank Fusion (RRF)..."},
        {"step": 4, "agent": "Validation Agent", "thought": "Inspecting piece compatibility & boutique in-stock status..."},
        {"step": 5, "agent": "Stylist Agent", "thought": "Synthesizing Haute Couture styling notes for complete look..."}
    ],
    [
        {"step": 1, "agent": "Query Agent", "thought": "Calibrating clean-girl & quiet luxury aesthetic parameters..."},
        {"step": 2, "agent": "Context Agent", "thought": "Evaluating versatility for effortless day-to-night transitions..."},
        {"step": 3, "agent": "Search Node", "thought": "Scanning catalog archive for high-affinity editorial pieces..."},
        {"step": 4, "agent": "Validation Agent", "thought": "Verifying brand craftsmanship & silhouette integrity..."},
        {"step": 5, "agent": "Stylist Agent", "thought": "Composing matching footwear & accessory tonal accents..."}
    ],
    [
        {"step": 1, "agent": "Query Agent", "thought": "Parsing modern athleisure & tailoring specifications..."},
        {"step": 2, "agent": "Context Agent", "thought": "Filtering occasion boundaries & climate appropriateness..."},
        {"step": 3, "agent": "Search Node", "thought": "Querying high-dimensional embeddings across MongoDB Atlas..."},
        {"step": 4, "agent": "Validation Agent", "thought": "Screening top recommendations against patron fit score..."},
        {"step": 5, "agent": "Stylist Agent", "thought": "Polishing the curated ensemble with bespoke designer tips..."}
    ]
]

class PlaceholderAgent:
    """
    Dynamic Search Placeholder & Progress Agent.
    Powered by `openai/gpt-oss-20b` on Groq (Temperature = 0.85).
    Generates clear, simple, intuitive fashion search prompts & dynamic pipeline thoughts.
    """

    def __init__(self, model: str = "openai/gpt-oss-20b"):
        self.model = model
        # Use Key 2 (Context/Validation key) or fallback for lowest latency
        self.api_key = config.GROQ_API_KEY_CONTEXT or config.GROQ_API_KEY_QUERY or config.GROQ_API_KEY
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self._prompt_pool: List[str] = list(DEFAULT_CATALOG_PROMPTS)
        random.shuffle(self._prompt_pool)
        self._pool_index: int = 0
        self._pipeline_set_index: int = 0

    def get_next_prompt(self) -> str:
        """Returns the next prompt from the active pool, rotating smoothly."""
        if not self._prompt_pool:
            self._prompt_pool = list(DEFAULT_CATALOG_PROMPTS)
            random.shuffle(self._prompt_pool)

        prompt = self._prompt_pool[self._pool_index % len(self._prompt_pool)]
        self._pool_index += 1
        return prompt

    def get_dynamic_pipeline_steps(self) -> List[Dict[str, Any]]:
        """Returns a dynamic, engaging set of agent thoughts for the progressive revelation banner."""
        steps_set = DYNAMIC_PIPELINE_SETS[self._pipeline_set_index % len(DYNAMIC_PIPELINE_SETS)]
        self._pipeline_set_index += 1
        return steps_set

    def generate_fresh_batch(self, count: int = 6) -> List[str]:
        """Calls Groq `openai/gpt-oss-20b` to generate fresh, clear, catalog-grounded search prompts."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AURA-Fashion/1.0"
        }

        system_instruction = """You are AURA's UX Fashion Search Guide.
Generate simple, clear, intuitive, and realistic fashion search queries that real everyday shoppers and new users would type in an e-commerce search bar.
Catalog context: We have 44,000+ items across Shirts, T-shirts, Jeans, Trousers, Sneakers, Formal Shoes, Watches, Dresses, Handbags, Sunglasses, Blazers, and Jackets for Men & Women with price filters (e.g., under $50, under $80).

Rules:
1. Make every prompt simple, natural, and immediately intuitive for a new shopper to understand.
2. Combine: [Color or Fit] + [Clothing/Footwear Item] + [Optional Occasion or Price Filter]
   Examples of ideal queries:
   - 'Minimal black running sneakers under $80...'
   - 'Blue casual cotton shirt for dinner...'
   - 'White summer linen dress under $60...'
   - 'Men slim fit black trousers...'
   - 'Classic leather watch under $100...'
   - 'Women floral top for weekend brunch...'
3. Keep each query between 4 to 8 words.
4. Do NOT use overly complex, cryptic, or obscure internet slang. Keep it clear, elegant, and realistic.
5. End each prompt with '...'
6. Return ONLY a valid JSON array of strings."""

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Generate {count} simple, realistic fashion search prompts as JSON array."}
            ],
            "temperature": 0.85
        }

        try:
            req = urllib.request.Request(self.api_url, data=json.dumps(data).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=4) as res:
                res_data = json.loads(res.read().decode("utf-8"))
                raw_text = res_data["choices"][0]["message"]["content"].strip()
                if "[" in raw_text and "]" in raw_text:
                    start = raw_text.index("[")
                    end = raw_text.rindex("]") + 1
                    items = json.loads(raw_text[start:end])
                    if isinstance(items, list) and items:
                        cleaned = [str(item).strip() for item in items if str(item).strip()]
                        if cleaned:
                            self._prompt_pool.extend(cleaned)
                            return cleaned
        except Exception as e:
            print(f"Notice on placeholder batch generation: {e}")

        return DEFAULT_CATALOG_PROMPTS[:count]

    def generate_combo_suggestion(self, anchor: Dict[str, Any], pairings: List[Dict[str, Any]]) -> str:
        """
        Uses openai/gpt-oss-20b to synthesize a chic, tailored styling combo tip
        deeply incorporating the anchor piece and the specific upselling recommendation pieces.
        """
        anchor_name = anchor.get("name", "Anchor Piece")
        anchor_brand = anchor.get("brand", "")
        anchor_type = anchor.get("article_type", "apparel")
        anchor_color = anchor.get("base_color", "")
        
        pair_details = []
        pair_names = []
        for p in pairings:
            p_name = p.get("name", "")
            p_type = p.get("article_type", "complementary piece")
            p_brand = p.get("brand", "")
            if p_name:
                pair_names.append(p_name)
                pair_details.append(f"- {p_type}: {p_name} ({p_brand})")

        # Context-rich fallback using the exact names of upselling pieces
        if len(pair_names) >= 3:
            fallback_tip = f"Pair the {anchor_name} with {pair_names[0]} and {pair_names[1]}, grounded by {pair_names[2]} for an impeccable tonal aesthetic."
        elif len(pair_names) >= 2:
            fallback_tip = f"Style the {anchor_name} seamlessly alongside {pair_names[0]} and {pair_names[1]} for an elevated, harmonious look."
        elif len(pair_names) == 1:
            fallback_tip = f"Match the {anchor_name} directly with {pair_names[0]} for a balanced, effortlessly curated silhouette."
        else:
            fallback_tip = f"Ground this {anchor_name} with tailored minimalist tones; keep the lines effortless and refined."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AURA-Fashion/1.0"
        }

        system_instruction = """You are AURA's Elite Runway Stylist & Creative Director.
Synthesize a single, ultra-chic 1-2 sentence styling suggestion explaining HOW to wear and combine the anchor piece with the specific recommended complementary pieces.
Rules:
1. Mention the pieces naturally (e.g., tucking, layering a blazer, matching footwear, tonal harmony, cuffing sleeves).
2. Sound like an effortless personal stylist (modern luxury, high fashion, Gen-Z / quiet luxury aesthetic).
3. Keep it to 1-2 sharp, engaging sentences. Do NOT use bullet points, quotes, or markdown headers."""

        prompt_user = f"""Anchor Piece:
- {anchor_type}: {anchor_name} ({anchor_brand}, {anchor_color})

Recommended Upsell Complementary Pieces:
{chr(10).join(pair_details[:4])}

Write 1-2 concise sentences on how to wear this exact complete look combo together:"""

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt_user}
            ],
            "temperature": 0.85,
            "max_tokens": 120
        }

        try:
            req = urllib.request.Request(self.api_url, data=json.dumps(data).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=3.5) as res:
                res_data = json.loads(res.read().decode("utf-8"))
                tip = res_data["choices"][0]["message"]["content"].strip()
                if tip and len(tip) > 15:
                    return tip.replace('"', '').strip()
        except Exception as e:
            print(f"Notice on combo suggestion generation: {e}")

        return fallback_tip

    def stream_tokens(self, text: str) -> Generator[str, None, None]:
        """Yields words/tokens character-by-character for streaming typewriter effect."""
        for char in text:
            yield char


# Global singleton instance
_placeholder_agent = None

def get_placeholder_agent() -> PlaceholderAgent:
    global _placeholder_agent
    if _placeholder_agent is None:
        _placeholder_agent = PlaceholderAgent()
    return _placeholder_agent
