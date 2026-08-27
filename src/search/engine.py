from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from src import config
from src.search.embeddings import get_embedding_engine

def serialize_doc(doc: dict) -> dict:
    """Ensures MongoDB document is JSON/msgpack serializable (e.g. converting ObjectId)."""
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

    def __init__(self, uri: Optional[str] = None):
        connection_uri = uri or config.MONGODB_URI
        if not connection_uri:
            raise ValueError("MONGODB_URI or MONGODB_PASSWORD environment variable is required.")
        self.client = MongoClient(connection_uri, server_api=ServerApi('1'))
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

    def vector_search(self, query: str, filter_dict: Optional[dict] = None, limit: int = 20) -> List[dict]:
        """Runs Atlas Vector Search using sentence-transformers embedding."""
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

    def keyword_search(self, query: str, filter_dict: Optional[dict] = None, limit: int = 20) -> List[dict]:
        """Runs MongoDB text keyword search with regex fallback."""
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
        filter_dict: Optional[dict] = None,
        vec_weight: float = 0.6,
        kw_weight: float = 0.4,
        rrf_k: int = 60,
        limit: int = 10,
        fallback: bool = True
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
        if not ranked and filter_dict and fallback:
            relaxed_filters = {}
            if "gender" in filter_dict: relaxed_filters["gender"] = filter_dict["gender"]
            if "master_category" in filter_dict: relaxed_filters["master_category"] = filter_dict["master_category"]
            if "price" in filter_dict: relaxed_filters["price"] = filter_dict["price"]
            
            if relaxed_filters != filter_dict:
                return self.hybrid_search(query, filter_dict=relaxed_filters, limit=limit, fallback=True)
            else:
                return self.hybrid_search(query, filter_dict=None, limit=limit, fallback=False)

        return ranked[:limit]

    def inspect_category_price_bounds(
        self,
        article_type: Optional[Any] = None,
        master_category: Optional[str] = None,
        gender: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculates minimum, maximum, and average price in MongoDB for the category constraints."""
        match = {}
        if article_type:
            if isinstance(article_type, dict):
                match["article_type"] = article_type
            elif isinstance(article_type, str):
                norm = article_type.strip().lower()
                if norm in ARTICLE_TYPE_SYNONYMS:
                    syns = ARTICLE_TYPE_SYNONYMS[norm]
                    match["article_type"] = syns[0] if len(syns) == 1 else {"$in": syns}
                else:
                    match["article_type"] = article_type.strip()
        if master_category:
            match["master_category"] = master_category
        if gender:
            match["gender"] = gender

        pipeline = [
            {"$match": match if match else {"price": {"$exists": True, "$gt": 0}}},
            {"$group": {
                "_id": None,
                "min_price": {"$min": "$price"},
                "max_price": {"$max": "$price"},
                "avg_price": {"$avg": "$price"},
                "count": {"$sum": 1}
            }}
        ]
        try:
            res = list(self.collection.aggregate(pipeline))
            if res and res[0].get("min_price") is not None:
                return {
                    "min_price": round(float(res[0]["min_price"]), 2),
                    "max_price": round(float(res[0]["max_price"]), 2),
                    "avg_price": round(float(res[0]["avg_price"]), 2),
                    "count": int(res[0]["count"])
                }
        except Exception as e:
            print(f"Price bounds aggregation notice: {e}")

        return {"min_price": 20.0, "max_price": 250.0, "avg_price": 65.0, "count": 100}

    def hybrid_search_with_price_intelligence(
        self,
        query: str,
        filter_dict: Optional[dict] = None,
        limit: int = 15
    ) -> tuple:
        """
        Executes hybrid search with budget & price boundary reasoning.
        Returns: (results, price_analysis_dict)
        """
        filter_dict = filter_dict or {}
        price_filter = filter_dict.get("price", {})
        requested_max_price = price_filter.get("$lte")
        requested_min_price = price_filter.get("$gte")

        category_label = filter_dict.get("article_type") or filter_dict.get("master_category") or "items"
        if isinstance(category_label, dict) and "$in" in category_label:
            category_label = "/".join(category_label["$in"])

        price_analysis = {
            "price_filter_present": bool(price_filter),
            "requested_min_price": requested_min_price,
            "requested_max_price": requested_max_price,
            "price_gap_detected": False,
            "catalog_min_price": None,
            "catalog_avg_price": None,
            "category_name": str(category_label)
        }

        # 1. First attempt: search with full strict filters (fallback disabled to detect price gap)
        results = self.hybrid_search(query=query, filter_dict=filter_dict, limit=limit, fallback=False)

        if results:
            return results, price_analysis

        # 2. If 0 results and a price ceiling was set (e.g. max_price):
        if requested_max_price is not None:
            bounds = self.inspect_category_price_bounds(
                article_type=filter_dict.get("article_type"),
                master_category=filter_dict.get("master_category"),
                gender=filter_dict.get("gender")
            )
            min_catalog_price = bounds.get("min_price", 20.0)
            avg_catalog_price = bounds.get("avg_price", 65.0)

            price_analysis["catalog_min_price"] = min_catalog_price
            price_analysis["catalog_avg_price"] = avg_catalog_price

            if requested_max_price < min_catalog_price:
                price_analysis["price_gap_detected"] = True
                price_analysis["suggested_budget_floor"] = min_catalog_price

                # Relax price filter to retrieve closest available entry-level pieces
                relaxed_filters = filter_dict.copy()
                relaxed_filters.pop("price", None)
                fallback_results = self.hybrid_search(query=query, filter_dict=relaxed_filters, limit=limit, fallback=True)
                
                # Sort fallback results by price ascending to prioritize entry-level pieces
                fallback_results.sort(key=lambda x: x.get("price", 999.0))
                return fallback_results, price_analysis

        # 3. Default fallback if no special price gap
        if not results and filter_dict:
            return self.hybrid_search(query=query, filter_dict=filter_dict, limit=limit, fallback=True), price_analysis

        return results, price_analysis
