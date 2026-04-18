# FieldPack AI

Hackathon entry for **Kaggle Gemma 4 Good Hackathon** (deadline May 18 2026). Offline AI for humanitarian field workers — Gemma 4 E2B on Ollama serves curated Knowledge Packs via agentic RAG on a laptop, with a phone thin-client APK for camera + UI.

See `docs/PHILOSOPHY.md` for strategy, `docs/TECH_FRAMEWORK.md` for architecture.

## Commands

```bash
source venv/Scripts/activate  # venv is at repo root

# Backend
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev   # localhost:5173, Vite proxy -> :8000

# Tests
cd backend && PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/ -v --ignore=tests/test_step_7_live.py

# Ollama
ollama serve

# APK (only for frontend/Capacitor/Android changes)
cd frontend && npm run build && npx cap sync android
JAVA_HOME="/c/fieldpack-ai/jdk-21.0.10+7" ANDROID_SDK_ROOT="/c/fieldpack-ai/.android-sdk" \
  PATH="$JAVA_HOME/bin:$PATH" ./android/gradlew -p android assembleDebug
# Output: frontend/android/app/build/outputs/apk/debug/app-debug.apk
# Ship location: dist-apk/fieldpack-ai-v1.0.0-debug.apk (gitignored — copy manually after build)
# SHA256 of current release: record in README after each rebuild
```

## Pipeline

```
classify → route → needs_search
  → [no search] → generate_answer → END
  → [search]    → craft_query → execute_search → rerank
      → [sufficient OR max 3 attempts] → generate_answer → END
      → [retry] → expand_route → craft_query (loop)
```

- Conversational messages ("hi", follow-ups) skip RAG via regex gate in `needs_search.py`
- `generate_answer` is async — streams tokens via `llm.astream()` for word-by-word frontend UX
- `reasoning=False` globally on all Ollama calls (`offline_llm.py`) — E2B thinking wastes tokens and produces empty content (see `docs/TROUBLESHOOTING_LLM.md`)
- `OLLAMA_NUM_GPU=0` for local (Intel iGPU) — partial GPU offload (75%CPU/25%GPU) produces garbage; full CPU is coherent. Tunnel (Colab T4) auto-detects and uses full GPU. Only applied to local, not tunnel (see `offline_llm.py`)
- Streaming tokens normalized via `extract_text()` in `field_assistant.py` — handles both string (Ollama) and list-of-dicts (Google) content formats
- LLM provider set via `FIELD_LLM_PROVIDER` env: `ollama-local`, `ollama` (tunnel+local fallback), or `google`

## Stack

- **Backend**: FastAPI, LangGraph, ChromaDB, sentence-transformers (MiniLM-L6-v2), pydantic-settings
- **Frontend**: React 19, Vite 8, Tailwind v4, Capacitor 8, TypeScript, Lucide icons
- **LLM**: Gemma 4 E2B Q4_K_M via Ollama (5.1B params, ~8 GB RAM)

## Architecture

- **Thin-client APK**: phone = camera + UI, laptop = all AI over WiFi hotspot. `config.ts:isNative()` switches URL resolution
- **Two-tier rerank**: fast heuristic first, LLM rerank only on retry
- **Parent/child chunking**: search matches child chunks, context uses parent chunks for detail
- **WebSocket streaming**: `field_assistant.py` emits status/token/sources/done events, frontend renders progressively

## Style

- Python 3.10+, type hints on public functions, async where possible
- `.env` + `pydantic-settings` for config, never hardcoded keys
- ChromaDB: always `PersistentClient(path=...)`, never in-memory for pack data
- Error handling at boundaries only (API calls, file I/O, Ollama), not internal logic

## Gotchas

- **Rebuild APK when frontend/backend contract changes.** The shipped APK bakes in the frontend bundle — backend API changes that alter request/response shape, WebSocket event names, or URL paths require a rebuild. Current release: `dist-apk/fieldpack-ai-v1.0.0-debug.apk`, SHA256 `831984eb9fa29bd585ddef60c409e87bdce01e4a24d038f26f68932ec6f525df` (2026-04-18)
- **APK distribution:** while repo is private, upload to Drive + VirusTotal (links go in README's "Run on Your Phone" section). When repo flips public, replace with GitHub Release (`/releases/latest`) — cleaner URL, no Drive permission glitches, zero git bloat
- **LAN discovery:** app auto-scans on launch via `config.ts:autoScanForServer()` — probes saved URL → hotspot IPs (Windows `192.168.137.1`, Android `192.168.43.1`) → /24 subnet scan via WebRTC-detected local IP. Hardcoded list in `priorityIps` — add new hotspot patterns there
- **Firewall:** Windows Defender prompts on first `docker-compose up` that serves on `:8000` — judges must "Allow access" or phone can't reach laptop. Document this in setup instructions
- `CapacitorHttp: { enabled: false }` — NEVER enable, silently breaks WebSocket
- `cleartext: true` in Capacitor config — required for HTTP over LAN (Android 9+)
- Tailwind v4 `oklch()` — demo device must be Android 12+ (Chrome 111+ WebView)
- JDK 21 required for APK builds. Local JDK at `jdk-21.0.10+7/`
- Vite proxy rewrites `/api` → strips prefix → port 8000. Native mode bypasses entirely
- Backend must bind `0.0.0.0` for LAN access (set in `config.py`)
- `ollama_num_ctx: 4096` must match Modelfile — oversized KV cache degrades attention on small models
- `_resolve_provider` in `offline_llm.py` has a TTL cache — `.env` changes require server restart
- **E2B + Intel iGPU = garbage output**: Ollama auto-offloads ~25% to iGPU, splits layers across precision boundaries, model produces incoherent text. Fix: `OLLAMA_NUM_GPU=0` forces CPU-only. This is the #1 recurring bug — if the model suddenly returns empty/nonsense, check `ollama ps` for the CPU/GPU split. See `docs/TROUBLESHOOTING_LLM.md`
- `FIELD_LLM_PROVIDER=ollama` must match a handled case in `get_field_llm()` — values `google`, `ollama-local`, `ollama` are explicit; anything else falls to auto-resolve which may silently switch providers
- **Empty `final_answer` = frontend shows fallback**: `generate_answer` guards against empty LLM output, but if it still happens, the `done` event carries `final_answer: ""` and the frontend shows "I processed your request but could not generate a response"

## Non-Negotiable

1. **Hero shot must work**: plant photo → diagnosis → treatment plan, every time
2. **Offline is the point**: internet features belong in Phase 1 only
3. **One pack**: Casamance agriculture. Platform concept in writeup/video only
4. **Google ecosystem**: AI Studio + Stitch + Gemma + Kaggle = all Google. Intentional
