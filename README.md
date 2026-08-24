# MongoDB Atlas + LangGraph Agentic E-Commerce System

Multi-Agent AI E-Commerce Shopping Assistant built with **LangGraph**, **Groq LLM (`openai/gpt-oss-120b`)**, **MongoDB Atlas Hybrid Search**, and **PyMongo**.

---

## 🤖 Agentic Architecture (LangGraph Workflow)

```
                       User Query
                           │
                           ▼
                    ┌──────────────┐
                    │ Query Agent  │ ── Parses intent, attributes, & constraints
                    └──────┬───────┘
                           │
                           ▼
                   ┌───────────────┐
                   │ Context Agent │ ── Evaluates context completeness
                   └───────┬───────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      [Needs Clarification?]    [Has Enough Context?]
              │                         │
     Ask Follow-up Question        Search Node
      (Max 2 user turns)                │
                                        ▼
                               ┌──────────────────┐
                               │ Validation Agent │ ── Checks product relevance
                               └────────┬─────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
                 [Validation Failed]            [Validation Passed]
                 (Rewrite query & retry)               │
                         │                             ▼
                         └──────────────►       ┌──────────────┐
                                                │ Upsell Agent │ ── Recommends outfits
                                                └──────┬───────┘
                                                       │
                                                       ▼
                                                 Final Results
```

### 1. The 5 Core Agents & Nodes

| Agent / Node | Role | Implementation |
| :--- | :--- | :--- |
| **1. Query Agent** | Extracts intent, category, brand, gender, price range, and attributes. | Structured Pydantic extraction using Groq `openai/gpt-oss-120b`. |
| **2. Context Agent** | Checks if query has enough context. Asks **at most 1 concise question** if critically vague (max 2 rounds). | Interactive follow-up loop. |
| **3. Search Node** | **Deterministic tool node**. Executes `hybrid_search(query, filters)` against MongoDB Atlas. | PyMongo `$vectorSearch` + `$text` + RRF fusion (no LLM decision). |
| **4. Validation Agent** | Validates retrieved products against requirements. Rewrites query if mismatched (max 2 retries). | Quality control agent with retry feedback loop. |
| **5. Upsell Agent** | Recommends matching complementary products (e.g. Shoes → Socks/Pants, Shirts → Trousers/Watches). | Searches matching categories and uses LLM to rank outfit compatibility. |

---

## 🚀 Running the Interactive Agent CLI

Run the multi-agent conversational shopping assistant in your terminal:

```bash
python agent_cli.py
```

### Example 1: Specific Query Flow
```
Enter your shopping request: casual blue shirts for men under 60

[LangGraph] Processing agent pipeline...
Intent Extracted:   search
Parsed Search Term: 'casual blue shirts for men'
Active Filters:     {'gender': 'Men', 'article_type': 'Shirts', 'price': {'$lte': 60.0}}
Validation Status:  PASSED

Validated Search Results (15 items):
+-----+------------+----------------------------------+----------+---------------+---------+---------+---------+-----------+-------------+
|   # | ID         | Name                             | Brand    | Gender/Type   | Color   | Price   | Rating  | RRF Score |
+=====+============+==================================+==========+===============+=========+=========+=========+===========+=============+
|   1 | PROD-15970 | Turtle Check Men Navy Blue Shirt | Turtle   | Men / Shirts  | Navy    | $51.38  | 4.1     | 0.015584  |
...

AI Fashion Stylist Outfit Recommendations (Upsell & Cross-Sell):
[Look #1] Basics Men Black Trousers ($58.91) - Black Trousers
  * Compatibility: Classic contrast pairing navy blue shirt with black trousers.
  * Stylist Tip:   Tuck in the front, add a brown leather belt and casual loafers.
```

### Example 2: Clarification Flow
```
Enter your shopping request: I want sneakers

[LangGraph] Processing agent pipeline...
🤖 Context Agent Follow-up:
   "Are you looking for men's or women's sneakers, and do you have a target budget?"

Your answer: Men's running sneakers under $80

[LangGraph] Processing agent pipeline...
Validation Status:  PASSED
... (Returns 15 validated Men's running sneakers under $80 with matching sportswear upsells)
```

---

## 🧪 Automated Agent Testing

Run the full end-to-end test suite for all 5 agents:
```bash
python test_agents.py
```

---

## 📁 File Structure

```
├── agent_state.py          # Pydantic models & LangGraph AgentState TypedDict
├── agents.py               # QueryAgent, ContextAgent, SearchNode, ValidationAgent, UpsellAgent
├── agent_graph.py          # LangGraph StateGraph assembly and conditional edges
├── agent_cli.py            # Interactive terminal CLI with follow-up loops
├── test_agents.py          # Automated multi-agent workflow verification test suite
├── hybrid_search.py        # MongoDB Atlas Vector Search + Text Search + RRF Engine
├── embedding_engine.py     # Sentence-Transformers (all-MiniLM-L6-v2, 384 dims)
├── index_manager.py        # MongoDB Atlas Vector Search & text indexes
├── ingest.py               # Fast bulk dataset ingestion script
└── config.py               # Configuration & DNS resolver fallback
```