# FieldPack AI — Technical Framework

> Companion to [PHILOSOPHY.md](./PHILOSOPHY.md). This document covers every technology decision, the reasoning behind it, and how the pieces connect.

---

## Table of Contents

1. [Technology Decisions Summary](#1-technology-decisions-summary)
2. [Decision Details & Rationale](#2-decision-details--rationale)
3. [System Architecture — High Level](#3-system-architecture--high-level)
4. [Phase 1: Online Knowledge Gathering Pipeline](#4-phase-1-online-knowledge-gathering-pipeline)
5. [Phase 2: Offline Field Assistant Pipeline](#5-phase-2-offline-field-assistant-pipeline)
6. [The Knowledge Pack Specification](#6-the-knowledge-pack-specification)
7. [The Agentic RAG Design — The Core Innovation](#7-the-agentic-rag-design--the-core-innovation)
8. [Frontend Architecture](#8-frontend-architecture)
9. [Local Development Setup](#9-local-development-setup)
10. [Project File Structure](#10-project-file-structure)
11. [Risk Register & Fallbacks](#11-risk-register--fallbacks)

---

## 1. Technology Decisions Summary

| # | Decision | Choice | Runner-Up | Key Reason |
|---|----------|--------|-----------|------------|
| 1 | Online inference platform | **Google AI Studio (free tier)** | Kaggle Notebooks | Free Gemma 4 31B/26B API. Google product in a Google hackathon. |
| 2 | Agent orchestration | **LangGraph** | Raw Python + function calling | Native parallel branching, state graphs, non-deterministic agentic RAG loops. Industry standard. |
| 3 | Vector store (offline) | **ChromaDB (persistent mode)** | FAISS | Metadata filtering on entities. SQLite backend = portable. Embedded mode = no server. |
| 4 | Structured DB | **SQLite** | — | Universal, single file, runs everywhere. |
| 5 | Embedding model | **Google text-embedding (online) + all-MiniLM-L6-v2 (offline)** | Gemma E2B hidden states | Pre-compute high-quality embeddings online. Ship tiny model for runtime queries offline. |
| 6 | Edge inference runtime | **Ollama** | llama.cpp server | One-line install, REST API, easy demo. Ships Gemma 4 E2B GGUF. |
| 7 | App UI | **Google Stitch → React/Tailwind export** | Gradio | Wow-factor UI. Google product optics. Professional look beats "demo widget." |
| 8 | Image processing | **Gemma E2B native vision (primary)** | CLIP + similarity hybrid | E2B handles images natively. Simpler pipeline. Fallback to hybrid if quality is insufficient. |
| 9 | Knowledge Pack format | **SQLite + ChromaDB + images folder, zipped** | Single SQLite with BLOBs | Clean, inspectable, judge-friendly structure. Human-readable manifest. |
| 10 | Development environment | **Local dev, Google AI Studio API for cloud calls** | Pure Kaggle notebooks | Best developer experience. No GPU needed — all LLM calls are API-based or Ollama CPU. |

---

## 2. Decision Details & Rationale

### 2.1 Google AI Studio (Free Tier)

**What**: Google's free API access to Gemma 4 31B and 26B models via `ai.google.dev`.

**Rate Limits (Free Tier)**:
- 15,000 tokens/minute
- 30 requests/minute
- 14,400 requests/day

**Why This Works**: Phase 1 (knowledge gathering) is a one-time batch operation per Knowledge Pack. We are not serving live traffic. A single pack creation session might use 200-500 API calls over 30-60 minutes — well within free tier limits.

**Integration**: LangChain's `ChatGoogle` class connects to Google AI Studio natively. This gives us LangGraph ↔ AI Studio ↔ Gemma 4 with minimal glue code.

**Strategic Value**: Using Google AI Studio (a Google product) to call Gemma 4 (a Google model) in a Google-sponsored hackathon on Kaggle (a Google platform). Every layer of our stack reinforces Google's ecosystem. Judges notice this.

**References**:
- [Google AI Studio Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)

### 2.2 LangGraph

**What**: LangChain's graph-based framework for building stateful, multi-actor LLM applications. v1.0 stable since October 2025.

**Why LangGraph Over Raw Python**:

The deciding factor is our **agentic RAG design**. The offline Field Assistant does not follow a fixed retrieval pipeline. Instead:

1. User asks a question (text or image)
2. The LLM analyzes the query and decides: *Do I need SQL data? Vector search? Both? An image comparison?*
3. It calls one or more tools
4. It evaluates the results: *Is this enough to answer? Do I need to refine the query? Should I search again with different parameters?*
5. It loops until it has sufficient context, then generates the answer

This is a **state graph with conditional edges and cycles** — exactly what LangGraph is built for. In raw Python, we would be reimplementing LangGraph's core abstractions poorly.

Additionally, LangGraph gives us:
- **Parallel branching** for Phase 1 research agents (3+ agents running concurrently)
- **State persistence** so we can save/resume agent sessions
- **Checkpointing** for debugging and demo replay
- **Native tool binding** with Gemma's function calling format

**What LangGraph Does NOT Do**: LangGraph does not hide Gemma's capabilities. The function calling, tool definitions, and prompt engineering are still ours. LangGraph is the orchestration layer — the wiring between components — not the intelligence. Judges will see Gemma's native function calling in action; LangGraph just makes the coordination reliable.

**References**:
- [LangGraph Official](https://www.langchain.com/langgraph)
- [Google's own LangGraph + Gemma tutorial](https://ai.google.dev/gemini-api/docs/langgraph-example)
- [LangGraph on Google Cloud](https://docs.cloud.google.com/agent-builder/agent-engine/develop/langgraph)

### 2.3 ChromaDB (Persistent Mode)

**What**: Open-source vector database. Embedded mode uses SQLite as its backend. Persistent mode writes to a local directory — portable, no server process needed.

**Why ChromaDB Over FAISS**:

Our agentic RAG is non-deterministic. The LLM decides at each step what to retrieve and how. This requires:

| Capability | FAISS | ChromaDB |
|------------|-------|----------|
| Vector similarity search | Yes | Yes |
| Metadata filtering (`WHERE crop = 'cassava' AND severity > 3`) | No (manual post-filtering) | **Native** |
| Combined vector + metadata queries | No | **Native** |
| Persistent storage (ship as files) | Manual serialization | **Built-in** (just copy the directory) |
| Embedded mode (no server) | Yes | **Yes** |
| LangChain/LangGraph integration | Yes | **Yes** (first-class) |
| Collection management (separate diseases, treatments, etc.) | Manual | **Native collections** |

The metadata filtering is critical. When the LLM calls `search_knowledge(query="leaf curl treatment", crop="cassava", type="treatment")`, we need to filter by entity metadata AND search by semantic similarity simultaneously. ChromaDB does this in a single query.

**Storage Structure** (what ships in the Knowledge Pack):
```
chroma_db/
├── chroma.sqlite3          (metadata + FTS index)
└── {collection_uuid}/      (vector segments, one per collection)
    ├── data_level0.bin
    ├── header.bin
    ├── index_metadata.pickle
    └── length.bin
```

This entire directory is portable. Copy it → load it on another machine → it works.

**References**:
- [ChromaDB Storage Layout](https://cookbook.chromadb.dev/core/storage-layout/)
- [ChromaDB + SQLite Integration](https://medium.com/@dassandipan9080/enhancing-retrieval-augmented-generation-with-chromadb-and-sqlite-c499109f8082)

### 2.4 SQLite

**What**: The world's most deployed database. Single-file, zero-configuration, serverless.

**Role**: Stores structured, relational data that the agentic RAG queries via SQL:
- Crops table (name, family, growing season, water needs, region suitability)
- Diseases table (name, type, symptoms, visual markers, severity, affected crops)
- Treatments table (disease FK, method, materials needed, difficulty, organic options)
- Climate data table (region, season, rainfall, drought risk)
- Image references table (image path, disease FK, description, visual features)

**Why Separate from ChromaDB**: SQLite handles structured, relational queries (JOINs, aggregations, exact lookups). ChromaDB handles semantic, fuzzy queries. The agentic RAG decides when to use which — or both.

### 2.5 Embedding Model Strategy

**Two-stage approach**:

**Online (Phase 1)**: Use Google's text-embedding model via AI Studio API to generate high-quality embeddings for all knowledge chunks. These embeddings are stored in ChromaDB and shipped in the Knowledge Pack.

**Offline (Phase 2)**: Ship `all-MiniLM-L6-v2` (~80MB) for embedding the user's runtime queries. This model:
- Runs on CPU instantly (< 50ms per query)
- Uses 384-dimensional embeddings (small, efficient)
- Is the most battle-tested sentence embedding model in production
- Adds minimal footprint to the Knowledge Pack

**Why not use the same model online and offline?** Google's embedding model is higher quality but requires API access. MiniLM is slightly lower quality but runs anywhere. The mismatch is manageable because:
- We can normalize embeddings to a shared space
- Alternatively, we pre-compute with MiniLM online too (simpler, guaranteed compatibility)
- **Decision point**: Start with MiniLM for both (guaranteed compatibility). Upgrade to Google embeddings online + MiniLM offline if we need higher retrieval quality.

### 2.6 Ollama

**What**: One-line install local LLM server. REST API compatible with OpenAI format.

**Model**: Gemma 4 E2B IT (instruction-tuned), GGUF quantized.

**Hardware Requirements**:
| Quantization | RAM Needed | Speed (CPU) | Quality |
|-------------|------------|-------------|---------|
| Q8 | ~8 GB | 5-8 tok/s | Near-original |
| Q4_K_M | ~5 GB | 8-12 tok/s | Slight quality loss |

**Recommendation**: Start with Q8 if your machine has 16GB+ RAM. Drop to Q4 if memory is tight.

**Multimodal**: Ollama supports Gemma 4 E2B's vision capabilities. Image input works through the REST API.

**LangGraph Integration**: LangGraph connects to Ollama via `ChatOllama` class. Same graph definition works for both online (AI Studio) and offline (Ollama) — we just swap the LLM provider.

### 2.7 Google Stitch → React/Tailwind

**What**: Google Labs AI design tool. Generates UI from natural language prompts. Exports React/JSX + Tailwind CSS.

**Why Stitch for a Hackathon**:
- The UI is where judges FIRST look. A professional React app looks 10x better than Gradio/Streamlit.
- Stitch generates the visual layer — we wire it to our backend.
- It is a Google Labs product. In a Google hackathon. The optics are intentional.
- Free tier: 350 generations/month. More than enough.
- New "vibe design" infinite canvas (March 2026) creates stunning, modern interfaces.

**What Stitch Generates vs. What We Build**:
| Stitch Generates | We Build |
|-----------------|----------|
| Visual layout (React/JSX) | State management (React hooks) |
| Tailwind styling | API integration (fetch to FastAPI) |
| Component structure | WebSocket for streaming responses |
| Responsive design scaffolding | Image upload handling |
| — | Chat interface logic |
| — | Offline/online mode toggle |

**Architecture**:
```
Stitch → React/Tailwind Export → Developer Integration → FastAPI Backend → LangGraph → Ollama/AI Studio
```

**The WOW Factor Plan**:
1. Design in Stitch: "A field assistant app for humanitarian workers. Dark mode. Chat interface on the left. Knowledge pack info panel on the right. Image upload button. Offline indicator badge. Map showing the deployment region."
2. Export React code
3. Wire to our FastAPI backend
4. The result looks like a polished product, not a hackathon prototype

**References**:
- [Stitch](https://stitch.withgoogle.com/)
- [Stitch Complete Guide 2026](https://www.nxcode.io/resources/news/google-stitch-complete-guide-vibe-design-2026)
- [Stitch Review](https://www.index.dev/blog/google-stitch-ai-review-for-ui-designers)

### 2.8 Image Processing — Gemma E2B Vision First

**Primary approach**: Feed plant photos directly to Gemma E2B. The model's native multimodal understanding handles image analysis. Combined with RAG context (disease descriptions, visual markers from the DB), it should identify common crop diseases.

**Why E2B vision first**:
- No extra model to ship (simpler Knowledge Pack)
- E2B handles native multimodal input — sufficient for plant disease matching when combined with strong RAG context
- The function calling flow: E2B sees image → calls `search_diseases(visual_description="leaf curl, yellow mosaic pattern")` → gets candidate diseases from DB → cross-references → provides diagnosis

**Fallback (if E2B vision is insufficient)**:
- Add CLIP model (~300MB) for image embedding
- Pre-compute CLIP embeddings for all reference disease images during Phase 1
- At runtime: CLIP embeds the user's photo → cosine similarity against reference embeddings → top matches feed into E2B as context
- This is more accurate but adds complexity and model size

**Decision**: Start with E2B vision only. Test with real plant disease images. Switch to hybrid only if identification quality is unacceptable.

### 2.9 Knowledge Pack Format

**Structure**:
```
fieldpack_casamance_agriculture_v1/
│
├── manifest.json                 # Pack metadata
│   {
│     "name": "Casamance Agriculture Pack",
│     "version": "1.0",
│     "region": "Casamance, Senegal",
│     "crops": ["cassava", "rice", "maize", "groundnut", "tomato"],
│     "diseases_count": 25,
│     "treatments_count": 40,
│     "images_count": 150,
│     "created_by": "FieldPack AI v1.0",
│     "created_at": "2026-04-15T10:00:00Z",
│     "gemma_models_used": ["gemma-4-31b-it", "gemma-4-26b-a4b-it"],
│     "embedding_model": "all-MiniLM-L6-v2",
│     "embedding_dimensions": 384
│   }
│
├── knowledge.db                  # SQLite — structured relational data
│   Tables:
│   - crops (id, name, family, season, water_needs, region_notes)
│   - diseases (id, name, type, symptoms, visual_markers, severity_scale, crop_ids)
│   - treatments (id, disease_id, method, materials, difficulty, organic_option, local_availability)
│   - climate (id, region, season, rainfall_mm, drought_risk, notes)
│   - image_refs (id, path, disease_id, crop_id, description, type)
│
├── chroma_db/                    # ChromaDB — vector embeddings + metadata
│   └── chroma.sqlite3
│   Collections:
│   - disease_knowledge (disease descriptions, symptom details, chunked text)
│   - treatment_guides (detailed treatment procedures, step-by-step)
│   - farming_practices (drought strategies, soil management, planting guides)
│   - regional_context (climate info, local resources, agricultural calendar)
│
├── images/                       # Reference photos, organized by category
│   ├── diseases/
│   │   ├── cassava_mosaic/
│   │   │   ├── early_stage_01.jpg
│   │   │   ├── advanced_stage_01.jpg
│   │   │   └── leaf_detail_01.jpg
│   │   ├── cassava_brown_streak/
│   │   ├── rice_blast/
│   │   └── ... (more diseases)
│   ├── healthy/
│   │   ├── cassava_healthy_leaf.jpg
│   │   ├── rice_healthy_plant.jpg
│   │   └── ...
│   └── treatments/
│       ├── neem_oil_preparation.jpg
│       └── ...
│
├── README.md                     # Human-readable pack description (judge-friendly)
│   "This Knowledge Pack was generated by FieldPack AI for a humanitarian
│    agronomist deploying to the Casamance region of Senegal..."
│
└── SOURCES.md                    # Data provenance (where the knowledge came from)
    "All data was gathered and validated by Gemma 4 31B/26B agents from
     the following sources: FAO, IITA, PlantVillage, ..."
```

**Distribution**: Zipped as a single `.fieldpack` file (renamed `.zip`). The extension is a branding touch — judges see "this is a format they invented."

### 2.10 Local Development Environment

**Requirements**:
- Windows 10 (confirmed from your system)
- Python 3.10+ (for LangGraph, ChromaDB, FastAPI)
- Node.js 18+ (for React frontend from Stitch)
- Ollama (for local Gemma E2B inference)
- 8GB+ RAM (for Ollama running E2B Q4_K_M)
- No GPU required

**How Each Component Runs Locally**:

| Component | How It Runs | Port/Access |
|-----------|-------------|-------------|
| LangGraph agents (Phase 1) | Python process, calls Google AI Studio API over internet | — |
| LangGraph agents (Phase 2) | Python process, calls Ollama over localhost | — |
| Ollama (E2B) | Background service | `http://localhost:11434` |
| ChromaDB | Embedded in Python process (no separate service) | — |
| SQLite | Embedded in Python process | — |
| FastAPI backend | Python uvicorn server | `http://localhost:8000` |
| React frontend | Node.js dev server | `http://localhost:3000` |
| MiniLM embeddings | Loaded in Python process (~200MB RAM) | — |

**For the Kaggle submission**: We will also prepare a Kaggle notebook that demonstrates the Phase 1 pipeline. This notebook calls Google AI Studio API and produces a Knowledge Pack. The Phase 2 demo runs from the video, showing the local offline app.

---

## 3. System Architecture — High Level

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: ONLINE (Google AI Studio)                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                   LangGraph Orchestrator                  │       │
│  │                                                          │       │
│  │  ┌─────────────┐    ┌──────────────────────────────┐     │       │
│  │  │   Mission    │    │    Parallel Research Agents    │     │       │
│  │  │   Planner    │───▶│  ┌────────┐ ┌────────┐ ┌───┐ │     │       │
│  │  │  (31B)       │    │  │ Crop   │ │Disease │ │Cli│ │     │       │
│  │  └─────────────┘    │  │ Agent  │ │ Agent  │ │mat│ │     │       │
│  │                      │  │ (26B)  │ │ (26B)  │ │e  │ │     │       │
│  │                      │  └───┬────┘ └───┬────┘ └─┬─┘ │     │       │
│  │                      └─────┼────────┼──────┼───┘     │       │
│  │                            │        │      │          │       │
│  │                      ┌─────▼────────▼──────▼───┐      │       │
│  │                      │   Knowledge Compiler     │      │       │
│  │                      │   (31B)                  │      │       │
│  │                      │   - Validates data       │      │       │
│  │                      │   - Structures into DB   │      │       │
│  │                      │   - Generates embeddings │      │       │
│  │                      │   - Organizes images     │      │       │
│  │                      └──────────┬───────────────┘      │       │
│  │                                 │                      │       │
│  └─────────────────────────────────┼──────────────────────┘       │
│                                    ▼                               │
│                         ┌──────────────────────┐                   │
│                         │   KNOWLEDGE PACK      │                   │
│                         │   .fieldpack file     │                   │
│                         └──────────┬───────────┘                   │
└────────────────────────────────────┼───────────────────────────────┘
                                     │ Download
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: OFFLINE (Local Device)                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │              React Frontend (Stitch-designed)             │       │
│  │  ┌────────────────┐ ┌──────────────┐ ┌──────────────┐   │       │
│  │  │  Chat Interface │ │ Image Upload │ │ Pack Info    │   │       │
│  │  └───────┬────────┘ └──────┬───────┘ └──────────────┘   │       │
│  └──────────┼─────────────────┼─────────────────────────────┘       │
│             │ HTTP/WebSocket  │                                      │
│             ▼                 ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                  FastAPI Backend                          │       │
│  │                       │                                  │       │
│  │  ┌────────────────────▼──────────────────────────┐       │       │
│  │  │          LangGraph Agentic RAG                │       │       │
│  │  │                                                │       │       │
│  │  │  ┌──────────┐   Conditional    ┌──────────┐   │       │       │
│  │  │  │  Gemma   │     Edges        │  Tool    │   │       │       │
│  │  │  │  E2B     │◄──────────────▶ │  Calls   │   │       │       │
│  │  │  │ (Ollama) │                  │          │   │       │       │
│  │  │  └──────────┘                  │ ┌──────┐ │   │       │       │
│  │  │                                │ │Chroma│ │   │       │       │
│  │  │                                │ │  DB  │ │   │       │       │
│  │  │                                │ ├──────┤ │   │       │       │
│  │  │                                │ │SQLite│ │   │       │       │
│  │  │                                │ ├──────┤ │   │       │       │
│  │  │                                │ │Image │ │   │       │       │
│  │  │                                │ │Match │ │   │       │       │
│  │  │                                │ └──────┘ │   │       │       │
│  │  └────────────────────────────────────────────┘  │       │       │
│  └──────────────────────────────────────────────────┘       │       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Phase 1: Online Knowledge Gathering Pipeline

### LangGraph State Graph

```
                    ┌─────────────┐
                    │    START     │
                    │  User Input  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Mission    │
                    │   Planner    │
                    │   (31B)      │
                    └──────┬──────┘
                           │ Outputs: research_plan
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼───┐ ┌─────▼────┐ ┌────▼──────┐
       │  Crop     │ │ Disease   │ │ Climate    │
       │  Research │ │ Research  │ │ Research   │
       │  Agent    │ │ Agent     │ │ Agent      │
       │  (26B)    │ │ (26B)     │ │ (26B)      │
       └──────┬───┘ └─────┬────┘ └────┬──────┘
              │            │            │
              └────────────┼────────────┘
                           │ All complete
                    ┌──────▼──────┐
                    │  Knowledge   │
                    │  Compiler    │
                    │  (31B)       │
                    │              │
                    │ - Validate   │
                    │ - Dedupe     │
                    │ - Structure  │
                    │ - Embed      │
                    │ - Organize   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Pack        │
                    │  Builder     │
                    │              │
                    │ - Write DB   │
                    │ - Save Chroma│
                    │ - Copy imgs  │
                    │ - Manifest   │
                    │ - Zip        │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │     END      │
                    │ .fieldpack   │
                    └─────────────┘
```

### Research Agent Tools (Function Calling)

Each research agent (26B MoE) has access to these tools via native Gemma 4 function calling:

```python
# Tools available to research agents
tools = [
    {
        "name": "web_search",
        "description": "Search the web for information about a specific agricultural topic",
        "parameters": {
            "query": "string - the search query",
            "source_preference": "string - prefer 'academic', 'fao', 'extension_service', or 'general'"
        }
    },
    {
        "name": "fetch_page",
        "description": "Fetch and extract content from a specific URL",
        "parameters": {
            "url": "string - the URL to fetch",
            "extract": "string - what to extract: 'full_text', 'tables', 'images'"
        }
    },
    {
        "name": "save_finding",
        "description": "Save a validated piece of knowledge to the research results",
        "parameters": {
            "category": "string - 'crop', 'disease', 'treatment', 'climate', 'practice'",
            "title": "string",
            "content": "string - the knowledge content",
            "source": "string - where this came from",
            "confidence": "number - 0.0 to 1.0",
            "metadata": "object - additional structured fields"
        }
    },
    {
        "name": "save_image",
        "description": "Save a reference image for the knowledge pack",
        "parameters": {
            "url": "string - image URL to download",
            "category": "string - 'disease', 'healthy', 'treatment'",
            "description": "string - what the image shows",
            "related_entity": "string - which crop/disease this relates to"
        }
    }
]
```

### Knowledge Compiler Process

The Knowledge Compiler (31B) receives all raw findings and:

1. **Deduplicates**: Multiple agents may find the same information
2. **Validates**: Cross-references facts across sources, flags contradictions
3. **Structures**: Creates SQLite table entries from unstructured findings
4. **Enriches**: Generates visual marker descriptions for diseases (helps E2B identify from photos)
5. **Chunks**: Splits long texts into retrieval-optimized chunks (300-500 tokens each)
6. **Embeds**: Generates embeddings for all chunks using MiniLM
7. **Indexes**: Loads embeddings + metadata into ChromaDB collections
8. **Organizes images**: Downloads, renames, organizes reference images by category

---

## 5. Phase 2: Offline Field Assistant Pipeline

### The Agentic RAG Graph (LangGraph)

This is the core innovation. See [Section 7](#7-the-agentic-rag-design--the-core-innovation) for the complete design.

### Ollama Integration

```python
# The E2B model runs locally via Ollama
# LangGraph connects via ChatOllama

from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="gemma4-e2b:q4_K_M",
    base_url="http://localhost:11434",
    temperature=0.3,
    # Enable multimodal
    # Enable function calling via format parameter
)
```

### Tool Definitions for Offline Agent

```python
# Tools the E2B agent can call via native function calling
offline_tools = [
    {
        "name": "search_knowledge",
        "description": "Search the knowledge base using semantic similarity. Use when user asks an open-ended question.",
        "parameters": {
            "query": "string - natural language search query",
            "collection": "string - 'disease_knowledge', 'treatment_guides', 'farming_practices', 'regional_context'",
            "filters": "object - optional metadata filters like {crop: 'cassava', type: 'treatment'}",
            "top_k": "integer - number of results (default 5)"
        }
    },
    {
        "name": "query_database",
        "description": "Run a structured query against the knowledge database. Use for specific factual lookups.",
        "parameters": {
            "table": "string - 'crops', 'diseases', 'treatments', 'climate', 'image_refs'",
            "conditions": "object - filter conditions like {name: 'cassava', region: 'casamance'}",
            "join_with": "string - optional related table to join"
        }
    },
    {
        "name": "identify_plant_issue",
        "description": "Analyze an uploaded plant photo to identify potential diseases or issues.",
        "parameters": {
            "image_path": "string - path to the uploaded image",
            "crop_hint": "string - optional, if user mentioned which crop this is",
            "compare_with": "array - optional list of disease IDs to compare against"
        }
    },
    {
        "name": "get_treatment_protocol",
        "description": "Get the full treatment protocol for a specific disease.",
        "parameters": {
            "disease_id": "integer",
            "prefer_organic": "boolean - default true",
            "local_materials_only": "boolean - default true"
        }
    },
    {
        "name": "log_field_observation",
        "description": "Log a field observation for later sync when back online.",
        "parameters": {
            "type": "string - 'disease_sighting', 'crop_condition', 'treatment_applied', 'note'",
            "location": "string - description or GPS if available",
            "details": "string",
            "image_path": "string - optional"
        }
    }
]
```

---

## 6. The Knowledge Pack Specification

### Manifest Schema (manifest.json)

```json
{
    "$schema": "fieldpack-manifest-v1",
    "name": "Casamance Agriculture Pack",
    "description": "Agricultural knowledge for humanitarian workers assisting smallholder farmers in the Casamance region of Senegal, focusing on cassava, rice, maize, groundnut, and tomato crops.",
    "version": "1.0.0",
    "region": {
        "name": "Casamance",
        "country": "Senegal",
        "coordinates": {"lat": 12.55, "lon": -15.5},
        "climate_zone": "tropical_savanna"
    },
    "domain": "agriculture",
    "crops": ["cassava", "rice", "maize", "groundnut", "tomato"],
    "statistics": {
        "diseases_count": 25,
        "treatments_count": 40,
        "farming_practices_count": 15,
        "text_chunks": 500,
        "images_count": 150,
        "total_size_mb": 350
    },
    "models_used": {
        "research_agents": "gemma-4-26b-a4b-it",
        "knowledge_compiler": "gemma-4-31b-it",
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_dimensions": 384
    },
    "recommended_edge_model": "gemma-4-e2b-it",
    "created_at": "2026-04-15T10:00:00Z",
    "sources": ["FAO", "IITA", "PlantVillage", "Senegalese Ministry of Agriculture"],
    "license": "CC-BY-SA-4.0"
}
```

### SQLite Schema (knowledge.db)

```sql
-- Crops
CREATE TABLE crops (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    scientific_name TEXT,
    family TEXT,
    growing_season TEXT,
    water_needs_mm_per_week REAL,
    drought_tolerance TEXT CHECK(drought_tolerance IN ('low', 'medium', 'high')),
    region_suitability TEXT,
    planting_notes TEXT,
    harvest_notes TEXT
);

-- Diseases
CREATE TABLE diseases (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    common_names TEXT,           -- JSON array of local/alternate names
    type TEXT CHECK(type IN ('viral', 'bacterial', 'fungal', 'pest', 'nutritional', 'environmental')),
    symptoms_text TEXT NOT NULL,
    visual_markers TEXT NOT NULL, -- detailed visual description for AI matching
    severity_scale TEXT CHECK(severity_scale IN ('low', 'medium', 'high', 'critical')),
    spread_mechanism TEXT,
    prevention_notes TEXT
);

-- Crop-Disease relationship (many-to-many)
CREATE TABLE crop_diseases (
    crop_id INTEGER REFERENCES crops(id),
    disease_id INTEGER REFERENCES diseases(id),
    susceptibility TEXT CHECK(susceptibility IN ('low', 'medium', 'high')),
    PRIMARY KEY (crop_id, disease_id)
);

-- Treatments
CREATE TABLE treatments (
    id INTEGER PRIMARY KEY,
    disease_id INTEGER REFERENCES diseases(id),
    method TEXT NOT NULL,
    description TEXT NOT NULL,
    materials_needed TEXT,       -- JSON array
    difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')),
    is_organic BOOLEAN DEFAULT 1,
    local_availability TEXT,     -- availability of materials in the region
    effectiveness TEXT CHECK(effectiveness IN ('low', 'medium', 'high')),
    application_timing TEXT,
    safety_notes TEXT
);

-- Climate Data
CREATE TABLE climate (
    id INTEGER PRIMARY KEY,
    region TEXT NOT NULL,
    month INTEGER,
    rainfall_mm REAL,
    temperature_avg_c REAL,
    humidity_pct REAL,
    drought_risk TEXT CHECK(drought_risk IN ('low', 'medium', 'high', 'severe')),
    notes TEXT
);

-- Image References
CREATE TABLE image_refs (
    id INTEGER PRIMARY KEY,
    file_path TEXT NOT NULL,     -- relative path within images/
    disease_id INTEGER REFERENCES diseases(id),
    crop_id INTEGER REFERENCES crops(id),
    type TEXT CHECK(type IN ('disease_symptom', 'healthy_reference', 'treatment_demo')),
    description TEXT,
    visual_features TEXT         -- AI-generated visual feature description
);

-- Field Observations (populated offline, synced later)
CREATE TABLE field_observations (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    type TEXT,
    location TEXT,
    details TEXT,
    image_path TEXT,
    synced BOOLEAN DEFAULT 0
);
```

### ChromaDB Collections

```python
# Collection structure within the Knowledge Pack

collections = {
    "disease_knowledge": {
        # Chunked text about diseases: descriptions, symptoms, progression, etc.
        "metadata_fields": ["disease_id", "crop", "type", "severity"],
        "example_doc": "Cassava Mosaic Disease (CMD) is caused by African cassava mosaic virus (ACMV). Early symptoms include yellow-green mosaic patterns on young leaves...",
    },
    "treatment_guides": {
        # Detailed step-by-step treatment procedures
        "metadata_fields": ["disease_id", "treatment_id", "is_organic", "difficulty"],
        "example_doc": "To prepare neem oil spray: Collect 500g of neem seeds. Crush and soak in 10 liters of water overnight. Strain through cloth...",
    },
    "farming_practices": {
        # General agricultural advice: drought strategies, soil management, etc.
        "metadata_fields": ["topic", "crop", "season", "practice_type"],
        "example_doc": "Drought-resistant cassava planting: Select TME 419 or IITA-TMS-IBA30572 varieties. Plant at the beginning of the rainy season...",
    },
    "regional_context": {
        # Region-specific information: climate, resources, infrastructure, contacts
        "metadata_fields": ["region", "topic", "data_type"],
        "example_doc": "The Casamance region has two seasons: wet (June-October) and dry (November-May). Average annual rainfall is 1,200mm...",
    }
}
```

---

## 7. The Agentic RAG Design — The Core Innovation

This is what separates FieldPack AI from a basic RAG chatbot. The retrieval is not a fixed pipeline — it is an **agent that reasons about what to retrieve, evaluates results, and loops until satisfied.**

### The State Graph

```
                         ┌──────────────┐
                         │    START      │
                         │  User Input   │
                         │ (text/image)  │
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │   CLASSIFY    │
                         │   Intent      │
                         │              │
                         │ Is this a:    │
                         │ - Question?   │
                         │ - Image?      │
                         │ - Follow-up?  │
                         │ - Observation?│
                         └──────┬───────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
             ┌──────▼──┐ ┌─────▼────┐ ┌────▼──────┐
             │ TEXT     │ │ IMAGE    │ │ LOG       │
             │ QUERY   │ │ ANALYSIS │ │ OBSERV.   │
             │ Path    │ │ Path     │ │ Path      │
             └──────┬──┘ └─────┬────┘ └────┬──────┘
                    │          │            │
                    ▼          ▼            │
             ┌─────────────────────┐       │
             │    PLAN RETRIEVAL    │       │
             │                     │       │
             │ LLM decides:        │       │
             │ - Which tools?      │       │
             │ - What queries?     │       │
             │ - What filters?     │       │
             └──────────┬──────────┘       │
                        │                  │
             ┌──────────▼──────────┐       │
             │   EXECUTE TOOLS     │       │
             │                     │       │
             │ Parallel execution: │       │
             │ - ChromaDB search   │       │
             │ - SQLite query      │       │
             │ - Image matching    │       │
             │ (as decided above)  │       │
             └──────────┬──────────┘       │
                        │                  │
             ┌──────────▼──────────┐       │
             │   EVALUATE RESULTS  │       │
             │                     │       │
             │ LLM evaluates:      │       │
             │ - Enough context?   │──NO──▶ PLAN RETRIEVAL (loop)
             │ - Contradictions?   │        (with refined query)
             │ - Need more detail? │
             │ - Confident?        │
             └──────────┬──────────┘
                        │ YES
             ┌──────────▼──────────┐
             │   GENERATE ANSWER   │◀──────┘
             │                     │
             │ Synthesize from all │
             │ retrieved context   │
             │ + conversation      │
             │ history             │
             └──────────┬──────────┘
                        │
             ┌──────────▼──────────┐
                         │     END      │
             │  Response to user   │
             └─────────────────────┘
```

### Key Design Principles

**1. The LLM is the retriever, not a pipeline.**

In traditional RAG: `query → embed → vector search → top-k → LLM → answer`. Fixed. Deterministic.

In our agentic RAG: The LLM sees the user's question and DECIDES:
- "This is about a specific disease — I should query the diseases table by name first, then search for treatment guides in ChromaDB"
- "This is a vague question about drought — I should do a broad vector search across farming_practices, then narrow down"
- "This photo shows a leaf — I should analyze it with vision, extract visual features, then search disease_knowledge with those features as the query"
- "The first search didn't give me enough — let me try a different query with broader filters"

**2. The loop is what makes it intelligent.**

The agent can do 1-4 retrieval cycles per question. Each cycle refines based on what it learned. This is dramatically better than single-shot RAG, especially for complex questions like "What could cause these brown streaks on my cassava, and what can I do about it with materials I can find locally?"

**3. Tool composition is natural via function calling.**

Gemma 4's native function calling means the LLM outputs structured tool calls:
```json
{"name": "search_knowledge", "arguments": {"query": "brown streaks cassava leaf", "collection": "disease_knowledge", "filters": {"crop": "cassava"}}}
```
```json
{"name": "query_database", "arguments": {"table": "treatments", "conditions": {"disease_id": 3, "is_organic": true}}}
```

LangGraph executes these, returns results, and the LLM decides the next step.

---

## 8. Frontend Architecture

### Component Structure (Post-Stitch Integration)

```
frontend/
├── src/
│   ├── App.tsx                    # Main app with routing
│   ├── components/
│   │   ├── ChatInterface/         # Main chat area
│   │   │   ├── ChatWindow.tsx     # Message history display
│   │   │   ├── MessageBubble.tsx  # Individual message (text, image, tool-call viz)
│   │   │   ├── InputBar.tsx       # Text input + image upload button
│   │   │   └── ToolCallCard.tsx   # Shows what tools the agent used (transparency)
│   │   ├── KnowledgePanel/        # Right sidebar
│   │   │   ├── PackInfo.tsx       # Current pack metadata
│   │   │   ├── PackSelector.tsx   # Choose/download packs (online mode)
│   │   │   └── SourceList.tsx     # Shows sources used in last answer
│   │   ├── StatusBar/
│   │   │   ├── OnlineIndicator.tsx  # Online/Offline badge
│   │   │   ├── ModelStatus.tsx      # Which model is active
│   │   │   └── PackStatus.tsx       # Current pack info
│   │   ├── MissionBriefing/       # Phase 1: Online setup
│   │   │   ├── MissionForm.tsx    # Describe your mission
│   │   │   ├── ResearchProgress.tsx # Live progress of agents
│   │   │   └── PackDownload.tsx   # Download the generated pack
│   │   └── ImageViewer/
│   │       ├── PlantPhoto.tsx     # Display uploaded photo
│   │       └── DiagnosisOverlay.tsx # Show diagnosis on image
│   ├── hooks/
│   │   ├── useChat.ts             # Chat state management
│   │   ├── useFieldPack.ts        # Pack loading/management
│   │   └── useOfflineMode.ts      # Online/offline detection
│   ├── api/
│   │   └── client.ts              # FastAPI client (HTTP + WebSocket)
│   └── types/
│       └── index.ts               # TypeScript types
├── public/
├── package.json
└── tailwind.config.js
```

### Backend API (FastAPI)

```
backend/
├── app/
│   ├── main.py                    # FastAPI app + WebSocket endpoint
│   ├── routers/
│   │   ├── chat.py                # POST /chat, WebSocket /ws/chat
│   │   ├── mission.py             # POST /mission/start, GET /mission/status
│   │   ├── pack.py                # GET /packs, POST /packs/load, GET /packs/download
│   │   └── health.py              # GET /health (model status, pack status)
│   ├── agents/
│   │   ├── mission_planner.py     # Phase 1: Mission planning graph
│   │   ├── research_agent.py      # Phase 1: Individual research agent
│   │   ├── knowledge_compiler.py  # Phase 1: Compilation graph
│   │   └── field_assistant.py     # Phase 2: Agentic RAG graph
│   ├── tools/
│   │   ├── web_search.py          # Online: web search tool
│   │   ├── web_fetch.py           # Online: page fetching tool
│   │   ├── chroma_search.py       # Offline: ChromaDB search
│   │   ├── sqlite_query.py        # Offline: SQLite query
│   │   ├── image_analysis.py      # Offline: Image processing
│   │   └── observation_log.py     # Offline: Field observation logging
│   ├── knowledge_pack/
│   │   ├── builder.py             # Build pack from research results
│   │   ├── loader.py              # Load pack for offline use
│   │   └── schema.py              # Pack validation / manifest
│   ├── models/
│   │   ├── online_llm.py          # Google AI Studio (31B/26B)
│   │   └── offline_llm.py         # Ollama (E2B)
│   └── config.py                  # Configuration
├── requirements.txt
└── .env
```

---

## 9. Local Development Setup

### Prerequisites

```bash
# Python 3.10+
python --version

# Node.js 18+
node --version

# Ollama
# Download from https://ollama.com
ollama --version
```

### Step-by-Step Setup

```bash
# 1. Clone/create project
cd /c/pro
mkdir fieldpack-ai && cd fieldpack-ai

# 2. Python backend
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
pip install langgraph langchain-google-genai langchain-ollama
pip install chromadb sentence-transformers
pip install fastapi uvicorn websockets
pip install python-dotenv httpx beautifulsoup4

# 3. Pull Gemma 4 E2B for offline use
ollama pull gemma4-e2b:q4_K_M    # ~5GB, ~8GB RAM

# 4. Frontend (after Stitch export)
cd frontend
npm install
npm run dev

# 5. Backend
cd ../backend
uvicorn app.main:app --reload --port 8000

# 6. Environment variables
# .env file:
# GOOGLE_AI_STUDIO_API_KEY=your_key_here
# OLLAMA_BASE_URL=http://localhost:11434
# KNOWLEDGE_PACK_DIR=./packs
```

### Testing the Full Loop

```bash
# Test 1: Verify Ollama is running with Gemma E2B
curl http://localhost:11434/api/generate -d '{"model":"gemma4-e2b:q4_K_M","prompt":"Hello"}'

# Test 2: Verify Google AI Studio connection
python -c "from langchain_google_genai import ChatGoogleGenerativeAI; print('OK')"

# Test 3: Run Phase 1 (creates a Knowledge Pack)
python -m app.agents.mission_planner --mission "cassava diseases in Casamance Senegal"

# Test 4: Run Phase 2 (loads pack, starts offline agent)
python -m app.agents.field_assistant --pack ./packs/casamance_agriculture_v1

# Test 5: Full stack
# Terminal 1: ollama serve
# Terminal 2: uvicorn app.main:app --reload --port 8000
# Terminal 3: cd frontend && npm run dev
# Open http://localhost:3000
```

---

## 10. Project File Structure

```
fieldpack-ai/
├── PHILOSOPHY.md                  # Project philosophy (already created)
├── TECH_FRAMEWORK.md              # This document
├── README.md                      # Project overview for judges
│
├── backend/                       # Python — FastAPI + LangGraph
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routers/
│   │   ├── agents/
│   │   ├── tools/
│   │   ├── knowledge_pack/
│   │   └── models/
│   ├── requirements.txt
│   ├── .env
│   └── tests/
│
├── frontend/                      # React/Tailwind — Stitch-designed
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── tailwind.config.js
│
├── packs/                         # Generated Knowledge Packs
│   └── casamance_agriculture_v1/
│       ├── manifest.json
│       ├── knowledge.db
│       ├── chroma_db/
│       ├── images/
│       ├── README.md
│       └── SOURCES.md
│
├── notebooks/                     # Kaggle submission notebooks
│   ├── phase1_knowledge_gathering.ipynb
│   └── phase2_field_assistant_demo.ipynb
│
├── stitch/                        # Stitch design exports (reference)
│   └── exports/
│
├── video/                         # Video assets for submission
│   ├── script.md
│   └── assets/
│
└── docs/                          # Additional documentation
    ├── WRITEUP.md                 # Kaggle writeup draft
    └── ARCHITECTURE.md            # Detailed architecture diagrams
```

---

## 11. Risk Register & Fallbacks

| Risk | Impact | Probability | Fallback |
|------|--------|------------|----------|
| E2B plant identification too weak | High | Medium | Add CLIP model for image embedding + similarity search |
| Google AI Studio rate limits hit during Phase 1 | Medium | Low | Batch requests, add delays, or use Kaggle notebooks for heavy lifting |
| ChromaDB persistent store too large (>500MB) | Low | Low | Reduce chunk count, compress embeddings, limit reference images |
| Ollama E2B too slow on CPU for demo | Medium | Medium | Use Q4 quantization, pre-warm the model, keep demo questions focused |
| Stitch React export needs heavy rework | Medium | Medium | Fall back to Gradio for MVP, Stitch for video screenshots only |
| LangGraph + Ollama function calling breaks | High | Low | Implement manual tool call parsing (regex on Gemma output) |
| MiniLM embeddings incompatible with online embeddings | Medium | Medium | Use MiniLM for both online and offline (guaranteed compatibility) |
| Knowledge Pack data quality is poor | High | Medium | Add human review step in the compiler, curate top sources manually |
| Hackathon time runs out | High | Medium | Prioritize: (1) working demo of hero shot, (2) video, (3) writeup, (4) polish |

---

## References

### Frameworks & Libraries
- [LangGraph](https://www.langchain.com/langgraph) — Agent orchestration
- [LangGraph + Gemma (Google's official tutorial)](https://ai.google.dev/gemini-api/docs/langgraph-example)
- [ChromaDB](https://www.trychroma.com/) — Vector database
- [Ollama](https://ollama.com/) — Local LLM inference
- [Google AI Studio](https://ai.google.dev/) — Free Gemma 4 API access
- [Google Stitch](https://stitch.withgoogle.com/) — AI UI design
- [sentence-transformers](https://www.sbert.net/) — Embedding models
- [FastAPI](https://fastapi.tiangolo.com/) — Backend API

### Gemma 4 Technical
- [Gemma 4 Function Calling Guide](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4)
- [Gemma 4 Hardware Requirements](https://avenchat.com/blog/gemma-4-hardware-requirements)
- [Gemma 4 E2B GGUF (Unsloth)](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF)
- [HuggingFace: Welcome Gemma 4](https://huggingface.co/blog/gemma4)
