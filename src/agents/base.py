import os
from typing import Optional
from langchain_groq import ChatGroq
from src import config
from src.search.engine import ProductHybridSearchEngine

# Lazy initialization of LLM
_llm: Optional[ChatGroq] = None

def get_llm() -> ChatGroq:
    """Returns the shared ChatGroq LLM instance (lazy initialized)."""
    global _llm
    if _llm is None:
        groq_api_key = config.GROQ_API_KEY
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing. Please set it in your .env file.")
        _llm = ChatGroq(
            model=config.LLM_MODEL,
            temperature=0.1,
            api_key=groq_api_key
        )
    return _llm

# Lazy initialization of Search Engine
_search_engine: Optional[ProductHybridSearchEngine] = None

def get_search_engine() -> ProductHybridSearchEngine:
    """Returns the shared ProductHybridSearchEngine instance (lazy initialized)."""
    global _search_engine
    if _search_engine is None:
        _search_engine = ProductHybridSearchEngine()
    return _search_engine
