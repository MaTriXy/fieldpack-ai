# FieldPack AI — Ship Punch List

Audit run: 2026-04-21. Goal: find correctness, polish, and distribution-hygiene
issues before the May 18 Kaggle deadline. **Perf-structural fixes are out of
scope for this round** (captured separately in the perf audit).

Ranking:
- **P0** — breaks or visibly degrades the hero demo (plant photo → diagnosis → treatment).
- **P1** — user-visible correctness or UX bug that judges may encounter.
- **P2** — hygiene, polish, defensive hardening.

Effort: **S** (<30 min), **M** (~1-2 h), **L** (half-day+).

---

## Pass 1 — Backend hero path

### P0

#### 1. WebSocket rate limiter is reset every message loop iteration
- **File:** `backend/app/routers/chat.py:215, 222`
- **Problem:** `_rate_timestamps` is a plain list initialised at the top of
  `chat_ws`, but line 222 reassigns it (`_rate_timestamps = [...]`) inside the
  message loop every iteration. Each inbound message replaces the list with a
  filtered copy — that's actually correct behaviour, but because the list is
  per-connection, a phone that opens a fresh WebSocket per chat session (which
  the frontend does on reconnect) gets a blank rate-limit window each time.
  Rate limiting is effectively per-connection only, not per-client.
- **Fix:** Keep the list per-connection if that's the intended semantics and
  document it, or move to a module-level dict keyed by client IP for a true
  client-level limit. For hackathon ship: document, don't add infra.
- **Effort:** S (doc-only) / M (IP-keyed)
- **Impact:** Judges reconnecting won't hit the limiter; at most an abuse
  resistance issue, not a demo-breaker. **Downgrade to P2** on reflection.

> Moving above to P2. Real P0s below:

#### 2. `generate_answer` strips leading punctuation that may truncate real output
- **File:** `backend/app/agents/nodes/generate_answer.py:270`
- **Problem:** `answer = "".join(...).lstrip("?!.,;: \n")` will eat legitimate
  leading characters if the model (Q4 small model, known to sometimes start
  with a stray token) emits e.g. `". Based on the sources..."` — the `.` and
  space go away which is fine, but it will also strip multi-char runs like
  `"?. Based on..."`. If the model ever leads with a question mark as a
  stylistic choice (rare, but Gemma sometimes does), the user never sees it.
- **Fix:** Replace with `.lstrip()` only, or limit to a single-char strip of a
  known-bad set. The current behaviour was likely added to clean up one
  specific bug; confirm which and keep it minimal.
- **Effort:** S
- **Impact:** Intermittent — answer looks slightly wrong on the first line.

#### 3. Empty-answer fallback message never reaches frontend as a `token` stream
- **File:** `backend/app/agents/nodes/generate_answer.py:276-279`
- **Problem:** When the LLM returns an empty completion, `generate_answer`
  fills `answer` with a fallback string ("I wasn't able to generate a complete
  answer..."). But because the streaming layer in `field_assistant.py:593`
  only forwards `on_chat_model_stream` chunks — and no chunks were produced —
  the frontend sees zero `token` events and then a `done` event with the
  fallback as `final_answer`. Depending on frontend state machine, this may
  render as an empty assistant bubble that suddenly pops the fallback on
  `done`. Per CLAUDE.md, this is the "frontend shows fallback" known gotcha.
- **Fix:** When the fallback path fires, synthesise a `token` event in the
  caller (field_assistant's stream loop) so the UI has progressive feedback.
  Alternatively, the frontend can detect "done with final_answer but no tokens
  seen" and render the full final_answer — simpler.
- **Effort:** S (frontend) / M (backend synthetic token)
- **Impact:** When it fires, the demo looks broken for ~40s then suddenly
  shows a generic message. Known issue — worth a belt-and-suspenders fix
  before judges test edge cases.

#### 4. `image_analysis.py` vision error path returns a success dict with an error message
- **File:** `backend/app/tools/image_analysis.py:271-282`
- **Problem:** On vision call failure, `analyze_plant_image` returns a dict
  with `visual_description` set to `"Image analysis failed: <err>"` and
  `confidence: "low"`. The caller in `classify_extract.py:193-198` then
  appends this failure string to the classification prompt *as if it were a
  real symptom description*. The classifier will happily generate a
  `disease_name` based on the garbage text, and the pipeline continues as if
  the photo was analysed correctly.
- **Fix:** Raise instead of returning a success-shaped dict on error, so
  `classify_extract.py`'s existing `except Exception` branch (line 203)
  catches it and sets `image_description = None`. Or: check for the `error`
  key in the caller and treat it as "image analysis unavailable."
- **Effort:** S
- **Impact:** Judges whose local vision model times out will get confident
  diagnoses from a garbage description. Direct hero-path hazard.

#### 5. `conversation_history` injected with `extract_text(response)` is never checked for empty/None
- **File:** `backend/app/agents/nodes/generate_answer.py:299-304`
- **Problem:** After fallback message is set, `updated_history` still appends
  the fallback as the assistant turn. On the next user message, the fallback
  becomes part of the few-shot context for classify. Not a crasher, but it
  poisons the conversation memory with "I encountered an error" — subsequent
  turns will see that and may drift.
- **Fix:** On the error path, don't append the fallback to
  `conversation_history` — return the original `history` unchanged.
- **Effort:** S
- **Impact:** Degrades multi-turn demos after any transient error.

### P1

#### 6. `_validate_image_path` calls `.is_relative_to` which requires Python 3.9+ semantics that differ from path normalisation
- **File:** `backend/app/routers/chat.py:60`
- **Problem:** `p.is_relative_to(uploads_root)` returns False if either path
  has unresolved symlinks or mixed forward/back slashes on Windows. On
  Windows the repo uses `C:\fieldpack-ai\...` but `upload.py:98` returns
  paths with `.as_posix()` (`C:/fieldpack-ai/...`). When the user sends that
  posix path back in the next request, resolve() re-normalises — usually
  fine, but the cross-platform round-trip is fragile.
- **Fix:** Normalise both sides to `str(Path(...).resolve().as_posix())`
  before comparison, or compare `str(p)` against `str(uploads_root)` with
  `startswith`. A quick `try/except HTTPException` to log the mismatched
  paths would help diagnose demo-day failures.
- **Effort:** S
- **Impact:** On Windows, an image upload followed immediately by a chat
  message sometimes fails with "Invalid image path." Reproducible when the
  device gives a posix-style path and the server normalises differently.

#### 7. `search_exhausted` flag depends on `retrieval_attempts >= 1` but rerank always increments — off-by-one on empty-first-attempt
- **File:** `backend/app/agents/nodes/generate_answer.py:132`, `rerank.py:400`
- **Problem:** `rerank_results` increments `retrieval_attempts` even when
  `search_results` is empty (line 397-401 of rerank.py). That means on the
  very first search that returned no results and routed straight to
  `generate_answer` (via `empty_and_unwinnable` at field_assistant.py:131),
  `retrieval_attempts == 1` and `search_exhausted` is True — which is
  correct. But for a conversational message that never searched (no engines
  in route), `retrieval_attempts` remains 0 and `is_conversational` fires
  instead. Verify the branch lines up for the LOG_OBSERVATION-skipping-search
  path — that's handled separately.
- **Fix:** Review — this is likely already correct but the condition is
  subtle and deserves a test that asserts the flag state in each branch.
- **Effort:** S (audit + add a test)
- **Impact:** Low — the logic appears right, but subtle. Worth a belt
  check before the demo.

#### 8. `_after_classify` short-circuits to END when `final_answer` is set, losing `route`/`needs_search` updates
- **File:** `backend/app/agents/field_assistant.py:71-75`
- **Problem:** The ask-back path in `classify_extract.py:278-284` sets
  `final_answer` + `needs_search=False` + `conversation_history`. The edge
  function short-circuits to END. Subsequent turns arrive with the stored
  history and a user reply like "cassava" — but the pipeline starts fresh
  and re-classifies without knowing this is a reply to an ask-back. The
  classifier has to infer from history that "cassava" is a crop-naming
  follow-up, not a general question.
- **Fix:** Either store an `ask_back_pending` flag in conversation metadata
  and have `classify_extract` check it (short "cassava" reply with
  `ask_back_pending=True` → auto-fill crop and rerun). Or accept the current
  behaviour and make sure the few-shot examples teach the model to handle
  one-word crop replies.
- **Effort:** M
- **Impact:** Ask-back UX is brittle — a good hero shot keeps the photo +
  user's one-word crop reply working, but easy to regress.

#### 9. `crop_filter` lowercased in route_intent but chunk metadata case is not normalised on ingest
- **File:** `backend/app/agents/nodes/route.py:71`, `chroma_search.py:131`
- **Problem:** `route.py:71` lowercases crop for filter (`"cassava"`). If
  the pack builder stored metadata as `crop="Cassava"`, ChromaDB `$eq` is
  case-sensitive and the filter matches nothing. I didn't verify the builder
  path — need to check `knowledge_pack/builder.py` or `seed_chunks.py`.
- **Fix:** Either verify ingest always lowercases, or switch filter to a
  case-insensitive check (ChromaDB doesn't natively support that — a
  separate `crop_lower` metadata field is the clean fix).
- **Effort:** S to check, M to fix if broken
- **Impact:** If broken, every filtered search returns 0 and we rely on the
  unfiltered companion search. That still works but is the whole reason
  `execute_search` does both — confirming the precision lift exists is
  worthwhile.

#### 10. FTS `_sanitize_fts_query` drops any word <3 chars — breaks queries like "E coli"
- **File:** `backend/app/tools/fts_search.py:62`
- **Problem:** For agricultural content this is mostly safe (Casamance pack
  isn't micro-organism-heavy), but any 2-letter crop abbreviation or short
  disease code becomes invisible to FTS. Known-unused for hero shot but a
  footgun.
- **Fix:** Allow 2-char tokens that aren't in `_STOP_WORDS`.
- **Effort:** S
- **Impact:** Low for Casamance, but a potential surprise for judges testing
  edge queries.

### P2

#### 11. Rate-limit list reset on reconnect (previously #1 — see above)
- **File:** `backend/app/routers/chat.py:215`
- **Problem:** Per-connection rate limit rather than per-client.
- **Fix:** Accept the current behaviour and document, or IP-key it.
- **Effort:** S (doc) / M (IP-keyed)
- **Impact:** Minimal for judges, security hygiene only.

#### 12. `CORS allow_headers` missing common headers for browser uploads
- **File:** `backend/app/main.py:73`
- **Problem:** `allow_headers=["Content-Type", "Upgrade", "Connection"]`
  does not include `Accept`, `Origin`, `Authorization`, or any custom
  `X-*` headers. Capacitor typically doesn't need these, but a judge
  running the frontend from `localhost:5173` with a hot-reload extension
  could hit CORS rejects on pre-flight.
- **Fix:** Add `Accept` at minimum; consider widening to `["*"]` since the
  origins list is already locked down.
- **Effort:** S
- **Impact:** Low — Vite dev server rarely trips this.

#### 13. `_cleanup_old_uploads` iterates `uploads_path` synchronously on every upload
- **File:** `backend/app/routers/upload.py:77-87`
- **Problem:** Blocking scan runs on every request. For demo-scale (dozens
  of files) it's instant. For a long-running demo box it could add latency.
  Not a perf-structural issue — it's a code smell.
- **Fix:** Run on a timer (APScheduler) or in a background task.
- **Effort:** M
- **Impact:** Low, but the README's "60-second setup" claim implies judges
  won't accumulate files — so moot for hackathon.

#### 14. `_after_rerank` logs `route_decision` via `log.log_step`, not emitted to frontend
- **File:** `backend/app/agents/field_assistant.py:161-171`
- **Problem:** The comment says "log_step alone would stay in the file
  logger but not reach the streaming pipeline." It still doesn't — the
  `tool_calls_log` buffer isn't flushed until the next node start. So the
  stated goal of "surfacing to frontend" isn't achieved; the decision is
  only visible post-hoc in `done.tool_calls_log`.
- **Fix:** Either yield an explicit `{"type": "pipeline_insight", ...}`
  from a wrapped edge function, or accept current behaviour and update the
  comment.
- **Effort:** S (comment) / M (real fix)
- **Impact:** Polish only — frontend loses one step of diagnostic detail
  during retries.

#### 15. `observation_log` fallback `summary` construction uses full `details` not a real summary
- **File:** `backend/app/routers/chat.py:156-159`
- **Problem:** On LLM failure, the fallback summary is the last assistant
  message truncated to 300 chars. That message may itself be a treatment
  recommendation — so the "observation" becomes the advice, not the
  observation. Wrong semantically.
- **Fix:** Prefer the last user message content instead, or produce
  `"Field chat logged — see details."`.
- **Effort:** S
- **Impact:** Rarely fires; only when the LLM summary call fails. Not on
  hero path.

---

## Backend pass summary (3-bullet status)

- Read all nodes in `backend/app/agents/**` (except nodes/route.py which
  another session owns) plus `field_assistant.py`, `image_analysis.py`,
  `chroma_search.py`, `fts_search.py`, `routers/chat.py`, `upload.py`,
  `main.py`, `config.py`, `offline_llm.py`.
- Found 4 P0 hero-path hazards: image-analysis-error-as-success, empty-
  answer-fallback-not-streamed, `lstrip` truncation risk, fallback message
  poisoning `conversation_history`. All are S-to-M fixes; none need perf
  changes.
- Found 5 P1 issues (ask-back brittleness, path-normalisation on Windows,
  crop case-sensitivity in filters, FTS short-word drop, `search_exhausted`
  off-by-one risk) and 5 P2 polish items.

Pass 2 (frontend) is next.

---

## Pass 2 — Frontend hero path UX

Files read: `pages/FieldChatPage.tsx`, `lib/config.ts`, `lib/api.ts`,
`hooks/useBackendReachable.ts`, `hooks/useServerConnection.ts`,
`components/MarkdownContent.tsx`, `App.tsx`.

### P0

#### 16. Streaming bubble disappears during retry loop — looks like a freeze
- **File:** `frontend/src/pages/FieldChatPage.tsx:1288`
- **Problem:** The live-token bubble only renders while `isStreaming &&
  (streamingContent || currentStep)`. During the ~20-30 s of `searching` →
  `reranking` retries, `streamingContent` is empty and `currentStep` is
  valid — so the `ThinkingBubble` renders with the current step. But when
  the backend transitions `rerank_results` → `expand_route_node` →
  `craft_search_query` → `execute_searches` → `rerank_results` (the retry
  loop), `currentStep` cycles and the UI flickers. On a real demo, this
  reads as "stuck" to the judge.
- **Fix:** Keep the same `ThinkingBubble` mounted across step transitions;
  only show the step label as a small sub-line and don't remount the
  container. Alternatively: add a smooth crossfade (~150 ms) on step change.
- **Effort:** M
- **Impact:** Demo polish — the longer the retry loop runs, the more the
  flicker builds.

#### 17. First-token `.replace(/^[?!.,;:\s]+/, '')` strips any prefix punctuation, not just a single char
- **File:** `frontend/src/pages/FieldChatPage.tsx:337`
- **Problem:** Mirrors the backend bug in finding #2 — if the real answer
  legitimately starts with punctuation (it rarely should, but Gemma Q4
  sometimes emits `". **Bacterial Blight**..."`), the opening dot + space
  are eaten and the user sees `"**Bacterial Blight**..."` which renders
  fine, but if any legitimate character like `"?"` leads the sentence, it's
  gone.
- **Fix:** Strip at most one leading character, not an unbounded run.
  `token.replace(/^[?!.,;:]\s*/, '')` stops after one.
- **Effort:** S
- **Impact:** Rare, cosmetic. But compounds with backend #2.

#### 18. `done` event fallback "I processed your request but could not generate a response" is the user-visible failure mode
- **File:** `frontend/src/pages/FieldChatPage.tsx:367-369`
- **Problem:** If `final_answer` is empty AND there are no observation
  stats, the UI puts `"I processed your request but could not generate a
  response. Please try again."` into chat. This is the demo-breaker path
  referenced in CLAUDE.md as the #1 recurring bug. The fallback text is
  generic and gives no indication of whether to retry or what went wrong.
- **Fix:** When this path fires, also include a diagnostic hint ("The model
  returned an empty answer — try rephrasing or check `ollama ps` for a
  CPU/GPU split issue"). Or: log the event type and pipeline state to
  console so judges running devtools can diagnose. For production demo:
  the fix really belongs in the backend (finding #3).
- **Effort:** S
- **Impact:** When it fires, judges see a blank-eyed error message with no
  recovery path. Wire this to backend finding #3.

#### 19. Photo → chat path uploads before WebSocket `send` — upload failure leaves orphan user message
- **File:** `frontend/src/pages/FieldChatPage.tsx:714-727`
- **Problem:** In `handleSend`, the user message is pushed to state at line
  679 *before* the image upload. If the upload then fails, line 721 does
  `prev.filter((m) => m.id !== userMsg.id)` to remove it. But if the user
  sent text + photo, the text message and the photo vanish together —
  there's no "save text, retry photo" path, and the input field has
  already been cleared at line 680. The text is gone from both state and
  input.
- **Fix:** Restore `setInput(messageText)` on upload failure, or keep the
  user message and mark it with an "upload failed" badge + retry button.
  For hackathon: easiest is `setInput(userMsg.content); setPendingImage(...)`
  to restore the whole compose state.
- **Effort:** S
- **Impact:** Judge takes a plant photo, upload fails (Wi-Fi flake), and
  their typed question is gone too. Direct hero-path hazard.

### P1

#### 20. `autoScanForServer` probes 254 IPs sequentially in batches of 30 with 2s timeouts — worst case ~17s
- **File:** `frontend/src/lib/config.ts:197-210`
- **Problem:** 254 / 30 = 9 batches × 2s timeout = ~18s worst case if
  nothing answers. Feels like a hang to first-launch judges on a network
  where the backend is only reachable via an unusual subnet. The retry
  loop in `useServerConnection` waits another 3s then restarts the whole
  thing.
- **Fix:** Show a progress indicator during scan ("Scanning local network
  — 3 of 9 batches complete"). The UX already says "scanning" but gives
  no sense of progress. Easy win for judge confidence.
- **Effort:** S (progress text) / M (real progress bar)
- **Impact:** First-launch experience — crucial for a hackathon where
  judges have 60 seconds of patience. Current state: they see "scanning"
  for 20 s and likely assume it's broken.

#### 21. Hero-shot photo overlay sits atop `msg.image` but the image element can be the *next* user message's image, not the one being analysed
- **File:** `frontend/src/pages/FieldChatPage.tsx:1155-1156`
- **Problem:** `isStreaming && msg.id === lastUserMsgId` gates the overlay.
  `lastUserMsgId` at 829 uses `findLast` over all messages. If the user
  sends a *second* photo mid-stream (stop button cancels the first, starts
  fresh), the overlay could transiently attach to the wrong image during
  the brief window where `isStreaming` flips false then true again.
- **Fix:** Also require `streamingContent.length === 0` in the condition
  so the overlay only shows during the pre-token phase.
- **Effort:** S
- **Impact:** Edge case — only affects rapid-fire demos. Unlikely to hit
  judges.

#### 22. `conversation_summary` never sent on `handleSendQueue` batch — loses prior-turn context
- **File:** `frontend/src/pages/FieldChatPage.tsx:773-779`
- **Problem:** The queue-send path omits `language` (line 779) but does
  include summary. Actually re-reading: summary IS included. Missing is
  `language`, which means queued messages always default to English even
  if the user set French. On a multilingual demo this drops context.
- **Fix:** Add `language: getLanguage()` to the payload.
- **Effort:** S
- **Impact:** Low — only affects French/Wolof/Portuguese demos of the
  offline-queue feature.

#### 23. `useBackendReachable` polls every 15s with no back-off — steady background traffic on the hotspot
- **File:** `frontend/src/hooks/useBackendReachable.ts:4`
- **Problem:** 15 s interval is reasonable when connected, but when the
  phone is offline it still keeps trying every 15s forever. Battery cost
  is small but non-zero.
- **Fix:** Exponential back-off on consecutive failures (15s → 30 → 60 →
  300). Trigger immediate retry on `online` event (already done).
- **Effort:** S
- **Impact:** Battery polish, not a demo issue.

#### 24. Auto-save debounce fires on every `isStreaming` transition — risk of saving incomplete state
- **File:** `frontend/src/pages/FieldChatPage.tsx:564-579`
- **Problem:** The effect depends on `[conversationId, messages,
  isStreaming]`. When streaming finishes (`isStreaming: true → false`),
  the effect re-runs and schedules a save. Good. But if the user then hits
  stop mid-stream, the partial message is added (line 1397), streaming
  stops, and a save fires with the partial content. Reload the conversation
  and you see an "interrupted" message permanently stored. Not a bug —
  intentional — but undocumented and unexpected.
- **Fix:** Accept as-is; consider adding a "(partial — generation stopped)"
  marker to the stored content so it's distinguishable on reload.
- **Effort:** S
- **Impact:** Minor polish; may confuse judges who hit stop and come back.

### P2

#### 25. `reconnectAttempts.current` not reset after user types — reconnect ceiling is permanent
- **File:** `frontend/src/pages/FieldChatPage.tsx:234`
- **Problem:** Once `reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS`
  (5), the user must click "Retry" in the error banner or the scan in
  `useServerConnection` has to succeed to reset it. On a transient Wi-Fi
  drop that later self-heals, the WS doesn't reconnect even after
  `useBackendReachable` goes true again.
- **Fix:** On `reachable: true` transition (line 508-518), the code already
  sets `reconnectAttempts.current = 0` before calling `connectWs()`. Good.
  But the guard at 281-283 returns early without clearing the error banner
  state. The user-visible `wsError` stays set until they manually dismiss.
- **Effort:** S
- **Impact:** Cosmetic — banner lingers after reconnect succeeds.

#### 26. `subnetCandidates` skips the device's own IP but not the broadcast / network addresses
- **File:** `frontend/src/lib/config.ts:124-128`
- **Problem:** On a /24 subnet, .0 and .255 are network and broadcast
  addresses. The loop skips neither (`i` goes 1..254 which excludes .0 and
  .255, actually — so this is fine). Noting it as checked.
- **Fix:** None needed.
- **Effort:** 0
- **Impact:** None.

#### 27. `priorityIps` list is hardcoded and order-dependent — `10.0.2.2` (emulator) first
- **File:** `frontend/src/lib/config.ts:170-177`
- **Problem:** `Promise.any` resolves on first success, so ordering only
  matters for the timeout. Real concern: `192.168.1.1` and `192.168.0.1`
  are *gateway* IPs, not laptop IPs. On typical home routers they'll 404
  rather than connect-refused, and if the router happens to run anything
  on :8000 (NAS admin panel, printer config) the probe may return 200 and
  lock in a bogus URL for the lifetime of the app.
- **Fix:** Validate `/health` response body actually contains FieldPack
  markers (e.g., `model.name` or `pack.pack_id`) before accepting. Current
  `probeHealth` only checks HTTP 200.
- **Effort:** S
- **Impact:** Rare but plausible on judge hardware; fix is cheap.

#### 28. `MarkdownContent` allows `target="_blank"` with `rel="noopener noreferrer nofollow"` but no CSP prevents data: URIs
- **File:** `frontend/src/components/MarkdownContent.tsx:78`
- **Problem:** `safeHref = href && /^https?:\/\//i.test(href) ? href : undefined`
  correctly rejects non-http(s) URIs (javascript:, data:, file:). Good.
  Model output shouldn't include hostile links (we're RAG-grounded from
  our pack), but this is the right defence. Flagging as checked.
- **Fix:** None needed.
- **Effort:** 0
- **Impact:** None.

#### 29. `parseDiagnosisFromAnswer` regex fires only when `imageDescription` is non-empty — any hero-shot path works, but text-only diagnosis won't get the card
- **File:** `frontend/src/pages/FieldChatPage.tsx:53-54, 377`
- **Problem:** Only shows the diagnosis card when an image was uploaded on
  this turn. If the user types "my cassava has brown spots and yellow
  leaves" without a photo, the LLM may name the disease in the answer but
  no card appears. Consistent with the spec — but we could surface it.
- **Fix:** Drop the `imageDescription` gate, or run a lighter text-only
  diagnosis parser. Not critical for hero path (photo path).
- **Effort:** M
- **Impact:** Polish — widens diagnosis card to text flows.

#### 30. ESC key listener uses `onKeyDown` on root div — requires focus, doesn't fire when focus is in textarea
- **File:** `frontend/src/pages/FieldChatPage.tsx:915`
- **Problem:** ESC to close sidebar is bound to `onKeyDown` on the root
  container. React bubbles keydown up from the textarea, so this should
  work. But ESC in a textarea doesn't have a universally consistent
  browser behaviour — may blur instead. Test on actual APK WebView.
- **Fix:** Use a `document.addEventListener('keydown', ...)` in a useEffect
  so it's global and not dependent on focus.
- **Effort:** S
- **Impact:** Niche — keyboard users only, probably never triggered on
  phone.

---

## Frontend pass summary (3-bullet status)

- Read `FieldChatPage` (the hero-path page), `config.ts` (LAN discovery),
  `api.ts`, `useBackendReachable`, `useServerConnection`, `MarkdownContent`,
  `App.tsx`. Confirmed no `dangerouslySetInnerHTML` or `eval` anywhere.
- Found 4 P0-ish issues: streaming-bubble flicker during retry (looks like a
  freeze), the mirror of backend's leading-punctuation strip, the
  empty-answer fallback UX, and the upload-failure-eats-text path on the
  photo flow. Most are S-effort.
- 5 P1s (LAN scan progress indicator, photo-overlay timing, missing
  language in queue-send, polling back-off, auto-save-on-stop-button) and
  6 P2s (cosmetic/hygiene). Good news: markdown sanitisation is solid,
  no XSS vectors via chat content.

Pass 3 (distribution surface) is next.

---

## Pass 3 — Distribution surface

Files read: `Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`,
`.dockerignore`, `frontend/.dockerignore`, `frontend/nginx.conf`,
`backend/.env.example`, `README.md` (for setup-claim verification),
`backend/app/main.py` (for CORS surface). Cross-checked APK SHA256 against
README (matches) and verified `.env` is not tracked in git (only
`.env.example` is).

### P0

#### 31. README "60-second setup" under-sells first-run time — risk of judge abandonment
- **File:** `README.md:38-47`, `README.md:55`
- **Problem:** The headline is "60-Second Setup" but the nested paragraph
  admits the first run pulls ~5 GB and takes ~5 minutes. A judge who runs
  `docker-compose up` expecting 60 seconds may Ctrl-C midway through the
  Ollama pull — leaving a partial volume. Worse, the app container
  `depends_on: ollama-init: service_completed_successfully`, so the frontend
  will never load while the pull is in progress and `localhost:5173`
  returns nginx "unable to connect" since the frontend container is also
  started but depends on the app being healthy. Judges get a blank page
  during the pull, no progress indicator, no guidance.
- **Fix:** Two options — (a) rename heading to "One-command setup (first
  run ~5 min)"; (b) remove the `depends_on` gate on frontend so the
  React shell loads immediately and shows "backend starting, pulling
  model — ~5 min on first run" via the existing `useServerConnection`
  reachability logic. Option (b) is better UX but requires the frontend's
  error banner to differentiate "backend not started" from "no WiFi."
- **Effort:** S (rename) / M (frontend-loads-first)
- **Impact:** Direct hero-path hazard — judges who give up during the
  5-minute pull never see the demo.

#### 32. `ollama pull` requires internet but README frames the project as "offline-first"
- **File:** `README.md:22, 38-47`, `docker-compose.yml:97-99`
- **Problem:** The README emphasises "no internet required" but the Docker
  flow *requires* internet on first run to pull the Gemma 4 E2B weights.
  A judge reading the tagline and then running `docker-compose up` on a
  plane/hotspot with no internet will get a hang followed by an
  `ollama-init` crash with no clear explanation.
- **Fix:** Add a one-line clarification in the 60-second setup block:
  "First run requires internet (~5 GB pull). After that, runs fully
  offline." Already implied in the paragraph at line 55 but the upfront
  block doesn't say it.
- **Effort:** S
- **Impact:** Narrative dissonance — judges running on a constrained
  network get a confusing failure, and the "offline-first" claim looks
  weaker than it is.

### P1

#### 33. `docker-compose.yml` does not set `OLLAMA_NUM_GPU=0` by default — Intel iGPU users get garbage
- **File:** `docker-compose.yml:42-47`
- **Problem:** The #1 recurring bug per CLAUDE.md (E2B + Intel iGPU =
  garbage output). The env var is commented out in both
  `docker-compose.yml` and `backend/.env.example`. A judge on a typical
  Intel laptop will run `docker-compose up`, get garbled text, and have
  to dig through README troubleshooting to find the fix. The README does
  document this (line 210) but only after the pipeline diagrams and
  tech stack table.
- **Fix:** Enable `OLLAMA_NUM_GPU=0` by default in compose, and
  comment-out the line that enables auto-detection with clear guidance:
  "If you have an Nvidia/AMD discrete GPU, comment the line below and
  uncomment the `deploy:` block for GPU acceleration." Default should
  be the safe path, not the fast path. Currently default is the unsafe
  path (auto-detect).
- **Effort:** S
- **Impact:** Judges on Intel hardware (majority) get garbage output on
  first run unless they read docs carefully. High-probability demo
  breaker.

#### 34. `Dockerfile` bakes embedding model download at build time — requires internet during `docker-compose up --build`
- **File:** `Dockerfile:36-38`
- **Problem:** The Dockerfile pre-downloads `all-MiniLM-L6-v2` (~90 MB)
  by running a Python script inside `RUN`. That's good for runtime
  (no first-request hang). But it means the image can't be rebuilt
  offline — a judge who rebuilds to pick up a code change from git
  needs HuggingFace reachable. Not a demo issue, but a "judge tweaks
  and rebuilds" issue.
- **Fix:** Accept as-is for hackathon; the baked model is on Docker Hub
  if we ever publish the image. Flag in README that rebuild needs
  internet.
- **Effort:** S (README line)
- **Impact:** Low — only affects reviewers who rebuild.

#### 35. `ollama-init` `ollama run … --hidethinking` warmup may fail silently on older Ollama versions
- **File:** `docker-compose.yml:107`
- **Problem:** The `--hidethinking` flag was added in Ollama 0.12+. The
  image is pinned to 0.21.0 so this should work, but the `|| true` on
  line 107 swallows the error if it doesn't. The subsequent warmth
  assumption ("model pinned, first query is fast") then breaks
  silently. The first judge query pays the 20-60 s cold-load cost that
  the warmup was supposed to prevent.
- **Fix:** Drop `|| true` — if the warmup fails, we want to know, not
  silently continue. Or, since the pinned-to-0.21.0 image guarantees
  the flag is supported, remove the defensive `|| true` and let any
  failure surface.
- **Effort:** S
- **Impact:** Demo polish — first query could be slow if warmup fails
  silently.

#### 36. CORS origin list does not include the laptop's LAN IP — phone-to-backend fetch could be blocked
- **File:** `backend/app/main.py:65-70`
- **Problem:** `allow_origins` only permits `localhost` variants and
  `capacitor://localhost`. The Capacitor WebView on Android serves the
  app at `capacitor://localhost` — correct — but if the judge opens
  the frontend via a browser on the phone (not the APK), the origin
  becomes `http://<laptop-ip>:5173` and CORS preflight fails. The APK
  path works; a curious judge with no APK who visits the laptop URL
  from their phone does not.
- **Fix:** Add a regex allow or add `http://192.168.*` patterns via
  `allow_origin_regex`. Capacitor flow is unaffected.
- **Effort:** S
- **Impact:** Low — most judges use the APK. But someone testing from
  a phone browser hits a silent CORS wall.

### P2

#### 37. `packs/*/chroma_db_backup_*` is in `.dockerignore` but still committed to git — bloats public repo
- **File:** `.dockerignore:64`, `packs/casamance_agriculture/chroma_db_backup_20260411_140517/`
- **Problem:** The `chroma_db_backup_20260411_140517/` directory
  exists in the repo (4 nested collection UUIDs with `.bin` files +
  a 2 MB sqlite). `.dockerignore` keeps it out of the image — good.
  `.gitignore` does NOT exclude it — `git ls-files` will include
  several megabytes of stale backup data that ships in the public
  repo once it flips. Check with `git ls-files packs/`; if the backup
  is tracked, remove before going public.
- **Fix:** `git rm -r --cached packs/casamance_agriculture/chroma_db_backup_*`
  and add `packs/*/chroma_db_backup_*` to `.gitignore`.
- **Effort:** S
- **Impact:** Repo bloat on public flip; no runtime impact.

#### 38. `OLLAMA_TUNNEL_TOKEN` + `GOOGLE_AI_STUDIO_API_KEY` mentioned in multiple places — secret-review surface area
- **File:** `backend/.env.example:11, 18`, `backend/tests/conftest.py`, `backend/app/agent_farm/tools/web_search.py`, `notebooks/colab_ollama_gpu.ipynb`
- **Problem:** Before the public flip, do a final pass: grep the entire
  history for any accidental key leak. `.env` is correctly gitignored.
  The notebook and test files should be verified to use env vars only,
  not literal keys. `notebooks/colab_ollama_gpu.ipynb` is the main risk
  — Colab notebooks sometimes have output cells containing tokens from
  the last run.
- **Fix:** Open the notebook, clear all outputs, and grep for known key
  prefixes (`AIza`, `tvly-`) across history. This belongs in Pass 4.
- **Effort:** S (notebook clean) + scan
- **Impact:** Existential if a leak exists — otherwise zero.

#### 39. `docker-compose.yml` image tag `ollama/ollama:0.21.0` — may be superseded by May 18
- **File:** `docker-compose.yml:26, 78`
- **Problem:** Pinning to a version is correct. But if Ollama 0.21.0
  gets yanked or the registry tags shift (has happened), judges with
  no local cache can't pull it. Low probability, but we're a month out.
- **Fix:** None needed; note in the WHERE_TO_WATCH section of README
  that this tag is tested.
- **Effort:** 0
- **Impact:** None unless Docker Hub does something unusual.

#### 40. Frontend nginx healthcheck uses `wget` — busybox wget in alpine doesn't return non-zero on HTTP 4xx cleanly
- **File:** `frontend/Dockerfile:27-28`
- **Problem:** `wget -qO- http://127.0.0.1:5173/` returns 0 on both
  200 and some 4xx responses in busybox. If nginx misconfigures and
  returns 404 for `/`, the healthcheck still passes. Real failure
  (nginx down) would correctly fail — so marginal issue.
- **Fix:** Use `wget -q --spider --tries=1` or curl with `-f`.
- **Effort:** S
- **Impact:** Low — nginx is reliable; this only masks config drift.

#### 41. `Dockerfile` does not pin `curl` / `ca-certificates` apt versions — reproducibility concern for a 4-week ship
- **File:** `Dockerfile:16-19`
- **Problem:** `apt-get install -y curl ca-certificates` installs
  whatever version Debian ships at build time. For a month-to-ship
  window this is fine; for long-term reproducibility a `=version`
  pin would help.
- **Fix:** Skip for hackathon.
- **Effort:** 0
- **Impact:** None at our timescale.

#### 42. `DEBUG=true` in `backend/.env.example` default — leaks stack traces on errors if judge copies template
- **File:** `backend/.env.example:52`
- **Problem:** Unclear whether the code honours this flag. If any
  exception handler changes behaviour on `DEBUG=true`, judges get
  verbose tracebacks in the response body. Grep didn't find a
  definitive branch, but belt-and-braces: default should be `false`
  in the example, enabled by devs who opt in.
- **Fix:** Flip to `DEBUG=false` in `backend/.env.example`. Docker
  path sets `DEMO_MODE=false` and never reads the example, so Docker
  is unaffected — only matters for native-install judges who `cp`
  the example.
- **Effort:** S
- **Impact:** Minor info-leak hygiene.

#### 43. `README.md` "Demo Mode" block references `source venv/bin/activate` on macOS/Linux but repo's venv script layout uses Windows style
- **File:** `README.md:152-154`
- **Problem:** Both variants documented correctly; just flagging that
  the shipped `venv/` in the repo is a Windows-built venv (has
  `Scripts/` not `bin/`) — judges on macOS/Linux who clone and see
  a pre-built venv will get confused. They should recreate locally.
- **Fix:** Clarify: "Create a fresh venv — do not reuse any pre-built
  one in the repo." Actually, `venv` is in `.gitignore`, so this is
  a non-issue — remove this finding. Leaving as a "checked, clean" note.
- **Effort:** 0
- **Impact:** None.

---

## Pass 3 summary (3-bullet status)

- Read Docker/compose/dockerignore pair, nginx config, `.env.example`,
  backend CORS setup, and README setup section end-to-end. Verified
  `.env` is correctly gitignored (only `.env.example` tracked). APK
  SHA256 in README matches `dist-apk/fieldpack-ai-v1.0.0-debug.apk`
  exactly (`831984eb...525df`).
- Found 2 P0 README/setup issues (60-second claim vs 5-minute reality,
  and offline-first narrative vs model-pull internet requirement), 4
  P1 (Intel iGPU default, rebuild-needs-internet, warmup `|| true`,
  CORS missing LAN origin), and 6 P2 (chroma backup in git, DEBUG
  default, nginx healthcheck, apt pin, image-tag risk, misc).
- Biggest single leverage: default `OLLAMA_NUM_GPU=0` in
  `docker-compose.yml`. That one change flips the #1 recurring bug
  from "judge sees garbage" to "judge sees slow but correct." The
  README trade-off line (uncomment for GPU) is one edit away.

Pass 4 (public-repo-flip hygiene) is next — or stop here for review.

---

## Pass 4 — Public-repo-flip hygiene

Checks run before the May 11-13 public flip: full git-history secret scan,
tracked-file audit, README-promise vs reality for a fresh clone, APK link
and SHA256 cross-check, large-file bloat, and markdown surface review.

### P0

#### 44. `packs/*/chroma_db/`, `packs/*/knowledge.db`, and `packs/*/images/` are gitignored — fresh clone has no Knowledge Pack, demo is impossible
- **File:** `.gitignore:28-30`, `Dockerfile:41`, `README.md:42-47`
- **Problem:** The `.gitignore` excludes the vector store, the SQLite
  knowledge DB, and the reference image set — the three things the
  Casamance Agriculture Pack needs to function. Locally the maintainer
  has all three (2.7 MB chroma + 684 KB knowledge.db), and
  `docker-compose up` bakes them via `COPY packs/ /app/packs/`. A judge
  who runs `git clone && docker-compose up` gets only
  `manifest.json`, `README.md`, `SOURCES.md` in `packs/casamance_agriculture/`.
  The app will start, auto-load the pack via `_auto_load_first_pack()`
  (which checks for `manifest.json` + `knowledge.db`) — the check at
  `main.py:29` requires `knowledge.db`, so the pack is NOT auto-loaded,
  ChromaDB is empty, and every query returns 0 sources → fallback
  answer or empty. **The README's "60-second setup" and "hero shot"
  cannot work on a fresh public clone.**
- **Fix:** Three options, pick one:
  1. Commit the built pack. ~3.4 MB total, well under GitHub's limits.
     Remove `packs/*/chroma_db/`, `packs/*/knowledge.db`,
     `packs/*/images/` from `.gitignore`, `git add` them. Easiest.
  2. Ship a GitHub Release containing a pack tarball, and have the
     Dockerfile `ADD` from the release URL at build time. Clean but
     adds a release-management step.
  3. Add a `build_pack` entrypoint that runs once on first
     `docker-compose up` before the app starts. Heaviest — requires
     the Agent Farm / Google AI Studio credentials at build time,
     which judges don't have.
- **Effort:** S (option 1) / M (option 2) / L (option 3)
- **Impact:** **Ship-blocker.** This is the single biggest risk for
  the May 11-13 public flip. Verified by inspecting `.gitignore` and
  confirming only 3 tiny files are tracked under `packs/`.

#### 45. APK distribution via Google Drive link — permission can break, and the file is not under repo control
- **File:** `README.md:73`, `dist-apk/fieldpack-ai-v1.0.0-debug.apk`
- **Problem:** The "Run on Your Phone" section points judges to a
  Drive URL (`https://drive.google.com/file/d/1fDdvSxdMTf0a_rqwmO2idPo_R_9eCQLu/view`).
  Two risks: (a) Drive can revoke public share at any time (rate-
  limit, ToS flag, account change); (b) the file at that Drive link
  may drift from the SHA256 published in README if the maintainer
  re-uploads without updating docs. `dist-apk/` is gitignored (line
  48), so the actual shipped binary is not in the public repo either.
- **Fix:** On public flip, cut a GitHub Release tagged
  `v1.0.0-judges`, attach the APK as a release asset, and swap the
  README link to
  `https://github.com/orkohol/fieldpack-ai/releases/latest/download/fieldpack-ai-v1.0.0-debug.apk`.
  Drive link stays as backup. This is already called out in CLAUDE.md
  gotchas — just needs execution.
- **Effort:** S
- **Impact:** If the Drive link 404s during judging, phone demo is
  dead. GitHub Release is zero-maintenance.

### P1

#### 46. `CLAUDE.md` is tracked — internal gotchas, dev-flow notes, and known-bug lore go public on flip
- **File:** `CLAUDE.md`
- **Problem:** The file is full of useful-for-us, awkward-in-public
  content: "#1 recurring bug", "E2B + Intel iGPU = garbage",
  troubleshooting tags, `demo/` path details, and a "Non-Negotiable"
  section that reads as internal strategy. Judges who Google the repo
  may infer instability from the gotcha list. Not a security issue;
  a narrative one.
- **Fix:** Either (a) rename to `docs/DEVELOPER_NOTES.md` and soften
  language; or (b) move sensitive bits into an untracked local file
  and keep a short, clean `CLAUDE.md` that references public
  `TECH_FRAMEWORK.md`. Judges don't need to see the gotcha list to
  evaluate the submission.
- **Effort:** S (rename + soften) / M (split)
- **Impact:** Narrative polish; optics.

#### 47. README Demo Mode promises work but `DEMO_MODE=true` path is untested for this shipping round
- **File:** `README.md:144-167`, `backend/.env.example:5`
- **Problem:** The README describes a native-install "Demo Mode" that
  should run without Ollama. It's listed first, before the full
  Docker flow. If a judge picks the shortest-looking path and native-
  installs with `DEMO_MODE=true`, they get a different code path
  than the one we've been polishing for the hackathon (Docker +
  real Ollama). Any recent regression in demo-mode handling
  (canned responses, fake image analysis, queued responses) would
  surface only here.
- **Fix:** Either (a) move Demo Mode below Docker in README so it's
  not the first thing judges see; or (b) run through Demo Mode end-
  to-end on a clean machine before public flip and fix any breakage.
  Recommend (a).
- **Effort:** S (reorder) / M (test end-to-end)
- **Impact:** Secondary path, but a judge who hits it first and it
  breaks forms a bad first impression.

#### 48. `docs/QUICKSTART_POWERSHELL.md` tracked but not referenced from README
- **File:** `docs/QUICKSTART_POWERSHELL.md`
- **Problem:** Tracked markdown file that the README never links to.
  On public flip, judges browsing `docs/` see it and may follow its
  instructions instead of the README's. If it's stale or references
  private paths, that's a bad user path. Worth a quick read before
  flip.
- **Fix:** Either link it from README as "Windows / PowerShell quick-
  start," update it to match current Docker flow, or add a front-
  matter deprecation note: "Legacy — use the README Docker flow."
- **Effort:** S
- **Impact:** Low — judges unlikely to find it, but one untested
  setup path.

#### 49. README Full-Mode block tells judges to `ollama pull gemma4:e2b-it-q4_K_M` — tag has changed before, may change again
- **File:** `README.md:172`, `docker-compose.yml:98`
- **Problem:** The README and compose both reference the exact
  Ollama tag. If Google re-publishes under a new naming convention
  (has happened twice already), every judge gets a `pull model
  manifest: file does not exist`. `docker-compose.yml:212` already
  documents the fallback in README, but the README's Full-Mode
  section copy-pastes the old tag without a "check first" caveat.
- **Fix:** In README Full-Mode block, add a one-liner: "If this
  fails, check `ollama list` in the Docker Troubleshooting section
  for the current tag." Not a pre-flip blocker — just a resilience
  thing.
- **Effort:** S
- **Impact:** Hinges on Ollama registry behaviour — we have no
  control.

### P2

#### 50. No git-history secret leaks detected — verified clean
- **Scan:** `git log --all -p | grep -oE "(AIza…|tvly-…|sk-…|ghp_…|hf_…)"`
  returned zero matches. Colab notebook outputs also clean (zero
  prefix matches).
- **Status:** ✅ verified. No action needed.
- **Impact:** Public flip is secret-safe based on pattern scan.
  Strongly recommend one more pass with a tool like `gitleaks` or
  `trufflehog` before flipping — pattern grep misses non-standard
  secret shapes.

#### 51. Repo size driven by `demo/assets/photos/*.jpg` + `video-frames/public/photos/*.jpg` — duplicate copies of the same images
- **File:** `demo/assets/photos/`, `video-frames/public/photos/`
- **Problem:** `git ls-files` shows the same JPEGs in both trees
  (e.g. `persona_mother.jpg` is 3.3 MB in both, 6.6 MB total).
  Total large-file weight is ~22 MB across tracked assets. Fine for
  clone time, but duplication is avoidable.
- **Fix:** Have `video-frames` symlink or import from `demo/assets`.
  Post-hackathon cleanup — out of scope for the May 18 ship.
- **Effort:** M
- **Impact:** Repo size only. Clone stays under 30 MB.

#### 52. `.dockerignore` lists `frontend/android/.gradle` but `frontend/.dockerignore` does the same for node_modules — duplication is fine, just flagging
- **File:** `.dockerignore:33-37`, `frontend/.dockerignore`
- **Problem:** Both dockerignore files are correct; the root one
  excludes android stuff because the root build context is the
  whole repo, and `frontend/.dockerignore` is scoped to the
  frontend build context. Verified both dockerignore files protect
  the right secrets (`.env` variants covered in root).
- **Fix:** None. Verified clean.
- **Effort:** 0
- **Impact:** None.

#### 53. `dist-apk/` is gitignored — correct, but means the APK cannot be diffed or versioned in-repo
- **File:** `.gitignore:48`
- **Problem:** APK binaries are correctly excluded from git. The
  trade-off is that the shipped binary can only be tracked via
  SHA256 in the README and whatever file is in the local
  `dist-apk/`. Finding #45 (move to GitHub Release) makes this a
  non-issue.
- **Fix:** See finding #45.
- **Effort:** See #45.
- **Impact:** Tied to #45.

#### 54. `NOTICE` + `LICENSE` both present and tracked — Apache 2.0 attribution chain looks clean
- **File:** `LICENSE`, `NOTICE`
- **Status:** ✅ verified. Both files exist at repo root; NOTICE is
  referenced from README line 306 and covers the Gemma Terms
  pass-through.
- **Impact:** None. Attribution hygiene done.

#### 55. All README image paths resolve — `docs/images/phone-hero/01-..05-*.png`, architecture + pipeline diagrams all present
- **File:** `README.md:27-35, 134, 140`
- **Status:** ✅ verified with `ls`. No broken image references.
- **Impact:** None.

#### 56. No `.env`, `.claude/`, `.aws/`, `.ssh/` or other credential-adjacent directories tracked
- **Scan:** `git ls-files | grep -iE "(\.env|secret|credential|\.aws|\.ssh)"` returned only `backend/.env.example` and `CLAUDE.md` (tracked by choice, not a secret).
- **Status:** ✅ verified. `.claude/` is gitignored at line 57.
- **Impact:** None.

---

## Pass 4 summary (3-bullet status)

- Git history secret scan: **clean** (no `AIza…`, `tvly-…`, `sk-…`,
  `ghp_…`, `hf_…` in any commit). Colab notebook outputs also clean.
  Tracked-file audit confirms `.env` is correctly gitignored, only
  `.env.example` ships.
- **Ship-blocker found:** finding #44 — Knowledge Pack artifacts
  (`chroma_db/`, `knowledge.db`, `images/`) are all gitignored, so
  `git clone && docker-compose up` produces a running app with zero
  knowledge. The README's hero demo cannot work on a fresh clone.
  Fix: `git add` the ~3.4 MB built pack before flipping public.
- One other P0 (APK on Google Drive — swap to GitHub Release), three
  P1 polish items (`CLAUDE.md` tracked, README Demo-Mode ordering,
  stale `QUICKSTART_POWERSHELL.md`), and 7 verified-clean items
  (NOTICE/LICENSE, image paths, dockerignore coverage, no credentials
  tracked, no secrets in history).

---

## Full-audit summary (passes 1-4)

| Pass | P0 | P1 | P2 | Total |
|------|---:|---:|---:|------:|
| 1 — Backend hero path      | 4 | 5 | 5 | 14 |
| 2 — Frontend hero path     | 4 | 5 | 6 | 15 |
| 3 — Distribution surface   | 2 | 4 | 7 | 13 |
| 4 — Public-flip hygiene    | 2 | 4 | 7 | 13 |
| **Total**                  | **12** | **18** | **25** | **55** |

**Top 5 fix-first (P0, ranked by ship risk):**
1. **#44** — commit the Knowledge Pack artifacts (fresh clone cannot run demo). **S**.
2. **#4** — `image_analysis.py` returning success-shape on vision failure poisons the classifier. **S**.
3. **#19** — upload-failure eats the user's typed text on the photo flow. **S**.
4. **#31 + #33** — README "60-second" claim + Intel iGPU default; fix both in one compose edit + README heading change. **S**.
5. **#3 + #18** — empty-answer fallback never streams, then shows generic UI text. Frontend-side detection is the easier fix. **S**.

All other P0s are S-effort too (leading-punctuation strip #2/#17,
`conversation_history` poisoning #5, streaming-bubble flicker #16,
APK-link #45). Everything P0 is a one-sitting session to close.

Pass done. Ready for review.
