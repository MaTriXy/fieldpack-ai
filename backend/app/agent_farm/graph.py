"""Agent Farm LangGraph StateGraph — Phase 1 pipeline orchestration.

Connects the 4 phases into a linear graph:
  source_gathering → knowledge_extraction → gap_analysis → compilation
    → generate_chunks → download_images → END

All phases are async LangGraph nodes operating on AgentFarmState.
No conditional edges — retry logic lives inside individual phases
(e.g., compilation's per-table retry escalation).

Entry points:
  run_agent_farm()        — async, returns final state dict
  run_agent_farm_stream() — async generator, yields progress events
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph

from app.agent_farm.phases.compilation import (
    compilation,
    generate_chunks_from_compilation,
)
from app.agent_farm.phases.gap_analysis import gap_analysis
from app.agent_farm.phases.knowledge_extraction import knowledge_extraction
from app.agent_farm.phases.source_gathering import source_gathering
from app.agent_farm.sources.image_downloader import download_image
from app.agent_farm.state import AgentFarmState
from app.logger import Step, pipeline_logger as log


# ============================================================
# Wrapper nodes (chunks + images)
# ============================================================


async def generate_chunks(state: AgentFarmState) -> dict[str, Any]:
    """Generate ChromaDB parent/child chunk pairs from compilation output.

    Reads from state: compilation
    Writes to state: chunks, status_messages, current_phase
    """
    comp = state.get("compilation")
    messages: list[str] = list(state.get("status_messages", []))

    if comp is None:
        messages.append("Chunk generation skipped — no compilation output")
        log.log_step(Step.AGENT_FARM_COMPILE, "chunks_skipped",
                     level="WARNING", details={"reason": "no compilation output"})
        return {
            "chunks": {},
            "status_messages": messages,
            "current_phase": "chunks",
        }

    messages.append("Generating ChromaDB chunks from compiled records...")
    chunks = generate_chunks_from_compilation(comp)

    total = sum(len(v) for v in chunks.values())
    messages.append(
        f"Generated {total} chunks across {len(chunks)} collections"
    )

    return {
        "chunks": chunks,
        "status_messages": messages,
        "current_phase": "chunks",
    }


async def download_images(state: AgentFarmState) -> dict[str, Any]:
    """Download all gathered image URLs to the pack images directory.

    Reads from state: image_urls, json_output_dir
    Writes to state: downloaded_images, status_messages, current_phase
    """
    image_urls = state.get("image_urls", [])
    json_output_dir = state.get("json_output_dir", "")
    messages: list[str] = list(state.get("status_messages", []))

    if not image_urls:
        messages.append("No images to download")
        return {
            "downloaded_images": [],
            "status_messages": messages,
            "current_phase": "images",
        }

    # Images go inside the JSON output dir (scoped to this run)
    images_dir = Path(json_output_dir) / "images" if json_output_dir else Path("images")
    images_dir.mkdir(parents=True, exist_ok=True)

    messages.append(f"Downloading {len(image_urls)} images...")

    log.log_step(Step.AGENT_FARM_GATHER, "image_download_start", details={
        "count": len(image_urls),
        "target_dir": str(images_dir),
    })

    _MAX_CONCURRENT_DOWNLOADS = 10
    sem = asyncio.Semaphore(_MAX_CONCURRENT_DOWNLOADS)

    async def _download_one(img: dict) -> dict | None:
        url = img.get("url", "")
        category = img.get("category", "misc")
        entity = img.get("entity", "unknown")
        if not url:
            return None
        async with sem:
            path = await download_image(
                url=url,
                category=category,
                entity_name=entity,
                images_dir=images_dir,
            )
        if path is None:
            return None
        return {
            "url": url,
            "category": category,
            "entity": entity,
            "local_path": str(path),
        }

    results = await asyncio.gather(
        *[_download_one(img) for img in image_urls],
        return_exceptions=True,
    )

    downloaded: list[dict] = []
    failed = 0
    for r in results:
        if isinstance(r, BaseException):
            failed += 1
        elif r is not None:
            downloaded.append(r)
        else:
            failed += 1

    messages.append(
        f"Downloaded {len(downloaded)} images"
        f"{f' ({failed} failed)' if failed else ''}"
    )

    log.log_step(Step.AGENT_FARM_GATHER, "image_download_complete", details={
        "downloaded": len(downloaded),
        "failed": failed,
    })

    return {
        "downloaded_images": downloaded,
        "status_messages": messages,
        "current_phase": "images",
    }


# ============================================================
# Graph builder
# ============================================================


def build_agent_farm_graph() -> StateGraph:
    """Build the LangGraph StateGraph for the Agent Farm pipeline.

    Returns the compiled graph ready for invocation.
    """
    graph = StateGraph(AgentFarmState)

    # Add all nodes
    graph.add_node("source_gathering", source_gathering)
    graph.add_node("knowledge_extraction", knowledge_extraction)
    graph.add_node("gap_analysis", gap_analysis)
    graph.add_node("compilation", compilation)
    graph.add_node("generate_chunks", generate_chunks)
    graph.add_node("download_images", download_images)

    # Linear edges
    graph.set_entry_point("source_gathering")
    graph.add_edge("source_gathering", "knowledge_extraction")
    graph.add_edge("knowledge_extraction", "gap_analysis")
    graph.add_edge("gap_analysis", "compilation")
    graph.add_edge("compilation", "generate_chunks")
    graph.add_edge("generate_chunks", "download_images")
    graph.add_edge("download_images", END)

    return graph.compile()


# Module-level compiled graph (singleton)
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_agent_farm_graph()
    return _graph


# ============================================================
# Entry points
# ============================================================


async def run_agent_farm(
    crops: list[str],
    region: str = "Casamance, Senegal",
    mission_description: str = "",
) -> dict:
    """Run the Agent Farm pipeline end-to-end.

    Args:
        crops: List of crop names to gather knowledge for.
        region: Target region for the Knowledge Pack.
        mission_description: Optional mission briefing text.

    Returns:
        Final AgentFarmState dict with compilation, chunks,
        json_output_dir, downloaded_images, and status_messages.
    """
    log.log_step(Step.AGENT_FARM_GATHER, "pipeline_start", details={
        "crops": crops, "region": region,
    })

    initial_state: AgentFarmState = {
        "crops": crops,
        "region": region,
        "mission_description": mission_description,
        "status_messages": [],
        "current_phase": "starting",
    }

    try:
        graph = _get_graph()
        final_state = await graph.ainvoke(initial_state)

        log.log_step(Step.AGENT_FARM_COMPILE, "pipeline_complete", details={
            "phases_completed": final_state.get("current_phase", "unknown"),
            "total_messages": len(final_state.get("status_messages", [])),
        })

        return final_state

    except Exception as e:
        log.log_step(Step.AGENT_FARM_COMPILE, "pipeline_failed",
                     level="ERROR", details={"error": str(e)[:500]})
        raise


async def run_agent_farm_stream(
    crops: list[str],
    region: str = "Casamance, Senegal",
    mission_description: str = "",
):
    """Stream the Agent Farm pipeline via astream_events.

    Yields event dicts for the WebSocket handler to forward to the client.

    Event types:
        {"type": "status", "phase": "...", "detail": "..."}
        {"type": "phase_complete", "phase": "...", "latency_ms": ...}
        {"type": "done", "summary": {...}}
        {"type": "error", "message": "..."}
    """
    log.log_step(Step.AGENT_FARM_GATHER, "pipeline_stream_start", details={
        "crops": crops, "region": region,
    })

    initial_state: AgentFarmState = {
        "crops": crops,
        "region": region,
        "mission_description": mission_description,
        "status_messages": [],
        "current_phase": "starting",
    }

    _NODE_STATUS_MAP = {
        "source_gathering": ("gathering", "Fetching HTML pages, PDFs, and climate data..."),
        "knowledge_extraction": ("extracting", "Extracting knowledge from sources..."),
        "gap_analysis": ("gap_analysis", "Identifying and filling knowledge gaps..."),
        "compilation": ("compiling", "Compiling structured database records..."),
        "generate_chunks": ("chunks", "Generating search index chunks..."),
        "download_images": ("images", "Downloading reference images..."),
    }

    try:
        graph = _get_graph()
        final_state = {}
        node_timings: dict[str, float] = {}
        pipeline_start = time.perf_counter()

        async for event in graph.astream_events(initial_state, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")

            # Node start → status event
            if kind == "on_chain_start" and name in _NODE_STATUS_MAP:
                node_timings[name] = time.perf_counter()
                phase, detail = _NODE_STATUS_MAP[name]
                yield {
                    "type": "status",
                    "phase": phase,
                    "detail": detail,
                }

            # Node end → phase_complete event
            if kind == "on_chain_end" and name in _NODE_STATUS_MAP:
                latency_ms = None
                if name in node_timings:
                    latency_ms = round(
                        (time.perf_counter() - node_timings[name]) * 1000
                    )

                phase, _ = _NODE_STATUS_MAP[name]
                yield {
                    "type": "phase_complete",
                    "phase": phase,
                    "latency_ms": latency_ms,
                }

            # Accumulate node outputs into final_state
            if kind == "on_chain_end" and name in _NODE_STATUS_MAP:
                output = event.get("data", {}).get("output", {})
                if isinstance(output, dict):
                    final_state.update(output)

        # Done — emit summary
        total_latency_ms = round(
            (time.perf_counter() - pipeline_start) * 1000
        )

        comp = final_state.get("compilation")
        chunks = final_state.get("chunks", {})

        yield {
            "type": "done",
            "summary": {
                "total_latency_ms": total_latency_ms,
                "findings": len(final_state.get("findings", [])),
                "tables": {
                    table: len(getattr(comp, table, []))
                    for table in [
                        "crops", "diseases", "treatments", "climate",
                        "pests", "varieties",
                    ]
                } if comp else {},
                "chunks": sum(len(v) for v in chunks.values()),
                "images": len(final_state.get("downloaded_images", [])),
                "json_output_dir": final_state.get("json_output_dir", ""),
            },
            "status_messages": final_state.get("status_messages", []),
        }

    except Exception as e:
        log.log_step(Step.AGENT_FARM_COMPILE, "pipeline_stream_failed",
                     level="ERROR", details={"error": str(e)[:500]})
        yield {"type": "error", "message": f"Agent Farm pipeline error: {e}"}
