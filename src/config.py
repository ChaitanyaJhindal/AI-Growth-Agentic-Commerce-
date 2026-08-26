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

# Distributed Multi-Key Groq Configuration (Prevents Rate Limiting Across Agents)
GROQ_API_KEY_QUERY = os.getenv("GROQ_API_KEY_QUERY", "")
GROQ_API_KEY_CONTEXT = os.getenv("GROQ_API_KEY_CONTEXT", "")
GROQ_API_KEY_UPSELL = os.getenv("GROQ_API_KEY_UPSELL", "")
GROQ_API_KEY_VALIDATION = os.getenv("GROQ_API_KEY_VALIDATION", GROQ_API_KEY_CONTEXT)
GROQ_API_KEY_CAMPAIGN = os.getenv("GROQ_API_KEY_CAMPAIGN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", GROQ_API_KEY_QUERY)

LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

# Voyage AI Embedding Configuration (High-Performance Remote Inference)
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "voyage-3-lite")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "512"))

# Search Text Fields for Hybrid Indexing
SEARCH_TEXT_FIELDS = [
    "name", "brand", "gender", "master_category",
    "sub_category", "article_type", "base_color", "season", "usage"
]

# Razorpay Configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

# WhatsApp Queue & Baileys Configuration
WHATSAPP_QUEUE_COLLECTION = os.getenv("WHATSAPP_QUEUE_COLLECTION", "whatsapp_messages")
WHATSAPP_SESSION_COLLECTION = os.getenv("WHATSAPP_SESSION_COLLECTION", "whatsapp_sessions")
WHATSAPP_MAX_ATTEMPTS = int(os.getenv("WHATSAPP_MAX_ATTEMPTS", "3"))
WHATSAPP_POLL_INTERVAL = float(os.getenv("WHATSAPP_POLL_INTERVAL", "5.0"))
WHATSAPP_RATE_LIMIT_DELAY = float(os.getenv("WHATSAPP_RATE_LIMIT_DELAY", "3.0"))
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")
WHATSAPP_BAILEYS_URL = os.getenv("WHATSAPP_BAILEYS_URL", "http://127.0.0.1:5001")
WHATSAPP_DRY_RUN = os.getenv("WHATSAPP_DRY_RUN", "false").lower() in ("true", "1", "yes")
WHATSAPP_SESSION_DIR = os.getenv("WHATSAPP_SESSION_DIR", "data/baileys_auth")
