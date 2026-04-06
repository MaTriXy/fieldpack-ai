"""Phase functions for the Agent Farm pipeline.

Phase A: source_gathering  — deterministic fetching (no LLM)
Phase B: knowledge_extraction — LLM per section → Finding
Phase C: gap_analysis — identify gaps + Tavily search + images
Phase D: compilation — per-table Pydantic compilation (11 steps)
"""
