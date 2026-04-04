# FieldPack AI — Continue from Phase 6

> Paste this into a new Claude Code conversation to continue building.

---

## PROMPT START

I'm building **FieldPack AI** — a Kaggle Gemma 4 Good Hackathon entry ($200K prize, deadline May 18, 2026). You're continuing from where a previous session left off.

### Read these files first (in order):

1. **`CLAUDE.md`** — Project overview, tech stack, architecture, conventions
2. **`docs/PHILOSOPHY.md`** — Strategy, competitive analysis, non-negotiable principles
3. **`docs/TECH_FRAMEWORK.md`** — Full technical framework, schemas, agentic RAG design

### Then read the implementation plan:

4. **`C:\Users\orkoh\.claude\plans\ticklish-discovering-gem.md`** — The detailed 7-phase implementation plan with all substeps

---

### About Me

I'm a hackathon competitor building AI projects. I value winning strategy AND presentation quality (LinkedIn, video). I prefer collaborative ideation — we make every decision together at a low level. I present options, give my lean, and you choose. **Quality first, never cut corners** — each pipeline step exists for a reason and must be fully implemented. Never merge steps to save performance unless I explicitly ask.

---

### What Has Been Completed (Phases 1-5):

**540 tests passing. All code below is implemented, tested, and working.**

#### Phase 1 — Pydantic models + state (85 tests)
- `backend/app/agents/models.py` — IntentType, SearchEngineType, ResultType, ClassifyExtractOutput (with default intent=GENERAL_QUESTION for safe fallbacks), SearchRoute, CraftedQuery, SearchResult, ScoredResult, ReRankOutput, GenerateAnswerInput
- `backend/app/agents/state.py` — FieldAssistantState TypedDict (total=False), ConversationMessage, trim_conversation_history

#### PipelineLogger (37 tests)
- `backend/app/logger.py` — Dual output (JSON file + colored console), in-memory ring buffer for API, user-facing gamification labels via `to_tool_calls_log()`, TimedContext, Step constants (CLASSIFY, ROUTE, CRAFT_QUERY, SEARCH, RERANK, GENERATE, IMAGE_ANALYSIS, OBSERVATION, PACK_LOAD, PACK_BUILD, SYSTEM)
- **Every tool and node uses the logger** — `from app.logger import Step, pipeline_logger as log`
- Convenience methods: `log.log_search()`, `log.log_route()`, `log.log_rerank()`, `log.log_llm_call()`, `log.pipeline_start()`, `log.pipeline_end()`, `log.timed()` context manager

#### Phase 2 — Knowledge Pack schema (53 tests)
- `backend/app/knowledge_pack/schema_sqlite.py` — 7 tables (crops, diseases, crop_diseases, treatments, climate, image_refs, field_observations), 9 indexes, 3 FTS5 virtual tables (prefix='2,3', unicode61), 9 auto-sync triggers, VALID_TABLES allowlist, FTS_TABLE_MAP, TABLE_JOINS
- `backend/app/knowledge_pack/schema_chroma.py` — 4 collections (cosine distance), parent/child model (topic_id + chunk_type metadata), **disease_name added to metadata** for disease_knowledge and treatment_guides, swappable embedding function with lazy cache
- `backend/app/knowledge_pack/schema_manifest.py` — ManifestSchema Pydantic model, RegionInfo, Statistics, ModelsUsed, validate_manifest, create_manifest

#### Phase 3 — Seed data + builder + loader (90 tests)
- `backend/app/knowledge_pack/seed_data.py` — 5 crops, 15 diseases, 31 treatments (organic + conventional, locally available in Casamance), 12 months climate
- `backend/app/knowledge_pack/seed_chunks.py` — Parent/child pairs for all 4 collections. ~140 chunks. Child = farmer's-voice keywords, parent = full detail. `get_all_chunks()`. **disease_name in all chunk metadata.**
- `backend/app/knowledge_pack/builder.py` — `build_pack()` creates full pack: SQLite + FTS5 + ChromaDB with embeddings + manifest + README + SOURCES
- `backend/app/knowledge_pack/loader.py` — `KnowledgePack` class (lazy load, health_check, context manager, **check_same_thread=False** for async/thread-safe reads). Module singleton: `load_pack()`, `get_active_pack()`, `unload_pack()`

#### Phase 4 — Search Tools (167 tests)
- `backend/app/tools/chroma_search.py` — `chroma_search()` (child→parent resolution, cosine distance→score via `max(0, 1-distance)`), `multi_collection_search()`, both with `@tool` wrappers for LangGraph
- `backend/app/tools/fts_search.py` — `fts_search()` (BM25 ranking, query sanitization: strip non-alnum, skip <3 chars and stop words, cap 8 words, OR with prefix*), `fuzzy_fts_search()` (3-tier: exact→ED1 typo variants→LIKE fallback), `_generate_typo_variants()`, both with `@tool` wrappers
- `backend/app/tools/sqlite_query.py` — `structured_query()` (parameterized, VALID_TABLES allowlist, operators: =/$gt/$gte/$lt/$lte/$like/$ne, JOINs via TABLE_JOINS), `fuzzy_structured_query()` (3-tier: exact→LIKE→per-word LIKE), both with `@tool` wrappers
- `backend/app/tools/image_analysis.py` — `analyze_plant_image()` (resize, base64, E4B vision via Ollama httpx, symptom-focused prompt with vocabulary hints, JSON parse with fallback), `@tool` wrapper. **Describes symptoms only — does NOT diagnose.**
- `backend/app/tools/observation_log.py` — `log_observation()` (validates type, no limit on details), `get_observations()`, `get_unsynced_observations()`, `@tool` wrappers

#### Phase 5 — Pipeline Nodes (109 tests)
- `backend/app/agents/nodes/__init__.py` — exports all 6 node functions
- `backend/app/agents/nodes/classify_extract.py` — LLM call #1. Pydantic structured output attempt with 4-tier NL fallback (JSON→code block→regex→safe defaults). 3 few-shot examples (disease, treatment, image). Last 2 history messages for follow-up context. Calls `analyze_plant_image()` when image_path present. Temperature=0.1.
- `backend/app/agents/nodes/route.py` — Pure Python, no LLM. ROUTING_RULES dict maps each IntentType to engines/collections/tables. `_build_metadata_filters()` from crop/disease_name. `expand_route()` for retry #2 (all engines + all collections + key tables). Narrow routes by default.
- `backend/app/agents/nodes/craft_query.py` — LLM call #2. NL + smart parsing. 2 few-shot examples. Generates embedding_query + fts_keywords. Skips if no chroma_embedding in route. Temperature=0.3. Falls back to user message + classify keywords on error.
- `backend/app/agents/nodes/execute_search.py` — Async node. `asyncio.gather` + `asyncio.to_thread` for parallel search. BM25 score normalization to [0,1]. Dedup by source ID. FTS keywords: crafted_query.fts_keywords with classify fallback. `execute_searches_sync()` wrapper for sync callers.
- `backend/app/agents/nodes/rerank.py` — LLM call #3. NL + parsing. Cap 8 highest-scored results. Index-based scoring `[{index, score, keep}]`. Keep threshold=0.4, sufficient=2+ at >=0.5. Temperature=0.1. Fallback: keep all with original scores on parse failure.
- `backend/app/agents/nodes/generate_answer.py` — LLM call #4. RAG-grounded persona: "Answer ONLY from provided context. It's OK to say you don't know." Score-proportional context assembly (max 2000 words, higher score=more space). Parent content only. Bullet points for treatment steps. Temperature=0.4. Updates conversation_history (sliding window 10).

#### LLM Wrapper
- `backend/app/models/offline_llm.py` — `get_field_llm(temperature=0.3)` returns `ChatOllama` with configurable temperature
- `backend/app/models/online_llm.py` — `get_planner_llm()` (31B) and `get_research_llm()` (26B) via Google AI Studio

---

### Architecture Decisions (All Confirmed):

**6-step retrieval pipeline**: Classify → Route → Craft Query → Execute Search → Re-Rank → Generate Answer

1. **4 LLM calls max**, each separate (never combine to save performance)
2. **Python routes, LLM doesn't choose collections** — deterministic routing based on classified intent
3. **3 search engines**: ChromaDB embedding, SQLite FTS5, SQLite structured — Python picks which to use
4. **Parent/child chunking**: Search hits children (keyword-rich, farmer-voice), LLM receives parents (full detail)
5. **Fuzzy matching** on FTS5 (ED1 typo variants → LIKE fallback) and structured queries (exact → LIKE → per-word)
6. **All tools use `get_active_pack()`** to access the loaded Knowledge Pack
7. **All tools and nodes use PipelineLogger** extensively
8. **All search tools have `@tool` decorated LangGraph wrappers** — crucial for LangGraph orchestration
9. **Score conversion**: ChromaDB cosine distance → `max(0, 1-distance)`, BM25 normalized to [0,1] by dividing by batch max
10. **Retry loop**: Attempt 1 = same route + new query. Attempt 2 = expand to ALL engines/collections. Attempt 3 = answer with whatever we have.
11. **disease_name added to ChromaDB metadata** (disease_knowledge + treatment_guides collections) — fixes metadata gap for filtering
12. **SQLite loader uses check_same_thread=False** — safe for asyncio.to_thread parallel reads (read-only + WAL mode)
13. **MiniLM embedding model is provisional** — keep swappable, don't hardcode 384 dims or MiniLM-specific assumptions

---

### What to Build Next: Phase 6 — LangGraph Assembly & Router Wiring

The plan specifies 2 substeps:

**Step 6.1: Assemble the LangGraph state graph** (`backend/app/agents/field_assistant.py`)
- Full StateGraph with all 6 nodes + observation logging node
- `route_condition(state)` → routes to log_observation, craft_query, or execute_search
- `rerank_condition(state)` → routes to generate_answer or loop back (with retry logic using `expand_route()` on attempt 2)
- `run_field_assistant(message, image_path=None, conversation_history=None)` → main entry point
- The graph has **conditional edges and cycles** — the re-rank → craft_query loop is the core agentic behavior

**Step 6.2: Wire graph to FastAPI routers** (`backend/app/routers/chat.py`, `backend/app/routers/pack.py`)
- POST /chat → load active pack → run_field_assistant → return response
- WS /ws/chat → stream intermediate states (classifying, searching, reranking, answer, done)
- POST /packs/load/{pack_id} → call load_pack()
- In-memory session dict for conversation history

### Then Phase 7: Integration Testing & Quality Calibration
- Step 7.1: Build POC Knowledge Pack script
- Step 7.2: End-to-end smoke tests (disease diagnosis, treatment, farming advice, follow-up, fuzzy matching, multi-engine)
- Step 7.3: Prompt tuning against real Ollama E4B

---

### Code Conventions to Follow:

- Python 3.10+, type hints on public functions, `|` for unions not `Union`
- `from app.logger import Step, pipeline_logger as log` — use `log.timed()`, `log.log_search()`, `log.log_step()` everywhere
- `from app.knowledge_pack.loader import get_active_pack` — all tools access pack through singleton
- `@tool` decorator from `langchain_core.tools` on all tool functions
- LangGraph patterns: `TypedDict` for state, `StateGraph` for graph, `add_conditional_edges` for routing
- Error handling at boundaries only. No comments on obvious code.
- Async where possible for FastAPI routes and LangGraph nodes

### Before you start building Phase 6:

**Ask me about any decisions you need to make** — we make every decision together at a low level. Specifically think about:
- LangGraph StateGraph wiring details (entry point, edges, conditional functions)
- How the retry loop modifies state between iterations
- WebSocket streaming protocol (what events to send, in what format)
- FastAPI session management for conversation history
- How to handle the observation logging path (skips search entirely)
- Error recovery at the graph level
