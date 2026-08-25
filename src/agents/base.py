import os
from typing import Optional, Dict
from langchain_groq import ChatGroq
from src import config
from src.search.engine import ProductHybridSearchEngine

# LLM Cache per temperature
_llm_cache: Dict[float, ChatGroq] = {}

def get_llm(temperature: float = 0.1) -> ChatGroq:
    """Returns a ChatGroq LLM instance configured with the specified temperature (cached)."""
    global _llm_cache
    if temperature not in _llm_cache:
        groq_api_key = config.GROQ_API_KEY
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing. Please set it in your .env file.")
        _llm_cache[temperature] = ChatGroq(
            model=config.LLM_MODEL,
            temperature=temperature,
            api_key=groq_api_key
        )
    return _llm_cache[temperature]

# Lazy initialization of Search Engine
_search_engine: Optional[ProductHybridSearchEngine] = None

def get_search_engine() -> ProductHybridSearchEngine:
    """Returns the shared ProductHybridSearchEngine instance (lazy initialized)."""
    global _search_engine
    if _search_engine is None:
        _search_engine = ProductHybridSearchEngine()
    return _search_engine
