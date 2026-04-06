# Phase 2 Bug Audit — Handoff for Fixes

> Generated 2026-04-06. 8 agents audited the entire Phase 2 codebase.
> 6 fixes already applied (marked FIXED). Remaining fixes need implementation.

## Status: 601/601 tests passing after initial fixes

---

## ALREADY FIXED (in current working tree, uncommitted)

| # | Fix | File | What was done |
|---|-----|------|---------------|
| F1 | Google provider now passes `max_output_tokens` | `backend/app/models/offline_llm.py` | `_make_google()` accepts and forwards `num_predict` as `max_output_tokens` to `ChatGoogleGenerativeAI` |
| F2 | Provider cache TTL (5-min re-probe) | `backend/app/models/offline_llm.py` | Added `_resolved_at` + `_RESOLVE_TTL=300`. `_resolve_provider()` re-probes when TTL expires instead of caching forever |
| F3 | Context window bumped 4096 → 8192 | `backend/app/config.py` | `ollama_num_ctx: int = 8192` |
| F4 | `log_observation_node` gets proper LLM params | `backend/app/agents/nodes/log_observation.py` | Changed `get_field_llm(temperature=0.2)` → `get_field_llm(temperature=0.2, num_predict=256, format="json")` |
| F5 | Image analysis enforces 20MB file size limit | `backend/app/tools/image_analysis.py` | Added `_MAX_FILE_SIZE` check before processing |
| F6 | Flaky ChromaDB test fixed | `backend/tests/test_step_3_3_builder.py` | Removed shared `chroma_client` class fixture; each test creates its own `PersistentClient` to avoid HNSW segment conflicts |

---

## REMAINING BUGS TO FIX (prioritized)

### CRITICAL — Will break the hero shot or cause crashes

**C1: `image_analysis.py` vision routing ignores auto-resolved provider**
- File: `backend/app/tools/image_analysis.py` lines 237-240
- Bug: `if settings.field_llm_provider == "google"` hardcodes the check. Default is `"ollama"`. When auto-resolve picks Google (tunnel down), vision STILL routes to Ollama → dead endpoint → hero shot fails silently.
- Fix: Import `_resolved_provider` from `offline_llm.py` (or add a `get_resolved_provider()` function). Check both `settings.field_llm_provider == "google"` AND `_resolved_provider == "google"`. Same fix needed for `_call_ollama_vision` which hardcodes `settings.ollama_base_url` — should use local URL when `_resolved_provider == "local"`.
- Also: `_call_ollama_vision` lines 139-161 always uses `settings.ollama_base_url` (tunnel URL) even when auto-resolve picked local Ollama.

**C2: No timeout on `ChatOllama` — hung Ollama hangs the process forever**
- File: `backend/app/models/offline_llm.py` → `_make_ollama()` lines 24-46
- Bug: `ChatOllama` is constructed with no `timeout`. `langchain-ollama` uses `httpx` with default `None` timeout. If Ollama becomes unresponsive (OOM, GPU pre-emption), `llm.invoke()` blocks forever.
- Fix: Add `ollama_timeout: int = 120` to `Settings` in `config.py`. Pass `client_kwargs={"timeout": settings.ollama_timeout}` in `_make_ollama()`. Merge with existing `client_kwargs` when tunnel token is also set.

**C3: Raw exception messages leaked to WebSocket clients**
- File: `backend/app/agents/field_assistant.py` line 392
- Bug: `yield {"type": "error", "message": str(e)}` — exposes internal paths, Ollama URLs, ChromaDB errors, stack traces to frontend. HTTP endpoint at `chat.py:82` correctly sanitizes but streaming does not.
- Fix: Change to `yield {"type": "error", "message": "Pipeline error. Please try again."}` and log the real error with `log.log_step(...)`.

### HIGH — Will cause incorrect results in common scenarios

**H1: `num_predict=128` too small for classify JSON (9 fields)**
- File: `backend/app/agents/nodes/classify_extract.py` line 207
- Bug: The `ClassifyExtractOutput` JSON with all 9 fields is ~160-170 tokens. `num_predict=128` causes Ollama to hard-stop mid-JSON → falls to parse fallback → returns `GENERAL_QUESTION` with confidence 0.2 → suboptimal routing.
- Fix: Change `num_predict=128` to `num_predict=256` at line 207.

**H2: `generate_answer` `num_predict=1024` is massive overkill — dominates latency**
- File: `backend/app/agents/nodes/generate_answer.py` line 138
- Bug: The system prompt says "3-8 sentences" which is ~120-250 tokens. 1024 tokens = 85-128s on CPU. Most of that time generates past the useful answer.
- Fix: Change `num_predict=1024` to `num_predict=512` at line 138. Still generous for treatment plans, saves ~40-50% latency on the biggest node.

**H3: `data_path` resolves one directory above the repo root**
- File: `backend/app/config.py` lines 64-68
- Bug: `Path(__file__).resolve().parent.parent / Path("../data")` = `backend/` + `../data` = goes ABOVE repo root. `conversations.db` gets created in the wrong location.
- Fix: Change `Path("../data")` to `Path("data")` so it resolves to `backend/data/` (consistent with how `packs_path` and `logs_path` work). Or use `Path("../data")` without the double parent — just `Path(__file__).resolve().parent.parent / "data"`.

**H4: `except (json.JSONDecodeError, Exception)` makes JSONDecodeError clause dead code**
- Files: `backend/app/agents/nodes/classify_extract.py` line 138, `craft_query.py` line 94, `rerank.py` line 157
- Bug: `except Exception` catches everything including `json.JSONDecodeError`, making the explicit catch dead code. More importantly, Pydantic `ValidationError` is silently swallowed across all 3 tiers.
- Fix: In all three files, change to `except (json.JSONDecodeError, ValidationError)` and add `from pydantic import ValidationError` import.

**H5: Health endpoint doesn't report pack status**
- File: `backend/app/routers/health.py`
- Bug: Frontend polling `/health` can't determine if the system is ready (pack loaded + Ollama up). `KnowledgePack.health_check()` exists but is never called from the health endpoint.
- Fix: In the health endpoint, call `get_active_pack()` and if not None, include `pack.health_check()` in the response. If None, include `"pack_loaded": false`.

### MEDIUM — Edge cases, performance

**M1: `_resolve_parent` N+1 pattern — 20 serial ChromaDB calls on broad queries**
- File: `backend/app/tools/chroma_search.py` lines 123-145
- Bug: For each child hit, `_resolve_parent` issues a separate `.get(where=...)` call. GENERAL_QUESTION route = 4 collections × 5 hits = 20 serial calls.
- Fix: After the `.query()` call, collect all `topic_id` values, batch-fetch parents with a single `collection.get(where={"$and": [{"topic_id": {"$in": topic_ids}}, {"chunk_type": "parent"}]})`, then map back to children.

**M2: No file upload endpoint — `image_path` flow is broken for any frontend**
- File: `backend/app/routers/` — no upload router exists
- Bug: `ChatMessage.image_path` accepts a filesystem path but there's no `POST /upload` endpoint for the frontend to put files on the server.
- Fix: Create an upload endpoint in `backend/app/routers/chat.py` or a new `upload.py` router. Accept `UploadFile`, save to `settings.uploads_path`, return the path. Add `DELETE` to CORS `allow_methods` in `main.py` while at it.

**M3: No DELETE endpoint for conversations, DELETE not in CORS**
- File: `backend/app/routers/conversations.py`, `backend/app/main.py` line 30
- Fix: Add `DELETE /conversations/{id}` endpoint. Add `"DELETE"` to `allow_methods` in CORS config.

**M4: `_pipeline_lock` serializes ALL users — only 1 concurrent request**
- File: `backend/app/routers/chat.py` line 15
- Root cause: `PipelineLogger` singleton has shared mutable state (`_session_id`, counters). The lock prevents corruption but creates a global bottleneck.
- Note: OK for hackathon demo (single user). For production: replace singleton logger with per-request logger instances.

**M5: `load_pack` / `unload_pack` have no concurrency protection**
- File: `backend/app/knowledge_pack/loader.py` lines 133-165
- Bug: `_active_pack` is a bare global. Two simultaneous `POST /packs/load/{id}` calls can interleave. A concurrent read between close and assign returns None.
- Fix: Add an `asyncio.Lock` in the pack router around `load_pack()` calls.

**M6: Mission endpoints return hardcoded stubs indistinguishable from real responses**
- File: `backend/app/routers/mission.py` lines 21-42
- Fix: Add `"stub": true` field to response, or return 501 Not Implemented.

**M7: `num_predict=256` borderline for 8-result reranker JSON array**
- File: `backend/app/agents/nodes/rerank.py` line 226
- Fix: Bump to `num_predict=512`.

**M8: `_get_table_columns` runs PRAGMA on every query — no cache**
- File: `backend/app/tools/sqlite_query.py` line 37
- Fix: Add `functools.lru_cache` or module-level dict cache.

**M9: `to_tool_calls_log()` does full buffer scan on every streaming event**
- File: `backend/app/agents/field_assistant.py` lines 307, 323
- Fix: Only call on `on_chain_end` events, not `on_chain_start`. Or cache the result.

---

## HANDOFF PROMPT FOR NEXT CLAUDE SESSION

Copy this into a fresh Claude Code session:

```
I need you to fix the remaining bugs from our Phase 2 audit. Read `docs/HANDOFF_PHASE2_BUGS.md` for the full list. The file has ALREADY FIXED items (skip those) and REMAINING BUGS TO FIX.

Priority order:
1. C1: Fix image_analysis.py vision routing to respect auto-resolved provider
2. C2: Add timeout to ChatOllama in offline_llm.py
3. C3: Sanitize error messages in field_assistant.py streaming path
4. H1: Bump classify num_predict from 128 to 256
5. H2: Reduce generate_answer num_predict from 1024 to 512
6. H3: Fix data_path resolution in config.py
7. H4: Fix dead except clauses in classify_extract.py, craft_query.py, rerank.py
8. H5: Add pack status to health endpoint
9. M1: Batch _resolve_parent calls in chroma_search.py
10. M7: Bump rerank num_predict from 256 to 512

After each fix, DON'T run the full test suite until all fixes are done. Then run once:
cd backend && PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/ -v --ignore=tests/test_step_7_live.py --tb=short

Current state: 601/601 tests passing. Don't break any.
```
