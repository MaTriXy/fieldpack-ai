# FieldPack AI — Offline Expert Knowledge for Humanitarian Field Workers

**Gemma 4 agents curate mission-specific Knowledge Packs that an edge model serves without internet**

*Track: Global Resilience*

<!-- Cover image: relative path works on GitHub, raw URL works on Kaggle -->
![FieldPack AI Cover](https://raw.githubusercontent.com/orkohol/fieldpack-ai/master/docs/images/kaggle-cover.png)

**▶ Watch the 3-minute demo video:** [https://youtu.be/y9FSAkYpFII](https://youtu.be/y9FSAkYpFII)

---

## The Problem

A farmer holds out a cassava cutting — curled leaves, yellowing mosaic pattern spreading across the surface. He looks at Amina Diallo and waits. Amina is an agronomist with Action Against Hunger, deployed to the Casamance region of Senegal. She has seen mosaic disease before. She knows the broad strokes. But which resistant variety is available through the extension service in Ziguinchor? What is the right intercropping strategy for this soil, this season? She cannot remember every protocol from every training.

Normally, she would search for an answer. But there is no signal here. The nearest reliable internet is hours away by unpaved road.

Cassava feeds 800 million people across Sub-Saharan Africa. In this region, farmers are losing up to half their harvest to disease. Amina is one of 3.7 billion people on Earth for whom "just Google it" is not an option.

The people who need AI most are the ones furthest from the cloud.

## The Insight

Offline AI already exists. You can run a model on a phone. But a general model without domain knowledge is like a doctor deployed to a malaria zone with a medical degree but no information about malaria — the intelligence is there, the knowledge is not.

**The value of offline AI is not the model. It is the knowledge the model carries.**

FieldPack AI solves this with a two-phase architecture: powerful cloud models curate mission-specific knowledge *before* deployment, package it into a portable database, and hand it off to an edge model that serves it *without internet*. We call these portable databases **Knowledge Packs** — and they can be built for any mission, any domain, anywhere.

## Architecture

![FieldPack AI Architecture — Two-phase system: cloud agents curate Knowledge Packs, edge model serves them offline](https://raw.githubusercontent.com/orkohol/fieldpack-ai/master/docs/images/architecture-diagram.png)

FieldPack uses the Gemma 4 model family across three tiers — each for what it does best:

**Phase 1 — Online: "Mission Briefing"** (Cloud, one-time per mission)

Before Amina leaves for the field, she describes her mission through a conversational interface — region, crops, known threats. The system launches a multi-stage pipeline via Google AI Studio:

1. **Source Gathering** — concurrent fetches pull HTML pages, CGIAR PDFs, and Open-Meteo climate data for her region
2. **Knowledge Extraction** (Gemma 4 26B MoE) — the LLM extracts structured knowledge from raw sources: diseases, treatments, pests, varieties, climate patterns
3. **Gap Analysis** (Gemma 4 31B) — identifies what's missing and fills gaps with targeted searches
4. **Compilation & Pack Building** (Gemma 4 31B) — deduplicates, validates, generates parent/child search chunks, and downloads reference images

The result: a ~200 MB portable Knowledge Pack containing structured data (SQLite), semantic search vectors (ChromaDB with MiniLM-L6-v2 embeddings), and reference images — everything Amina needs for her specific mission. The architecture is domain-agnostic: agriculture today, disaster medical triage or rural literacy tomorrow. The Knowledge Pack is the variable — the platform is the constant.

**Phase 2 — Offline: "Field Assistant"** (Edge, runs daily via Ollama)

In the field, Amina's laptop runs **Gemma 4 E2B** (5.1B total parameters, Q4_K_M quantization) through **Ollama** — the open-source inference runtime that makes running quantized models on consumer hardware practical. One-line install. REST API. Cross-platform. No GPU required. Ollama is what makes FieldPack's edge deployment possible, turning any laptop into an AI inference server.

Her phone connects over a local WiFi hotspot. **There is no internet. There is no mobile data. The hotspot connects only Amina's phone to her laptop.** The edge model navigates her Knowledge Pack through an agentic RAG pipeline — not a fixed retrieval chain, but a LangGraph state machine that decides at each step whether it has enough context or needs to refine its search:

![Agentic RAG Pipeline — classify, route, search, rerank, generate with retry loop](https://raw.githubusercontent.com/orkohol/fieldpack-ai/master/docs/images/pipeline-diagram.png)

The pipeline loops up to three times with expanded queries. Two-tier reranking (fast heuristic first, LLM rerank on retry) keeps latency low while ensuring quality. This is what makes a 5.1B parameter model punch above its weight: it is not guessing from general training — it is navigating curated, mission-specific knowledge.

| Model | Role | Why |
|-------|------|-----|
| Gemma 4 31B Dense | Gap Analysis + Compilation | Highest reasoning for validation and structuring |
| Gemma 4 26B MoE | Knowledge Extraction | Best quality-per-compute for batch extraction |
| Gemma 4 E2B | Field Assistant (offline, via Ollama) | Fits on a laptop CPU, multimodal, agentic |

## The Demo — Amina's Mission

Amina arrives in Casamance. She sets up her laptop in a community center — no router, no SIM card, no satellite link. Farmers begin arriving with samples of diseased crops.

**The hero moment takes five seconds.**

<p align="center">
  <img src="https://raw.githubusercontent.com/orkohol/fieldpack-ai/master/frontend/qa-screenshots/03-field-chat.png" alt="FieldPack AI hero shot — plant photo uploaded, Cassava Mosaic Disease diagnosed with 92% confidence" width="300">
</p>

A farmer hands her a cassava cutting with curled, yellowing leaves. She photographs it with her phone. The app streams a response word by word:

> *"This appears to be Cassava Mosaic Disease (CMD), likely caused by the African cassava mosaic virus. Severity: moderate — the mosaic pattern covers approximately 40% of visible leaf area."*

Then the treatment — specific to what is available in Casamance:

> *"Immediate action: Remove and burn this plant and any within 2 meters showing similar symptoms to prevent whitefly transmission. For replanting, use CMD-resistant varieties — TME 419 or IITA-TMS-IBA30572 are available through the Senegalese agricultural extension service in Ziguinchor. Intercrop with maize to reduce whitefly density. Apply neem oil extract as a natural deterrent — neem trees are abundant in this region."*

This is not a generic chatbot answer. Every detail — the variety names, the extension service location, the intercropping recommendation, the locally available neem — was curated for this exact mission by cloud agents that researched Casamance agriculture before Amina ever boarded a plane.

Amina logs the observation: location, severity, photo, diagnosis. When she eventually reaches connectivity, the data syncs, building a regional disease surveillance map that informs future Knowledge Packs — a compound flywheel where offline use generates data that improves future missions.

## Try It Yourself — Reproduce Amina's Demo

Two ways to experience FieldPack AI, in order of realism:

**1. Docker (laptop only — 60 seconds)**

```bash
git clone https://github.com/orkohol/fieldpack-ai.git
cd fieldpack-ai && docker-compose up
# Open http://localhost:5173
```

First run pulls Gemma 4 E2B (~5 GB, ~5 min). Requires Docker Desktop, ~8 GB RAM. This gives you the full agentic RAG pipeline running against real Ollama.

**2. Phone + Laptop (the real product)**

The way FieldPack is designed to run: laptop as the AI server, phone as a thin client over local WiFi — no internet.

- Laptop: `docker-compose up` (as above)
- Phone: install [fieldpack-ai-v1.0.0-debug.apk](https://drive.google.com/file/d/1fDdvSxdMTf0a_rqwmO2idPo_R_9eCQLu/view?usp=sharing) *(9.7 MB · SHA256 `831984eb9fa29bd585ddef60c409e87bdce01e4a24d038f26f68932ec6f525df` · [VirusTotal](https://www.virustotal.com/gui/file/831984eb9fa29bd585ddef60c409e87bdce01e4a24d038f26f68932ec6f525df/detection))*
- Connect both devices to the same WiFi (or turn on the laptop's mobile hotspot)
- Launch the app — it auto-scans for the backend on the local network

Full step-by-step instructions: [README — Run on Your Phone](https://github.com/orkohol/fieldpack-ai#run-on-your-phone-the-real-demo).

## Technical Depth

<p align="center">
  <img src="https://raw.githubusercontent.com/orkohol/fieldpack-ai/master/frontend/qa-screenshots/08-agent-progress.png" alt="Live pipeline — Research Agents gathering data from PlantVillage, IITA, climate sources" width="300">
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/orkohol/fieldpack-ai/master/frontend/qa-screenshots/05-diagnosis-card.png" alt="Full diagnosis result card — Cassava Mosaic Disease, 92% confidence, symptoms matched" width="300">
</p>

FieldPack is not a prototype. It ships with 581 automated tests across 10,765 lines of test code. The entire system runs end-to-end — backend, frontend, Android APK, and demo mode.

**Agentic RAG, not retrieval.** The pipeline uses LangGraph to orchestrate a non-deterministic search loop. Each query is classified, routed to the appropriate knowledge domain, and searched. If results are insufficient, the system expands the query and retries — up to three iterations.

**Parent/child chunking.** Documents are split into small child chunks for precise search matching, but linked to larger parent chunks that provide full context. The model searches children, reads parents — combining precision with richness.

**WebSocket streaming.** The frontend receives token-by-token responses over WebSocket, rendering progressively. Status events keep the user informed. On a laptop CPU, first tokens arrive in under 3 seconds.

**Thin-client architecture.** The phone is a camera and a UI. All AI runs on the laptop. A $50 Android device is sufficient — it just needs a browser and a camera. The laptop handles Ollama inference, vector search, and SQLite queries over the local hotspot.

**The stack:** FastAPI, LangGraph, ChromaDB, sentence-transformers (MiniLM-L6-v2), React, Tailwind, Capacitor (Android APK). Every layer of the stack reinforces the Google ecosystem: Gemma 4 models, Google AI Studio for cloud inference, Google Stitch for UI design — all running on Ollama at the edge.

## Impact

**Cost of deployment:** one laptop, one phone, one Knowledge Pack. No GPU. No server. No subscription. No internet.

3.7 billion people lack reliable internet. Among them are the humanitarian workers, farmers, teachers, and health workers who hold communities together. They make decisions every day with incomplete information — and people suffer for the gaps.

FieldPack AI does not bring these people to the cloud. It brings the cloud's knowledge to them — curated for their specific mission, packaged to travel, and served by a model small enough to run on hardware they already own.

Somewhere in Casamance, Amina is still answering questions. The laptop is still running. The farmers are still coming. And the internet is still hours away — but it no longer matters.
