# Troubleshooting

One-stop reference for the most common issues when setting up or running FieldPack AI. If you hit something that isn't listed here, check the backend logs (`docker-compose logs app` or the uvicorn stdout) and Ollama logs (`docker-compose logs ollama`).

---

## Model output is garbled or nonsensical (Intel integrated GPU)

**Symptom:** the assistant returns word salad, repeated tokens, or obviously wrong sentences — even for simple questions it should handle.

**Cause:** Ollama is partially offloading Gemma 4 E2B to an Intel integrated GPU. Partial offload on small quantised models frequently corrupts outputs.

**Fix:** force CPU-only mode.

- **Docker (default):** the bundled `docker-compose.yml` sets `OLLAMA_NUM_GPU=0` for exactly this reason. If you removed it for Nvidia passthrough and you're on an Intel iGPU machine, put it back and run `docker-compose restart ollama`.
- **Native Ollama:** export `OLLAMA_NUM_GPU=0` before `ollama serve`.

**Why this is the #1 recurring bug:** looks like a model problem, but it's a GPU-offload problem. If the assistant ever produces garbage after it was working, suspect this first.

---

## First query after startup is very slow

**Symptom:** the first chat request after `docker-compose up` (or a restart) takes 30–90 seconds before tokens start streaming. Subsequent requests are much faster.

**Cause:** ChromaDB has to warm its HNSW vector index on the first query against each collection. After warm-up the index is resident; queries return in milliseconds.

**This is normal.** Not a bug. If you want to hide the latency during a demo, issue a throwaway query after startup to pre-warm the index before your audience sees anything.

---

## Ollama model pull fails with "pull model manifest: file does not exist"

**Symptom:** the `ollama-init` container exits immediately with a manifest error, or `ollama pull gemma4:e2b-it-q4_K_M` fails with the same.

**Cause:** the Gemma 4 tag in the public Ollama registry has changed. Google occasionally re-tags or deprecates specific quantisations.

**Fix:** find the current tag and update the pull command.

```bash
curl https://ollama.com/library/gemma4/tags
```

Or browse the [ollama.com/library/gemma4](https://ollama.com/library/gemma4) page. Then update:

- `OLLAMA_MODEL` in `docker-compose.yml`
- The `ollama pull` command inside the `ollama-init` service
- `OLLAMA_MODEL` in `backend/.env` if you're running natively

---

## Phone can't reach the laptop backend (APK thin-client)

**Symptom:** "Cannot reach server" in the Android app, or the auto-scan completes without finding anything.

**Diagnostic order (stop at the first failing check):**

1. **Same subnet?** From a terminal app on the phone, `ping <laptop-ip>`. If ping fails, the phone and laptop aren't on the same network. Cellular-hotspot pairing, enterprise WiFi with client isolation, and guest networks all cause this.
2. **Firewall on the laptop?** Windows Defender usually prompts on first `docker-compose up` — choose "Allow access" on both Private and Public networks. If you clicked "Block" previously, open **Windows Security → Firewall → Allow an app → Docker Desktop** and re-enable.
3. **Port 8000 listening?** From another machine on the same network: `curl http://<laptop-ip>:8000/health` should return `{"status":"ok"}`. If it does from your dev machine but not from the phone, it's the firewall.
4. **Correct URL in the app?** Tap the gear icon in the app → enter `http://<laptop-ip>:8000` (not `https`, not `localhost`, include the port).

**Laptop IP lookup:**

- Windows: `ipconfig` → IPv4 under the active adapter. Hotspot mode usually reports `192.168.137.1`.
- macOS/Linux: `ifconfig | grep "inet "` → the `192.168.x.x` or `10.x.x.x` line.

---

## WebSocket connection fails on the APK, HTTP works

**Symptom:** the app loads the home screen and can reach `/health`, but Field Chat hangs or drops with "connection lost."

**Cause:** Capacitor's `CapacitorHttp` plugin intercepts HTTP requests but **not** WebSocket connections. WebSocket traffic goes through the system WebView's networking, which respects different rules (cleartext-traffic permission, HTTPS-only enforcement).

**Status:** the shipped APK has cleartext traffic enabled explicitly via `network_security_config.xml`, so this should work on stock Android. If you built your own debug APK and it's failing:

1. Check `frontend/android/app/src/main/AndroidManifest.xml` has `android:usesCleartextTraffic="true"` or a `networkSecurityConfig` reference.
2. Check the WiFi network isn't a captive-portal / HTTPS-only network that blocks LAN WS traffic. Hotel and airport WiFi commonly do this.

---

## Docker build requires internet even after a successful first build

**Symptom:** `docker-compose up --build` fails offline, even though you built successfully once while online.

**Cause:** the backend Dockerfile pre-downloads the sentence-transformers embedding model (~90 MB from huggingface.co) at build time. This is intentional — it means the first chat request doesn't hang — but it requires internet **every time you rebuild the image**.

**Workaround:** use `docker-compose up` (without `--build`) for offline restarts. Only rebuild when you're online.

---

## ChromaDB test flake: "Nothing found on disk"

**Symptom:** running the backend test suite occasionally fails with `chromadb.errors.InternalError: Error creating hnsw segment reader: Nothing found on disk`. A different test fails each run; retrying usually passes.

**Cause:** ChromaDB's `SharedSystemClient` caches `System` objects per `(tenant, database, persist_directory)`. When tests load and unload packs at different `tmp_path` locations, stale `System` references keep Rust-side file handles open on HNSW files that no longer exist. The next pack's query then finds the cached System's file handles pointing at nothing.

**Status:** partial mitigation is in `backend/app/knowledge_pack/loader.py:close()` — calls `SharedSystemClient.clear_system_cache()` and forces a GC pass on pack unload. Reduces flake from "always" to "occasional." If you hit this during a test run, **retry the run** before investigating as a new bug.

**Not a production issue.** The running backend loads a pack once at startup and keeps it for the life of the process. This only affects test harnesses that repeatedly load/unload packs.

---

## Backend logs are flooded with `/health` polls

**Symptom:** tailing `docker-compose logs app` shows `GET /health 200 OK` every second or two, drowning out real pipeline logs.

**Cause:** the frontend's connection-status indicator polls `/health` on a short interval. The Docker healthcheck also polls it. That's two pollers by design.

**Fix:** filter them out when reading logs:

```bash
docker-compose logs -f app 2>&1 | grep -v "/health"
```

Or use `/metrics`-style filtering if you add a log aggregator later. Don't silence the endpoint itself — the healthcheck needs it.

---

## Manual APK smoke-test plan (when no phone is available at build time)

If you can't test the APK on a real phone before shipping, run through this checklist the first time you do get a phone in hand:

1. **SHA256 match** — `certutil -hashfile fieldpack-ai-v1.0.0-debug.apk SHA256` on Windows (or `shasum -a 256` on macOS/Linux) against the value in README.md.
2. **Install** — open the APK from Downloads, accept the "Unknown developer" warning, install, launch.
3. **Auto-discover** — on the same WiFi as the laptop running `docker-compose up`, launch the app. It should show "Connected" within a few seconds. If not, use the gear icon → enter `http://<laptop-ip>:8000` → **Test Connection**.
4. **Golden shot** — Field Chat → camera icon → photograph any leaf → ask "what is wrong with this plant?" → the diagnosis should stream in within ~60–90 seconds on CPU.
5. **Knowledge Packs screen** — confirm the Casamance Agriculture pack is listed and queryable.
6. **Offline test** — disconnect the **laptop** from the internet (keep the LAN up). Repeat step 4. Diagnosis should still work.

If any step fails, see the corresponding section above.
