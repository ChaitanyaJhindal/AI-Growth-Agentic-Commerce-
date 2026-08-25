from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from src import config

class EmbeddingEngine:
    """Generates 384-dim normalized vector embeddings using SentenceTransformer."""

    def __init__(self, model_name: str = config.EMBEDDING_MODEL):
        self.model = SentenceTransformer(model_name)
        self.dimensions = config.EMBEDDING_DIM

    @staticmethod
    def build_search_text(doc: Dict[str, Any]) -> str:
        """Combines the 9 specified text fields into a unified search_text string."""
        tokens = [str(doc[f]).strip() for f in config.SEARCH_TEXT_FIELDS if doc.get(f)]
        return " ".join(tokens)

    def generate_embedding(self, text: str) -> List[float]:
        """Encodes a single text query into a normalized embedding vector."""
        if not text or not text.strip():
            return [0.0] * self.dimensions
        return self.model.encode(text, normalize_embeddings=True).tolist()

    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 256) -> List[List[float]]:
        """Encodes a batch of texts efficiently."""
        cleaned = [t if (t and t.strip()) else " " for t in texts]
        return self.model.encode(cleaned, batch_size=batch_size, normalize_embeddings=True).tolist()

# Lazy-loaded singleton instance
_engine: Optional[EmbeddingEngine] = None

def get_embedding_engine() -> EmbeddingEngine:
    """Returns or initializes the global EmbeddingEngine singleton."""
    global _engine
    if _engine is None:
        _engine = EmbeddingEngine()
    return _engine
