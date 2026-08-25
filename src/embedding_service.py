from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from sentence_transformers import SentenceTransformer
from src import config

app = FastAPI(
    title="AURA - Dedicated Embedding Microservice",
    description="High-performance dedicated microservice for 384-dim normalized vector embeddings.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model once on microservice startup
print(f"==> Loading SentenceTransformer model: {config.EMBEDDING_MODEL}...")
_model = SentenceTransformer(config.EMBEDDING_MODEL)
print("==> Model loaded and ready for vector inference!")

class EmbedRequest(BaseModel):
    text: str = Field(..., description="Query or product text to embed")

class EmbedBatchRequest(BaseModel):
    texts: List[str] = Field(..., description="List of texts to embed in batch")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "AURA Dedicated Embedding Engine",
        "model": config.EMBEDDING_MODEL,
        "dimensions": config.EMBEDDING_DIM
    }

@app.post("/embed")
async def embed_single(req: EmbedRequest):
    text = req.text.strip() if req.text else ""
    if not text:
        return {"embedding": [0.0] * config.EMBEDDING_DIM}
    vec = _model.encode(text, normalize_embeddings=True).tolist()
    return {
        "embedding": vec,
        "dimensions": len(vec)
    }

@app.post("/embed/batch")
async def embed_batch(req: EmbedBatchRequest):
    cleaned = [t if (t and t.strip()) else " " for t in req.texts]
    if not cleaned:
        return {"embeddings": []}
    vecs = _model.encode(cleaned, batch_size=64, normalize_embeddings=True).tolist()
    return {
        "embeddings": vecs,
        "count": len(vecs)
    }

if __name__ == "__main__":
    uvicorn.run("src.embedding_service:app", host="0.0.0.0", port=8001, reload=False)
