"""Phase B: Knowledge extraction (LLM per section → Finding objects).

Each PageSection gets one Gemma 4 26B call via get_research_llm() with
Pydantic structured output. The LLM produces FindingExtract objects
guided by rich Field(description=...) annotations.

Climate records from Phase A skip LLM — they're converted directly to
Finding objects in Python.

Concurrency: asyncio.Semaphore caps concurrent LLM calls (default 10).
The AdaptiveRateLimiter handles per-model sliding window + backoff.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.agent_farm.models import (
    ExtractionOutput,
    Finding,
    PageSection,
    finding_extract_to_dataclass,
)
from app.agent_farm.rate_limiter import rate_limiter
from app.agent_farm.state import AgentFarmState
from app.config import settings
from app.logger import Step, pipeline_logger as log
from app.models.online_llm import get_research_llm, invoke_structured

_MAX_CONCURRENT = 10
_MODEL_NAME = settings.online_model_research


# ------------------------------------------------------------------
# Prompt template
# ------------------------------------------------------------------

_EXTRACTION_PROMPT = """\
You are an agricultural knowledge extraction agent. Your task is to extract
specific, actionable knowledge from the text below.

CROP CONTEXT: {crop}
SECTION TYPE HINT: {section_type}
SOURCE: {source}

--- TEXT ---
{content}
--- END TEXT ---

Extract all distinct knowledge nuggets from this text. For each finding:
- Assign the correct domain (crop, disease, treatment, pest, variety, climate, \
soil, fertilization, storage, planting, practice, regional)
- Name the specific entity (e.g., "Cassava Mosaic Disease", not "a disease")
- Extract 200-800 chars of rich, specific content with numbers and details
- List related entities mentioned
- Include any structured data you can extract in raw_data (numbers, percentages, ranges)
- Set confidence based on how specific and reliable the source text is

Focus on information useful for a field worker in {region}.
"""


# ------------------------------------------------------------------
# Single section extraction
# ------------------------------------------------------------------


async def _extract_section(
    section: PageSection,
    llm,
    semaphore: asyncio.Semaphore,
    region: str,
) -> list[Finding]:
    """Extract findings from a single section via LLM call."""
    async with semaphore:
        model_name = _MODEL_NAME
        await rate_limiter.wait(model_name)

        prompt = _EXTRACTION_PROMPT.format(
            crop=section.crop or "unknown",
            section_type=section.section_type or "general",
            source=section.source_url,
            content=section.content,
            region=region,
        )

        # Include table content if present
        if section.tables:
            table_text = "\n\n--- TABLES ---\n"
            for i, table in enumerate(section.tables):
                table_text += f"\nTable {i + 1}:\n"
                for row in table:
                    table_text += " | ".join(row) + "\n"
            prompt += table_text

        source_ref = f"{section.source_name} — {section.heading}"

        try:
            with log.timed(Step.AGENT_FARM_EXTRACT, "llm_call") as t:
                result = await invoke_structured(llm, prompt, ExtractionOutput)
                t.set(details={
                    "source": section.source_name,
                    "heading": section.heading,
                    "crop": section.crop,
                    "findings_count": len(result.findings),
                })

            rate_limiter.on_success(model_name)

            return [
                finding_extract_to_dataclass(fe, source=source_ref)
                for fe in result.findings
            ]

        except Exception as exc:
            error_str = str(exc)
            if "429" in error_str or "rate" in error_str.lower():
                rate_limiter.on_rate_limit(model_name)

            log.log_step(Step.AGENT_FARM_EXTRACT, "extraction_failed",
                         level="WARNING", details={
                             "source": section.source_name,
                             "heading": section.heading,
                             "error": error_str[:200],
                         })
            return []


# ------------------------------------------------------------------
# Climate → Finding conversion (no LLM)
# ------------------------------------------------------------------


def _climate_records_to_findings(climate_records: list[dict]) -> list[Finding]:
    """Convert Phase A climate records directly to Finding objects."""
    findings: list[Finding] = []

    for rec in climate_records:
        region = rec.get("region", "unknown")
        month = rec.get("month", 0)

        # Build descriptive content from structured data
        parts: list[str] = [f"Climate data for {region}, month {month}."]
        if rec.get("rainfall_mm") is not None:
            parts.append(f"Average rainfall: {rec['rainfall_mm']} mm.")
        if rec.get("temperature_avg_c") is not None:
            parts.append(f"Average temperature: {rec['temperature_avg_c']}°C.")
        if rec.get("humidity_pct") is not None:
            parts.append(f"Relative humidity: {rec['humidity_pct']}%.")
        if rec.get("drought_risk"):
            parts.append(f"Drought risk: {rec['drought_risk']}.")
        if rec.get("evapotranspiration_mm") is not None:
            parts.append(f"Evapotranspiration: {rec['evapotranspiration_mm']} mm.")

        content = " ".join(parts)

        # raw_data = the full structured dict (minus region/month which are in entity_name)
        raw = {k: v for k, v in rec.items() if k not in ("region", "month") and v is not None}

        findings.append(Finding(
            domain="climate",
            entity_name=f"{region} month {month}",
            content=content,
            related_entities=[region],
            source=f"weather-and-climate.com ({region})",
            confidence=0.95,  # direct table parsing, high confidence
            raw_data=raw,
        ))

    return findings


# ------------------------------------------------------------------
# Main phase function (LangGraph node)
# ------------------------------------------------------------------


async def knowledge_extraction(state: AgentFarmState) -> dict[str, Any]:
    """Phase B: Extract findings from all sections via LLM + climate conversion.

    Reads from state: sections, climate_records
    Writes to state: findings, status_messages, current_phase
    """
    sections = state.get("sections", [])
    climate_records = state.get("climate_records", [])
    region = state.get("region", "the target region")
    messages: list[str] = list(state.get("status_messages", []))
    messages.append(f"Phase B: Extracting knowledge from {len(sections)} sections...")

    log.log_step(Step.AGENT_FARM_EXTRACT, "phase_start", details={
        "sections_count": len(sections),
        "climate_records_count": len(climate_records),
    })

    # ---- Set up LLM ----

    llm = get_research_llm()

    # ---- Extract from all sections concurrently ----

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    tasks = [
        _extract_section(section, llm, semaphore, region)
        for section in sections
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # ---- Collect findings ----

    all_findings: list[Finding] = []
    succeeded = 0
    failed = 0

    for result in results:
        if isinstance(result, BaseException):
            failed += 1
            log.log_step(Step.AGENT_FARM_EXTRACT, "task_exception",
                         level="WARNING", details={"error": str(result)[:200]})
        elif isinstance(result, list):
            succeeded += 1
            all_findings.extend(result)
        else:
            failed += 1

    # ---- Convert climate records to findings (no LLM) ----

    climate_findings = _climate_records_to_findings(climate_records)
    all_findings.extend(climate_findings)

    # ---- Log summary ----

    domain_counts: dict[str, int] = {}
    for f in all_findings:
        domain_counts[f.domain] = domain_counts.get(f.domain, 0) + 1

    messages.append(
        f"Extracted {len(all_findings)} findings "
        f"({succeeded} sections succeeded, {failed} failed, "
        f"{len(climate_findings)} climate records converted)"
    )

    log.log_step(Step.AGENT_FARM_EXTRACT, "phase_complete", details={
        "total_findings": len(all_findings),
        "sections_succeeded": succeeded,
        "sections_failed": failed,
        "climate_findings": len(climate_findings),
        "domain_counts": domain_counts,
    })

    return {
        "findings": all_findings,
        "status_messages": messages,
        "current_phase": "extracting",
    }
