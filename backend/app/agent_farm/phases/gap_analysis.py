"""Phase C: Gap analysis + targeted search + image gathering.

Uses Gemma 4 31B to analyze findings coverage, identify gaps, and
generate targeted search queries. Two-tier gap filling:
  1. Tavily with preferred agricultural domains
  2. Fallback: site-specific queries for critical domains (FAO, CGIAR, etc.)

Also runs Tavily image search for disease/crop photos.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.agent_farm.models import (
    ExtractionOutput,
    Finding,
    GapAnalysisOutput,
    PageSection,
    finding_extract_to_dataclass,
)
from app.agent_farm.rate_limiter import rate_limiter
from app.agent_farm.sources.html_parser import sliding_window
from app.agent_farm.state import AgentFarmState
from app.agent_farm.tools.web_search import search_images, search_text
from app.config import settings
from app.logger import Step, pipeline_logger as log
from app.models.online_llm import get_planner_llm, get_research_llm

_MAX_CONCURRENT_SEARCH = 10
_MAX_CONCURRENT_EXTRACT = 10
_PLANNER_MODEL = settings.online_model_large
_RESEARCH_MODEL = settings.online_model_research

# Preferred domains for agricultural knowledge — Tavily biases toward these
_PREFERRED_DOMAINS = [
    "fao.org",
    "cgiar.org",
    "iita.org",
    "irri.org",
    "worldveg.org",
    "africarice.org",
    "isra.sn",
    "infonet-biovision.org",
    "plantvillage.psu.edu",
    "cabi.org",
]

# Site-specific fallback domains — tried individually when preferred search
# returns zero results for a gap
_FALLBACK_SITES = [
    "fao.org",
    "cgiar.org",
    "iita.org",
    "irri.org",
    "africarice.org",
    "worldveg.org",
]


# ------------------------------------------------------------------
# Gap analysis prompt
# ------------------------------------------------------------------

_GAP_ANALYSIS_PROMPT = """\
You are an agricultural knowledge analyst preparing a Knowledge Pack for a \
field worker deploying to the Casamance region of Senegal. The pack covers \
these crops: {crops}.

Below is a summary of all knowledge gathered so far, grouped by domain. \
Your job is to identify what's MISSING — gaps that would hurt a field \
worker's ability to diagnose diseases, recommend treatments, or advise \
on farming practices.

--- COVERAGE SUMMARY ---
{coverage_summary}
--- END SUMMARY ---

Focus on:
- Domains with zero or very few findings for a crop that needs them
- Missing variety data (especially drought-resistant varieties with local seed sources)
- Missing treatment costs in XOF (West African CFA francs)
- Missing fertilization schedules or planting calendars for specific crops
- Missing pest data for crops known to have pest problems
- Region-specific practices that generic sources wouldn't cover

Generate targeted search queries that will find the missing information. \
Include the crop name, "Senegal" or "Casamance", and the specific data needed.
"""


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _build_coverage_summary(findings: list[Finding], crops: list[str]) -> str:
    """Build a concise summary of findings for the gap analysis prompt."""
    # Group by (domain, crop-related entity)
    domain_entities: dict[str, dict[str, int]] = {}
    for f in findings:
        domain = f.domain
        if domain not in domain_entities:
            domain_entities[domain] = {}
        name = f.entity_name
        domain_entities[domain][name] = domain_entities[domain].get(name, 0) + 1

    lines: list[str] = []
    lines.append(f"Crops in pack: {', '.join(crops)}")
    lines.append(f"Total findings: {len(findings)}")
    lines.append("")

    for domain in sorted(domain_entities.keys()):
        entities = domain_entities[domain]
        lines.append(f"[{domain.upper()}] ({sum(entities.values())} findings)")
        for entity, count in sorted(entities.items(), key=lambda x: -x[1]):
            lines.append(f"  - {entity}: {count} finding(s)")
        lines.append("")

    # Explicitly note domains with zero findings
    expected_domains = {
        "crop", "disease", "treatment", "pest", "variety",
        "soil", "fertilization", "storage", "planting", "climate",
    }
    missing_domains = expected_domains - set(domain_entities.keys())
    if missing_domains:
        lines.append(f"MISSING DOMAINS (zero findings): {', '.join(sorted(missing_domains))}")

    return "\n".join(lines)


async def _extract_from_tavily_result(
    result: dict,
    gap_description: str,
    llm_with_schema,
    semaphore: asyncio.Semaphore,
) -> list[Finding]:
    """Parse a Tavily result into PageSections and extract findings."""
    raw_content = result.get("raw_content") or result.get("content", "")
    url = result.get("url", "")
    title = result.get("title", "")

    if not raw_content or len(raw_content) < 300:
        return []

    # Parse into sections using sliding window (Tavily content has no headings)
    sections = sliding_window(
        text=raw_content,
        source_url=url,
        source_name=f"Tavily: {title}",
    )

    if not sections:
        return []

    # Extract findings from each section via LLM
    findings: list[Finding] = []

    for section in sections[:3]:  # cap at 3 sections per result to control costs
        async with semaphore:
            await rate_limiter.wait(_RESEARCH_MODEL)

            prompt = (
                f"You are filling a knowledge gap: {gap_description}\n\n"
                f"SOURCE: {url}\n\n"
                f"--- TEXT ---\n{section.content}\n--- END TEXT ---\n\n"
                "Extract all relevant knowledge nuggets from this text."
            )

            try:
                with log.timed(Step.AGENT_FARM_GAP, "gap_extract") as t:
                    output: ExtractionOutput = await llm_with_schema.ainvoke(prompt)
                    t.set(details={
                        "url": url, "findings_count": len(output.findings),
                    })

                rate_limiter.on_success(_RESEARCH_MODEL)

                source_ref = f"Tavily — {title} ({url})"
                findings.extend(
                    finding_extract_to_dataclass(fe, source=source_ref)
                    for fe in output.findings
                )

            except Exception as exc:
                error_str = str(exc)
                if "429" in error_str or "rate" in error_str.lower():
                    rate_limiter.on_rate_limit(_RESEARCH_MODEL)
                log.log_step(Step.AGENT_FARM_GAP, "gap_extract_failed",
                             level="WARNING", details={"url": url, "error": error_str[:200]})

    return findings


async def _search_for_gap(
    gap_query: str,
    gap_description: str,
    llm_with_schema,
    search_semaphore: asyncio.Semaphore,
    extract_semaphore: asyncio.Semaphore,
) -> list[Finding]:
    """Two-tier search for a single gap: preferred domains, then site-specific fallback."""
    findings: list[Finding] = []

    # ---- Tier 1: Tavily with preferred domains ----

    async with search_semaphore:
        results = await asyncio.to_thread(
            search_text,
            query=gap_query,
            max_results=3,
            include_domains=_PREFERRED_DOMAINS,
        )

    log.log_step(Step.AGENT_FARM_GAP, "gap_search_tier1", details={
        "query": gap_query, "results_count": len(results),
    })

    # Extract findings from Tier 1 results
    if results:
        extract_tasks = [
            _extract_from_tavily_result(r, gap_description, llm_with_schema, extract_semaphore)
            for r in results
        ]
        extract_results = await asyncio.gather(*extract_tasks, return_exceptions=True)
        for r in extract_results:
            if isinstance(r, list):
                findings.extend(r)

    # ---- Tier 2: Site-specific fallback if Tier 1 found nothing ----

    if not findings:
        log.log_step(Step.AGENT_FARM_GAP, "gap_search_tier2_start", details={
            "query": gap_query, "reason": "tier1 returned zero findings",
        })

        for site in _FALLBACK_SITES:
            async with search_semaphore:
                site_results = await asyncio.to_thread(
                    search_text,
                    query=f"site:{site} {gap_query}",
                    max_results=2,
                )

            if not site_results:
                continue

            log.log_step(Step.AGENT_FARM_GAP, "gap_search_tier2_hit", details={
                "site": site, "query": gap_query,
                "results_count": len(site_results),
            })

            extract_tasks = [
                _extract_from_tavily_result(r, gap_description, llm_with_schema, extract_semaphore)
                for r in site_results
            ]
            extract_results = await asyncio.gather(*extract_tasks, return_exceptions=True)
            for r in extract_results:
                if isinstance(r, list):
                    findings.extend(r)

            # Stop after first site that yields findings
            if findings:
                break

    return findings


async def _do_one_image_search(
    query: str,
    category: str,
    entity: str,
) -> list[dict]:
    """Run a single Tavily image search in a thread."""
    try:
        results = await asyncio.to_thread(search_images, query=query, max_results=3)
        found: list[dict] = []
        for img in results:
            url = img.get("url", "")
            if url:
                found.append({
                    "url": url,
                    "category": category,
                    "entity": entity,
                    "description": f"{category}: {entity}",
                })
        return found
    except Exception as exc:
        log.log_step(Step.AGENT_FARM_GAP, "image_search_failed",
                     level="WARNING", details={
                         "query": query, "error": str(exc)[:200],
                     })
        return []


async def _search_images_for_entities(
    disease_entities: list[str],
    crop_entities: list[str],
) -> list[dict]:
    """Run Tavily image searches concurrently for disease symptoms and healthy crop references."""
    search_tasks: list[tuple[str, str, str]] = []

    for disease in disease_entities:
        search_tasks.append((
            f"{disease} symptoms plant photo",
            "diseases",
            disease,
        ))

    for crop in crop_entities:
        search_tasks.append((
            f"healthy {crop} plant field photo",
            "healthy",
            crop,
        ))

    results = await asyncio.gather(*[
        _do_one_image_search(query, category, entity)
        for query, category, entity in search_tasks
    ], return_exceptions=True)

    image_urls: list[dict] = []
    for r in results:
        if isinstance(r, list):
            image_urls.extend(r)

    log.log_step(Step.AGENT_FARM_GAP, "image_search_complete", details={
        "queries": len(search_tasks), "images_found": len(image_urls),
    })

    return image_urls


# ------------------------------------------------------------------
# Main phase function (LangGraph node)
# ------------------------------------------------------------------


async def gap_analysis(state: AgentFarmState) -> dict[str, Any]:
    """Phase C: Analyze coverage gaps, search for missing data, gather images.

    Reads from state: findings, crops, region
    Writes to state: findings (augmented), identified_gaps, gap_search_queries,
                     image_urls, status_messages, current_phase
    """
    findings = list(state.get("findings", []))
    crops = state.get("crops", [])
    messages: list[str] = list(state.get("status_messages", []))
    messages.append("Phase C: Analyzing knowledge gaps...")

    log.log_step(Step.AGENT_FARM_GAP, "phase_start", details={
        "existing_findings": len(findings), "crops": crops,
    })

    # ---- Step 1: Ask 31B to identify gaps ----

    coverage_summary = _build_coverage_summary(findings, crops)
    prompt = _GAP_ANALYSIS_PROMPT.format(
        crops=", ".join(crops),
        coverage_summary=coverage_summary,
    )

    planner_llm = get_planner_llm()
    planner_with_schema = planner_llm.with_structured_output(GapAnalysisOutput)

    await rate_limiter.wait(_PLANNER_MODEL)

    try:
        with log.timed(Step.AGENT_FARM_GAP, "gap_identification") as t:
            gap_output: GapAnalysisOutput = await planner_with_schema.ainvoke(prompt)
            t.set(details={
                "gaps_found": len(gap_output.gaps),
                "coverage_summary": gap_output.coverage_summary[:200],
            })
        rate_limiter.on_success(_PLANNER_MODEL)
    except Exception as exc:
        error_str = str(exc)
        if "429" in error_str or "rate" in error_str.lower():
            rate_limiter.on_rate_limit(_PLANNER_MODEL)
        log.log_step(Step.AGENT_FARM_GAP, "gap_identification_failed",
                     level="ERROR", details={"error": error_str[:200]})
        # Can't identify gaps — return state unchanged
        messages.append("Gap analysis failed — proceeding with existing findings")
        return {
            "findings": findings,
            "identified_gaps": [],
            "gap_search_queries": [],
            "image_urls": [],
            "status_messages": messages,
            "current_phase": "gap_analysis",
        }

    identified_gaps = [g.description for g in gap_output.gaps]
    gap_queries = [g.search_query for g in gap_output.gaps]

    messages.append(
        f"Identified {len(gap_output.gaps)} gaps — "
        f"searching with preferred domains + site-specific fallback..."
    )

    log.log_step(Step.AGENT_FARM_GAP, "gaps_identified", details={
        "count": len(gap_output.gaps),
        "high_priority": sum(1 for g in gap_output.gaps if g.priority == "high"),
        "domains": [g.domain for g in gap_output.gaps],
    })

    # ---- Step 2: Search and extract for each gap ----

    research_llm = get_research_llm()
    research_with_schema = research_llm.with_structured_output(ExtractionOutput)

    search_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_SEARCH)
    extract_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_EXTRACT)

    search_tasks = [
        _search_for_gap(
            gap_query=gap.search_query,
            gap_description=gap.description,
            llm_with_schema=research_with_schema,
            search_semaphore=search_semaphore,
            extract_semaphore=extract_semaphore,
        )
        for gap in gap_output.gaps
    ]

    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    new_findings: list[Finding] = []
    gaps_filled = 0
    gaps_unfilled = 0

    for i, result in enumerate(search_results):
        gap = gap_output.gaps[i]
        if isinstance(result, BaseException):
            gaps_unfilled += 1
            log.log_step(Step.AGENT_FARM_GAP, "gap_search_exception",
                         level="WARNING", details={
                             "gap": gap.description, "error": str(result)[:200],
                         })
        elif result:
            gaps_filled += 1
            new_findings.extend(result)
        else:
            gaps_unfilled += 1

    findings.extend(new_findings)

    messages.append(
        f"Filled {gaps_filled}/{len(gap_output.gaps)} gaps "
        f"({len(new_findings)} new findings)"
    )

    # ---- Step 3: Image search ----

    # Collect disease and crop entity names for image search
    disease_entities = list({
        f.entity_name for f in findings if f.domain == "disease"
    })
    crop_entities = list({c.lower() for c in crops})

    image_urls = await _search_images_for_entities(disease_entities, crop_entities)
    messages.append(f"Found {len(image_urls)} images for diseases and crops")

    # ---- Log summary ----

    log.log_step(Step.AGENT_FARM_GAP, "phase_complete", details={
        "gaps_identified": len(gap_output.gaps),
        "gaps_filled": gaps_filled,
        "gaps_unfilled": gaps_unfilled,
        "new_findings": len(new_findings),
        "total_findings": len(findings),
        "images_found": len(image_urls),
    })

    return {
        "findings": findings,
        "identified_gaps": identified_gaps,
        "gap_search_queries": gap_queries,
        "image_urls": image_urls,
        "status_messages": messages,
        "current_phase": "gap_analysis",
    }
