import json
import csv
import argparse
from tqdm import tqdm
from pymongo import MongoClient, UpdateOne
from pymongo.server_api import ServerApi
import config
from embedding_engine import get_embedding_engine
from index_manager import setup_indexes

def sanitize(row: dict) -> dict:
    """Cleans and casts catalog document types."""
    return {
        "product_id": str(row.get("product_id", "")).strip(),
        "original_id": int(float(row.get("original_id", 0) or 0)),
        "name": str(row.get("name", "")).strip(),
        "brand": str(row.get("brand", "")).strip(),
        "gender": str(row.get("gender", "")).strip(),
        "master_category": str(row.get("master_category", "")).strip(),
        "sub_category": str(row.get("sub_category", "")).strip(),
        "article_type": str(row.get("article_type", "")).strip(),
        "base_color": str(row.get("base_color", "")).strip(),
        "season": str(row.get("season", "")).strip(),
        "year": int(float(row.get("year", 0) or 0)),
        "usage": str(row.get("usage", "")).strip(),
        "image_url": str(row.get("image_url", "")).strip(),
        "price": round(float(row.get("price", 0.0) or 0.0), 2),
        "stock": int(float(row.get("stock", 0) or 0)),
        "rating": round(float(row.get("rating", 0.0) or 0.0), 2),
        "review_count": int(float(row.get("review_count", 0) or 0))
    }

def load_data(filepath: str, limit: int = None) -> list:
    """Loads records using Python standard library."""
    if filepath.endswith(".json"):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [sanitize(r) for r in (data[:limit] if limit else data)]
    elif filepath.endswith(".csv"):
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            records = []
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                records.append(sanitize(row))
            return records
    raise ValueError("Supported formats: .json, .csv")

def ingest(filepath: str = "products_catalog.json", batch_size: int = 256, limit: int = None):
    print(f"Connecting to MongoDB Atlas...")
    client = MongoClient(config.MONGODB_URI, server_api=ServerApi('1'))
    collection = client[config.DB_NAME][config.COLLECTION_NAME]

    setup_indexes(collection)

    records = load_data(filepath, limit=limit)
    print(f"Ingesting {len(records):,} products...")
    engine = get_embedding_engine()

    for i in tqdm(range(0, len(records), batch_size), desc="Ingesting"):
        batch = records[i : i + batch_size]
        texts = [engine.build_search_text(doc) for doc in batch]
        embeddings = engine.generate_embeddings_batch(texts, batch_size=len(batch))

        ops = []
        for doc, st, emb in zip(batch, texts, embeddings):
            doc["search_text"] = st
            doc["embedding"] = emb
            ops.append(UpdateOne({"product_id": doc["product_id"]}, {"$set": doc}, upsert=True))

        if ops:
            collection.bulk_write(ops, ordered=False)

    print(f"Done! Collection total: {collection.count_documents({}):,} items.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest product catalog to MongoDB Atlas")
    parser.add_argument("--file", default="products_catalog.json", help="Path to JSON or CSV file")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items")
    args = parser.parse_args()

    ingest(filepath=args.file, batch_size=args.batch_size, limit=args.limit)
