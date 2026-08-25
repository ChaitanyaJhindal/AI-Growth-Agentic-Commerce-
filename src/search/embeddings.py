import json
import urllib.request
from typing import List, Dict, Any, Optional
from src import config

class EmbeddingEngine:
    """
    Robust Dual-Mode Embedding Engine:
    1. Remote Microservice Mode: Offloads inference to dedicated service over HTTP (zero memory load on main API).
    2. Local Fallback Mode: Runs lightweight CPU-only SentenceTransformer locally if microservice is offline.
    """

    def __init__(self, model_name: str = config.EMBEDDING_MODEL, service_url: Optional[str] = None):
        self.model_name = model_name
        self.dimensions = config.EMBEDDING_DIM
        self.service_url = (service_url or config.EMBEDDING_SERVICE_URL).rstrip("/")
        self._local_model = None

    @property
    def local_model(self):
        """Lazy-loads local SentenceTransformer model only when needed as fallback."""
        if self._local_model is None:
            try:
                import torch
                torch.set_grad_enabled(False)
                torch.set_num_threads(1)
            except Exception:
                pass
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer(self.model_name)
        return self._local_model

    @staticmethod
    def build_search_text(doc: Dict[str, Any]) -> str:
        """Combines catalog text fields into a unified search_text string."""
        tokens = [str(doc[f]).strip() for f in config.SEARCH_TEXT_FIELDS if doc.get(f)]
        return " ".join(tokens)

    def generate_embedding(self, text: str) -> List[float]:
        """Generates a 384-dim normalized embedding vector (remote microservice first, local fallback)."""
        if not text or not text.strip():
            return [0.0] * self.dimensions

        cleaned = text.strip()

        # Try Remote Microservice first if configured
        if self.service_url:
            try:
                req = urllib.request.Request(
                    f"{self.service_url}/embed",
                    data=json.dumps({"text": cleaned}).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=4) as res:
                    if res.status == 200:
                        data = json.loads(res.read().decode("utf-8"))
                        if "embedding" in data:
                            return data["embedding"]
            except Exception as e:
                # Log and fallback seamlessly
                pass

        # Local Fallback
        return self.local_model.encode(cleaned, normalize_embeddings=True).tolist()

    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 256) -> List[List[float]]:
        """Generates embeddings for a batch of texts (remote microservice first, local fallback)."""
        cleaned = [t if (t and t.strip()) else " " for t in texts]
        if not cleaned:
            return []

        if self.service_url:
            try:
                req = urllib.request.Request(
                    f"{self.service_url}/embed/batch",
                    data=json.dumps({"texts": cleaned}).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as res:
                    if res.status == 200:
                        data = json.loads(res.read().decode("utf-8"))
                        if "embeddings" in data:
                            return data["embeddings"]
            except Exception as e:
                pass

        # Local Fallback
        return self.local_model.encode(cleaned, batch_size=batch_size, normalize_embeddings=True).tolist()

# Lazy-loaded singleton instance
_engine: Optional[EmbeddingEngine] = None

def get_embedding_engine() -> EmbeddingEngine:
    """Returns or initializes the global EmbeddingEngine singleton."""
    global _engine
    if _engine is None:
        _engine = EmbeddingEngine()
    return _engine
