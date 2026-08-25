import sys
import argparse
from tabulate import tabulate
from src.search.engine import ProductHybridSearchEngine

def run():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description="MongoDB Atlas Product Hybrid Search")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--mode", choices=["hybrid", "vector", "keyword"], default="hybrid")
    parser.add_argument("--brand", help="Filter by brand")
    parser.add_argument("--gender", help="Filter by gender")
    parser.add_argument("--category", help="Filter by master_category")
    parser.add_argument("--color", help="Filter by base_color")
    parser.add_argument("--min-price", type=float, help="Min price")
    parser.add_argument("--max-price", type=float, help="Max price")
    parser.add_argument("--in-stock", action="store_true", help="In-stock items only")
    parser.add_argument("--min-rating", type=float, help="Min rating")
    parser.add_argument("--limit", type=int, default=5, help="Number of results")
    args = parser.parse_args()

    engine = ProductHybridSearchEngine()
    query = args.query or input("Search query: ").strip()
    if not query:
        return

    filter_dict = engine.build_filter(
        brand=args.brand,
        gender=args.gender,
        master_category=args.category,
        base_color=args.color,
        min_price=args.min_price,
        max_price=args.max_price,
        in_stock=args.in_stock,
        min_rating=args.min_rating
    )

    print(f"\nSearching '{query}' [Filters: {filter_dict or 'None'}]...\n")

    if args.mode == "vector":
        results = engine.vector_search(query, filter_dict=filter_dict, limit=args.limit)
    elif args.mode == "keyword":
        results = engine.keyword_search(query, filter_dict=filter_dict, limit=args.limit)
    else:
        results = engine.hybrid_search(query, filter_dict=filter_dict, limit=args.limit)

    if not results:
        print("No products found.")
        return

    rows = []
    for i, p in enumerate(results, 1):
        name = p.get('name', 'N/A')[:32]
        price = f"${p.get('price', 0):.2f}"
        rating = f"{p.get('rating', 0):.1f} ({p.get('review_count', 0)})"
        rows.append([
            i, p.get('product_id'), name, p.get('brand'), p.get('gender'),
            p.get('base_color'), price, p.get('stock'), rating, p.get('rrf_score', '-')
        ])

    headers = ["#", "ID", "Name", "Brand", "Gender", "Color", "Price", "Stock", "Rating", "RRF Score"]
    print(tabulate(rows, headers=headers, tablefmt="grid"))

if __name__ == "__main__":
    run()
