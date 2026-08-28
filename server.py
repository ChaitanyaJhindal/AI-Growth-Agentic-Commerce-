import os
import json
import uuid
import asyncio
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.agents.workflow import agent_app
from src.agents.state import AgentState
from src.agents.nodes import upsell_agent_node, get_search_engine
from src.search.engine import serialize_doc
from src.auth import get_user_manager
from src.protocol.router import protocol_router

# Initialize FastAPI
app = FastAPI(
    title="AURA - AI-Native Luxury Fashion Concierge & AI Buyer Protocol API",
    description="Backend API powered by LangGraph, Groq LLM (openai/gpt-oss-120b), MongoDB Atlas Hybrid Search, and AP2/MCP AI Buyer Protocol.",
    version="1.0.0"
)

# Mount AI Buyer Commerce Protocol Router
app.include_router(protocol_router)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# Request / Response Models
# =====================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., description="User's natural language request or refinement.")
    thread_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4())[:8], description="Session thread ID.")

class ClarificationReplyRequest(BaseModel):
    thread_id: str
    answer: str

class OutfitRequest(BaseModel):
    product_id: str

class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 15

class SignUpRequest(BaseModel):
    name: str = Field(..., description="Full Name")
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password (min 6 characters)")
    phone: Optional[str] = Field(None, description="Optional phone number (e.g. +919876543210)")

class LoginRequest(BaseModel):
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password")

class UpdatePhoneRequest(BaseModel):
    email: str = Field(..., description="User email")
    phone: str = Field(..., description="Phone number in E.164 format (e.g. +919876543210)")

class SyncUserDataRequest(BaseModel):
    email: str = Field(..., description="User email")
    wardrobe: Optional[List[Dict[str, Any]]] = None
    bag: Optional[List[Dict[str, Any]]] = None
    phone: Optional[str] = None

class ValidateCouponRequest(BaseModel):
    code: str = Field(..., description="Coupon / Promo code")
    subtotal: float = Field(0.0, description="Current cart subtotal amount")

class CheckoutOrderRequest(BaseModel):
    email: str = Field(..., description="User email")
    items: List[Dict[str, Any]] = Field(..., description="Ordered items")
    total: float = Field(..., description="Total price")
    coupon_code: Optional[str] = Field(None, description="Applied coupon code")
    discount_amount: Optional[float] = Field(0.0, description="Discount amount saved")
    subtotal: Optional[float] = Field(None, description="Subtotal before discount")

class CreateRazorpayOrderRequest(BaseModel):
    amount: float = Field(..., description="Amount in currency units (e.g. 50.00)")
    currency: Optional[str] = Field("INR", description="Currency code (e.g. INR)")
    receipt: Optional[str] = Field(None, description="Receipt reference")

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str = Field(..., description="Razorpay Order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay Payment ID")
    razorpay_signature: str = Field(..., description="Razorpay Signature")
    email: str = Field(..., description="User email")
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Cart items")
    total: float = Field(..., description="Total order amount")
    coupon_code: Optional[str] = Field(None, description="Applied coupon code")
    discount_amount: Optional[float] = Field(0.0, description="Discount amount saved")
    subtotal: Optional[float] = Field(None, description="Subtotal before discount")

class TriggerAbandonedCartCampaignRequest(BaseModel):
    coupon_code: Optional[str] = Field("AURA20", description="Promotional voucher code for re-engagement")
    tone: Optional[str] = Field("witty_hinglish", description="Copywriting tone")
    override_phone: Optional[str] = Field(None, description="Override recipient phone for test triggers")
    cooldown_hours: Optional[float] = Field(1.0, description="Cooldown hours before re-messaging same user")
    max_users: Optional[int] = Field(20, description="Max users to process in single batch")
    user_email: Optional[str] = Field(None, description="Target specific user by email")


# =====================================================================
# Health Check & Uptime Monitoring Endpoints (Keep-Alive Cron)
# =====================================================================

@app.get("/health")
@app.get("/api/health")
async def health_check():
    """
    Health check endpoint for cron jobs (e.g. Cron-job.org),
    uptime monitors (UptimeRobot, BetterUptime), and Render keep-alive pings.
    """
    db_status = "connected"
    try:
        engine = get_search_engine()
        # Fast non-blocking ping to MongoDB Atlas
        engine.collection.database.command("ping")
    except Exception as e:
        db_status = f"degraded: {str(e)}"

    return {
        "status": "healthy",
        "service": "AURA AI Luxury Fashion Concierge",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "version": "1.0.0"
    }


# =====================================================================
# Authentication & Order Endpoints
# =====================================================================

@app.post("/api/auth/signup")
async def signup(req: SignUpRequest):
    """Registers a new user in MongoDB with PBKDF2 hashed password and optional phone."""
    manager = get_user_manager()
    result = manager.signup(name=req.name, email=req.email, password=req.password, phone=req.phone)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Sign up failed."))
    return result

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Authenticates user against MongoDB and returns their saved collections."""
    manager = get_user_manager()
    result = manager.login(email=req.email, password=req.password)
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error", "Invalid credentials."))
    return result

@app.get("/api/auth/me")
async def get_me(email: str):
    """Fetches user profile and saved items from MongoDB."""
    manager = get_user_manager()
    profile = manager.get_user_profile(email)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"success": True, "user": profile}

@app.post("/api/user/phone")
@app.post("/api/user/update-phone")
async def update_user_phone_endpoint(req: UpdatePhoneRequest):
    """Updates user contact phone number in MongoDB."""
    manager = get_user_manager()
    result = manager.update_user_phone(email=req.email, phone=req.phone)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail="User not found.")
    return result

@app.post("/api/user/sync")
async def sync_user_data(req: SyncUserDataRequest):
    """Synchronizes user's shopping bag and wardrobe into MongoDB."""
    manager = get_user_manager()
    result = manager.sync_user_data(email=req.email, wardrobe=req.wardrobe, bag=req.bag, phone=req.phone)
    return result

@app.post("/api/coupon/validate")
async def validate_coupon(req: ValidateCouponRequest):
    """Validates coupon code and returns discount percentage and savings."""
    from src.whatsapp import validate_coupon_code
    return validate_coupon_code(code=req.code, subtotal=req.subtotal)

@app.post("/api/orders/checkout")
async def checkout_order(req: CheckoutOrderRequest):
    """Places an order for the authenticated user and persists it in MongoDB with coupon details."""
    manager = get_user_manager()
    result = manager.create_order(
        email=req.email,
        items=req.items,
        total=req.total,
        coupon_code=req.coupon_code,
        discount_amount=req.discount_amount or 0.0,
        subtotal=req.subtotal
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Checkout failed."))
    return result


# =====================================================================
# Razorpay Standard Checkout Endpoints
# =====================================================================

@app.post("/api/create-order")
async def create_order(req: CreateRazorpayOrderRequest):
    """
    Creates a Razorpay order.
    Validates minimum amount (>= 100 paise).
    Returns order_id, amount, currency, and key_id.
    """
    from src.payments import create_razorpay_order
    from src import config

    amount_in_paise = int(round(req.amount * 100))
    if amount_in_paise < 100:
        raise HTTPException(status_code=400, detail="Minimum amount must be at least 100 paise (1.00 INR).")

    try:
        order_data = create_razorpay_order(
            amount_in_paise=amount_in_paise,
            currency=req.currency or "INR",
            receipt=req.receipt
        )
        return {
            "order_id": order_data.get("order_id"),
            "amount": order_data.get("amount"),
            "currency": order_data.get("currency"),
            "key_id": config.RAZORPAY_KEY_ID
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        traceback.print_exc()
        err_msg = str(e)
        if "Authentication failed" in err_msg or "Unauthorized" in err_msg:
            raise HTTPException(status_code=401, detail="Razorpay authentication failed. Please check your API keys.")
        raise HTTPException(status_code=500, detail=f"Failed to create Razorpay order: {err_msg}")


@app.post("/api/verify-payment")
async def verify_payment(req: VerifyPaymentRequest):
    """
    Verifies Razorpay payment signature using HMAC-SHA256.
    If valid, marks order as paid and records it in MongoDB with coupon details.
    """
    from src.payments import verify_razorpay_signature

    if not req.razorpay_order_id or not req.razorpay_payment_id or not req.razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing required payment verification fields.")

    is_valid = verify_razorpay_signature(
        razorpay_order_id=req.razorpay_order_id,
        razorpay_payment_id=req.razorpay_payment_id,
        razorpay_signature=req.razorpay_signature
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Payment verification failed: Signature mismatch. Order not recorded."
        )

    # Signature is valid -> record confirmed paid order in MongoDB
    manager = get_user_manager()
    order_result = manager.create_order(
        email=req.email,
        items=req.items,
        total=req.total,
        payment_id=req.razorpay_payment_id,
        razorpay_order_id=req.razorpay_order_id,
        payment_status="Paid (Razorpay)",
        coupon_code=req.coupon_code,
        discount_amount=req.discount_amount or 0.0,
        subtotal=req.subtotal
    )

    return {
        "success": True,
        "message": "Payment verified successfully.",
        "order_id": order_result.get("order_id"),
        "razorpay_payment_id": req.razorpay_payment_id,
        "razorpay_order_id": req.razorpay_order_id,
        "coupon_code": req.coupon_code,
        "discount_amount": req.discount_amount
    }


# =====================================================================
# Cart Campaign Automation Endpoints (MongoDB Abandoned Cart AI Re-Engagement)
# =====================================================================

@app.post("/api/automation/abandoned-cart-campaign")
async def trigger_abandoned_cart_campaign_endpoint(req: TriggerAbandonedCartCampaignRequest):
    """
    Scans MongoDB for users with items in their bag, generates personalized Hinglish
    copy with CampaignAgent (openai/gpt-oss-20b), and enqueues to WhatsApp Queue.
    """
    try:
        from src.whatsapp import get_automation_manager
        auto_mgr = get_automation_manager()
        res = auto_mgr.trigger_abandoned_cart_campaign(
            coupon_code=req.coupon_code or "AURA20",
            tone=req.tone or "witty_hinglish",
            cooldown_hours=req.cooldown_hours or 1.0,
            override_phone=req.override_phone,
            max_users=req.max_users or 20,
            user_email=req.user_email
        )
        return res
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to execute abandoned cart campaign: {str(e)}")

@app.get("/api/automation/abandoned-cart-stats")
async def get_abandoned_cart_stats_endpoint():
    """Returns real-time abandoned cart metrics from MongoDB."""
    try:
        from src.whatsapp import get_automation_manager
        auto_mgr = get_automation_manager()
        return {"success": True, "stats": auto_mgr.get_stats()}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch cart stats: {str(e)}")


# =====================================================================
# User Profile & Orders Endpoints
# =====================================================================

@app.get("/api/user/orders")
async def get_user_orders(email: str):
    """Retrieves full order documents and profile for the specified user."""
    manager = get_user_manager()
    profile = manager.get_user_profile(email)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found.")
    orders = manager.get_user_orders(email)
    return {"success": True, "user": profile, "orders": orders}


# =====================================================================
# Admin Intelligence & Executive Atelier Endpoints
# =====================================================================

class UpdateOrderStatusRequest(BaseModel):
    order_id: str = Field(..., description="Order Reference ID")
    status: str = Field(..., description="New fulfillment status (e.g. In Transit, Delivered)")

@app.get("/api/admin/overview")
async def get_admin_overview():
    """Retrieves high-level executive analytics, gross metrics, and recent orders for admin."""
    manager = get_user_manager()
    metrics = manager.get_admin_metrics()
    return {"success": True, "metrics": metrics}

@app.get("/api/admin/orders")
async def get_admin_orders(limit: Optional[int] = 100):
    """Retrieves all orders placed across the boutique."""
    manager = get_user_manager()
    orders = manager.get_all_orders(limit=limit or 100)
    return {"success": True, "orders": orders}

@app.get("/api/admin/users")
async def get_admin_users():
    """Retrieves registered patrons directory."""
    manager = get_user_manager()
    users = manager.get_all_users()
    return {"success": True, "users": users}

@app.post("/api/admin/orders/update-status")
async def update_order_status(req: UpdateOrderStatusRequest):
    """Updates fulfillment status for an order."""
    manager = get_user_manager()
    success = manager.update_order_status(order_id=req.order_id, new_status=req.status)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found or status unchanged.")
    return {"success": True, "order_id": req.order_id, "status": req.status}

@app.get("/admin")
async def serve_admin_portal():
    """Serves the AURA Executive Atelier Admin Dashboard."""
    admin_file = os.path.join(static_dir, "admin.html")
    if os.path.exists(admin_file):
        return FileResponse(admin_file)
    raise HTTPException(status_code=404, detail="Admin dashboard file not found.")


# =====================================================================
# Gen-Z Dynamic Placeholder Agent Endpoints (openai/gpt-oss-20b)
# =====================================================================

@app.get("/api/placeholder/next")
async def get_next_placeholder():
    """
    Returns the next Gen-Z dynamic search prompt curated by PlaceholderAgent
    powered by Groq (openai/gpt-oss-20b).
    """
    from src.agents.placeholder_agent import get_placeholder_agent
    agent = get_placeholder_agent()
    prompt = agent.get_next_prompt()
    return {
        "success": True,
        "prompt": prompt,
        "model": agent.model,
        "interval_seconds": 10,
        "display_duration_seconds": 3.5
    }

@app.get("/api/placeholder/batch")
async def get_placeholder_batch(count: Optional[int] = 6):
    """
    Generates a fresh batch of Gen-Z fashion search prompts using openai/gpt-oss-20b.
    """
    from src.agents.placeholder_agent import get_placeholder_agent
    agent = get_placeholder_agent()
    prompts = agent.generate_fresh_batch(count=count or 6)
    return {
        "success": True,
        "prompts": prompts,
        "model": agent.model
    }

@app.get("/api/placeholder/stream")
async def stream_placeholder():
    """
    Server-Sent Events (SSE) streaming token endpoint for real-time typewriter effect.
    """
    from src.agents.placeholder_agent import get_placeholder_agent

    agent = get_placeholder_agent()
    prompt = agent.get_next_prompt()

    async def event_generator():
        yield f"data: {json.dumps({'type': 'start', 'full_prompt': prompt})}\n\n"
        for char in prompt:
            yield f"data: {json.dumps({'type': 'token', 'token': char})}\n\n"
            await asyncio.sleep(0.03)
        yield f"data: {json.dumps({'type': 'done', 'full_prompt': prompt})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/placeholder/pipeline-steps")
async def get_pipeline_steps():
    """
    Returns dynamic, engaging step thoughts for the progressive revelation banner.
    """
    from src.agents.placeholder_agent import get_placeholder_agent
    agent = get_placeholder_agent()
    steps = agent.get_dynamic_pipeline_steps()
    return {
        "success": True,
        "steps": steps,
        "model": agent.model
    }

class ComboSuggestionRequest(BaseModel):
    anchor: Dict[str, Any] = Field(..., description="Selected anchor product")
    pairings: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Complementary outfit products")

@app.post("/api/placeholder/combo-suggestion")
async def get_combo_suggestion(req: ComboSuggestionRequest):
    """
    Synthesizes a context-aware outfit styling combo tip using openai/gpt-oss-20b.
    """
    from src.agents.placeholder_agent import get_placeholder_agent
    agent = get_placeholder_agent()
    suggestion = agent.generate_combo_suggestion(anchor=req.anchor, pairings=req.pairings or [])
    return {
        "success": True,
        "suggestion": suggestion,
        "model": agent.model
    }


# =====================================================================
# AI Campaign & Re-Engagement Agent Endpoints (openai/gpt-oss-20b)
# =====================================================================

class CampaignMessageRequest(BaseModel):
    customer_name: str = Field(..., description="Name of the customer (e.g. Rahul, Priya)")
    bag_items: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Items in user cart/bag")
    channel: Optional[str] = Field("whatsapp", description="Target channel: whatsapp, push, sms, or email")
    discount_code: Optional[str] = Field("AURA15", description="Promotional voucher code")
    tone: Optional[str] = Field("witty_hinglish", description="Tone: witty_hinglish, playful_urgency, or luxury_chic")

class CampaignVariationsRequest(BaseModel):
    customer_name: str = Field(..., description="Name of the customer")
    bag_items: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Items in cart/bag")
    count: Optional[int] = Field(3, description="Number of variations")
    discount_code: Optional[str] = Field("AURA15", description="Voucher code")

@app.post("/api/campaign/generate")
async def generate_campaign_message(req: CampaignMessageRequest):
    """
    Generates a high-converting, personalized promotional message for WhatsApp/Push
    based on the customer's name and cart items using openai/gpt-oss-20b.
    """
    from src.agents.campaign_agent import get_campaign_agent
    agent = get_campaign_agent()
    result = agent.generate_message(
        customer_name=req.customer_name,
        bag_items=req.bag_items or [],
        channel=req.channel or "whatsapp",
        discount_code=req.discount_code or "AURA15",
        tone=req.tone or "witty_hinglish"
    )
    return result

@app.post("/api/campaign/variations")
async def generate_campaign_variations(req: CampaignVariationsRequest):
    """
    Generates multiple creative variations of campaign copy for A/B testing.
    """
    from src.agents.campaign_agent import get_campaign_agent
    agent = get_campaign_agent()
    variations = agent.generate_campaign_variations(
        customer_name=req.customer_name,
        bag_items=req.bag_items or [],
        count=req.count or 3,
        discount_code=req.discount_code or "AURA15"
    )
    return {
        "success": True,
        "customer_name": req.customer_name,
        "variations": variations,
        "count": len(variations)
    }

@app.get("/api/campaign/sample")
async def get_sample_campaign(name: Optional[str] = "Rahul"):
    """
    Sample preview endpoint demonstrating personalized Hinglish WhatsApp promotional copy.
    """
    from src.agents.campaign_agent import get_campaign_agent
    agent = get_campaign_agent()
    sample_bag = [
        {"name": "Puma Nitro Carbon Running Shoes", "article_type": "Sports Shoes", "price": 85.0},
        {"name": "Nike Tech Fleece Black Track Pants", "article_type": "Track Pants", "price": 55.0}
    ]
    result = agent.generate_message(
        customer_name=name or "Rahul",
        bag_items=sample_bag,
        channel="whatsapp",
        discount_code="AURA20",
        tone="witty_hinglish"
    )
    return result


# =====================================================================
# AI Agent & Search Endpoints
# =====================================================================

@app.post("/api/chat")
async def handle_chat(req: ChatRequest):
    """
    Primary endpoint: Runs the user's natural language request through
    the LangGraph agent pipeline with session memory.
    """
    thread_id = req.thread_id or str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": thread_id}}

    try:
        input_state = {
            "current_query": req.message,
            "original_query": req.message
        }

        result_state = agent_app.invoke(input_state, config=config)

        search_results = [serialize_doc(p) for p in result_state.get("search_results", [])]
        upsell_results = [serialize_doc(p) for p in result_state.get("upsell_results", [])]
        selected_product = serialize_doc(result_state["selected_product"]) if result_state.get("selected_product") else None

        return {
            "thread_id": thread_id,
            "intent": result_state.get("intent", "search"),
            "current_query": result_state.get("current_query", req.message),
            "filters": result_state.get("filters", {}),
            "needs_clarification": result_state.get("needs_clarification", False),
            "clarification_question": result_state.get("clarification_question"),
            "clarification_count": result_state.get("clarification_count", 0),
            "validation_result": result_state.get("validation_result", {}),
            "search_results": search_results,
            "selected_product": selected_product,
            "upsell_results": upsell_results,
            "conversation_history": result_state.get("conversation_history", [])
        }
    except Exception as e:
        traceback.print_exc()
        # Fallback to direct hybrid search if agent LLM encounters an unexpected issue
        engine = get_search_engine()
        results = engine.hybrid_search(req.message, limit=15)
        return {
            "thread_id": thread_id,
            "intent": "search",
            "current_query": req.message,
            "filters": {},
            "needs_clarification": False,
            "clarification_question": None,
            "clarification_count": 0,
            "validation_result": {"validated": True, "explanation": "Fallback hybrid search"},
            "search_results": [serialize_doc(p) for p in results],
            "selected_product": None,
            "upsell_results": [],
            "conversation_history": []
        }


@app.post("/api/clarify")
async def handle_clarification(req: ClarificationReplyRequest):
    """
    Resumes LangGraph execution after user responds to a clarification question.
    """
    config = {"configurable": {"thread_id": req.thread_id}}

    try:
        input_state = {
            "current_query": req.answer,
            "needs_clarification": False,
            "clarification_question": None
        }

        result_state = agent_app.invoke(input_state, config=config)

        return {
            "thread_id": req.thread_id,
            "intent": result_state.get("intent", "search"),
            "current_query": result_state.get("current_query"),
            "filters": result_state.get("filters", {}),
            "needs_clarification": result_state.get("needs_clarification", False),
            "clarification_question": result_state.get("clarification_question"),
            "validation_result": result_state.get("validation_result", {}),
            "search_results": [serialize_doc(p) for p in result_state.get("search_results", [])],
            "upsell_results": [serialize_doc(p) for p in result_state.get("upsell_results", [])],
            "selected_product": serialize_doc(result_state["selected_product"]) if result_state.get("selected_product") else None
        }
    except Exception as e:
        traceback.print_exc()
        engine = get_search_engine()
        results = engine.hybrid_search(req.answer, limit=15)
        return {
            "thread_id": req.thread_id,
            "intent": "search",
            "current_query": req.answer,
            "filters": {},
            "needs_clarification": False,
            "clarification_question": None,
            "validation_result": {"validated": True, "explanation": "Fallback search"},
            "search_results": [serialize_doc(p) for p in results],
            "upsell_results": [],
            "selected_product": None
        }


@app.post("/api/outfit")
async def generate_outfit_for_product(req: OutfitRequest):
    """
    Generates a complete 3-to-4 piece modular ensemble for any selected product.
    """
    engine = get_search_engine()
    doc = engine.collection.find_one({"product_id": req.product_id})
    if not doc:
        try:
            doc = engine.collection.find_one({"product_id": int(req.product_id)})
        except (ValueError, TypeError):
            pass
    if not doc:
        # Fallback search by ID or name
        res = engine.hybrid_search(str(req.product_id), limit=1)
        if res:
            doc = res[0]
            
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")

    selected = serialize_doc(doc)
    mock_state: AgentState = {
        "original_query": selected.get("name", ""),
        "current_query": selected.get("name", ""),
        "filters": {},
        "intent": "select_product",
        "clarification_count": 0,
        "needs_clarification": False,
        "clarification_question": None,
        "search_results": [selected],
        "validation_result": {"validated": True, "retry_count": 0},
        "selected_product": selected,
        "upsell_results": [],
        "conversation_history": []
    }

    try:
        res = upsell_agent_node(mock_state)
        return {
            "selected_product": selected,
            "outfit_pairings": [serialize_doc(p) for p in res.get("upsell_results", [])]
        }
    except Exception as e:
        print(f"Notice on outfit API: {e}")
        return {
            "selected_product": selected,
            "outfit_pairings": []
        }


@app.get("/api/trending")
async def get_trending_curations():
    """
    Returns curated editorial items across footwear, apparel, and accessories for the discovery page.
    """
    engine = get_search_engine()
    trending_items = []
    
    for cat in ["Footwear", "Apparel", "Accessories"]:
        items = list(engine.collection.find(
            {"master_category": cat, "rating": {"$gte": 4.0}},
            {"embedding": 0}
        ).limit(3))
        trending_items.extend([serialize_doc(i) for i in items])

    return {"curations": trending_items}


@app.get("/api/product/{product_id}")
async def get_product_details(product_id: str):
    """
    Returns full details for a single product.
    """
    engine = get_search_engine()
    doc = engine.collection.find_one({"product_id": product_id}, {"embedding": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product": serialize_doc(doc)}


# =====================================================================
# WhatsApp Messaging Service & Queue Endpoints (OpenWA / Baileys)
# =====================================================================

class WhatsAppQueueRequest(BaseModel):
    recipient_phone: str = Field(..., description="Recipient phone in E.164 format (e.g. +919876543210)")
    message: str = Field(..., description="WhatsApp message text body")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional custom metadata")

class WhatsAppCampaignQueueRequest(BaseModel):
    customer_name: str = Field(..., description="Name of the customer (e.g. Rahul, Priya)")
    recipient_phone: str = Field(..., description="Recipient phone in E.164 format (e.g. +919876543210)")
    bag_items: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Items currently in customer bag")
    discount_code: Optional[str] = Field("AURA20", description="Promotional voucher code")
    tone: Optional[str] = Field("witty_hinglish", description="Copywriting tone")

@app.on_event("startup")
async def start_whatsapp_background_worker():
    """Starts the sequential WhatsApp message queue worker and Baileys daemon on boot."""
    import subprocess
    import shutil

    # 1. Spawn Baileys Node Engine if Node is available
    try:
        baileys_script = os.path.join(os.path.dirname(__file__), "src", "whatsapp", "baileys_service.js")
        if shutil.which("node") and os.path.exists(baileys_script):
            subprocess.Popen(["node", baileys_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✓ WhatsApp Baileys Engine daemon spawned in background.")
    except Exception as e:
        print(f"Notice on Baileys Node daemon spawn: {e}")

    # 2. Start Python MongoDB Queue Worker
    try:
        from src.whatsapp import get_whatsapp_worker
        worker = get_whatsapp_worker()
        worker.start_background()
        print("✓ WhatsApp Queue Worker initialized in background.")
    except Exception as e:
        print(f"Notice on WhatsApp Worker startup: {e}")

@app.get("/whatsapp")
@app.get("/whatsapp-link")
async def serve_whatsapp_page():
    """Serves the visual WhatsApp QR code linking and campaign dashboard."""
    whatsapp_html = os.path.join(static_dir, "whatsapp.html")
    if os.path.exists(whatsapp_html):
        return FileResponse(whatsapp_html)
    raise HTTPException(status_code=404, detail="WhatsApp management interface not found.")

@app.post("/whatsapp/queue")
@app.post("/api/whatsapp/queue")
async def queue_whatsapp_message(req: WhatsAppQueueRequest):
    """
    Validates recipient phone (E.164) and message body, and enqueues to MongoDB whatsapp_messages collection.
    Does NOT send message directly.
    """
    try:
        from src.whatsapp import get_whatsapp_queue
        queue = get_whatsapp_queue()
        result = queue.enqueue(
            recipient_phone=req.recipient_phone,
            message=req.message,
            metadata=req.metadata
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue WhatsApp message: {e}")

@app.get("/whatsapp/queue/{message_id}")
@app.get("/api/whatsapp/queue/{message_id}")
async def get_whatsapp_queue_status(message_id: str):
    """
    Checks status and retry attempts of a queued WhatsApp message.
    """
    from src.whatsapp import get_whatsapp_queue
    queue = get_whatsapp_queue()
    doc = queue.get_message(message_id)
    if not doc:
        raise HTTPException(status_code=404, detail="WhatsApp message not found in queue.")
    return {"success": True, "message": doc}

@app.get("/whatsapp/status")
@app.get("/api/whatsapp/status")
async def get_whatsapp_service_status():
    """
    Returns real-time queue statistics and Baileys engine connection status.
    """
    from src.whatsapp import get_whatsapp_queue, get_baileys_client
    queue = get_whatsapp_queue()
    client = get_baileys_client()
    stats = queue.get_stats()
    engine_status = client.get_status()
    return {
        "success": True,
        "queue": stats,
        "engine": engine_status
    }

@app.get("/whatsapp/qr")
@app.get("/api/whatsapp/qr")
async def get_whatsapp_qr_code():
    """
    Returns the QR code string for initial WhatsApp authentication if not yet linked.
    """
    from src.whatsapp import get_baileys_client
    client = get_baileys_client()
    return client.get_qr()

@app.post("/whatsapp/campaign/queue")
@app.post("/api/whatsapp/campaign/queue")
async def generate_and_queue_campaign(req: WhatsAppCampaignQueueRequest):
    """
    Integrates Campaign Agent with WhatsApp Queue:
    1. Generates hyper-personalized, witty Hinglish promotional copy using CampaignAgent (openai/gpt-oss-20b).
    2. Automatically enqueues the crafted message into MongoDB whatsapp_messages queue.
    """
    try:
        from src.agents.campaign_agent import get_campaign_agent
        from src.whatsapp import get_whatsapp_queue

        # 1. Generate personalized promotional copy
        agent = get_campaign_agent()
        campaign_res = agent.generate_message(
            customer_name=req.customer_name,
            bag_items=req.bag_items or [],
            channel="whatsapp",
            discount_code=req.discount_code or "AURA20",
            tone=req.tone or "witty_hinglish"
        )
        message_text = campaign_res.get("message", "")
        if not message_text:
            raise RuntimeError("Campaign agent failed to produce copy.")

        # 2. Enqueue to MongoDB queue
        queue = get_whatsapp_queue()
        queue_res = queue.enqueue(
            recipient_phone=req.recipient_phone,
            message=message_text,
            metadata={
                "customer_name": req.customer_name,
                "campaign_headline": campaign_res.get("headline"),
                "discount_code": req.discount_code,
                "model": campaign_res.get("model", agent.model),
                "source": "campaign_agent"
            }
        )

        return {
            "success": True,
            "message_id": queue_res.get("message_id"),
            "status": queue_res.get("status"),
            "recipient_phone": queue_res.get("recipient_phone"),
            "generated_headline": campaign_res.get("headline"),
            "generated_message": message_text,
            "call_to_action": campaign_res.get("call_to_action")
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Campaign queue error: {e}")


# =====================================================================
# Mount Static Frontend
# =====================================================================

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Starting AURA FastAPI server on http://127.0.0.1:8000...")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
