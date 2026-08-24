import json
from pymongo.collection import Collection
from pymongo.operations import SearchIndexModel
import config

VECTOR_INDEX_DEF = {
    "fields": [
        {"type": "vector", "path": "embedding", "numDimensions": config.EMBEDDING_DIM, "similarity": "cosine"},
        {"type": "filter", "path": "brand"},
        {"type": "filter", "path": "gender"},
        {"type": "filter", "path": "master_category"},
        {"type": "filter", "path": "sub_category"},
        {"type": "filter", "path": "article_type"},
        {"type": "filter", "path": "base_color"},
        {"type": "filter", "path": "season"},
        {"type": "filter", "path": "usage"},
        {"type": "filter", "path": "price"},
        {"type": "filter", "path": "stock"},
        {"type": "filter", "path": "rating"}
    ]
}

def setup_indexes(collection: Collection):
    """Creates text, filter, and Atlas vector search indexes."""
    # 1. Unique ID index
    collection.create_index("product_id", unique=True)

    # 2. Text Search index
    collection.create_index(
        [("name", "text"), ("brand", "text"), ("article_type", "text"), ("search_text", "text")],
        weights={"name": 10, "brand": 5, "article_type": 5, "search_text": 1},
        name="idx_text_search"
    )

    # 3. Metadata Filter indexes
    for field in ["brand", "gender", "master_category", "sub_category", "article_type", "base_color", "season", "usage", "price", "stock", "rating"]:
        collection.create_index([(field, 1)])

    # 4. Atlas Vector Search index
    try:
        existing = [idx.get("name") for idx in collection.list_search_indexes()]
        if config.VECTOR_INDEX_NAME not in existing:
            collection.create_search_index(
                model=SearchIndexModel(definition=VECTOR_INDEX_DEF, name=config.VECTOR_INDEX_NAME, type="vectorSearch")
            )
    except Exception as e:
        print(f"Notice on Atlas Search index creation: {e}")
