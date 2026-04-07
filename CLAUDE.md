# FieldPack AI

Hackathon entry for **Kaggle Gemma 4 Good Hackathon** ($200K prize, deadline May 18 2026). Two-phase offline AI for humanitarian field workers. Phase 1 (online): LangGraph agents curate knowledge into portable Knowledge Packs. Phase 2 (offline): Gemma 4 E2B on Ollama serves that knowledge via agentic RAG on a laptop, with a phone thin-client APK for camera + UI.

See `PHILOSOPHY.md` for strategy, `TECH_FRAMEWORK.md` for full architecture.

## Commands

```bash
# Venv (at repo root, not backend/)
source venv/Scripts/activate

# Backend
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend dev
cd frontend && npm run dev   # localhost:5173, Vite proxy -> :8000

# Tests
cd backend && PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/ -v --ignore=tests/test_step_7_live.py

# Ollama
ollama serve
ollama create fieldpack-assistant -f backend/modelfiles/fieldpack-assistant.Modelfile

# APK rebuild (only needed for frontend/Capacitor/Android changes, NOT backend)
cd frontend && npm run build && npx cap sync android
JAVA_HOME="/c/fieldpack-ai/jdk-21.0.10+7" ANDROID_SDK_ROOT="/c/fieldpack-ai/.android-sdk" \
  PATH="$JAVA_HOME/bin:$PATH" ./android/gradlew -p android assembleDebug
# Output: frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

## Architecture Decisions

- **Thin-client APK**: phone is camera + UI only, laptop runs all AI over WiFi hotspot. Same React code serves browser and APK — `config.ts:isNative()` switches URL resolution.
- **LLM fallback chain**: tunnel Ollama -> local Ollama -> Google AI Studio. Set via `FIELD_LLM_PROVIDER` env var.
- **Two-tier rerank**: fast heuristic first, LLM rerank only on retry when heuristic marks insufficient.
- **Agentic RAG is non-deterministic**: the LLM decides retrieval strategy each turn. Not a fixed pipeline.

## Style

- Python 3.10+, type hints on public functions, async where possible
- `.env` + `pydantic-settings` for config, never hardcoded keys
- ChromaDB: always `PersistentClient(path=...)`, never in-memory for pack data
- Error handling at boundaries only (API calls, file I/O, Ollama), not internal logic
- No comments on obvious code

## Gotchas

- `CapacitorHttp: { enabled: false }` in `capacitor.config.ts` — NEVER enable, silently breaks WebSocket
- `cleartext: true` in Capacitor config — required for HTTP over LAN (Android 9+ blocks by default)
- Tailwind v4 uses `oklch()` — demo device must be Android 12+ (Chrome 111+ WebView)
- JDK 21 required for APK builds (Capacitor 8 / SDK 36). Local JDK at `jdk-21.0.10+7/`
- Vite proxy (`vite.config.ts`) rewrites `/api` -> strips prefix -> port 8000. Native mode bypasses this entirely.
- Backend must bind `0.0.0.0` for LAN access (set in config.py)

## Non-Negotiable Rules

1. **Hero shot must work every time**: plant photo -> diagnosis -> local treatment plan
2. **Offline is the point**: internet-requiring features belong in Phase 1 only
3. **Narrow execution**: ONE Knowledge Pack (Casamance agriculture). Platform concept in writeup/video only.
4. **Google ecosystem optics**: AI Studio + Stitch + Gemma + Kaggle = all Google. Intentional.
