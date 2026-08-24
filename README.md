# MongoDB Atlas + PyMongo E-Commerce Hybrid Search Engine

High-performance **Hybrid Search Engine** (Vector Search + Full-Text Keyword Search + Structured Metadata Filtering) powered by **MongoDB Atlas**, **PyMongo**, and **Sentence-Transformers (`all-MiniLM-L6-v2`)**.

---

## 🏗️ Architecture & Search Strategy

```
                          User Search Query & Filters
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
                 ▼                                       ▼
    ┌───────────────────────────┐           ┌───────────────────────────┐
    │    Vector Search (ANN)    │           │    Keyword Text Search    │
    │  `all-MiniLM-L6-v2` (384) │           │     MongoDB `$text` Index │
    │   Cosine Similarity       │           │     `textScore` Relevance │
    └────────────┬──────────────┘           └────────────┬──────────────┘
                 │                                       │
                 │   Pre-filtered by Metadata:           │
                 │   (Brand, Gender, Price, Stock, etc.) │
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     ▼
                    ┌─────────────────────────────────┐
                    │  Reciprocal Rank Fusion (RRF)   │
                    │  + Dynamic Score Normalization  │
                    └────────────────┬────────────────┘
                                     ▼
                        Ranked Product Results
```

### 1. Document Schema & Embedding Rules

Each product is stored in MongoDB Atlas with structured JSON fields:

```json
{
  "product_id": "PROD-15970",
  "original_id": 15970,
  "name": "Turtle Check Men Navy Blue Shirt",
  "brand": "Turtle",
  "gender": "Men",
  "master_category": "Apparel",
  "sub_category": "Topwear",
  "article_type": "Shirts",
  "base_color": "Navy Blue",
  "season": "Fall",
  "year": 2011,
  "usage": "Casual",
  "image_url": "https://assets.myntassets.com/v1/images/style/properties/7a5b82d1372a7a5c6de67ae7a314fd91_images.jpg",
  "price": 51.38,
  "stock": 0,
  "rating": 4.1,
  "review_count": 217,
  "search_text": "Turtle Check Men Navy Blue Shirt Turtle Men Apparel Topwear Shirts Navy Blue Fall Casual",
  "embedding": [0.0123, -0.0456, ..., 0.0891]
}
```

- **`search_text` Composition**:
  `name` + `brand` + `gender` + `master_category` + `sub_category` + `article_type` + `base_color` + `season` + `usage`
- **`embedding` Field**:
  Dense 384-dimensional float vector generated strictly from `search_text` using `all-MiniLM-L6-v2`.
- **Excluded From Embedding**:
  `product_id`, `original_id`, `image_url`, `price`, `stock`, `rating`, `review_count`, `year` are strictly stored as queryable metadata attributes for indexing and filtering.

---

## ⚡ Atlas Vector Search Index Configuration

The Vector Search index (`vector_index`) in MongoDB Atlas is defined as follows (also exported in [`atlas_vector_search_index.json`](file:///c:/Users/Chait/Downloads/Desktop/AI%20Growth%20&%20Agentic%20Commerce/atlas_vector_search_index.json)):

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 384,
      "similarity": "cosine"
    },
    { "type": "filter", "path": "brand" },
    { "type": "filter", "path": "gender" },
    { "type": "filter", "path": "master_category" },
    { "type": "filter", "path": "sub_category" },
    { "type": "filter", "path": "article_type" },
    { "type": "filter", "path": "base_color" },
    { "type": "filter", "path": "season" },
    { "type": "filter", "path": "usage" },
    { "type": "filter", "path": "price" },
    { "type": "filter", "path": "stock" },
    { "type": "filter", "path": "rating" }
  ]
}
```

> **To create via MongoDB Atlas UI**:
> 1. In your MongoDB Atlas cluster, navigate to **Atlas Search** (or **Search / Vector Search**).
> 2. Click **Create Search Index** -> Select **JSON Editor**.
> 3. Select your Database (`ecommerce_catalog`) and Collection (`products`).
> 4. Set Index Name to: `vector_index`.
> 5. Paste the JSON from [`atlas_vector_search_index.json`](file:///c:/Users/Chait/Downloads/Desktop/AI%20Growth%20&%20Agentic%20Commerce/atlas_vector_search_index.json) and click **Create Search Index**.

---

## 🚀 Quickstart & Setup

### 1. Configure Credentials
Copy `.env.example` to `.env` and fill in your MongoDB password:
```bash
cp .env.example .env
```
In `.env`:
```env
MONGODB_PASSWORD=your_actual_password
```

### 2. Test Connection
Verify connection and ping your Atlas deployment:
```bash
python test_connection.py
```
*(Or pass the password directly via `--password <your_password>`)*

### 3. Run Pipeline Tests
Run the local unit test suite to verify schema sanitation, embedding generation, and metadata filter creation:
```bash
python test_pipeline.py
```

### 4. Ingest Product Catalog with Embeddings
Ingest products into MongoDB Atlas with automated index creation and batch embeddings:
```bash
# Ingest full dataset (44,424 items):
python ingest.py --batch-size 256

# Or ingest a quick test sample (e.g. 500 items):
python ingest.py --limit 500
```

---

## 🔍 Hybrid Search CLI Usage

Use `search_cli.py` to search interactively or with precise metadata filters:

### Semantic Hybrid Search
```bash
python search_cli.py "breathable summer running shoes" --gender Men --min-rating 4.0 --in-stock
```

### Keyword Exact Search
```bash
python search_cli.py "Peter England Blue Jeans" --mode keyword
```

### Vector Only Search
```bash
python search_cli.py "water resistant luxury wrist watch" --mode vector --max-price 150
```

### Advanced Multi-Filter Search
```bash
python search_cli.py "casual t-shirt" --brand Puma --gender Men --min-price 20 --max-price 60 --color Grey --in-stock --limit 5
```

---

## 💻 Python Code Usage

You can import and use `ProductHybridSearchEngine` in any Python application or API:

```python
from hybrid_search import ProductHybridSearchEngine

engine = ProductHybridSearchEngine()

# 1. Build metadata filter
filter_query = engine.build_metadata_filter(
    brand="Puma",
    gender="Men",
    min_price=20.0,
    max_price=80.0,
    in_stock_only=True,
    min_rating=4.0
)

# 2. Execute hybrid search
results = engine.hybrid_search(
    query="lightweight gym training shoes",
    filter_query=filter_query,
    vector_weight=0.6,
    keyword_weight=0.4,
    limit=10
)

for product in results:
    print(f"[{product['product_id']}] {product['name']} - ${product['price']} | RRF Score: {product['rrf_score']}")
```

---

## 📊 Dataset Columns Reference

| Field | Description | Sample Value |
| :--- | :--- | :--- |
| `product_id` | Unique ID | `PROD-15970` |
| `original_id` | Dataset numerical ID | `15970` |
| `name` | Product display name | `Turtle Check Men Navy Blue Shirt` |
| `brand` | Extracted brand name | `Turtle` |
| `gender` | Gender target | `Men`, `Women`, `Unisex`, `Boys`, `Girls` |
| `master_category` | High-level category | `Apparel`, `Footwear`, `Accessories` |
| `sub_category` | Sub-category | `Topwear`, `Shoes`, `Watches`, `Bags` |
| `article_type` | Specific article type | `Shirts`, `Jeans`, `Casual Shoes`, `Tshirts` |
| `base_color` | Base color | `Navy Blue`, `Black`, `White`, `Blue` |
| `season` | Season | `Fall`, `Summer`, `Winter`, `Spring` |
| `year` | Catalog year | `2011`, `2016`, `2018` |
| `usage` | Intended usage | `Casual`, `Sports`, `Formal`, `Ethnic` |
| `image_url` | Direct Remote CDN Image URL | `https://assets.myntassets.com/...` |
| `price` | Price (USD) | `51.38` |
| `stock` | Stock count | `0` to `50` |
| `rating` | Rating | `4.1` |
| `review_count` | Review count | `217` |
| `search_text` | Generated searchable text string | `Turtle Check Men Navy Blue Shirt Turtle Men Apparel Topwear Shirts Navy Blue Fall Casual` |
| `embedding` | 384-dimensional vector | `[-0.0273, 0.0750, ...]` |
#   A I - G r o w t h - A g e n t i c - C o m m e r c e -  
 