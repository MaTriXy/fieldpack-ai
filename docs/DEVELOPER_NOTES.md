# Developer Notes

Full reference for development, testing, and environment setup.

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
- `OLLAMA_NUM_GPU=0` for local (Intel iGPU) — partial GPU offload (75%CPU/25%GPU) produces less coherent output; full CPU mode is preferred. Tunnel (Colab T4) auto-detects and uses full GPU. Only applied to local, not tunnel (see `offline_llm.py`)
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

## Code Style

- Python 3.10+, type hints on public functions, async where possible
- `.env` + `pydantic-settings` for config, never hardcoded keys
- ChromaDB: always `PersistentClient(path=...)`, never in-memory for pack data
- Error handling at boundaries only (API calls, file I/O, Ollama), not internal logic

## Environment-Specific Tips

### APK and Frontend/Backend Contract
Rebuild the APK when frontend/backend contract changes. The shipped APK bakes in the frontend bundle — API changes that alter request/response shape, WebSocket event names, or URL paths require a rebuild.

Current release: `dist-apk/fieldpack-ai-v1.0.0-debug.apk`, SHA256 `831984eb9fa29bd585ddef60c409e87bdce01e4a24d038f26f68932ec6f525df` (2026-04-18)

### Distribution
While repo is private, APK is uploaded to Drive + VirusTotal. When repo flips public, use GitHub Release (`/releases/latest`) for cleaner URLs and reduced friction.

### LAN Discovery
App auto-scans on launch via `config.ts:autoScanForServer()` — probes saved URL → hotspot IPs (Windows `192.168.137.1`, Android `192.168.43.1`) → /24 subnet scan via WebRTC-detected local IP. Hardcoded priority list in `priorityIps` — add new hotspot patterns there when testing on different networks.

### Network and Configuration
- **Firewall**: Windows Defender may prompt on first `docker-compose up` that serves on `:8000` — grant network access or the phone can't reach the laptop
- `CapacitorHttp: { enabled: false }` — do not enable; it silently breaks WebSocket
- `cleartext: true` in Capacitor config — required for HTTP over LAN (Android 9+)
- Backend must bind `0.0.0.0` for LAN access (set in `config.py`)

### GPU and Model Configuration
- **Intel iGPU with Ollama**: If output becomes incoherent, set `OLLAMA_NUM_GPU=0` to force CPU-only mode. Partial offloads across precision boundaries can degrade quality; full CPU is stable. Check `ollama ps` to verify GPU split
- **Context size**: `ollama_num_ctx: 4096` must match the Modelfile — oversized KV cache degrades attention on small models
- **Provider resolution**: `_resolve_provider` in `offline_llm.py` has a TTL cache — `.env` changes require server restart

### Android and Tailwind
- Tailwind v4 uses `oklch()` colors — target device must be Android 12+ (Chrome 111+ WebView)
- JDK 21 required for APK builds. Local JDK at `jdk-21.0.10+7/`

### Vite and Proxy
Vite proxy rewrites `/api` → strips prefix → port 8000. Native mode bypasses proxy entirely.

### LLM Response Handling
- `FIELD_LLM_PROVIDER=ollama` must match a handled case in `get_field_llm()` — values `google`, `ollama-local`, `ollama` are explicit; anything else falls to auto-resolve which may silently switch providers
- Empty `final_answer`: if `generate_answer` somehow emits empty output despite guards, the `done` event carries `final_answer: ""` and the frontend shows "I processed your request but could not generate a response"
