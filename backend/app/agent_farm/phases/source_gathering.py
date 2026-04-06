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
from app.agent_farm.sources.climate_parser import parse_climate_tables
from app.agent_farm.sources.html_parser import parse_html_by_headings
from app.agent_farm.sources.pdf_parser import parse_pdf_bytes
from app.agent_farm.sources.registry import (
    WEATHER_AND_CLIMATE,
    get_pdf_urls,
    get_urls_for_crop,
)
from app.agent_farm.state import AgentFarmState
from app.agent_farm.tools.web_fetch import fetch_html, fetch_pdf_bytes
from app.logger import Step, pipeline_logger as log


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


async def _fetch_and_parse_climate(
    city: str,
    url: str,
) -> list[dict]:
    """Fetch one climate page and parse tables into structured records."""
    html = await fetch_html(url)
    if html is None:
        return []
    return parse_climate_tables(html, region=city, source_url=url)


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

    # Tier 3: Climate tables (per city in the region)
    for city, slug in WEATHER_AND_CLIMATE.slug_map.items():
        url = WEATHER_AND_CLIMATE.url_template.format(slug=slug)
        climate_tasks.append(
            _fetch_and_parse_climate(city, url)
        )

    # ---- Fire everything concurrently ----

    all_tasks = html_tasks + pdf_tasks + climate_tasks
    task_count = len(all_tasks)
    messages.append(f"Fetching {task_count} sources concurrently...")

    results = await asyncio.gather(*all_tasks, return_exceptions=True)

    # ---- Separate results by type ----

    all_sections: list[PageSection] = []
    all_climate: list[dict] = []
    errors: list[str] = []

    html_count = len(html_tasks)
    pdf_count = len(pdf_tasks)

    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            errors.append(f"Task {i} failed: {result}")
            log.log_step(Step.AGENT_FARM_GATHER, "fetch_exception",
                         level="WARNING", details={"task_index": i, "error": str(result)})
            continue

        if i < html_count:
            # HTML result
            all_sections.extend(result)
        elif i < html_count + pdf_count:
            # PDF result
            all_sections.extend(result)
        else:
            # Climate result
            all_climate.extend(result)

    # ---- Log summary ----

    html_sections = sum(
        len(r) for i, r in enumerate(results)
        if i < html_count and not isinstance(r, BaseException)
    )
    pdf_sections = sum(
        len(r) for i, r in enumerate(results)
        if html_count <= i < html_count + pdf_count
        and not isinstance(r, BaseException)
    )
    climate_months = len(all_climate)

    messages.append(
        f"Gathered {html_sections} HTML sections, "
        f"{pdf_sections} PDF sections, "
        f"{climate_months} climate records"
    )
    if errors:
        messages.append(f"{len(errors)} sources failed (skipped)")

    log.log_step(Step.AGENT_FARM_GATHER, "phase_complete", details={
        "html_sections": html_sections,
        "pdf_sections": pdf_sections,
        "climate_records": climate_months,
        "total_sections": len(all_sections),
        "errors": len(errors),
    })

    return {
        "sections": all_sections,
        "climate_records": all_climate,
        "status_messages": messages,
        "current_phase": "gathering",
    }
