# FieldPack AI

Offline AI for humanitarian field workers — Gemma 4 E2B on Ollama serves curated Knowledge Packs via agentic RAG on a laptop, with a phone thin-client APK for camera + UI. **Hackathon entry for Kaggle Gemma 4 Good Hackathon.**

For design philosophy and technical architecture, see `docs/PHILOSOPHY.md` and `docs/TECH_FRAMEWORK.md`. For full development notes, environment tips, and configuration details, see `docs/DEVELOPER_NOTES.md`.

## Quick Start

```bash
source venv/Scripts/activate  # venv is at repo root

# Backend
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev

# Tests
cd backend && PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/ -v --ignore=tests/test_step_7_live.py

# Ollama
ollama serve
```

## Important Configuration

**Intel iGPU users**: Set `OLLAMA_NUM_GPU=0` to force CPU-only mode if model output becomes incoherent. Partial GPU offload can degrade quality on small models.

See `docs/DEVELOPER_NOTES.md` for APK build commands, LAN discovery setup, network configuration, and full environment tips.
