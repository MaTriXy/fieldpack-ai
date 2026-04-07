"""Phase A: Deterministic source gathering (no LLM calls).

Fetches all known HTML pages, PDFs, and climate tables concurrently.
Returns updated AgentFarmState with sections, climate_records, and
status_messages populated.

All fetches run in a single asyncio.gather() for maximum concurrency.
Individual failures are logged and skipped — the pipeline continues
with whatever data it got.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.agent_farm.models import PageSection
from app.agent_farm.sources.cgiar_fetcher import fetch_cgiar_pdfs
from app.agent_farm.sources.html_parser import parse_html_by_headings
from app.agent_farm.sources.open_meteo import fetch_climate_open_meteo
from app.agent_farm.sources.pdf_parser import parse_pdf_bytes
from app.agent_farm.sources.registry import (
    CGIAR_FERTILIZATION,
    get_climate_cities,
    get_pdf_urls,
    get_urls_for_crop,
)
from app.agent_farm.sources.section_scorer import rank_sections
from app.agent_farm.state import AgentFarmState
from app.agent_farm.tools.web_fetch import fetch_html, fetch_pdf_bytes
from app.logger import Step, pipeline_logger as log


# Per-source-type section caps (protects against unbounded input)
_MAX_SECTIONS_PER_HTML = 20   # any single HTML page
_MAX_SECTIONS_PER_PDF = 50    # any single PDF document
_MAX_SECTIONS_GLOBAL = 150    # total across all sources
_MIN_RELEVANCE_SCORE = 0.05   # drop sections below this


# ------------------------------------------------------------------
# Individual fetch-and-parse coroutines
# ------------------------------------------------------------------


async def _fetch_and_parse_html(
    crop: str,
    source_name: str,
    url: str,
) -> list[PageSection]:
    """Fetch one HTML page and parse into sections, tagged with crop."""
    html = await fetch_html(url)
    if html is None:
        return []
    sections = parse_html_by_headings(html, source_url=url, source_name=source_name)
    for s in sections:
        s.crop = crop
    return sections


async def _fetch_and_parse_pdf(
    source_name: str,
    url: str,
    crops: list[str],
) -> list[PageSection]:
    """Fetch one PDF and parse into sections.

    PDFs may cover multiple crops (e.g., FAO guides). If the PDF source
    maps to a single crop, tag all sections with that crop. Otherwise
    leave crop blank for Phase B to infer from content.
    """
    pdf_bytes = await fetch_pdf_bytes(url)
    if pdf_bytes is None:
        return []
    sections = parse_pdf_bytes(pdf_bytes, source_url=url, source_name=source_name)
    # If only one crop is associated with this PDF source, tag sections
    if len(crops) == 1:
        for s in sections:
            s.crop = crops[0]
    return sections



# ------------------------------------------------------------------
# Main phase function (LangGraph node)
# ------------------------------------------------------------------


async def source_gathering(state: AgentFarmState) -> dict[str, Any]:
    """Phase A: Fetch all known sources concurrently. No LLM calls.

    Reads from state: crops, region
    Writes to state: sections, climate_records, status_messages, current_phase
    """
    crops = [c.lower() for c in state.get("crops", [])]
    messages: list[str] = list(state.get("status_messages", []))
    messages.append("Phase A: Starting source gathering...")

    log.log_step(Step.AGENT_FARM_GATHER, "phase_start", details={
        "crops": crops, "region": state.get("region", ""),
    })

    # ---- Build all fetch tasks ----

    html_tasks: list = []
    pdf_tasks: list = []
    climate_tasks: list = []

    # Tier 1: HTML sources (per crop)
    for crop in crops:
        for source, url in get_urls_for_crop(crop):
            html_tasks.append(
                _fetch_and_parse_html(crop, source.name, url)
            )

    # Tier 2: PDF sources
    for source, url in get_pdf_urls():
        # Determine which crops this PDF covers
        pdf_crops = [c for c in crops if c.lower() in source.slug_map]
        pdf_tasks.append(
            _fetch_and_parse_pdf(source.name, url, pdf_crops)
        )

    # Tier 2b: CGIAR/IITA PDFs (fertilization data)
    cgiar_tasks: list = []
    for crop in crops:
        query = CGIAR_FERTILIZATION.slug_map.get(crop)
        if query:
            cgiar_tasks.append(
                fetch_cgiar_pdfs(query=query, crops=[crop])
            )

    # Tier 3: Climate data (Open-Meteo Archive API)
    for city, (lat, lon) in get_climate_cities().items():
        climate_tasks.append(
            fetch_climate_open_meteo(lat, lon, region=city)
        )

    # ---- Fire everything concurrently ----

    all_tasks = html_tasks + pdf_tasks + cgiar_tasks + climate_tasks
    task_count = len(all_tasks)
    messages.append(f"Fetching {task_count} sources concurrently...")

    results = await asyncio.gather(*all_tasks, return_exceptions=True)

    # ---- Separate results by type ----

    all_sections: list[PageSection] = []
    all_climate: list[dict] = []
    errors: list[str] = []

    html_count = len(html_tasks)
    pdf_count = len(pdf_tasks)
    cgiar_count = len(cgiar_tasks)
    section_end = html_count + pdf_count + cgiar_count

    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            errors.append(f"Task {i} failed: {result}")
            log.log_step(Step.AGENT_FARM_GATHER, "fetch_exception",
                         level="WARNING", details={"task_index": i, "error": str(result)})
            continue

        if i < section_end:
            # HTML, PDF, or CGIAR result — all return list[PageSection]
            all_sections.extend(result)
        else:
            # Climate result
            all_climate.extend(result)

    # ---- Log raw gather summary ----

    html_sections = sum(
        len(r) for i, r in enumerate(results)
        if i < html_count and not isinstance(r, BaseException)
    )
    pdf_sections = sum(
        len(r) for i, r in enumerate(results)
        if html_count <= i < html_count + pdf_count
        and not isinstance(r, BaseException)
    )
    cgiar_sections = sum(
        len(r) for i, r in enumerate(results)
        if html_count + pdf_count <= i < section_end
        and not isinstance(r, BaseException)
    )
    climate_months = len(all_climate)
    raw_total = len(all_sections)

    messages.append(
        f"Gathered {html_sections} HTML sections, "
        f"{pdf_sections} PDF sections, "
        f"{cgiar_sections} CGIAR sections, "
        f"{climate_months} climate records"
    )
    if errors:
        messages.append(f"{len(errors)} sources failed (skipped)")

    # ---- Filter & rank sections by relevance ----

    # Step 1: Per-source caps (ranked by fuzzy relevance score)
    source_groups: dict[str, list[PageSection]] = {}
    for s in all_sections:
        source_groups.setdefault(s.source_name, []).append(s)

    capped_sections: list[PageSection] = []
    for source_name, group in source_groups.items():
        # Determine cap based on source type
        is_pdf = any(
            s.heading.startswith("page_") for s in group
        )
        cap = _MAX_SECTIONS_PER_PDF if is_pdf else _MAX_SECTIONS_PER_HTML

        ranked = rank_sections(group, max_sections=cap, min_score=_MIN_RELEVANCE_SCORE)
        capped_sections.extend(ranked)

        if len(group) > len(ranked):
            log.log_step(Step.AGENT_FARM_GATHER, "source_capped", details={
                "source": source_name,
                "raw": len(group),
                "kept": len(ranked),
                "cap": cap,
            })

    # Step 2: Global cap (ranked by fuzzy relevance score)
    filtered_sections = rank_sections(
        capped_sections,
        max_sections=_MAX_SECTIONS_GLOBAL,
        min_score=_MIN_RELEVANCE_SCORE,
    )

    # Restore original document order (source + page/heading sequence)
    # so consecutive sections from the same PDF stay together
    original_order = {id(s): i for i, s in enumerate(all_sections)}
    filtered_sections.sort(key=lambda s: original_order.get(id(s), 0))

    messages.append(
        f"Filtered {raw_total} -> {len(filtered_sections)} sections "
        f"(per-source caps + relevance scoring)"
    )

    log.log_step(Step.AGENT_FARM_GATHER, "phase_complete", details={
        "html_sections": html_sections,
        "pdf_sections": pdf_sections,
        "cgiar_sections": cgiar_sections,
        "climate_records": climate_months,
        "raw_sections": raw_total,
        "filtered_sections": len(filtered_sections),
        "errors": len(errors),
    })

    return {
        "sections": filtered_sections,
        "climate_records": all_climate,
        "status_messages": messages,
        "current_phase": "gathering",
    }
