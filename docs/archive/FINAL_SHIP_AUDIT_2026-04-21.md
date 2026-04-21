# FINAL SHIP AUDIT

**Date:** 2026-04-21
**Head commit:** 2080b7d (Wave 3 ship punch list)
**Deadline:** 2026-05-18 (Kaggle Gemma 4 Good Hackathon)
**Scope:** everything required for a clean `git clone && docker-compose up` to work end-to-end, including the APK thin-client loop.

This audit was produced without modifying any code. Findings are ranked P0 (ships broken), P1 (painful but recoverable), P2 (polish). Every finding below has a concrete reproduction path and a proposed fix. Execution happens in waves after the user approves this plan.

---

## Method

1. Read the Docker stack: `Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `frontend/nginx.conf`, `.dockerignore`.
2. Read the backend config surface: `backend/app/config.py`, `backend/.env.example`, `backend/app/main.py`, router entry points.
3. Read the APK connection contract: `frontend/src/lib/config.ts`, `frontend/src/hooks/useServerConnection.ts`, `frontend/capacitor.config.ts`, `frontend/android/app/src/main/AndroidManifest.xml`, `frontend/vite.config.ts`.
4. Probed the live containers (stack was already up from prior session) — `/health`, `/packs/`, nginx proxy path.
5. Fresh-cloned master to `C:/fieldpack-test/` and validated the compose file parses.

Not done yet (deferred to execution phase): cold `docker-compose build`, APK install on a real phone, full user-simulation harness run.

---

## P0 — Ships broken

### P0-1. `vite.config.ts` proxies to port **8003**, backend runs on **8000**

**Where:** `frontend/vite.config.ts:10,15`
```ts
'/api':  { target: 'http://localhost:8003' ... }
'/ws':   { target: 'ws://localhost:8003'   ... }
```

**Impact:** The "Alternative: native install" path in `README.md:189` starts uvicorn on `:8000`, then `npm run dev` proxies `/api` and `/ws` to `:8003`. The dev-mode frontend cannot reach the backend. Anyone following the native-install flow hits a hard dead-end.

**Docker path is unaffected** — nginx proxies `/api` → `app:8000` — so judges running `docker-compose up` never see this. But the README explicitly offers the native path to "contributors or judges who prefer a local Python/Node setup" (line 175).

**Fix:** change both `8003` → `8000` in `vite.config.ts`. One commit, one file.

**Caveat:** `demo/record.ts` also references `8003` — that's the demo-recording harness the user runs to generate demo video assets. Likely intentional (different port to avoid collision). Verify before changing.

---

### P0-2. Image-path validation rejects files served by `/upload/files/{filename}`

**Where:** `backend/app/routers/chat.py:53-73` (`_validate_image_path`)

**Flow:** APK sends a photo via `POST /upload/image/base64` → `upload.py:90` saves to `uploads_path` and returns a **resolved, absolute, posix-normalised** path string: `/app/uploads/<uuid>.jpeg`. APK stores that string and passes it back as `image_path` in subsequent chat messages.

**Problem (partial):** `_validate_image_path` accepts paths under `uploads_path` OR `packs_path`, good. But the comparison uses `uploads_root_str = ... + "/"`. The returned path already starts with `/app/uploads/<uuid>` → prefix match succeeds. This particular case appears to work.

**Possible problem (needs live test):** what about path stability across requests? `uploads_path` is a `@property` that calls `.mkdir(parents=True, exist_ok=True)` on every access (`config.py:75-78`). On Windows dev it normalises to a different case than what upload returns. Needs a real upload→chat round trip to confirm.

**Fix:** add an integration test that exercises the upload → image_path → chat cycle against a live backend. Part of the E2E QA harness (Phase B4).

---

### P0-3. Pack mutation is baked into the image, not volumed

**Where:** `Dockerfile:41` (`COPY ... packs/ /app/packs/`), `docker-compose.yml` has no `packs:` volume mount.

**Impact:** ChromaDB mutates `/app/packs/casamance_agriculture/chroma_db/*.sqlite3` on every container start (HNSW index warm-up, confirmed by the user's perpetual git diff of those files). Because packs are in the image layer and not a volume, those mutations are lost on `docker-compose down && docker-compose up` (container is recreated → fresh layer). First query after restart pays the warm-up cost again.

Worse: on `docker-compose down -v`, the uploads volume is destroyed but the pack is fine (baked in). On a fresh `docker-compose up --build`, everything works. This is **actually a feature** — the image is self-contained and deterministic — but the warm-up cost hits every restart.

**Fix:** no code change. Document in README troubleshooting: "first chat after restart can take 20-30 seconds while ChromaDB warms HNSW indices." P2 really, but the user's perpetually-dirty git tree is a symptom worth noting — the fact that the running **dev backend** (not the container) mutates `packs/casamance_agriculture/chroma_db/*` in the working tree means a native-path contributor ends up with unstageable churn. Add these paths to `.gitignore` or the `info/exclude`.

---

### P0-4. README "Alternative: native install" Ollama pull command is wrong

**Where:** `README.md:180-181`
```bash
ollama pull gemma4:e2b-it-q4_K_M
```

**Status:** actually correct **right now** — this matches `ollama-init` in compose and `backend/.env.example:16`. No bug.

**But:** the README troubleshooting at line 171 already warns "If the Gemma 4 E2B tag in the public Ollama registry has changed, run `curl https://ollama.com/library/gemma4/tags`". That's the right hedge. No action.

Promoting this from "potential P0" to "resolved, don't touch."

---

## P1 — Painful but recoverable

### P1-1. CORS `allow_methods` is missing `OPTIONS`

**Where:** `backend/app/main.py:80`
```python
allow_methods=["GET", "POST", "PUT", "DELETE"],
```

**Impact:** Browsers send an `OPTIONS` preflight for cross-origin JSON requests (e.g., `POST /chat/` with `Content-Type: application/json`). Starlette's `CORSMiddleware` handles preflight internally regardless of `allow_methods` (it short-circuits `OPTIONS` before hitting the user handler list), but linters and strict clients may complain. Low risk.

**Fix:** add `"OPTIONS"` to the list for clarity. One-line change.

---

### P1-2. CORS `allow_origin_regex` escapes `.` as `\.` but the values in the string use `\d` (works) — **verify no surrogate regex issues**

**Where:** `backend/app/main.py:72-78`

The regex looks correct; `192\.168\.` has `\.` — wait, no it doesn't, it has `192\.168\.` in the source with `\.`. Let me re-read:

```python
r"^https?://"
r"(192\.168\.\d{1,3}\.\d{1,3}"
```

Actually in the source the dots are NOT escaped (`192\.168` is present but `\.\d` is escaped dots separating octets — double-check rendered regex). Unescaped `.` would match any character. Fine at worst, over-permissive at worst.

**Status:** confirmed in the re-read: the regex has the proper `\.` escapes between each octet group. No bug. Removing from P1.

---

### P1-3. Health-check access logs flood the uvicorn log output

**Where:** observed in `docker logs fieldpack-app` — last 60 lines are 100% `GET /health 200 OK`. Healthcheck fires every 30s (Dockerfile:64) plus frontend polls every 10s (`useServerConnection.ts:37`) plus `useBackendReachable` polls on a backoff.

**Impact:** real errors and pipeline logs get buried. During the demo, a judge who runs `docker logs fieldpack-app` to troubleshoot sees only noise.

**Fix:** add a uvicorn access-log filter to drop `/health` 200s, or switch to `--access-log false` and let the custom `pipeline_logger` carry the signal. Config change, no new code path.

---

### P1-4. APK image size: backend image is 9.17 GB

**Where:** `docker images fieldpack-ai-app` → 9.17 GB.

**Composition:** Python 3.11-slim base (~150 MB) + `pip install -r backend/requirements.txt` (torch, sentence-transformers, chromadb, langchain — ~6 GB) + the MiniLM model (~90 MB) + packs (~100 MB) + FastAPI stack.

**Impact:** judges on slow networks pulling the image directly from a registry would suffer. But this repo is source-only; the build happens on the judge's machine, so the 9 GB is CPU + dependency install time (~15 min first run), not bandwidth. Acceptable for a hackathon entry. Flagging for awareness.

**Optional fix:** multi-stage build with a `builder` stage that installs deps to a wheel cache, runtime stage that only copies the installed site-packages. Realistic saving: 1-2 GB (torch dominates). Not worth the risk of breaking a working build 4 weeks from deadline.

---

### P1-5. No `depends_on: condition: service_healthy` from `frontend` to `app`

**Where:** `docker-compose.yml:152-153`
```yaml
frontend:
  depends_on:
    - app
```

**Impact:** nginx starts before the backend is healthy. First user to load `http://localhost:5173/` while the backend is still starting gets a 502 from nginx (or a hang on `/api/health`). `app` has `depends_on: ollama: condition: service_healthy` — the frontend should match that pattern against `app`.

**Fix:** add `condition: service_healthy` to the frontend's `depends_on: app`. One-line change.

---

### P1-6. APK distribution relies on a Google Drive link

**Where:** `README.md:75`
> **APK download:** [fieldpack-ai-v1.0.0-debug.apk](https://drive.google.com/file/d/1fDdvSxdMTf0a_rqwmO2idPo_R_9eCQLu/view?usp=sharing)

**Impact:** Drive links expire, change permissions, or get flagged. Judges clicking through can get "access denied" — no fallback. Also the SHA256 hard-coded in the README (line 79) breaks silently if the Drive file is rebuilt without updating the README.

**Fix:** once the repo is public, migrate APK to GitHub Releases (`/releases/latest`). The `docs/DEVELOPER_NOTES.md:76` already notes this plan. Move it from "planned" to "done before submission."

---

### P1-7. `.dockerignore` excludes `demo/` — `demo_replay.py` imports survive, but `demo/script.json` is stripped

**Where:** `.dockerignore:69`, `backend/app/demo_replay.py:27`

**Impact:** in `DEMO_MODE=false` (the compose default), `_load_script()` is never called (all demo code paths are gated behind `if settings.demo_mode:`). Safe. But if a user ever runs the Docker image with `-e DEMO_MODE=true`, it crashes at first demo endpoint with `FileNotFoundError: /app/demo/script.json`. The README actively warns against copying `.env.example` (line 165), which would flip this.

**Fix:** fail-fast guard in `config.py`: if `demo_mode=True` and `demo_script_path` doesn't resolve, log a loud warning at startup. Or just bake `demo/script.json` into the image anyway (~50 KB). Either is fine.

---

## P2 — Polish

### P2-1. `config.py:14` default `ollama_model = "fieldpack-assistant-lite"` is a dead legacy value

Docker, `.env.example`, and README all use `gemma4:e2b-it-q4_K_M`. A fresh native-install user who skips the `.env` ends up with a default model name that doesn't exist in the Ollama registry. Fix: change the default in `config.py` to `gemma4:e2b-it-q4_K_M`.

### P2-2. `backend/app/routers/health.py` `/api/version` timing-out silently yields `ollama_version: null`

Minor UX issue. The frontend displays "ollama: unknown" when the server response is slow. Increase the per-call timeout from 5s to 10s, or surface the degraded state more clearly.

### P2-3. APK auto-scan worst case is 18 s

`config.ts:199` scans 254 /24 candidates in batches of 30 at 2s timeout. This is fine, but the user message "Scanning local network — batch X of Y" is only in `console.log`, not visible to the user. The app sits on a spinner for up to 18 seconds. Surface batch progress in the UI.

### P2-4. No end-to-end golden-path smoke test runs in CI

There is no CI. All 896 tests pass locally. For a hackathon that is fine. For shipping, add a GitHub Actions workflow: install, boot stack, hit `/health`, hit `/chat` with a known question, verify non-empty grounded answer. Post-submission polish.

### P2-5. README has no "What can go wrong and how to tell" cheat sheet

Common failure modes: garbled output (Intel iGPU), WebSocket drop (CapacitorHttp enabled), phone can't reach laptop (firewall). README addresses each but scattered. Consolidate to a single troubleshooting block.

---

## Execution plan — Phase B (waves)

After this audit is approved, execute in three waves. Each wave = bundled commit, full test run at the end, no push until the user says so.

### Wave B1 — ship-critical fixes
- P0-1: fix Vite proxy port 8003 → 8000
- P1-1: add OPTIONS to CORS allow_methods
- P1-5: frontend depends_on app with service_healthy
- P1-7: fail-fast guard for missing demo script when DEMO_MODE=true
- P2-1: fix dead default `ollama_model` in config.py

**Commit:** `fix: Phase B wave 1 — native dev proxy, CORS, startup ordering`

### Wave B2 — real end-to-end QA harness
Write `backend/tests/e2e/test_real_stack.py` (no `live` marker — this runs on demand, not in the default suite). Uses `httpx.AsyncClient` + `websockets` library to drive a real backend. Scenarios:
1. **Golden path:** `POST /chat/` with "what variety of cassava is best for Casamance?" — assert `status_code == 200`, `reply` is non-empty, `sources` list is non-empty, no hallucination markers.
2. **Image upload path:** POST a test image (check `packs/casamance_agriculture/images/` for a valid test asset), pass returned `image_path` to `/chat/`, assert diagnosis-shaped reply.
3. **Ask-back path:** `POST /chat/` with "my plant is sick" — assert reply contains a clarifying question, does NOT invoke full RAG retrieval.
4. **No-match path:** `POST /chat/` asking about a crop NOT in the pack (e.g., "how do I grow coffee?") — assert graceful refusal, not hallucinated answer.
5. **Offline test:** Drop the container's network access to the internet (host firewall rule or `docker network disconnect`), run scenarios 1-4, assert all still work.

Runner script: `scripts/run_e2e.sh` boots the Docker stack (or uses the already-running one), runs the e2e pytest, tears down.

**Commit:** `feat: Phase B wave 2 — real end-to-end QA harness`

### Wave B3 — pull-and-run verification + docs
- Fresh clone in `C:/fieldpack-test/` is already done. Do a full `docker-compose -p fieldpack-test build && up` (allow ~20 min for first build), run Wave B2 scenarios against it on a non-default port (override `8000 → 8001`, `5173 → 5174`, `11434 → 11435`).
- Install the shipped APK on a real Android phone, connect to the Docker stack, exercise the image-upload path.
- Consolidate all findings into a `docs/TROUBLESHOOTING.md` block; link from README.
- Update README if any step differs from reality.

**Commit:** `docs: Phase B wave 3 — pull-and-run verification + troubleshooting`

### Deferred (post-deadline)
- P1-4: image-size optimisation (multi-stage build)
- P2-4: CI workflow
- P1-6: GitHub Releases APK distribution — do this *at* submission time, not before

---

## Confirm before execution

Decisions I want validated:
1. Wave ordering: B1 (fixes) → B2 (E2E harness) → B3 (pull-and-run + docs). Reasonable?
2. Wave B2 harness: HTTP+WebSocket from a Python script. APK smoke is manual in B3. OK?
3. B3 runs compose with `-p fieldpack-test` on **non-default ports** so the existing dev stack keeps running in parallel. OK, or tear down the dev stack first?
4. Any finding you want demoted/promoted? Anything to skip?
