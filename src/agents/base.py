import os
from typing import Optional, Dict, Tuple
from langchain_groq import ChatGroq
from src import config
from src.search.engine import ProductHybridSearchEngine

# Agent-to-Key Mapping for Rate Limit Distribution
AGENT_KEY_MAP = {
    "query": config.GROQ_API_KEY_QUERY,
    "context": config.GROQ_API_KEY_CONTEXT,
    "validation": config.GROQ_API_KEY_VALIDATION,
    "upsell": config.GROQ_API_KEY_UPSELL,
    "campaign": config.GROQ_API_KEY_CAMPAIGN,
    "default": config.GROQ_API_KEY_QUERY
}

# LLM Cache keyed by (temperature, api_key)
_llm_cache: Dict[Tuple[float, str], ChatGroq] = {}

def get_llm(temperature: float = 0.1, agent_name: str = "default") -> ChatGroq:
    """
    Returns a ChatGroq LLM instance configured with dedicated API key per agent.
    - Query Agent -> Key 1
    - Context & Validation Agents -> Key 2
    - Upsell Stylist Agent -> Key 3
    """
    global _llm_cache
    api_key = AGENT_KEY_MAP.get(agent_name, config.GROQ_API_KEY_QUERY)
    if not api_key:
        api_key = config.GROQ_API_KEY_QUERY or config.GROQ_API_KEY

    cache_key = (round(temperature, 2), api_key)
    if cache_key not in _llm_cache:
        _llm_cache[cache_key] = ChatGroq(
            model=config.LLM_MODEL,
            temperature=temperature,
            api_key=api_key
        )
    return _llm_cache[cache_key]

# Lazy initialization of Search Engine
_search_engine: Optional[ProductHybridSearchEngine] = None

def get_search_engine() -> ProductHybridSearchEngine:
    """Returns the shared ProductHybridSearchEngine instance (lazy initialized)."""
    global _search_engine
    if _search_engine is None:
        _search_engine = ProductHybridSearchEngine()
    return _search_engine
