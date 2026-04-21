# Handoff — FieldPack AI final ship phase, Waves B2 + B3

**Date generated:** 2026-04-21
**From:** Claude session working on Wave B1 (ship-critical fixes)
**To:** Next Claude session, to pick up Waves B2 and B3

---

## Your mission

Finish the final ship prep for FieldPack AI (Kaggle Gemma 4 Good Hackathon, deadline **2026-05-18**). Wave B1 is done and committed by the previous session. You own Waves B2 (real E2E QA harness) and B3 (pull-and-run verification + docs).

**Working directory:** `C:/fieldpack-ai` (Windows, bash shell via Git Bash, venv at `venv/Scripts/`)
**Scratch directory:** `C:/fieldpack-test` (fresh clone of master for pull-and-run verification)
**Main reference:** `docs/FINAL_SHIP_AUDIT.md` — the audit that drove all this work. Read it first for context.

---

## What the previous session accomplished (don't redo)

### Wave B1 — shipped and committed
Five ship-critical fixes, one bundled commit. All verified with the full test suite. Changes made:

1. `frontend/vite.config.ts:10,15` — proxy target changed from `http://localhost:8003` → `http://localhost:8000` for both `/api` and `/ws` (native dev path was broken). `demo/record.ts` deliberately left at 8003.
2. `backend/app/main.py:80` — added `"OPTIONS"` to CORS `allow_methods` list.
3. `backend/app/main.py` lifespan — added fail-fast guard: when `DEMO_MODE=true` but `demo/script.json` is missing, logs a WARNING at startup (prevents silent runtime crash).
4. `docker-compose.yml:152-153` — frontend's `depends_on: app` upgraded to `condition: service_healthy` to match the ollama pattern. Prevents nginx from serving while backend is still starting.
5. `backend/app/config.py:14` — default `ollama_model` changed from the dead legacy `"fieldpack-assistant-lite"` → `"gemma4:e2b-it-q4_K_M"` (matches `.env.example` and compose).

### Test flake investigation + fix
During B1 verification, the suite showed **intermittent ChromaDB failures** (1-2 tests failed per run in ~2/5 runs). Unmasked the error: `chromadb.errors.InternalError: Error creating hnsw segment reader: Nothing found on disk`. Root cause: `SharedSystemClient` cached chromadb `System` objects across test-pack loads, holding stale Rust-side file handles after tmp_path cleanup. Fix added to `backend/app/knowledge_pack/loader.py:close()` — calls `SharedSystemClient.clear_system_cache()` on pack unload.

**The fix is partial — flake rate dropped from "always" to "~40% of runs" before the session ended.** Deeper fix attempt planned (option 2 below) may or may not be complete when you receive this — check git log for a second "test flake" commit. If not there, this is still a known issue. See "Known issues" section.

---

## Your actual work — Wave B2

### Goal
Real end-to-end QA harness that drives the live running stack, not mocks. This is the actual user-simulation test gate before shipping.

### Scope
- Create `backend/tests/e2e/__init__.py` (empty)
- Create `backend/tests/e2e/conftest.py`:
  - Fixture `e2e_base_url`: reads env `FIELDPACK_E2E_URL`, defaults to `http://localhost:8000`
  - Fixture `e2e_client`: returns `httpx.AsyncClient(base_url=..., timeout=120.0)` — long timeout for LLM calls
  - Do NOT reuse the project's existing `conftest.py` pack fixtures — E2E hits a real server, no in-process pack needed
- Register a new `e2e` marker in `backend/pyproject.toml` alongside `live` and `integration`
- Create `backend/tests/e2e/test_real_stack.py` with these scenarios (each a separate test, all marked `@pytest.mark.e2e`, all async):

  1. **Golden path:** `POST /chat/` with `{"message": "what variety of cassava is best for Casamance?"}` → assert `status == 200`, `reply` non-empty, `sources` list non-empty, reply length > 100 chars.
  2. **Image upload:** find a test JPEG in `packs/casamance_agriculture/images/` (any file), base64-encode it, POST to `/upload/image/base64` with `{"image_base64": "...", "filename": "test.jpg"}`, capture returned `image_path`. Then POST `/chat/` with `{"message": "what is wrong with my cassava?", "image_path": "<that path>"}` → assert status 200, reply non-empty. (Do not assert specific diagnosis content — LLMs are non-deterministic; just assert shape.)
  3. **Ask-back:** `POST /chat/` with `{"message": "my plant is sick"}` → assert reply contains `?` (agent should ask a clarifying question), and `sources` is empty or reply length < 300 (not a full RAG response).
  4. **No-match refusal:** `POST /chat/` with `{"message": "how do I grow coffee beans?"}` → assert reply does NOT contain fabricated specific varieties/treatments. Accept any response that says "not in pack", "I don't have information", or similar graceful refusal. (Soft assertion: log reply for human review if it looks hallucinated.)

  Skip the offline-network test for now — it's hard to test reliably without `docker network disconnect` and re-running. Document as a manual smoke in `TROUBLESHOOTING.md`.

- Create `scripts/run_e2e.sh`:
  ```bash
  #!/usr/bin/env bash
  set -e
  export FIELDPACK_E2E_URL="${FIELDPACK_E2E_URL:-http://localhost:8000}"
  cd "$(dirname "$0")/../backend"
  PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/e2e/ -m e2e -v
  ```
  `chmod +x scripts/run_e2e.sh` after creation.

### Important constraints
- **Do NOT use `FastAPI TestClient`** — this harness tests the real server over HTTP. Use `httpx.AsyncClient`.
- **Do NOT use `@pytest.mark.live`** — that marker is auto-deselected by `conftest.py:44-52`. Use `@pytest.mark.e2e`. Register the new marker in `pyproject.toml`.
- E2E tests must be opt-in: default `pytest tests/` must NOT run them. The suite currently has 896 tests; after B2 your default suite should still be 896 (plus whatever new tests you add are only picked up by `-m e2e`).
- `@pytest.mark.asyncio` should be set per-test or via `asyncio_mode = "auto"` (already set in `pyproject.toml`). Since the E2E tests are async, decorate the test functions with `async def` and pytest-asyncio's auto mode handles them.

### Docker stack state when you inherit the session
The dev stack is running at time of handoff:
- `fieldpack-app` on `:8000` (healthy)
- `fieldpack-ollama` on `:11434` (healthy, model loaded)
- `fieldpack-frontend` on `:5173` (healthy)

Verify with `docker ps`. If the stack is down, the user will need to `docker-compose up -d` from `C:/fieldpack-ai` — they control docker-compose lifecycle.

### Test-suite canonical command
```bash
cd /c/fieldpack-ai/backend && PYTHONPATH=. /c/fieldpack-ai/venv/Scripts/python.exe -m pytest tests/ --ignore=tests/test_step_7_live.py -q
```
Runs ~60s, should report 896 passed.

### Running the E2E harness
```bash
cd /c/fieldpack-ai/backend && PYTHONPATH=. /c/fieldpack-ai/venv/Scripts/python.exe -m pytest tests/e2e/ -m e2e -v
```
Each scenario takes 10-30s (LLM call). Plan ~2 min total.

### Commit
Bundled commit for Wave B2:
```
feat: Phase B wave 2 — real end-to-end QA harness

- backend/tests/e2e/{__init__,conftest,test_real_stack}.py (4 scenarios)
- backend/pyproject.toml: register e2e marker
- scripts/run_e2e.sh runner
- Tests opt-in via -m e2e; default suite unaffected (still 896 tests)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```
**Do NOT push.** User pushes manually.

---

## Your actual work — Wave B3

### Goal
Prove `git clone && docker-compose up` works end-to-end on a fresh environment. Document everything a judge would need.

### Pre-flight question for the user
**Ask before starting:** "Wave B3 needs to build the full Docker stack in `C:/fieldpack-test` (~20 min first build). Should I tear down the currently-running dev stack first, or run the test clone in parallel on non-default ports 8001/5174/11435?"

Previous session's context suggests parallel (non-default ports) is preferred — but confirm before acting since it's a resource-heavy operation.

### Scope

#### B3-a: compose override in the test clone
Create `C:/fieldpack-test/docker-compose.override.yml` (don't edit the original compose in the test clone):
```yaml
services:
  ollama:
    ports:
      - "11435:11434"
  app:
    ports:
      - "8001:8000"
  frontend:
    ports:
      - "5174:5173"
```

#### B3-b: build and launch
```bash
docker-compose -f C:/fieldpack-test/docker-compose.yml -f C:/fieldpack-test/docker-compose.override.yml -p fieldpack-test up -d --build
```
Run in background. Allow ~20 min for first build. Model pull adds another ~5 min.

Monitor with `docker-compose -p fieldpack-test logs -f app` — watch for `Uvicorn running on`.

#### B3-c: run B2 harness against the fresh stack
```bash
export FIELDPACK_E2E_URL=http://localhost:8001
bash scripts/run_e2e.sh
```
All 4 scenarios must pass.

#### B3-d: manual APK smoke
Install `dist-apk/fieldpack-ai-v1.0.0-debug.apk` on a real Android phone, connect phone to same Wi-Fi as dev laptop, launch app, exercise the golden shot (take a photo of a leaf, ask a question).

**If the user has no phone available at handoff time:** mark as `manual-smoke-deferred` in the commit message and include a brief test plan in `docs/TROUBLESHOOTING.md` for the user to run later.

#### B3-e: consolidate TROUBLESHOOTING.md
Create `docs/TROUBLESHOOTING.md`. Consolidate these existing scattered notes into one document:

- Intel iGPU garbled output → `OLLAMA_NUM_GPU=0` (from `CLAUDE.md`, `docker-compose.yml:42-48`)
- First-query slowness after restart (HNSW warm-up, documented in `FINAL_SHIP_AUDIT.md` P0-3)
- Ollama model tag changes → `curl https://ollama.com/library/gemma4/tags` (from `README.md:171`)
- APK LAN discovery (phone can't reach laptop) → firewall, same Wi-Fi network (from `docs/DEVELOPER_NOTES.md`)
- CapacitorHttp + WebSocket (known incompatibility)
- ChromaDB `Nothing found on disk` during tests → known flake, see "Known issues" below
- Log flood from `/health` polls (audit P1-3) — how to filter

Link from `README.md` under the existing "Common issues" section.

#### B3-f: README reality-check
After pull-and-run succeeds, re-read `README.md` end-to-end and fix any step that doesn't match what you just did. Especially the native-dev alternative and the Docker path.

### Commit
```
docs: Phase B wave 3 — pull-and-run verification + troubleshooting

- C:/fieldpack-test verified: docker-compose up --build (~X min) → E2E 4/4 passed
- docs/TROUBLESHOOTING.md: consolidated common issues from README + DEVELOPER_NOTES + audit
- README.md: updated step-by-step to match verified reality
- APK smoke: [passed on <phone model>] OR [manual-smoke-deferred — user to test]

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```
**Do NOT push.** User pushes manually.

---

## Known issues you may encounter

### ChromaDB test flake (inherited from B1)
Tests occasionally fail with `chromadb.errors.InternalError: Error creating hnsw segment reader: Nothing found on disk`. Failing tests rotate — not a specific test, any test that queries chroma. Current mitigation is `SharedSystemClient.clear_system_cache()` in `KnowledgePack.close()`. Flake rate is ~40% last measured. **If you see this during test runs, it's the known issue — retry the run rather than investigating anew.** If the previous session's second fix attempt committed before handoff, this may already be green — check git log for commits after the first B1 commit.

Do NOT let this delay B2/B3. If the full suite shows 1-2 unrelated ChromaDB failures, retry once; if clean, proceed. Your E2E harness uses the real baked-in pack, not tmp packs, so it's not affected.

### Hook gotchas (learned the hard way)
- `enforce-venv.sh` PreToolUse **BLOCKS** bash commands containing bare tokens `py`, `python`, or `pytest` — even inside quoted strings or grep regex or pipes
  - Use `/c/fieldpack-ai/venv/Scripts/python.exe -m pytest` for all test runs (the full path bypasses the check)
  - Use Grep tool for searches (not bash `grep`)
  - Commit messages: don't write `pytest` — say "test suite" or "pytest marker" or describe it differently
- MSYS path mangling: `docker exec` with `/app/...` gets rewritten to `C:/Program Files/Git/app/...`. Workaround: wrap in `sh -c 'command'` or use `//app/...`

### Uncommitted runtime churn
`packs/casamance_agriculture/chroma_db/*.bin` and `chroma.sqlite3` mutate on every backend load/query — this is ChromaDB's normal HNSW warm-up behavior. **EXCLUDE these from any commit.** Use `git add` with specific file paths, never `git add -A` or `git add .`.

### Forbidden file
Do NOT edit `backend/app/agents/nodes/route.py` — owned by another session.

---

## User preferences (durable, apply to all your replies)

- Terse replies. No trailing summaries. No emojis.
- Bundled commits per wave, NOT per-file.
- User does NOT push commits; you commit on explicit instruction but never push.
- Parallelize tool calls within a wave where possible.
- Explanations should be at junior-developer level — user is a hackathon competitor, full-stack engineer, but wants collaborative/educational tone.
- When you hit a non-obvious decision, ask the user before proceeding rather than choosing silently.

---

## Environment sanity check (run first thing)

```bash
cd /c/fieldpack-ai && git status
cd /c/fieldpack-ai && git log --oneline -5
docker ps --format "table {{.Names}}\t{{.Status}}"
ls /c/fieldpack-test/
```

Expected:
- `git status` shows only `packs/casamance_agriculture/chroma_db/*` dirty (and possibly `docs/FINAL_SHIP_AUDIT.md` and this handoff file)
- Recent commits include the Wave B1 commit(s)
- Docker stack healthy on 8000/11434/5173
- `C:/fieldpack-test/` is a fresh clone of master

If anything is off, ask the user before doing anything destructive.

---

## Useful references in the repo

- `docs/FINAL_SHIP_AUDIT.md` — the audit that motivated all these waves. Read it.
- `CLAUDE.md` — short project overview
- `docs/PHILOSOPHY.md`, `docs/TECH_FRAMEWORK.md`, `docs/DEVELOPER_NOTES.md` — architecture
- `backend/tests/conftest.py` — existing test infrastructure, shows marker conventions
- `backend/app/routers/chat.py`, `upload.py` — endpoint contracts for the E2E harness
- `frontend/capacitor.config.ts`, `frontend/android/app/src/main/AndroidManifest.xml` — APK config

Good luck. Ship it clean.
