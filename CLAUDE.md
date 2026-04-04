# FieldPack AI

Hackathon entry for the **Kaggle Gemma 4 Good Hackathon** ($200K prize, deadline May 18, 2026). Read `PHILOSOPHY.md` for strategy and `TECH_FRAMEWORK.md` for architecture details.

## What This Is

Two-phase offline AI for humanitarian field workers. Phase 1 (online): LangGraph agents using Gemma 4 31B/26B curate domain-specific knowledge into portable **Knowledge Packs**. Phase 2 (offline): Gemma 4 E4B on Ollama serves that knowledge via agentic RAG with function calling. Demo scenario: agronomist in Senegal photographs a sick cassava plant → offline agent diagnoses disease → provides treatment using local materials.

## Tech Stack

- **Online LLM**: Gemma 4 31B/26B via Google AI Studio free API (`langchain-google-genai` / `ChatGoogleGenerativeAI`)
- **Offline LLM**: Gemma 4 E4B Q8 via Ollama (`langchain-ollama` / `ChatOllama` at `localhost:11434`)
- **Orchestration**: LangGraph (state graphs, parallel branching, conditional edges, tool binding)
- **Vector DB**: ChromaDB persistent mode (embedded, no server, metadata filtering)
- **Structured DB**: SQLite
- **Embeddings**: `all-MiniLM-L6-v2` via `sentence-transformers` (384 dims, used both online and offline)
- **Backend**: FastAPI + WebSocket (uvicorn, port 8000)
- **Frontend**: React + Tailwind (designed in Google Stitch, exported)
- **Image processing**: Gemma E4B native vision (fallback: CLIP hybrid if quality insufficient)

## Project Structure

```
fieldpack-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, WebSocket /ws/chat
│   │   ├── config.py                # Env vars, paths, model config
│   │   ├── routers/
│   │   │   ├── chat.py              # POST /chat, WS /ws/chat
│   │   │   ├── mission.py           # POST /mission/start, GET /mission/status
│   │   │   ├── pack.py              # GET /packs, POST /packs/load
│   │   │   └── health.py            # GET /health
│   │   ├── agents/
│   │   │   ├── mission_planner.py   # Phase 1: plans research from user mission description
│   │   │   ├── research_agent.py    # Phase 1: single research agent (web search, fetch, save)
│   │   │   ├── knowledge_compiler.py# Phase 1: validates, structures, embeds, builds pack
│   │   │   └── field_assistant.py   # Phase 2: agentic RAG graph (THE core innovation)
│   │   ├── tools/
│   │   │   ├── web_search.py        # Online: search tool for research agents
│   │   │   ├── web_fetch.py         # Online: page content extraction
│   │   │   ├── chroma_search.py     # Offline: ChromaDB vector + metadata search
│   │   │   ├── sqlite_query.py      # Offline: structured SQL queries
│   │   │   ├── image_analysis.py    # Offline: E4B vision + DB cross-reference
│   │   │   └── observation_log.py   # Offline: save field observations for later sync
│   │   ├── knowledge_pack/
│   │   │   ├── builder.py           # Assemble pack from research results
│   │   │   ├── loader.py            # Load pack for offline use
│   │   │   └── schema.py            # Manifest validation, DB schema creation
│   │   └── models/
│   │       ├── online_llm.py        # Google AI Studio wrapper (31B/26B)
│   │       └── offline_llm.py       # Ollama wrapper (E4B)
│   ├── requirements.txt
│   └── .env                         # GOOGLE_AI_STUDIO_API_KEY, OLLAMA_BASE_URL, KNOWLEDGE_PACK_DIR
├── frontend/                        # React/Tailwind from Stitch export
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface/       # Chat window, message bubbles, input bar
│   │   │   ├── KnowledgePanel/      # Pack info sidebar, source list
│   │   │   ├── StatusBar/           # Online/offline indicator, model status
│   │   │   ├── MissionBriefing/     # Phase 1 mission form + progress
│   │   │   └── ImageViewer/         # Photo display + diagnosis overlay
│   │   ├── hooks/                   # useChat, useFieldPack, useOfflineMode
│   │   └── api/client.ts            # FastAPI HTTP + WebSocket client
│   └── package.json
├── packs/                           # Generated Knowledge Packs
├── notebooks/                       # Kaggle submission notebooks
├── PHILOSOPHY.md                    # Strategy, competitive analysis, narrative
├── TECH_FRAMEWORK.md                # Full architecture, schemas, decisions
└── BOOTSTRAP_PROMPT.md              # Context prompt for new Claude sessions
```

## Key Commands

```bash
# Backend
cd fieldpack-ai && source venv/Scripts/activate   # Windows Git Bash
uvicorn backend.app.main:app --reload --port 8000

# Frontend
cd fieldpack-ai/frontend && npm run dev            # localhost:3000

# Ollama (E4B for offline)
ollama serve                                        # localhost:11434
ollama pull gemma4-e4b:q8

# Test Ollama
curl http://localhost:11434/api/generate -d '{"model":"gemma4-e4b:q8","prompt":"Hello"}'
```

## Architecture Patterns

### LangGraph Agents

All agents are LangGraph `StateGraph` instances. Two distinct graphs:

**Phase 1 graph** (online): `mission_planner` → parallel `research_agent` x3 → `knowledge_compiler` → `pack_builder`. Uses `ChatGoogleGenerativeAI` (31B for planner/compiler, 26B MoE for research agents).

**Phase 2 graph** (offline): `classify_intent` → `plan_retrieval` → `execute_tools` → `evaluate_results` → (loop back or) `generate_answer`. Uses `ChatOllama` (E4B). This graph has **conditional edges** and **cycles** — the LLM decides each turn whether to query ChromaDB, SQLite, analyze images, or loop.

### Tool Definitions

All tools use Gemma 4 native function calling format. Tools are Python functions decorated with LangGraph's `@tool` decorator. The LLM returns structured JSON tool calls; LangGraph executes them and feeds results back.

### ChromaDB Collections

Four collections in each Knowledge Pack, all with metadata filtering:
- `disease_knowledge` — metadata: `disease_id`, `crop`, `type`, `severity`
- `treatment_guides` — metadata: `disease_id`, `treatment_id`, `is_organic`, `difficulty`
- `farming_practices` — metadata: `topic`, `crop`, `season`, `practice_type`
- `regional_context` — metadata: `region`, `topic`, `data_type`

### SQLite Tables

`crops`, `diseases`, `crop_diseases` (M2M), `treatments`, `climate`, `image_refs`, `field_observations`. Full schema in TECH_FRAMEWORK.md Section 6.

### Knowledge Pack Format

```
pack_name/
├── manifest.json       # Metadata: region, crops, counts, models used, embedding info
├── knowledge.db        # SQLite structured data
├── chroma_db/          # ChromaDB persistent store (vector embeddings + metadata)
├── images/             # Reference photos: diseases/, healthy/, treatments/
├── README.md           # Human-readable description
└── SOURCES.md          # Data provenance
```

Zipped as `.fieldpack`. The manifest, README, and SOURCES.md exist for judge inspection.

## Critical Constraints

- **No local GPU** — online LLM = Google AI Studio API calls, offline LLM = Ollama on CPU
- **Google AI Studio free tier** — 15K tokens/min, 30 req/min, 14.4K req/day. Sufficient for batch knowledge gathering, not for serving live traffic.
- **Ollama E4B on CPU** — ~5-10 tokens/sec. Acceptable for demo. Pre-warm model before recording video.
- **Deadline May 18, 2026** — working demo > feature count. If something blocks the hero shot, drop it.

## Non-Negotiable Rules

1. **The hero shot must work every time**: plant photo → disease diagnosis → local treatment plan. This is the demo. Everything else is secondary.
2. **Impact first, technology second**: every feature must serve "Amina in the field." If it doesn't help the user persona, don't build it.
3. **Narrow execution, broad vision**: we build ONE Knowledge Pack (Casamance agriculture). We show the platform concept in the writeup/video. We do not build two packs.
4. **Offline is the point, not a feature**: if a feature requires internet, it belongs in Phase 1 only.
5. **Full Gemma 4 family on purpose**: 31B plans, 26B researches, E4B serves offline. Each model has a justified role.
6. **Google ecosystem optics**: AI Studio + Stitch + Gemma + Kaggle = all Google. Intentional for a Google hackathon.
7. **Agentic RAG is non-deterministic**: the LLM decides retrieval strategy each turn (SQL vs vector vs image vs loop). This is NOT a fixed pipeline. This is the core technical differentiator.

## Style & Code Conventions

- Python 3.10+, type hints on public functions
- Async where possible (FastAPI routes, LangGraph nodes)
- Environment variables via `.env` + `python-dotenv`, never hardcoded keys
- LangGraph patterns: `TypedDict` for state, `@tool` decorator for tools, `add_conditional_edges` for routing
- ChromaDB: always use `PersistentClient(path=...)`, never in-memory for anything that ships in a pack
- Error handling at boundaries (API calls, file I/O, Ollama), not internal logic
- No comments on obvious code. Comments only where the "why" isn't clear from context.

## Deliverables Checklist

- [ ] Phase 1 pipeline: mission → research agents → knowledge compiler → .fieldpack
- [ ] Phase 2 pipeline: load pack → agentic RAG → chat + image upload → diagnosis
- [ ] FastAPI backend with WebSocket streaming
- [ ] React frontend (Stitch-designed)
- [ ] Kaggle notebook (reproducible Phase 1 demo)
- [ ] 3-minute YouTube video (Amina narrative arc)
- [ ] Kaggle writeup (<1,500 words, cover image, architecture diagram)
