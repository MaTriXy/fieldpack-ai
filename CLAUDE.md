# FieldPack AI

Offline AI for humanitarian field workers. Gemma 4 E2B on Ollama serves curated Knowledge Packs via agentic RAG on a laptop, with a phone thin-client APK for camera + UI. **Hackathon entry for the Kaggle Gemma 4 Good Hackathon.**

This file is the entry point for anyone — human or AI assistant — new to the repo. Read top to bottom and you'll know what the app does, how to run it, where things live, and what's likely to bite you.

---

## 1. What the app actually is

Two phases, one system:

1. **Phase 1 — Online curation (one-time per Knowledge Pack).** Cloud Gemma 4 31B / 26B via Google AI Studio orchestrates a research pipeline: source gathering (PDFs, HTML, CGIAR, climate sites, Tavily), extraction, chunking, embedding, and packaging into a portable Knowledge Pack (SQLite + ChromaDB + images + manifest). Lives in `backend/app/agent_farm/`.
2. **Phase 2 — Offline serving (runs in the field).** The laptop runs FastAPI + LangGraph + Ollama + Gemma 4 E2B Q4_K_M. The phone is a thin Capacitor/React client that hits the laptop over WiFi — no internet needed for inference. Lives in `backend/app/agents/` (the LangGraph field assistant) and `frontend/`.

The demo pack is `packs/casamance_agriculture/` (5 crops, ~15 diseases, southern Senegal context).

**Design docs:** `docs/PHILOSOPHY.md` (why) and `docs/TECH_FRAMEWORK.md` (how). `docs/TROUBLESHOOTING.md` covers the most common setup pain points.

---

## 2. Quick Start

The venv lives at the repo root (`venv/`). Use Git Bash on Windows — commands below assume Unix-style paths.

```bash
source venv/Scripts/activate   # Windows Git Bash; on macOS/Linux use venv/bin/activate

# 1. Ollama (Phase 2 edge LLM)
ollama serve                                   # in one terminal
ollama pull gemma4:e2b-it-q4_K_M               # first time only, ~5 GB

# 2. Backend (FastAPI on :8000)
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Frontend (Vite on :5173, proxies /api to :8000)
cd frontend && npm run dev

# 4. Tests (581+ tests; skip the slow live test by default)
cd backend && PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/ -v --ignore=tests/test_step_7_live.py
```

Then open <http://localhost:5173>. For the phone-as-client demo, see the README.

**Docker alternative (judges, clean machines):** `docker-compose up` from the repo root. First run pulls ~5 GB and takes ~5 min; subsequent starts are seconds. Do **not** copy `backend/.env.example` to `.env` when using Docker — Compose injects the env directly. See README "Run in Docker" for GPU passthrough and firewall notes.

---

## 3. Critical Configuration (read before running)

These are the settings that most often cause "it doesn't work" reports.

### Intel integrated GPU → garbled output
`OLLAMA_NUM_GPU=0` (CPU-only) is the default and should stay that way on Intel iGPUs. Partial offload across precision boundaries corrupts Gemma 4 E2B output — this is the **#1 recurring bug**. If the model suddenly produces word salad, check this first.

### LLM provider
`FIELD_LLM_PROVIDER` in `backend/.env`:
- `ollama-local` — local Ollama only (default dev setup)
- `ollama` — Colab GPU tunnel with local fallback (see `notebooks/colab_ollama_gpu.ipynb`)
- `google` — Google AI Studio (needs `GOOGLE_AI_STUDIO_API_KEY`)

Changes to `.env` require a backend restart — `_resolve_provider` in `backend/app/models/offline_llm.py` has a TTL cache.

### Demo mode
`DEMO_MODE=true` (default in `.env.example`) serves canned responses — useful for UI work without a GPU. Set to `false` for the real pipeline. Docker Compose sets this to `false` directly.

### Ollama tuning
- `OLLAMA_NUM_CTX=4096` must match the Modelfile. Oversized KV cache degrades attention on small models.
- `OLLAMA_KEEP_ALIVE=-1` keeps the model resident so the first query isn't a cold start.
- Server-level vars (`OLLAMA_KV_CACHE_TYPE`, `OLLAMA_FLASH_ATTENTION`, etc.) must be set **before** `ollama serve` starts — see `backend/.env.example` for the menu.

### API keys
Never commit keys. `.env` only. Google AI Studio's Gemma 4 access is free tier; rate limits are 15k tokens/min, 30 req/min, 14.4k req/day — plenty for one-shot pack builds, not for serving live traffic.

---

## 4. Repo Layout (what lives where)

```
fieldpack-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry; wires routers, CORS, startup
│   │   ├── config.py                # pydantic-settings; reads .env
│   │   ├── agents/                  # Phase 2: offline Field Assistant (LangGraph)
│   │   │   ├── field_assistant.py   # Graph build + WebSocket streaming
│   │   │   ├── state.py             # TypedDict-style agent state
│   │   │   └── nodes/               # classify_extract, route, needs_search,
│   │   │                            #   craft_query, execute_search, rerank,
│   │   │                            #   expand_route, generate_answer, log_observation
│   │   ├── agent_farm/              # Phase 1: online knowledge curation
│   │   │   ├── phases/              # source gathering, extraction, packaging
│   │   │   ├── sources/             # PDF, HTML, CGIAR, climate parsers
│   │   │   └── tools/               # web search (Tavily), web fetch
│   │   ├── knowledge_pack/          # Pack schema, builder, loader, manifest
│   │   ├── models/                  # LLM providers: offline_llm.py, online LLMs
│   │   ├── routers/                 # chat, conversations, mission, pack,
│   │   │                            #   observations, upload, health
│   │   └── tools/                   # RAG tools: chroma search, sqlite query,
│   │                                #   FTS, image analysis, observation log
│   ├── tests/                       # 581+ tests (pytest); e2e/ and fixtures/ subdirs
│   ├── modelfiles/                  # Ollama Modelfile overrides
│   ├── scripts/                     # one-off utilities (pack ops, smoke tests)
│   ├── quality_test_*.py            # End-to-end quality harnesses
│   └── .env.example                 # Copy to .env (native runs only)
├── frontend/
│   ├── src/
│   │   ├── App.tsx, main.tsx        # Router + mount
│   │   ├── pages/                   # HomePage, FieldChatPage, DiagnosisCardPage,
│   │   │                            #   ObservationsPage, MissionChatPage,
│   │   │                            #   KnowledgeExplorerPage, PackListPage,
│   │   │                            #   PackInfoPage, SettingsPage,
│   │   │                            #   OnboardingPage, AgentProgressPage,
│   │   │                            #   PipelineDebugPage
│   │   ├── components/              # Reusable UI (cards, pipeline panel, etc.)
│   │   ├── hooks/                   # useBackendReachable, swipe, Android back
│   │   └── lib/                     # config.ts (URL resolution + LAN scan),
│   │                                #   API client, offline queue
│   └── android/                     # Capacitor Android project (APK source)
├── packs/
│   └── casamance_agriculture/       # Demo Knowledge Pack
│       ├── knowledge.db             # Structured: diseases, treatments, crops
│       ├── chroma_db/               # Vector embeddings (HNSW)
│       ├── images/                  # Reference crop photos
│       ├── manifest.json            # Pack metadata
│       └── SOURCES.md               # Data provenance
├── notebooks/
│   └── colab_ollama_gpu.ipynb       # Optional Colab T4 tunnel for remote Ollama
├── docs/
│   ├── PHILOSOPHY.md                # Strategy, competition analysis
│   ├── TECH_FRAMEWORK.md            # Full architecture, decisions, rationale
│   ├── DEVELOPER_NOTES.md           # Environment tips, APK build, gotchas
│   ├── TROUBLESHOOTING.md           # One-stop setup issue guide
│   ├── QUICKSTART_POWERSHELL.md     # Windows PowerShell variant
│   ├── SUBMISSION_PLAYBOOK.md       # Hackathon submission steps
│   ├── KAGGLE_WRITEUP.md            # Competition writeup
│   └── VIDEO_SCRIPT.md              # 3-min demo video script
├── dist-apk/                        # Shipped APK (gitignored, built manually)
├── docker-compose.yml               # One-command setup (Ollama + app)
├── Dockerfile                       # Backend + frontend build
├── jdk-21.0.10+7/                   # Local JDK for APK builds
└── CLAUDE.md                        # This file
```

---

## 5. The Agentic RAG Pipeline

The Field Assistant is a LangGraph state machine, not a fixed retrieval chain. It decides at each step whether it has enough context.

```
classify → route → needs_search
  → [no search]  → generate_answer → END
  → [search]     → craft_query → execute_search → rerank
      → [sufficient OR max 3 attempts] → generate_answer → END
      → [retry]  → expand_route → craft_query (loop)
```

Key behaviors and why they exist:

- **Conversational gate** — "hi", simple follow-ups, etc. skip RAG entirely via a regex gate in `needs_search.py`. Cheap and preserves conversational feel.
- **Streaming** — `generate_answer` is async and streams tokens via `llm.astream()`; the frontend renders word-by-word over WebSocket.
- **Two-tier rerank** — fast heuristic first, LLM rerank only on retry. Avoids paying for LLM rerank on easy queries.
- **Parent/child chunking** — search matches child chunks (higher precision), but context uses parent chunks (richer detail). Classic RAG win.
- **`reasoning=False` globally** on all Ollama calls (`offline_llm.py`). E2B thinking tokens produce empty content and burn context. Don't re-enable without evidence.
- **Content normalization** — `extract_text()` in `field_assistant.py` handles both string (Ollama) and list-of-dicts (Google) content formats so provider swaps are transparent.
- **WebSocket events** — `field_assistant.py` emits `status`, `token`, `sources`, `done` events. Adding or renaming one of these requires an APK rebuild (the shipped APK bakes in the frontend bundle).

---

## 6. Stack Summary

| Layer | Technology | Notes |
|---|---|---|
| Backend | FastAPI + uvicorn | Async, WebSocket streaming |
| Orchestration | LangGraph | State machine for agentic RAG |
| Vector store | ChromaDB (persistent) | Always `PersistentClient(path=...)`, never in-memory for pack data |
| Structured DB | SQLite + FTS | Per-pack `knowledge.db` |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | Offline, ~90 MB, pre-downloaded in Docker build |
| Edge LLM | Gemma 4 E2B Q4_K_M via Ollama | 5.1B params, ~8 GB RAM, runs on CPU |
| Cloud LLMs | Gemma 4 31B + 26B via AI Studio | Free tier, used for Phase 1 |
| Frontend | React 19 + Vite 8 + Tailwind v4 + TS | Tailwind v4 `oklch()` → Android 12+ / Chrome 111+ |
| Mobile | Capacitor 8 | Thin client, JDK 21 to build |
| Config | pydantic-settings + `.env` | Never hardcode keys |

Python 3.10+. Type hints on public functions. Async where possible. Error handling at boundaries only (API calls, file I/O, Ollama) — not internal logic.

---

## 7. Phone Thin-Client (the real demo)

`frontend/src/lib/config.ts:isNative()` switches URL resolution between web and Capacitor modes.

- **LAN discovery** — `autoScanForServer()` probes saved URL → known hotspot IPs (`192.168.137.1` Windows, `192.168.43.1` Android) → WebRTC-detected local IP /24 scan. Add new hotspot patterns to `priorityIps` if testing on new networks.
- **Capacitor config** — `CapacitorHttp: { enabled: false }` (do not flip; it silently breaks WebSocket). `cleartext: true` is required for HTTP-over-LAN on Android 9+.
- **Firewall** — Windows Defender prompts on first `docker-compose up`; must "Allow access" on Private + Public, or the phone can't reach `:8000`.
- **Backend binding** — must be `0.0.0.0` (set in `config.py`) for LAN.

**APK build (only when frontend/backend contract changes):**
```bash
cd frontend && npm run build && npx cap sync android
JAVA_HOME="/c/fieldpack-ai/jdk-21.0.10+7" ANDROID_SDK_ROOT="/c/fieldpack-ai/.android-sdk" \
  PATH="$JAVA_HOME/bin:$PATH" ./android/gradlew -p android assembleDebug
# Output: frontend/android/app/build/outputs/apk/debug/app-debug.apk
# Copy to dist-apk/fieldpack-ai-v1.0.0-debug.apk (gitignored)
# Record SHA256 in README after each rebuild
```

Current release SHA256 (2026-04-18): `831984eb9fa29bd585ddef60c409e87bdce01e4a24d038f26f68932ec6f525df`.

---

## 8. Top Gotchas (check here before investigating)

All of these have bitten us before. See `docs/TROUBLESHOOTING.md` for full context.

1. **Garbled model output** → `OLLAMA_NUM_GPU=0`. See §3.
2. **First query is slow (30–90s)** → ChromaDB HNSW warm-up on first query per collection. Normal. Fire a throwaway query before a demo.
3. **`ollama pull` fails with "file does not exist"** → Gemma 4 tag in Ollama registry changed. `curl https://ollama.com/library/gemma4/tags` and update `OLLAMA_MODEL` in `docker-compose.yml` + `backend/.env` + the pull command in the `ollama-init` service.
4. **Phone can't reach laptop** → in order: (a) same subnet? `ping` from phone. (b) Windows Firewall blocking `:8000`? (c) `curl http://<laptop-ip>:8000/health` from another machine. (d) correct URL in-app (http, laptop-ip, port 8000).
5. **WebSocket fails but HTTP works** → Capacitor `CapacitorHttp` does not handle WS; cleartext must be enabled; captive-portal WiFi blocks LAN WS.
6. **Docker rebuild needs internet** → Dockerfile pre-downloads the embedding model (~90 MB from huggingface.co). Use `docker-compose up` without `--build` offline.
7. **`chromadb.errors.InternalError: Nothing found on disk`** → test-only flake from `SharedSystemClient` cache. Retry the run. Partial mitigation in `backend/app/knowledge_pack/loader.py:close()`. Not a production issue.
8. **Backend logs flooded with `/health`** → frontend + Docker healthcheck both poll. Filter: `docker-compose logs -f app 2>&1 | grep -v "/health"`.
9. **`.env` changes don't take effect** → provider resolution caches; restart the backend.
10. **Windows `__pycache__` staleness** → when behavior doesn't match the code, nuke `backend/app/**/__pycache__`.
11. **Port 8000 zombie after uvicorn crash** → Windows: `taskkill //F //PID <pid>` (double-slash in Git Bash).

---

## 9. Working in This Repo (for Claude Code and collaborators)

- **Edit existing files over creating new ones.** Especially for docs — this repo already has a lot of them.
- **Don't write comments unless WHY is non-obvious.** Identifiers explain WHAT.
- **Don't add error handling for cases that can't happen.** Boundaries only.
- **Run tests before and after refactors.** 581+ tests cover the core paths. `--ignore=tests/test_step_7_live.py` skips the one that needs a live LLM.
- **Measure, don't theorize.** When tuning RAG or prompts, dump the actual prompt and raw LLM output before changing scoring thresholds. Q4 models pattern-copy refusal strings — a "bad answer" may be a retrieval problem, not a generation problem.
- **UI changes need browser verification.** Type-check and tests verify code correctness, not feature correctness. Open `http://localhost:5173` and click through. If you can't, say so — don't claim success.
- **Confirm destructive actions.** Force-push, reset --hard, dropping tables, overwriting dist-apk — ask first.
- **Never skip git hooks (`--no-verify`).** If a hook fails, fix the root cause.

---

## 10. Where to go next

- **Getting started from zero** → README §"For Judges — One-Command Setup" or §2 of this file.
- **Understanding decisions** → `docs/PHILOSOPHY.md` (strategy) and `docs/TECH_FRAMEWORK.md` (full architecture + rationale).
- **Day-to-day dev reference** → `docs/DEVELOPER_NOTES.md`.
- **Something broken** → `docs/TROUBLESHOOTING.md` then §8 of this file.
- **Submitting / shipping** → `docs/SUBMISSION_PLAYBOOK.md`, `docs/SHIP_PUNCH_LIST.md`, `docs/FINAL_SHIP_AUDIT.md`.
