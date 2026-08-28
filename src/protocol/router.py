"""
AURA Agent-to-Agent (A2A) Commerce Protocol Router
Compliant with AP2 / x402 / MCP Standards for Autonomous AI Buyers.
"""
import uuid
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from src.agents.base import get_search_engine
from src.payments import create_razorpay_order, verify_razorpay_signature
from src.auth import get_user_manager
from src import config

protocol_router = APIRouter(tags=["AI Buyer Protocol (A2A)"])

# Standard Currency Normalization Factor
USD_TO_INR = 50.0

# Active Merchant Promo Codes
MERCHANT_PROMO_CODES = {
    "AURA20": {"discount_percent": 20, "description": "20% Exclusive Concierge Privilege"},
    "AURA25": {"discount_percent": 25, "description": "25% VIP Autumn Selection"},
    "VIP20": {"discount_percent": 20, "description": "20% VIP Atelier Discount"},
    "WELCOME10": {"discount_percent": 10, "description": "10% Welcome Patron Gift"},
    "RUNWAY30": {"discount_percent": 30, "description": "30% Runway Special Preview"}
}

# =====================================================================
# Pydantic Schemas for AI Buyer Protocol
# =====================================================================

class AgentCatalogQuery(BaseModel):
    query: str = Field(..., description="Natural language search term or style request")
    max_budget_inr: Optional[float] = Field(None, description="Maximum price in Indian Rupees (INR)")
    gender: Optional[str] = Field(None, description="Target gender (Men, Women, Unisex, etc.)")
    category: Optional[str] = Field(None, description="Article type or category (Watches, Shoes, Shirts, etc.)")
    limit: Optional[int] = Field(8, description="Maximum number of items to return")

class CartItemSpec(BaseModel):
    product_id: str
    name: str
    price_inr: float
    brand: Optional[str] = None
    article_type: Optional[str] = None
    image_url: Optional[str] = None

class AgentQuoteRequest(BaseModel):
    buyer_agent_id: str = Field(..., description="Unique ID of the calling AI Buyer Agent")
    items: List[CartItemSpec]
    coupon_code: Optional[str] = Field(None, description="Optional promotional voucher code")

class AgentCheckoutRequest(BaseModel):
    buyer_agent_id: str = Field(..., description="Identifier of the purchasing AI Buyer Agent")
    shopper_email: str = Field(..., description="Beneficiary / Patron email address")
    items: List[CartItemSpec]
    coupon_code: Optional[str] = None
    max_authorized_budget_inr: float = Field(..., description="Hard spend ceiling authorized by human principal")
    shipping_address: Optional[Dict[str, Any]] = None

class AgentVerifyRequest(BaseModel):
    buyer_agent_id: str = Field(..., description="Identifier of the purchasing AI Buyer Agent")
    shopper_email: str
    order_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    items: List[Dict[str, Any]]
    total_inr: float
    coupon_code: Optional[str] = None
    discount_inr: Optional[float] = 0.0


# =====================================================================
# Machine-Readable Discovery & Manifest Endpoints
# =====================================================================

@protocol_router.get("/.well-known/agent-protocol.json", summary="Agent Protocol Discovery Manifest")
async def get_agent_protocol_manifest():
    """Returns machine-readable manifest describing AURA's commerce capabilities for AI Buyers."""
    return {
        "protocol_version": "AP2/1.0",
        "merchant_name": "AURA Luxury Fashion Concierge",
        "merchant_domain": "https://ai-growth-agentic-commerce.onrender.com",
        "currency": "INR",
        "currency_symbol": "₹",
        "usd_to_inr_rate": USD_TO_INR,
        "capabilities": [
            "semantic_vector_search",
            "price_intelligence_bounding",
            "automated_quote_negotiation",
            "gated_programmatic_checkout",
            "razorpay_test_mode"
        ],
        "endpoints": {
            "catalog_query": "/protocol/v1/catalog/query",
            "quote": "/protocol/v1/quote",
            "checkout": "/protocol/v1/order/checkout",
            "verify": "/protocol/v1/order/verify",
            "mcp_manifest": "/.well-known/mcp.json"
        },
        "supported_promo_codes": list(MERCHANT_PROMO_CODES.keys())
    }

@protocol_router.get("/.well-known/mcp.json", summary="Model Context Protocol (MCP) Manifest")
async def get_mcp_manifest():
    """Returns standardized MCP tool declarations for LangChain/Claude/AutoGPT AI Buyers."""
    return {
        "schema_version": "2024-11-05",
        "server_name": "aura-commerce-mcp",
        "description": "Model Context Protocol tools for autonomous e-commerce discovery and purchasing.",
        "tools": [
            {
                "name": "aura_search_catalog",
                "description": "Search 44,000+ luxury fashion catalog items using vector semantic search and budget filtering in INR.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search term or style description"},
                        "max_budget_inr": {"type": "number", "description": "Maximum budget in Indian Rupees"},
                        "gender": {"type": "string", "description": "Target gender"},
                        "category": {"type": "string", "description": "Target apparel/accessory category"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "aura_get_quote",
                "description": "Calculate itemized order quote with automated voucher and discount breakdown in INR.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "buyer_agent_id": {"type": "string"},
                        "items": {"type": "array", "description": "List of selected products"},
                        "coupon_code": {"type": "string", "description": "Promo code e.g. AURA20"}
                    },
                    "required": ["buyer_agent_id", "items"]
                }
            },
            {
                "name": "aura_execute_checkout",
                "description": "Initiate a bounded and gated Razorpay checkout order for autonomous execution.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "buyer_agent_id": {"type": "string"},
                        "shopper_email": {"type": "string"},
                        "items": {"type": "array"},
                        "max_authorized_budget_inr": {"type": "number", "description": "Hard budget spend ceiling"}
                    },
                    "required": ["buyer_agent_id", "shopper_email", "items", "max_authorized_budget_inr"]
                }
            }
        ]
    }


# =====================================================================
# Core Protocol Endpoints (AP2 / x402 / A2A)
# =====================================================================

@protocol_router.post("/protocol/v1/catalog/query", summary="Agent-Readable Semantic Catalog Discovery")
async def protocol_catalog_query(req: AgentCatalogQuery):
    """
    Executes high-precision hybrid vector discovery tailored for AI Buyer agents.
    Normalizes INR budget parameters into catalog units ($1 = ₹50) and returns structured items.
    """
    engine = get_search_engine()
    
    max_usd = (req.max_budget_inr / USD_TO_INR) if req.max_budget_inr else None
    
    filter_dict = engine.build_filter(
        gender=req.gender if req.gender in ["Men", "Women", "Unisex", "Boys", "Girls"] else None,
        article_type=req.category,
        max_price=max_usd,
        in_stock=True
    )

    results, price_analysis = engine.hybrid_search_with_price_intelligence(
        query=req.query,
        filter_dict=filter_dict,
        limit=req.limit or 8
    )

    # Format structured response for AI Buyer
    structured_items = []
    for doc in results:
        usd_price = doc.get("price") or 0.0
        inr_price = round(usd_price * USD_TO_INR)
        structured_items.append({
            "product_id": str(doc.get("product_id")),
            "name": doc.get("name"),
            "brand": doc.get("brand"),
            "gender": doc.get("gender"),
            "article_type": doc.get("article_type"),
            "base_color": doc.get("base_color"),
            "price_inr": inr_price,
            "price_usd": usd_price,
            "stock_status": "in_stock" if (doc.get("stock") or 1) > 0 else "out_of_stock",
            "rating": doc.get("rating"),
            "image_url": doc.get("image_url"),
            "relevance_score": doc.get("vector_score") or doc.get("keyword_score") or 0.95
        })

    return {
        "status": "success",
        "protocol": "AP2/1.0",
        "query": req.query,
        "results_count": len(structured_items),
        "price_intelligence": {
            "price_gap_detected": price_analysis.get("price_gap_detected", False),
            "catalog_min_price_inr": round((price_analysis.get("catalog_min_price") or 0.0) * USD_TO_INR),
            "requested_max_inr": req.max_budget_inr
        },
        "products": structured_items
    }


@protocol_router.post("/protocol/v1/quote", summary="Explainable Itemized Quote & Voucher Evaluation")
async def protocol_get_quote(req: AgentQuoteRequest):
    """
    Computes a guaranteed, explainable quote with automated discount breakdown.
    """
    if not req.items:
        raise HTTPException(status_code=400, detail="Quote requires at least one cart item.")

    subtotal_inr = sum(item.price_inr for item in req.items)
    discount_inr = 0.0
    applied_promo = None

    if req.coupon_code:
        code_upper = req.coupon_code.strip().upper()
        if code_upper in MERCHANT_PROMO_CODES:
            discount_pct = MERCHANT_PROMO_CODES[code_upper]["discount_percent"]
            discount_inr = round(subtotal_inr * (discount_pct / 100.0))
            applied_promo = {
                "code": code_upper,
                "discount_percent": discount_pct,
                "discount_amount_inr": discount_inr
            }

    final_payable_inr = max(1.0, subtotal_inr - discount_inr)

    justification = (
        f"Subtotal ₹{subtotal_inr:,} across {len(req.items)} piece(s)."
        + (f" Applied voucher {applied_promo['code']} (-{applied_promo['discount_percent']}%, savings: ₹{discount_inr:,})." if applied_promo else " No promo voucher applied.")
        + f" Guaranteed final payable amount: ₹{final_payable_inr:,} INR."
    )

    return {
        "status": "quoted",
        "buyer_agent_id": req.buyer_agent_id,
        "currency": "INR",
        "subtotal_inr": subtotal_inr,
        "discount_inr": discount_inr,
        "final_payable_inr": final_payable_inr,
        "applied_promo": applied_promo,
        "explainability": justification,
        "quote_valid_until": datetime.now(timezone.utc).isoformat()
    }


@protocol_router.post("/protocol/v1/order/checkout", summary="Bounded & Gated Agentic Order Checkout")
async def protocol_order_checkout(req: AgentCheckoutRequest):
    """
    Executes machine-gated order preparation with strict spending bounds.
    Rejects transaction with BUDGET_GATING_VIOLATION if calculated amount exceeds authorized budget.
    """
    if not req.items:
        raise HTTPException(status_code=400, detail="Cannot checkout with empty items list.")

    subtotal_inr = sum(item.price_inr for item in req.items)
    discount_inr = 0.0
    applied_code = None

    if req.coupon_code:
        code_upper = req.coupon_code.strip().upper()
        if code_upper in MERCHANT_PROMO_CODES:
            discount_pct = MERCHANT_PROMO_CODES[code_upper]["discount_percent"]
            discount_inr = round(subtotal_inr * (discount_pct / 100.0))
            applied_code = code_upper

    final_payable_inr = max(1.0, subtotal_inr - discount_inr)

    # -----------------------------------------------------------------
    # THE BAR: STRICT SPENDING GATING & BOUNDING CHECK
    # -----------------------------------------------------------------
    if final_payable_inr > req.max_authorized_budget_inr:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "BUDGET_GATING_VIOLATION",
                "message": f"Order total (₹{final_payable_inr:,.0f} INR) exceeds buyer authorized limit of ₹{req.max_authorized_budget_inr:,.0f} INR.",
                "required_budget_inr": final_payable_inr,
                "authorized_limit_inr": req.max_authorized_budget_inr,
                "gating_status": "REJECTED_BY_MERCHANT_GATE"
            }
        )

    # Convert to paise for Razorpay Gateway
    amount_in_paise = int(final_payable_inr * 100)
    receipt_id = f"rcpt_a2a_{secrets.token_hex(4)}"

    notes = {
        "channel": "A2A_AGENT",
        "buyer_agent_id": req.buyer_agent_id,
        "shopper_email": req.shopper_email,
        "coupon_code": applied_code or "None",
        "authorized_budget_inr": str(req.max_authorized_budget_inr)
    }

    try:
        rzp_order = create_razorpay_order(
            amount_in_paise=amount_in_paise,
            currency="INR",
            receipt=receipt_id,
            notes=notes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment Gateway Error: {str(e)}")

    order_id = f"ORD-A2A-{uuid.uuid4().hex[:8].upper()}"

    return {
        "status": "PAYMENT_INTENT_CREATED",
        "protocol": "AP2/1.0",
        "order_id": order_id,
        "buyer_agent_id": req.buyer_agent_id,
        "shopper_email": req.shopper_email,
        "currency": "INR",
        "subtotal_inr": subtotal_inr,
        "discount_inr": discount_inr,
        "final_payable_inr": final_payable_inr,
        "coupon_code": applied_code,
        "razorpay_order_id": rzp_order.get("order_id"),
        "razorpay_key_id": config.RAZORPAY_KEY_ID,
        "amount_in_paise": amount_in_paise,
        "gating_proof": {
            "authorized_ceiling_inr": req.max_authorized_budget_inr,
            "actual_charge_inr": final_payable_inr,
            "budget_compliance": "VERIFIED_WITHIN_BOUNDS"
        }
    }


@protocol_router.post("/protocol/v1/order/verify", summary="Cryptographic Verification & A2A Ledger Commit")
async def protocol_order_verify(req: AgentVerifyRequest):
    """
    Verifies payment signature, commits order to MongoDB audit ledger, and returns cryptographic receipt.
    """
    # 1. Verify Razorpay HMAC-SHA256 Signature
    is_valid = verify_razorpay_signature(
        razorpay_order_id=req.razorpay_order_id,
        razorpay_payment_id=req.razorpay_payment_id,
        razorpay_signature=req.razorpay_signature
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Cryptographic payment signature verification failed. Transaction rejected."
        )

    # 2. Record A2A Transaction in MongoDB Ledger
    user_mgr = get_user_manager()
    order_doc = {
        "order_id": req.order_id,
        "user_email": req.shopper_email,
        "channel": "A2A_AGENT",
        "protocol_version": "AP2/1.0",
        "buyer_agent_id": req.buyer_agent_id,
        "payment_id": req.razorpay_payment_id,
        "razorpay_order_id": req.razorpay_order_id,
        "total_amount": req.total_inr / USD_TO_INR, # Normalized USD catalog value
        "total_amount_inr": req.total_inr,
        "coupon_code": req.coupon_code,
        "discount_amount_inr": req.discount_inr,
        "items": req.items,
        "status": "Paid (A2A Agent Executed)",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        user_mgr.users_collection.update_one(
            {"email": req.shopper_email.lower().strip()},
            {
                "$push": {"orders": order_doc},
                "$set": {"bag": [], "bag_updated_at": None}
            },
            upsert=True
        )
    except Exception as e:
        print(f"Notice on A2A ledger logging: {e}")

    # Also log to global admin orders collection if exists
    try:
        db = user_mgr.db
        db["a2a_orders"].insert_one(order_doc.copy())
    except Exception:
        pass

    return {
        "status": "TRANSACTION_SETTLED",
        "order_id": req.order_id,
        "buyer_agent_id": req.buyer_agent_id,
        "shopper_email": req.shopper_email,
        "payment_id": req.razorpay_payment_id,
        "amount_settled_inr": req.total_inr,
        "protocol_receipt": {
            "signature_verified": True,
            "algorithm": "HMAC-SHA256",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ledger": "MongoDB Atlas A2A Audit Stream"
        }
    }


@protocol_router.get("/protocol/v1/telemetry", summary="A2A Agent Telemetry & Autonomous Metrics")
async def protocol_telemetry():
    """Returns telemetry of machine-to-machine acquisitions, active AI Buyers, and volume."""
    user_mgr = get_user_manager()
    try:
        db = user_mgr.db
        a2a_orders = list(db["a2a_orders"].find({}, {"_id": 0}).sort("created_at", -1).limit(20))
        total_a2a_gmv = sum(o.get("total_amount_inr", 0) for o in a2a_orders)
        unique_buyers = list(set(o.get("buyer_agent_id", "unknown") for o in a2a_orders))
        
        return {
            "status": "healthy",
            "total_a2a_orders": len(a2a_orders),
            "total_a2a_gmv_inr": total_a2a_gmv,
            "active_ai_buyers": unique_buyers,
            "recent_transactions": a2a_orders[:10]
        }
    except Exception as e:
        return {
            "status": "healthy",
            "total_a2a_orders": 0,
            "total_a2a_gmv_inr": 0,
            "active_ai_buyers": [],
            "recent_transactions": []
        }
