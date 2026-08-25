import json
import random
import time
import urllib.request
from typing import List, Dict, Any, Generator, AsyncGenerator
from src import config

# Curated High-Vibe Gen-Z Fashion Prompts Buffer
DEFAULT_GENZ_PROMPTS = [
    "main character energy, black oversized tailored blazer...",
    "clean girl aesthetic linen button-down for Sunday brunch...",
    "drop a vibe for a late night rooftop fit under $90...",
    "coastal granddaughter mood, breezy white sundress...",
    "stealth wealth minimal white leather sneakers on a budget...",
    "y2k vintage chronograph watch for the ultimate wrist flex...",
    "gym rat chic, breathable dry-fit compression tee under $40...",
    "quiet luxury cashmere knit sweater for evening dinner...",
    "blokecore retro jersey drip paired with relaxed denim...",
    "streetwear essentials, matte black cargo trousers under $60...",
    "old money aesthetic polo shirt in rich navy blue...",
    "dark academia tailored trousers with a structured leather belt...",
    "sunset festival outfit, crochet top with vintage sunglasses...",
    "scandinavian minimalism, neutral tone crewneck sweatshirt..."
]

class PlaceholderAgent:
    """
    Gen-Z Aesthetic Dynamic Placeholder Agent.
    Powered by `openai/gpt-oss-20b` on Groq (Temperature = 0.95).
    Generates short, punchy, engaging fashion search prompts for high-converting UX.
    """

    def __init__(self, model: str = "openai/gpt-oss-20b"):
        self.model = model
        # Use Key 2 (Context/Validation key) or fallback for lowest latency
        self.api_key = config.GROQ_API_KEY_CONTEXT or config.GROQ_API_KEY_QUERY or config.GROQ_API_KEY
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self._prompt_pool: List[str] = list(DEFAULT_GENZ_PROMPTS)
        random.shuffle(self._prompt_pool)
        self._pool_index: int = 0

    def get_next_prompt(self) -> str:
        """Returns the next prompt from the active pool, rotating smoothly."""
        if not self._prompt_pool:
            self._prompt_pool = list(DEFAULT_GENZ_PROMPTS)
            random.shuffle(self._prompt_pool)

        prompt = self._prompt_pool[self._pool_index % len(self._prompt_pool)]
        self._pool_index += 1
        return prompt

    def generate_fresh_batch(self, count: int = 6) -> List[str]:
        """Calls Groq `openai/gpt-oss-20b` to generate a fresh batch of Gen-Z search prompts."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AURA-Fashion/1.0"
        }

        system_instruction = """You are a Gen-Z High-Fashion Trendsetter & UX Copywriter for AURA Luxury Concierge.
Generate creative, short, catchy fashion search queries that Gen-Z and luxury shoppers would type in an AI search bar.
Rules:
1. Keep each prompt between 5 to 10 words.
2. Use aesthetics like: 'clean girl', 'old money', 'streetwear drip', 'coastal granddaughter', 'quiet luxury', 'dark academia', 'y2k', 'main character'.
3. Mention realistic fashion items (blazers, sneakers, linen shirts, watches, cargo pants, sunglasses, dresses, hoodies).
4. End each prompt with '...'
5. Return ONLY a valid JSON array of strings."""

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Generate {count} unique Gen-Z fashion search prompts as JSON array."}
            ],
            "temperature": 0.95
        }

        try:
            req = urllib.request.Request(self.api_url, data=json.dumps(data).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=4) as res:
                res_data = json.loads(res.read().decode("utf-8"))
                raw_text = res_data["choices"][0]["message"]["content"].strip()
                # Parse JSON array
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

        return DEFAULT_GENZ_PROMPTS[:count]

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
