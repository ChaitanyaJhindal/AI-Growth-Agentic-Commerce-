import os
import sys

# Ensure root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agents.base import get_search_engine

def main():
    engine = get_search_engine()
    res = engine.collection.aggregate([
        {"$group": {
            "_id": "$article_type",
            "min_price": {"$min": "$price"},
            "max_price": {"$max": "$price"},
            "avg_price": {"$avg": "$price"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 15}
    ])
    for r in res:
        print(f"{r['_id']}: Count={r['count']}, Min=${r['min_price']:.2f}, Max=${r['max_price']:.2f}, Avg=${r['avg_price']:.2f}")

if __name__ == "__main__":
    main()
