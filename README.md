# AURA — AI-Native Luxury Fashion Concierge & Agentic Commerce Platform

[![Track](https://img.shields.io/badge/Razorpay%20Hackathon-Track%2001%3A%20AI%20Growth%20%26%20Agentic%20Commerce-blueviolet?style=for-the-badge)](https://razorpay.com)
[![Production Status](https://img.shields.io/badge/Production-Live-success?style=for-the-badge&logo=render)](https://ai-growth-agentic-commerce.onrender.com)
[![Protocol](https://img.shields.io/badge/Protocol-AP2%20%2F%20MCP%20%2F%20x402-blue?style=for-the-badge)](https://ai-growth-agentic-commerce.onrender.com/.well-known/agent-protocol.json)
[![Payment Engine](https://img.shields.io/badge/Payments-Razorpay%20Standard%20%26%20A2A%20Settlement-blue?style=for-the-badge&logo=razorpay)](https://razorpay.com)
[![Architecture](https://img.shields.io/badge/Architecture-LangGraph%20Multi--Agent-0052CC?style=for-the-badge&logo=diagramsdotnet)](https://github.com/ChaitanyaJhindal/AI-Growth-Agentic-Commerce-)
[![LLM Inference](https://img.shields.io/badge/LLM-Groq%20(120B%20%26%2020B)-orange?style=for-the-badge)](https://groq.com)
[![Vector Search](https://img.shields.io/badge/Search-MongoDB%20Atlas%20Hybrid%20RRF-green?style=for-the-badge&logo=mongodb)](https://www.mongodb.com/atlas)
[![Embeddings](https://img.shields.io/badge/Embeddings-Voyage%20AI%20(512--dim)-indigo?style=for-the-badge)](https://voyageai.com)

---

## 🌐 Live Deployments & Protocol Discovery Links

| Service / Interface | Live URL | Description |
| :--- | :--- | :--- |
| **🛍️ Production Storefront** | [https://ai-growth-agentic-commerce.onrender.com](https://ai-growth-agentic-commerce.onrender.com) | Conversational Luxury Fashion Concierge & AI Styling Experience |
| **📊 Executive Atelier Admin** | [https://ai-growth-agentic-commerce.onrender.com/admin](https://ai-growth-agentic-commerce.onrender.com/admin) | Real-Time Revenue Analytics, Orders, Patrons & A2A Machine Telemetry |
| **📜 AP2 Agent Discovery Manifest** | [https://ai-growth-agentic-commerce.onrender.com/.well-known/agent-protocol.json](https://ai-growth-agentic-commerce.onrender.com/.well-known/agent-protocol.json) | Machine-readable capability & endpoint manifest for external AI Buyers |
| **🔌 MCP Tool Schema** | [https://ai-growth-agentic-commerce.onrender.com/.well-known/mcp.json](https://ai-growth-agentic-commerce.onrender.com/.well-known/mcp.json) | Model Context Protocol (MCP) declarations for Claude & AutoGPT |
| **📱 WhatsApp QR Pairing** | [https://ai-growth-agentic-commerce.onrender.com/whatsapp](https://ai-growth-agentic-commerce.onrender.com/whatsapp) | Live Baileys Engine QR Scanner & Campaign Dispatcher |
| **💓 Keep-Alive Health Probe** | [https://ai-growth-agentic-commerce.onrender.com/health](https://ai-growth-agentic-commerce.onrender.com/health) | Uptime Monitoring & Database Health Check Endpoint |

---

## 💎 Product Overview

> **AURA transforms traditional e-commerce into a dual-sided autonomous commerce platform: empowering human shoppers with conversational runway stylists while allowing external AI agents to discover, negotiate, and execute bounded purchases.**

AURA delivers on both frontiers of modern intelligent retail:

### 1. Growing Merchant Revenue (AI Growth Engine)
* **Upsell & Cross-Sell Agent:** Chain-of-Thought (CoT) stylist dynamically composes high-affinity complementary pieces and editorial styling notes from a 44,000+ catalog item collection, expanding average basket size (AOV).
* **Autonomous Abandoned Cart Recovery:** Identifies incomplete carts in MongoDB, synthesizes high-converting Hinglish/English copy using Groq `gpt-oss-20b`, and dispatches messages via an ultra-lightweight Baileys WhatsApp worker.
* **Graceful Budget-Floor Upsell:** When shopper queries fall below catalog price floors, AURA intercepts the gap, retrieves entry-level luxury alternatives, and politely explains the baseline in `₹`, preventing lost sales.

### 2. Transactable by AI Buyers (Agent-to-Agent / A2A Protocol)
* **Autonomous Discovery:** Exposes AP2 (`/.well-known/agent-protocol.json`) and MCP (`/.well-known/mcp.json`) for zero-configuration integration with external agents (Claude Desktop, AutoGPT, LangChain).
* **Machine Catalog Query & Quotes:** Programmatic endpoints (`/protocol/v1/catalog/query` and `/protocol/v1/quote`) providing itemized pricing, applied promotional vouchers, and mathematical explainability strings.
* **Bounded & Gated Checkout:** Strict budget compliance via `max_authorized_budget_inr`.
* **Cryptographic Razorpay Settlement:** Server-side HMAC-SHA256 signature verification and dedicated persistent ledger logging (`a2a_orders`).

---

## 🛡️ Financial Safeguards & Autonomous Commerce Governance

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │               FINANCIAL COMPLIANCE & GOVERNANCE             │
                    └──────────────────────────────┬──────────────────────────────┘
                                                   │
                1. EXPLAINABILITY                  │ 2. BUDGET GATING
       ┌───────────────────────────────┐           │           ┌───────────────────────────────┐
       │ Itemized subtotal breakdown,  │           │           │ Client specifies ceiling:     │
       │ promo codes applied, and      │◄──────────┴──────────►│ max_authorized_budget_inr.    │
       │ transparent text justification│                       │ Checked strictly on backend.  │
       └───────────────────────────────┘                       └───────────────┬───────────────┘
                                                                               │
                                                                               ▼
                                                   ┌───────────────────────────────────────────┐
                                                   │ Does Order Total <= Authorized Budget?    │
                                                   └───────┬───────────────────────────┬───────┘
                                                           │                           │
                                                  YES (Authorized)            NO (Budget Exceeded)
                                                           │                           │
                                                           ▼                           ▼
                                            ┌─────────────────────────┐ ┌─────────────────────────┐
                                            │ 200 OK                  │ │ 422 UNPROCESSABLE ENTITY│
                                            │ Razorpay Intent Created │ │ BUDGET_GATING_VIOLATION │
                                            │ Audit Ledger Recorded   │ │ Structured Error Logged │
                                            └─────────────────────────┘ └─────────────────────────┘
```

1. **Deterministic Financial Gating:** External AI buyers specify an explicit authorized spending ceiling (`max_authorized_budget_inr`). The server treats this as an absolute boundary. If the computed order total exceeds this threshold, the transaction is rejected immediately before funds move.
2. **Predictable Exception Handling:** Over-budget requests fail gracefully with HTTP `422 Unprocessable Entity` and a structured `BUDGET_GATING_VIOLATION` payload detailing the exact ceiling, order total, and variance instead of failing silently.
3. **Full Quote Transparency:** Every quote generated by `/protocol/v1/quote` produces a mathematical breakdown (subtotal, voucher deduction, final payable) plus an explicit narrative justification explaining applied privileges.
4. **End-to-End Audit Trail:** Every transaction records Razorpay Order IDs, Payment IDs, HMAC signatures, buyer agent IDs, and itemized manifests in persistent MongoDB `a2a_orders` and `orders` collections, observable in real time on the [Executive Admin Portal](/admin).

---

## 💳 Razorpay Payment Architecture (Test Mode)

AURA natively integrates Razorpay across both human and agentic payment pipelines:

```
[Human Shopper] ──► /api/create-order ──► Razorpay Orders API ──► Standard Checkout Modal ──► /api/verify-payment ──► MongoDB Order
                                                                                               (HMAC-SHA256)
[AI Buyer Agent] ─► /protocol/v1/order/checkout ──► (Budget Gate) ──► Razorpay Order Intent ─► /protocol/v1/order/verify ─► a2a_orders Ledger
                                                                                               (HMAC-SHA256)
```

* **Server-Side Order Creation:** `/api/create-order` creates orders via the official Razorpay SDK (`razorpay.Client`) with minimum unit validation (>= 100 paise).
* **Client Modal Integration:** Standard Razorpay modal integration (`new Razorpay(options)`) with branded luxury gold UI theme and automatic error/dismissal handling.
* **Cryptographic Verification:** `/api/verify-payment` verifies payment signatures using server-side HMAC-SHA256 comparison (`hmac.new(secret, order_id|payment_id, sha256)`).
* **Machine A2A Settlement:** `/protocol/v1/order/checkout` generates compliant Razorpay payment intents for autonomous buyers, verified cryptographically via `/protocol/v1/order/verify`.

---

## 🔌 Technology Stack: Architecture & Design Decisions

| Technology | Role in System | Architectural Rationale |
| :--- | :--- | :--- |
| **FastAPI (Python 3.11)** | Core Backend & API Gateway | High-performance asynchronous runtime for non-blocking LLM token generation, Pydantic validation, and OpenAPI documentation. |
| **LangGraph (StateGraph)** | Multi-Agent Orchestration | Provides cyclic state machines, conditional branching, clarification halts, and validation-retry feedback loops that linear chains cannot support. |
| **Groq LPU (120B & 20B)** | Ultra-Low Latency Inference | Sub-second response times across 5 distributed API keys. Heavy `gpt-oss-120b` handles styling & intent; lightweight `gpt-oss-20b` generates Hinglish copy. |
| **MongoDB Atlas** | Unified Data & Vector Engine | Single datastore for 44,000+ fashion documents, native cosine Vector Search, atomic message queues, and session persistence. |
| **Voyage AI (`voyage-3-lite`)** | High-Affinity Embeddings | Remote 512-dimensional fashion embeddings via zero-dependency HTTP API. Zero PyTorch/CUDA overhead on production servers. |
| **Reciprocal Rank Fusion (RRF)** | Hybrid Search Ranking | Merges dense vector embeddings (0.6 weight) and lexical text scores (0.4 weight) to eliminate hallucinated search misses. |
| **Model Context Protocol (MCP)** | Agent Tool Interoperability | Open Anthropic standard allowing Claude Desktop, AutoGPT, and external LLMs to automatically discover and invoke catalog tools. |
| **AP2 / A2A Protocol** | Agent-to-Agent Commerce Standard | Provides the financial safety envelope: bounded budget validation, itemized quotes, and machine checkout verification. |
| **Baileys (`@whiskeysockets/baileys`)** | WhatsApp Engine Sidecar | Direct WebSocket implementation for WhatsApp multi-device. Runs on <35MB RAM without Chromium, persisting session keys in MongoDB. |
| **Razorpay Python SDK** | Payment Infrastructure | Test-mode order creation, transaction verification, and programmatic settlement compliance. |

---

## ⚖️ Interoperability Architecture: MCP vs. A2A

```
┌────────────────────────────────────────────────────────┐  ┌────────────────────────────────────────────────────────┐
│           MCP (Model Context Protocol)                 │  │             A2A (Agent-to-Agent Protocol)              │
├────────────────────────────────────────────────────────┤  ├────────────────────────────────────────────────────────┤
│ • Role: AI Tool Discovery & Syntax                     │  │ • Role: Financial Governance & Settlement              │
│ • "What capabilities does this merchant support?"      │  │ • "How do two software agents safely exchange value?"  │
│ • Served at: /.well-known/mcp.json                     │  │ • Served at: /protocol/v1/...                          │
│ • Exposes tool names, parameters, schemas for Claude   │  │ • Enforces budget limits, quotes, Razorpay settlement  │
└────────────────────────────────────────────────────────┘  └────────────────────────────────────────────────────────┘
```
* **MCP provides the agent-facing tool contract:** External LLMs read standard schemas to construct tool calls.
* **A2A provides the transactional governance engine:** The backend validates commercial boundaries, evaluates budgets, and orchestrates Razorpay settlement.

---

## 🏗️ System Architecture Diagram

```mermaid
flowchart TD
    subgraph HumanShopperFlow ["1. Human Conversational Experience (5-Agent LangGraph Workflow)"]
        User([Patron / Shopper]) --> Q[1. Query Agent<br/><b>Groq Key 1 / gpt-oss-120b</b><br/>Intent & INR Budget Parsing]
        Q --> C[2. Context Agent<br/><b>Groq Key 2 / gpt-oss-120b</b><br/>Specificity & Ambiguity Gate]
        
        C -->|Needs Clarification| Clarify[Concierge Clarification Prompt<br/>Max 2 Turns]
        Clarify --> User
        
        C -->|Sufficient Context| S[3. Search Node<br/><b>Voyage AI 512-dim + Atlas</b><br/>Vector Search + Lexical RRF]
        S --> V[4. Validation Agent<br/><b>Groq Key 2 / gpt-oss-120b</b><br/>QA & Budget Floor Upsell]
        
        V -->|Validation Failed| S
        V -->|Validation Passed| U[5. AI Runway Stylist<br/><b>Groq Key 3 / gpt-oss-120b</b><br/>3-Piece Capsule Composition]
        
        U --> Res([Luxury Curated Recommendations & Outfits])
    end

    subgraph A2AProtocolFlow ["2. Machine-to-Machine (A2A) AI Buyer Protocol Layer"]
        AIBuyer([External AI Buyer Agent<br/>AutoGPT / Claude Assistant]) -->|1. Discovery| Manifest[GET /.well-known/agent-protocol.json<br/>GET /.well-known/mcp.json]
        AIBuyer -->|2. Search| PQuery[POST /protocol/v1/catalog/query]
        AIBuyer -->|3. Quote| PQuote[POST /protocol/v1/quote<br/>Applied Vouchers + Math Justification]
        AIBuyer -->|4. Gated Checkout| PCheckout[POST /protocol/v1/order/checkout<br/><b>Strict Spending Gating</b>]
        PCheckout -->|5. Settle & Verify| PVerify[POST /protocol/v1/order/verify<br/>HMAC-SHA256 Signature Verification]
        PVerify --> MongoLedger[(MongoDB Atlas `a2a_orders` Ledger)]
    end

    subgraph GrowthEngine ["3. Autonomous Growth & Retention Loop"]
        AbandonedBags[(MongoDB Uncompleted Bags)] --> CA[6. AI Campaign Agent<br/><b>Groq Key 5 / gpt-oss-20b</b><br/>Hinglish/English Recovery Copy]
        CA --> WQ[(MongoDB `whatsapp_messages` Queue)]
        WQ --> WW[Baileys WhatsApp Worker<br/>Zero Chromium / <35MB RAM]
        WW --> WA([Patron WhatsApp Notification])
    end
```

---

## 📁 Repository Structure

```
AI Growth & Agentic Commerce/
├── server.py                     # Primary FastAPI application entrypoint
├── requirements.txt              # Pinned Python dependencies
├── package.json                  # Node.js dependencies for Baileys WhatsApp worker
├── render.yaml                   # Infrastructure-as-Code for Render Cloud deployment
├── render-build.sh               # Fast build script for Python & Node runtimes
│
├── src/
│   ├── config.py                 # Environment variables & distributed Groq key routing
│   ├── auth.py                   # PBKDF2-HMAC-SHA256 auth, cart & order persistence
│   ├── payments.py               # Razorpay order creation & HMAC-SHA256 verification
│   │
│   ├── protocol/                 # Agent-to-Agent (A2A) Commerce Protocol Layer
│   │   ├── __init__.py           # Protocol package initializer
│   │   └── router.py             # AP2 / MCP / x402 Router (Discovery, Quotes, Gated Checkout)
│   │
│   ├── agents/                   # Multi-Agent Workflow Engine
│   │   ├── state.py              # Pydantic data schemas & unified AgentState
│   │   ├── base.py               # Distributed LLM key routing & search engine singletons
│   │   ├── workflow.py           # LangGraph StateGraph assembly & conditional routing
│   │   ├── query_agent.py        # Intent, attribute & INR budget extraction (Groq Key 1)
│   │   ├── context_agent.py      # Specificity check & clarification prompts (Groq Key 2)
│   │   ├── search_agent.py       # Hybrid vector retrieval node
│   │   ├── validation_agent.py   # Candidate validation & budget gap upsell (Groq Key 2)
│   │   ├── upsell_agent.py       # AI Runway Stylist (CoT matching capsules) (Groq Key 3)
│   │   ├── campaign_agent.py     # Abandoned cart WhatsApp copywriter (Groq Key 5)
│   │   ├── placeholder_agent.py  # Dynamic search bar cues & streaming thought generator
│   │   └── nodes.py              # Modular node aggregator and re-exports
│   │
│   ├── search/                   # Vector Search & Catalog Intelligence
│   │   ├── embeddings.py         # Remote Voyage AI embedding generator (512-dim)
│   │   ├── engine.py             # Hybrid Search (Vector + Text + RRF ranking + Bounds)
│   │   └── indexing.py           # Atlas vector search indexer
│   │
│   └── whatsapp/                 # WhatsApp Messaging & Background Queue
│       ├── queue.py              # MongoDB persistent queue with retry backoffs
│       ├── session_store.py      # MongoDB session persistence across restarts
│       ├── baileys_service.js    # Lightweight Baileys WebSocket sidecar
│       ├── baileys_client.py     # Python IPC client for Baileys sidecar
│       ├── worker.py             # Background sequential dispatch worker
│       └── automation.py         # Abandoned cart campaign orchestrator
│
├── static/                       # Production Web Frontends (Pure Vanilla JS & CSS)
│   ├── index.html                # Luxury fashion concierge storefront
│   ├── styles.css                # Dark-mode luxury CSS tokens & glassmorphism
│   ├── app.js                    # Client state, dynamic streaming & Razorpay checkout
│   ├── admin.html                # Executive Atelier Admin Dashboard
│   ├── admin.css                 # Admin portal styles & KPI cards
│   ├── admin.js                  # Admin metrics, orders stream, cart campaigns, A2A telemetry
│   └── whatsapp.html             # Live QR code scanner & queue monitor
│
├── scripts/
│   └── ai_buyer_agent.py         # Standalone Autonomous AI Buyer simulation client
│
└── tests/                        # Comprehensive Automated Test Suites
    ├── test_agent_protocol.py    # A2A Protocol, MCP discovery, and budget gating tests
    ├── test_razorpay.py          # Razorpay order creation & HMAC-SHA256 signature tests
    ├── test_money_filters_and_upsell.py # INR budget filters & price gap upsell tests
    ├── test_coupon_and_automation.py    # Coupon validation & cart sync tests
    ├── test_abandoned_cart_dispatch.py  # AI copy synthesis & WhatsApp queue tests
    ├── test_whatsapp_service.py  # Queue atomic claiming & Baileys worker tests
    ├── test_auth.py              # PBKDF2 password hashing & cart persistence tests
    ├── test_agents.py            # End-to-end multi-agent pipeline tests
    ├── test_dynamic_upsell.py    # AI stylist Chain-of-Thought ensemble tests
    ├── test_campaign_agent.py    # Multichannel Hinglish copy generation tests
    ├── test_placeholder_agent.py # Real-time prompt streaming tests
    ├── test_health.py            # Health routes & keep-alive tests
    └── test_conversation.py      # Multi-turn conversation flow tests
```

---

## 🛠️ Complete REST API Reference

### 1. Agent-to-Agent (A2A) & MCP Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/.well-known/agent-protocol.json` | AP2/1.0 discovery manifest with merchant capabilities, currency, and rate. |
| `GET` | `/.well-known/mcp.json` | Model Context Protocol tool schema for Claude Desktop & AutoGPT. |
| `POST` | `/protocol/v1/catalog/query` | Structured machine catalog search with price bounding and category filters. |
| `POST` | `/protocol/v1/quote` | Guaranteed quote with voucher discounts (`AURA20`) and math explainability. |
| `POST` | `/protocol/v1/order/checkout` | **Budget Gating**. Creates Razorpay order if within authorized ceiling. |
| `POST` | `/protocol/v1/order/verify` | Validates HMAC-SHA256 signature and records A2A order with `buyer_agent_id`. |
| `GET` | `/protocol/v1/telemetry` | Real-time telemetry of machine orders, active AI Buyers, and GMV. |

### 2. Conversational Concierge Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/chat` | Full LangGraph 5-agent conversational search pipeline. |
| `POST` | `/api/clarify` | Resumes multi-turn conversation after concierge clarification. |
| `POST` | `/api/outfit` | Generates complete look pairings and editorial styling tips. |
| `GET` | `/api/placeholder/batch` | Fetches dynamic typewriter cues and pipeline thought sequences. |

### 3. Auth, Checkout & Growth Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/signup` | Registers patron with PBKDF2-HMAC-SHA256 password hash. |
| `POST` | `/api/auth/login` | Authenticates patron and returns active bag and wardrobe. |
| `POST` | `/api/user/sync` | Persists cart and wardrobe state in MongoDB. |
| `POST` | `/api/coupon/validate` | Validates promo codes (`AURA20`, `AURA25`, `VIP20`, `RUNWAY30`). |
| `POST` | `/api/create-order` | Creates standard Razorpay order in INR test mode. |
| `POST` | `/api/verify-payment` | Cryptographically verifies Razorpay signature and logs order. |
| `POST` | `/api/automation/abandoned-cart-campaign` | Scans MongoDB for abandoned carts and triggers WhatsApp copy dispatch. |

---

## 💻 Local Quickstart

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/ChaitanyaJhindal/AI-Growth-Agentic-Commerce-.git
cd AI-Growth-Agentic-Commerce-

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies for WhatsApp worker
npm install
```

### 2. Configure Environment (`.env`)
```ini
MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.gdjxqnz.mongodb.net/?appName=Cluster0
DB_NAME=ecommerce_catalog
COLLECTION_NAME=products
VOYAGE_API_KEY=pa-...

GROQ_API_KEY_QUERY=gsk_...       # Query Agent
GROQ_API_KEY_CONTEXT=gsk_...     # Context & Validation Agents
GROQ_API_KEY_UPSELL=gsk_...      # Upsell Stylist Agent
GROQ_API_KEY_CAMPAIGN=gsk_...    # Campaign Agent

RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
```

### 3. Start Application Server
```bash
python server.py
# Server running at http://127.0.0.1:8000
```

---

## 🧪 Automated Test Verification

AURA includes 13 test suites proving system correctness across payments, agents, and protocol boundaries:

```bash
# 1. Test AI Buyer Protocol, MCP, and Budget Gating (Includes Error Handling Verification)
python tests/test_agent_protocol.py

# 2. Test Razorpay Order Creation & HMAC-SHA256 Signature Verification
python tests/test_razorpay.py

# 3. Test INR Budget Filters & Graceful Price Gap Upsell
python tests/test_money_filters_and_upsell.py

# 4. Test Coupon Validation & Bag Sync
python tests/test_coupon_and_automation.py

# 5. Simulate Autonomous AI Buyer End-to-End Purchase
python scripts/ai_buyer_agent.py
```

---

## 🚢 Continuous Deployment (Render)
* **Build Command**: `./render-build.sh`
* **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
* **Live Service**: [https://ai-growth-agentic-commerce.onrender.com](https://ai-growth-agentic-commerce.onrender.com)

---

## 📄 License
Developed for the **Razorpay AI Growth & Agentic Commerce Hackathon**. Open-source under the [MIT License](LICENSE).