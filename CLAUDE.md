# FieldPack AI

Hackathon entry for the **Kaggle Gemma 4 Good Hackathon** ($200K prize, deadline May 18 2026). See `PHILOSOPHY.md` for strategy, `TECH_FRAMEWORK.md` for full architecture.

Two-phase offline AI for humanitarian field workers. Phase 1 (online): LangGraph agents curate knowledge into portable **Knowledge Packs**. Phase 2 (offline): Gemma 4 E2B on Ollama serves that knowledge via agentic RAG. Demo: agronomist in Senegal photographs sick cassava plant -> offline agent diagnoses disease -> provides treatment using local materials.

## Tech Stack

- **Online LLM**: Gemma 4 31B/26B via Google AI Studio (`langchain-google-genai`)
- **Offline LLM**: Gemma 4 E2B Q4 via Ollama (`langchain-ollama` / `ChatOllama`)
- **Orchestration**: LangGraph (`StateGraph`, conditional edges, retry loops)
- **Vector DB**: ChromaDB persistent mode (4 collections with metadata filtering)
- **Structured DB**: SQLite + FTS5
- **Embeddings**: `all-MiniLM-L6-v2` via `sentence-transformers` (384 dims)
- **Backend**: FastAPI + WebSocket (uvicorn, port 8000)

## Project Layout

```
backend/
  app/
    agents/
      field_assistant.py   # StateGraph wiring, streaming entry points
      nodes/               # One file per pipeline node (9 nodes)
      models.py            # Pydantic models (ClassifyExtractOutput, ScoredResult, etc.)
      state.py             # FieldAssistantState TypedDict
      history.py           # Conversation summary heuristics
    tools/                 # chroma_search, fts_search, sqlite_query, image_analysis, observation_log
    knowledge_pack/        # builder, loader, schema_sqlite, schema_chroma, schema_manifest, seed_*
    models/                # offline_llm.py (Ollama + fallback), online_llm.py (Google AI Studio)
    routers/               # chat (POST /chat, WS /chat/ws), health, mission, pack
    config.py              # Settings via pydantic-settings + .env
  tests/                   # ~580 unit/integration tests
  modelfiles/              # Custom Ollama Modelfile (fieldpack-assistant)
packs/                     # Generated Knowledge Packs
```

## Key Commands

```bash
# Activate venv (Windows Git Bash — venv is at repo root)
cd fieldpack-ai && source venv/Scripts/activate

# Backend
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Tests (venv is at repo root, not backend/)
cd backend && PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/ -v --ignore=tests/test_step_7_live.py

# Ollama
ollama serve
ollama pull gemma4:e2b-it-q4_K_M
# Custom Modelfile:
ollama create fieldpack-assistant -f backend/modelfiles/fieldpack-assistant.Modelfile
```

## Phase 2 Pipeline (the core innovation)

The agentic RAG graph in `field_assistant.py` has 9 nodes with conditional edges and retry loops:

```
classify_and_extract -> route_intent -> needs_search_node
  -> [no search + observation] -> log_observation_node -> END
  -> [no search + other]       -> generate_answer -> END
  -> [needs search]            -> craft_search_query -> execute_searches -> rerank_results
      -> [sufficient OR max 3 attempts] -> generate_answer -> END
      -> [attempt 2]                    -> expand_route_node -> craft_query (loop)
      -> [attempt 1]                    -> craft_query (loop, same route)
```

LLM calls: classify (#1), craft_query (#2), rerank (#3), generate (#4), plus needs_search (ambiguous cases only).

Each node passes tailored Ollama params via `get_field_llm(temperature, num_predict, format)`:
- classify: `num_predict=128, format="json"` | craft_query: `256, "json"` | rerank: `256, "json"`
- needs_search: `num_predict=32` | generate_answer: `num_predict=1024`

Reranking uses a **two-tier strategy**: fast heuristic first (normalize scores per engine type, dedup, sort), LLM fallback only on retry when heuristic marks results insufficient.

## LLM Provider Fallback

`get_field_llm()` in `offline_llm.py` resolves: tunnel Ollama -> local Ollama -> Google AI Studio API. Provider set via `FIELD_LLM_PROVIDER` env var. All Ollama instances get `num_ctx` and `keep_alive` from settings.

## Style & Code Conventions

- Python 3.10+, type hints on public functions
- Async where possible (FastAPI routes, LangGraph nodes)
- Environment variables via `.env` + `pydantic-settings`, never hardcoded keys
- LangGraph patterns: `TypedDict` for state, `@tool` for tools, `add_conditional_edges` for routing
- ChromaDB: always `PersistentClient(path=...)`, never in-memory for pack data
- Error handling at boundaries (API calls, file I/O, Ollama), not internal logic
- No comments on obvious code. Comments only where "why" isn't clear from context

## Non-Negotiable Rules

1. **Hero shot must work every time**: plant photo -> diagnosis -> local treatment plan. Everything else is secondary.
2. **Offline is the point**: if a feature requires internet, it belongs in Phase 1 only.
3. **Agentic RAG is non-deterministic**: the LLM decides retrieval strategy each turn. This is NOT a fixed pipeline.
4. **Narrow execution**: ONE Knowledge Pack (Casamance agriculture). Show the platform concept in writeup/video.
5. **Google ecosystem optics**: AI Studio + Stitch + Gemma + Kaggle = all Google. Intentional for a Google hackathon.
