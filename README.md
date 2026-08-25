# AURA — AI-Native Luxury Fashion Concierge & Agentic Commerce System

A multi-agent conversational e-commerce shopping assistant built with **LangGraph**, **Groq LLM (`openai/gpt-oss-120b`)**, **MongoDB Atlas Hybrid Search**, and **FastAPI**.

---

## 🤖 Agentic Architecture (LangGraph Workflow)

```
                       User Query / Interaction
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │     1. Query Agent       │ ── Parses intent, attributes, & active filters
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │     2. Context Agent     │ ── Evaluates context completeness
                     └────────────┬─────────────┘
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
             [Needs Clarification?]    [Has Enough Context?]
                     │                         │
            Ask Follow-up Question             ▼
             (Max 2 user turns)      ┌──────────────────┐
                                     │  3. Search Node  │ ── Atlas Vector Search + Text Search + RRF
                                     └─────────┬────────┘
                                               │
                                               ▼
                                     ┌──────────────────┐
                                     │ 4. Validation    │ ── Verifies result relevance
                                     └─────────┬────────┘
                                               │
                                ┌──────────────┴──────────────┐
                                ▼                             ▼
                        [Validation Failed]            [Validation Passed]
                       (Rewrite query & retry)                │
                                │                             ▼
                                └──────────────►     ┌──────────────────┐
                                                     │  5. Upsell Agent │ ── Styles complementary outfits
                                                     └────────┬─────────┘
                                                              │
                                                              ▼
                                                        Final Results
```

### The 5 Core Agents & Nodes

| Node | Role | Implementation |
| :--- | :--- | :--- |
| **1. Query Agent** | Extracts intent, category, brand, gender, price limits, and attributes. | Structured Pydantic extraction using Groq `openai/gpt-oss-120b`. |
| **2. Context Agent** | Evaluates if query is actionable. Generates 1 concise question if vague. | Interactive clarification loop (max 2 rounds). |
| **3. Search Node** | **Deterministic tool node**. Executes `hybrid_search` against MongoDB Atlas. | PyMongo `$vectorSearch` + `$text` + Reciprocal Rank Fusion (RRF). |
| **4. Validation Agent** | Validates product matches against user criteria; triggers query rewrite retry if needed. | Quality control with retry loop (max 2 retries). |
| **5. Upsell Agent** | AI Fashion Stylist recommending matching complementary items. | Complementary category mapping + LLM style harmony ranking. |

---

## 📁 Clean & Modular Project Layout

```
AI Growth & Agentic Commerce/
├── data/                           # Catalog datasets & Atlas index schema
│   ├── products_catalog.json
│   ├── products_catalog.csv
│   ├── products_catalog.xlsx
│   └── atlas_vector_search_index.json
├── src/                            # Core application source code
│   ├── __init__.py
│   ├── config.py                   # Environment & runtime configuration
│   ├── search/                     # Hybrid search & vector embedding engine
│   │   ├── __init__.py
│   │   ├── embeddings.py           # 384-dim SentenceTransformer embedding singleton
│   │   ├── engine.py               # Hybrid Search (Vector + Text + RRF ranking)
│   │   └── indexing.py             # Atlas vector search & metadata indexing
│   └── agents/                     # LangGraph Multi-Agent system
│       ├── __init__.py
│       ├── state.py                # Pydantic structured schemas & AgentState
│       ├── nodes.py                # The 5 agent nodes (Query, Context, Search, Validation, Upsell)
│       └── workflow.py             # LangGraph StateGraph & memory checkpointer
├── static/                         # Web UI frontend assets
│   ├── index.html                  # Luxury fashion concierge web interface
│   ├── styles.css                  # Modern dark-mode styling
│   └── app.js                      # Client state, dynamic filtering & outfit studio
├── tests/                          # Automated verification test suites
│   ├── test_agents.py              # End-to-end agent workflow tests
│   └── test_conversation.py        # Multi-turn dialogue persistence test
├── scripts/                        # Utility & operational scripts
│   └── ingest.py                   # Bulk catalog ingestion to MongoDB Atlas
├── server.py                       # Root Entrypoint: FastAPI web server (http://127.0.0.1:8000)
├── agent_cli.py                    # Root Entrypoint: Interactive terminal shopping assistant
├── search_cli.py                   # Root Entrypoint: Direct hybrid search CLI
├── requirements.txt                # Pinned dependencies
├── .env.example                    # Environment configuration template
└── README.md
```

---

## ⚡ Quick Start Guide

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and provide your credentials:
```ini
MONGODB_PASSWORD=your_mongodb_password
GROQ_API_KEY=your_groq_api_key
```

### 3. Ingest Data (Optional / First Time Setup)
```bash
python scripts/ingest.py --file data/products_catalog.json
```

---

## 🚀 Running the Applications

### 🌐 Option A: Launch Web Concierge (FastAPI + Modern Web UI)
```bash
python server.py
```
Open **`http://127.0.0.1:8000`** in your browser to experience the full AURA AI luxury fashion concierge.

### 💻 Option B: Run Interactive Terminal Shopping Assistant
```bash
python agent_cli.py
```

### 🔍 Option C: Run Direct Hybrid Search CLI
```bash
python search_cli.py "casual blue shirts" --gender Men --max-price 60
```

---

## 🧪 Running Automated Tests

Run the full end-to-end agent test suite:
```bash
python tests/test_agents.py
```

Run the multi-turn conversational persistence test:
```bash
python tests/test_conversation.py
```