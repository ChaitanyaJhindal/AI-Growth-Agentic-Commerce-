import os
import urllib.parse
from dotenv import load_dotenv

# Fix DNS SRV lookup timeout on Windows
try:
    import dns.resolver
    if dns.resolver.default_resolver is None:
        dns.resolver.default_resolver = dns.resolver.Resolver(configure=True)
    for ns in ['8.8.8.8', '1.1.1.1']:
        if ns not in dns.resolver.default_resolver.nameservers:
            dns.resolver.default_resolver.nameservers.append(ns)
except Exception:
    pass

load_dotenv()

# MongoDB Configuration
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD", "")
DEFAULT_URI_TEMPLATE = "mongodb+srv://chaitanyavedansh_db_user:{password}@cluster0.gdjxqnz.mongodb.net/?appName=Cluster0"

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI and MONGODB_PASSWORD:
    MONGODB_URI = DEFAULT_URI_TEMPLATE.format(password=urllib.parse.quote_plus(MONGODB_PASSWORD))

DB_NAME = os.getenv("MONGODB_DB_NAME", "ecommerce_catalog")
COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "products")
VECTOR_INDEX_NAME = os.getenv("MONGODB_VECTOR_INDEX_NAME", "vector_index")

# LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

# Embedding Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Search Text Fields for Hybrid Indexing
SEARCH_TEXT_FIELDS = [
    "name", "brand", "gender", "master_category",
    "sub_category", "article_type", "base_color", "season", "usage"
]

# Razorpay Configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

