"""LangGraph state for the Phase 1 Agent Farm pipeline.

The AgentFarmState flows through the 4-phase graph:
  Phase A: source_gathering  -> sections
  Phase B: knowledge_extraction -> findings
  Phase C: gap_analysis -> findings (augmented)
  Phase D: compilation -> compiled JSON files -> Knowledge Pack
"""

from typing import TypedDict

from app.agent_farm.models import CompilationOutput, Finding, PageSection


class AgentFarmState(TypedDict, total=False):
    # --- Input ---
    mission_description: str  # user's natural-language mission briefing
    region: str  # e.g., "Casamance, Senegal"
    currency: str  # e.g., "XOF (West African CFA francs)"
    crops: list[str]  # e.g., ["cassava", "rice", "maize", "groundnut", "tomato"]

    # --- Phase A: Source Gathering ---
    sections: list[PageSection]  # all parsed page sections from HTTP/PDF sources
    climate_records: list[dict]  # directly-parsed climate table rows (no LLM)
    image_urls: list[dict]  # {"url": ..., "category": ..., "entity": ..., "description": ...}

    # --- Phase B: Knowledge Extraction ---
    findings: list[Finding]  # all extracted knowledge nuggets

    # --- Phase C: Gap Analysis ---
    identified_gaps: list[str]  # domains/entities with insufficient coverage
    gap_search_queries: list[str]  # Tavily queries generated for gaps

    # --- Phase D: Compilation ---
    compilation: CompilationOutput | None  # all 11 compiled tables
    json_output_dir: str  # path to directory with 11 JSON files

    # --- Chunk Generation ---
    chunks: dict[str, list[dict]]  # collection_name -> list of chunk dicts

    # --- Image Download ---
    downloaded_images: list[dict]  # {"url", "category", "entity", "local_path"}

    # --- Pack Building ---
    pack_path: str  # final path to the built Knowledge Pack

    # --- Observability ---
    status_messages: list[str]  # UI progress messages
    current_phase: str  # "gathering", "extracting", "gap_analysis", "compiling", "building"
    error: str | None
