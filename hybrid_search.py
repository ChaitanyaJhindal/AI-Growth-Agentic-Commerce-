from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import config
from embedding_engine import get_embedding_engine

def serialize_doc(doc: dict) -> dict:
    """Ensures document is JSON/msgpack serializable (e.g. stringifying ObjectId)."""
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# Common synonyms and catalog normalization mapping
ARTICLE_TYPE_SYNONYMS = {
    "sneakers": ["Casual Shoes", "Sports Shoes"],
    "sneaker": ["Casual Shoes", "Sports Shoes"],
    "running shoes": ["Sports Shoes"],
    "running shoe": ["Sports Shoes"],
    "trainer": ["Sports Shoes", "Casual Shoes"],
    "trainers": ["Sports Shoes", "Casual Shoes"],
    "watch": ["Watches"],
    "watches": ["Watches"],
    "tshirt": ["Tshirts"],
    "t-shirt": ["Tshirts"],
    "tee": ["Tshirts"],
    "shirt": ["Shirts"],
    "denim": ["Jeans"],
    "pants": ["Trousers", "Track Pants", "Jeans"]
}

class ProductHybridSearchEngine:
    """Combines Atlas Vector Search + MongoDB Text Search + Metadata Filtering via RRF."""

    def __init__(self, uri: str = None):
        self.client = MongoClient(uri or config.MONGODB_URI, server_api=ServerApi('1'))
        self.collection = self.client[config.DB_NAME][config.COLLECTION_NAME]
        self.engine = get_embedding_engine()

    @staticmethod
    def build_filter(
        brand: Optional[str] = None,
        gender: Optional[str] = None,
        master_category: Optional[str] = None,
        sub_category: Optional[str] = None,
        article_type: Optional[str] = None,
        base_color: Optional[str] = None,
        season: Optional[str] = None,
        usage: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock: bool = False,
        min_rating: Optional[float] = None
    ) -> Dict[str, Any]:
        """Constructs robust MongoDB query filters."""
        query = {}
        for field, val in [
            ("brand", brand), ("gender", gender), ("master_category", master_category),
            ("sub_category", sub_category), ("base_color", base_color),
            ("season", season), ("usage", usage)
        ]:
            if val:
                query[field] = val.strip()

        # Handle article_type normalization
        if article_type:
            norm_key = article_type.strip().lower()
            if norm_key in ARTICLE_TYPE_SYNONYMS:
                syns = ARTICLE_TYPE_SYNONYMS[norm_key]
                if len(syns) == 1:
                    query["article_type"] = syns[0]
                else:
                    query["article_type"] = {"$in": syns}
            else:
                query["article_type"] = article_type.strip()

        price = {}
        if min_price is not None: price["$gte"] = float(min_price)
        if max_price is not None: price["$lte"] = float(max_price)
        if price: query["price"] = price

        if in_stock: query["stock"] = {"$gt": 0}
        if min_rating is not None: query["rating"] = {"$gte": float(min_rating)}

        return query

    def vector_search(self, query: str, filter_dict: dict = None, limit: int = 20) -> List[dict]:
        """Runs Atlas Vector Search using all-MiniLM-L6-v2."""
        vec = self.engine.generate_embedding(query)
        stage = {
            "$vectorSearch": {
                "index": config.VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": vec,
                "numCandidates": max(limit * 5, 100),
                "limit": limit
            }
        }
        if filter_dict:
            stage["$vectorSearch"]["filter"] = filter_dict

        try:
            docs = list(self.collection.aggregate([stage, {"$project": {"embedding": 0, "vector_score": {"$meta": "vectorSearchScore"}}}]))
            return [serialize_doc(d) for d in docs]
        except Exception:
            return []

    def keyword_search(self, query: str, filter_dict: dict = None, limit: int = 20) -> List[dict]:
        """Runs MongoDB text keyword search."""
        match = {"$text": {"$search": query}}
        if filter_dict:
            match.update(filter_dict)

        pipeline = [
            {"$match": match},
            {"$project": {"embedding": 0, "keyword_score": {"$meta": "textScore"}}},
            {"$sort": {"keyword_score": -1}},
            {"$limit": limit}
        ]
        try:
            docs = list(self.collection.aggregate(pipeline))
            return [serialize_doc(d) for d in docs]
        except Exception:
            regex_match = {"$or": [{"name": {"$regex": query, "$options": "i"}}, {"brand": {"$regex": query, "$options": "i"}}]}
            if filter_dict: regex_match.update(filter_dict)
            docs = list(self.collection.find(regex_match, {"embedding": 0}).limit(limit))
            return [serialize_doc(d) for d in docs]

    def hybrid_search(
        self,
        query: str,
        filter_dict: dict = None,
        vec_weight: float = 0.6,
        kw_weight: float = 0.4,
        rrf_k: int = 60,
        limit: int = 10
    ) -> List[dict]:
        """Fuses Vector Search + Keyword Search with Reciprocal Rank Fusion (RRF) & Smart Fallback."""
        vec_results = self.vector_search(query, filter_dict=filter_dict, limit=limit * 3)
        kw_results = self.keyword_search(query, filter_dict=filter_dict, limit=limit * 3)

        items = {}
        rrf_scores = {}

        for rank, doc in enumerate(vec_results, 1):
            pid = doc.get("product_id") or str(doc["_id"])
            items[pid] = serialize_doc(doc)
            items[pid]["vector_rank"] = rank
            rrf_scores[pid] = rrf_scores.get(pid, 0.0) + (vec_weight / (rrf_k + rank))

        for rank, doc in enumerate(kw_results, 1):
            pid = doc.get("product_id") or str(doc["_id"])
            if pid not in items:
                items[pid] = serialize_doc(doc)
            items[pid]["keyword_rank"] = rank
            rrf_scores[pid] = rrf_scores.get(pid, 0.0) + (kw_weight / (rrf_k + rank))

        ranked = []
        for pid, score in rrf_scores.items():
            doc = items[pid]
            doc["rrf_score"] = round(score, 6)
            ranked.append(doc)

        ranked.sort(key=lambda x: x["rrf_score"], reverse=True)

        # Smart Fallback: If strict filtering returned 0 results, relax constraints gracefully
        if not ranked and filter_dict:
            relaxed_filters = {}
            if "gender" in filter_dict: relaxed_filters["gender"] = filter_dict["gender"]
            if "master_category" in filter_dict: relaxed_filters["master_category"] = filter_dict["master_category"]
            if "price" in filter_dict: relaxed_filters["price"] = filter_dict["price"]
            
            if relaxed_filters != filter_dict:
                return self.hybrid_search(query, filter_dict=relaxed_filters, limit=limit)
            else:
                return self.hybrid_search(query, filter_dict=None, limit=limit)

        return ranked[:limit]
