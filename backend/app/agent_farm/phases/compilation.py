"""Phase D: Decomposed compilation (11 sequential per-table steps).

Takes all Finding objects from Phases B+C and produces 11 compiled
JSON outputs — one per SQLite table — in strict FK-safe order.

Each step:
  1. Filters findings by domain relevance
  2. Builds a prompt with FK context from previous steps
  3. Calls invoke_structured(get_planner_llm(), prompt, Model)
  4. Validates FK references, skips invalid records
  5. Writes JSON file to disk

Retry escalation on validation failure:
  Attempt 1: 31B, temp=0.3, normal prompt
  Attempt 2: 31B, temp=0.3, prompt + validation error
  Attempt 3: 31B, temp=0.5, prompt + validation error

Climate records (step 5) skip LLM — converted directly from
Finding.raw_data since they're already structured numbers.
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.agent_farm.models import (
    ClimateRecord,
    CompilationOutput,
    CropDiseaseRecord,
    CropRecord,
    DiseaseRecord,
    FertilizationRecord,
    Finding,
    PestRecord,
    PlantingCalendarRecord,
    SoilRecord,
    StorageRecord,
    TreatmentRecord,
    VarietyRecord,
    record_to_sqlite_row,
)
from app.agent_farm.rate_limiter import rate_limiter
from app.agent_farm.state import AgentFarmState
from app.config import settings
from app.logger import Step, pipeline_logger as log
from app.models.online_llm import get_planner_llm, invoke_structured

_MAX_RETRIES = 3

_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ============================================================
# Step configuration
# ============================================================


@dataclass
class _StepConfig:
    """Configuration for a single compilation step."""

    table_name: str
    model_class: type[BaseModel]
    domain_filter: list[str]
    fk_fields: dict[str, str] = field(default_factory=dict)


# Strict FK-safe order — each step can only reference IDs from earlier steps
_COMPILATION_STEPS: list[_StepConfig] = [
    _StepConfig("crops", CropRecord, ["crop"]),
    _StepConfig("diseases", DiseaseRecord, ["disease"]),
    _StepConfig("crop_diseases", CropDiseaseRecord, ["crop", "disease"],
                fk_fields={"crop_id": "crops", "disease_id": "diseases"}),
    _StepConfig("treatments", TreatmentRecord, ["treatment", "disease"],
                fk_fields={"disease_id": "diseases"}),
    _StepConfig("climate", ClimateRecord, ["climate"]),
    _StepConfig("pests", PestRecord, ["pest"],
                fk_fields={"crop_id": "crops"}),
    _StepConfig("varieties", VarietyRecord, ["variety"],
                fk_fields={"crop_id": "crops"}),
    _StepConfig("fertilization_schedule", FertilizationRecord, ["fertilization"],
                fk_fields={"crop_id": "crops"}),
    _StepConfig("planting_calendar", PlantingCalendarRecord, ["planting"],
                fk_fields={"crop_id": "crops"}),
    _StepConfig("storage_guidelines", StorageRecord, ["storage"],
                fk_fields={"crop_id": "crops"}),
    _StepConfig("soil_requirements", SoilRecord, ["soil"],
                fk_fields={"crop_id": "crops"}),
]


# ============================================================
# Pydantic wrappers for structured output (list of records)
# ============================================================

# LLM structured output needs a top-level model wrapping the list.
# We create one per table to keep Field descriptions table-specific.

class _CropList(BaseModel):
    records: list[CropRecord]

class _DiseaseList(BaseModel):
    records: list[DiseaseRecord]

class _CropDiseaseList(BaseModel):
    records: list[CropDiseaseRecord]

class _TreatmentList(BaseModel):
    records: list[TreatmentRecord]

class _ClimateList(BaseModel):
    records: list[ClimateRecord]

class _PestList(BaseModel):
    records: list[PestRecord]

class _VarietyList(BaseModel):
    records: list[VarietyRecord]

class _FertilizationList(BaseModel):
    records: list[FertilizationRecord]

class _PlantingCalendarList(BaseModel):
    records: list[PlantingCalendarRecord]

class _StorageList(BaseModel):
    records: list[StorageRecord]

class _SoilList(BaseModel):
    records: list[SoilRecord]


_LIST_MODEL_MAP: dict[str, type[BaseModel]] = {
    "crops": _CropList,
    "diseases": _DiseaseList,
    "crop_diseases": _CropDiseaseList,
    "treatments": _TreatmentList,
    "climate": _ClimateList,
    "pests": _PestList,
    "varieties": _VarietyList,
    "fertilization_schedule": _FertilizationList,
    "planting_calendar": _PlantingCalendarList,
    "storage_guidelines": _StorageList,
    "soil_requirements": _SoilList,
}


# ============================================================
# Prompt helpers
# ============================================================


def _filter_findings(findings: list[Finding], domains: list[str]) -> list[Finding]:
    """Filter findings to only those matching the given domains."""
    return [f for f in findings if f.domain in domains]


def _build_findings_context(findings: list[Finding]) -> str:
    """Format findings as bullet points for the compilation prompt."""
    if not findings:
        return "(No findings available for this domain)"

    lines: list[str] = []
    for f in findings:
        line = f"- [{f.domain}] {f.entity_name}: {f.content[:400]}"
        if f.related_entities:
            line += f" (related: {', '.join(f.related_entities[:5])})"
        if f.raw_data:
            # Include key structured data inline
            raw_parts = [f"{k}={v}" for k, v in list(f.raw_data.items())[:5]]
            line += f" | data: {', '.join(raw_parts)}"
        lines.append(line)

    return "\n".join(lines)


def _build_id_context(compiled_ids: dict[str, dict[int, str]],
                      fk_fields: dict[str, str]) -> str:
    """Format previously-compiled IDs for FK reference in prompts."""
    if not fk_fields:
        return ""

    parts: list[str] = []
    for fk_field, source_table in fk_fields.items():
        ids = compiled_ids.get(source_table, {})
        if ids:
            id_list = ", ".join(f"{k}: '{v}'" for k, v in sorted(ids.items()))
            parts.append(f"Valid {fk_field} values (from {source_table}): {{{id_list}}}")
        else:
            parts.append(f"WARNING: No {source_table} records compiled yet — {fk_field} has no valid values")

    return "\n".join(parts)


# ============================================================
# Prompt templates
# ============================================================


_COMPILATION_PROMPT = """\
You are compiling {table_name} records for a Knowledge Pack targeting \
the Casamance region of Senegal. This pack covers crops: cassava, rice, \
maize, groundnut, and tomato.

Compile structured records from the research findings below. Each record \
must match the schema exactly. Use the Field descriptions in the schema \
as guidance for what each field expects.

RULES:
- Assign sequential integer IDs starting from 1
- Set confidence based on how well-supported the data is by the findings
- List any fields where you lack reliable data in data_gaps
- Do NOT hallucinate data — use null/None for fields you cannot fill
- Prefer specific, actionable information over generic descriptions
- For Casamance/Senegal context: use local variety names, XOF currency, \
  local materials, and region-specific practices where known
{fk_instructions}

--- RESEARCH FINDINGS ---
{findings_context}
--- END FINDINGS ---
{id_context}

Compile all {table_name} records from these findings. \
Aim for {expected_range} records based on the data available.
"""


_TABLE_GUIDANCE: dict[str, dict[str, str]] = {
    "crops": {
        "fk_instructions": "",
        "expected_range": "5",
    },
    "diseases": {
        "fk_instructions": "",
        "expected_range": "12-20",
    },
    "crop_diseases": {
        "fk_instructions": (
            "\n- CRITICAL: crop_id and disease_id MUST use ONLY the IDs listed below."
            "\n- Create one record per crop-disease pairing found in the findings."
            "\n- If a disease affects multiple crops, create a record for each."
        ),
        "expected_range": "12-20",
    },
    "treatments": {
        "fk_instructions": (
            "\n- CRITICAL: disease_id MUST use ONLY the IDs listed below."
            "\n- Include both organic and conventional treatments."
            "\n- Emphasize treatments using locally available materials in Casamance."
        ),
        "expected_range": "25-35",
    },
    "climate": {
        "fk_instructions": "",
        "expected_range": "12 (one per month)",
    },
    "pests": {
        "fk_instructions": (
            "\n- CRITICAL: crop_id MUST use ONLY the IDs listed below."
            "\n- Include identification notes useful for field diagnosis."
        ),
        "expected_range": "10-15",
    },
    "varieties": {
        "fk_instructions": (
            "\n- CRITICAL: crop_id MUST use ONLY the IDs listed below."
            "\n- Prioritize varieties available in Casamance/Senegal."
            "\n- Include local names where known."
        ),
        "expected_range": "15-20",
    },
    "fertilization_schedule": {
        "fk_instructions": (
            "\n- CRITICAL: crop_id MUST use ONLY the IDs listed below."
            "\n- Include organic alternatives where possible."
            "\n- Cost estimates in XOF (West African CFA francs)."
        ),
        "expected_range": "15-20",
    },
    "planting_calendar": {
        "fk_instructions": (
            "\n- CRITICAL: crop_id MUST use ONLY the IDs listed below."
            "\n- Calendar for Casamance wet season (June-October) and dry season."
        ),
        "expected_range": "20-25",
    },
    "storage_guidelines": {
        "fk_instructions": (
            "\n- CRITICAL: crop_id MUST use ONLY the IDs listed below."
            "\n- Emphasize local materials available in Casamance."
        ),
        "expected_range": "5-8",
    },
    "soil_requirements": {
        "fk_instructions": (
            "\n- CRITICAL: crop_id MUST use ONLY the IDs listed below."
            "\n- Include locally available soil amendments."
        ),
        "expected_range": "5",
    },
}


# ============================================================
# FK validation
# ============================================================


def _validate_fks(
    records: list[BaseModel],
    fk_fields: dict[str, str],
    compiled_ids: dict[str, dict[int, str]],
    table_name: str,
) -> tuple[list[BaseModel], int]:
    """Validate FK references. Returns (valid_records, skipped_count)."""
    if not fk_fields:
        return records, 0

    valid: list[BaseModel] = []
    skipped = 0

    for record in records:
        record_dict = record.model_dump()
        is_valid = True

        for fk_field, source_table in fk_fields.items():
            fk_value = record_dict.get(fk_field)
            valid_ids = compiled_ids.get(source_table, {})

            if fk_value not in valid_ids:
                log.log_step(Step.AGENT_FARM_COMPILE, "fk_invalid",
                             level="WARNING", details={
                                 "table": table_name,
                                 "field": fk_field,
                                 "value": fk_value,
                                 "valid_ids": list(valid_ids.keys()),
                             })
                is_valid = False
                break

        if is_valid:
            valid.append(record)
        else:
            skipped += 1

    return valid, skipped


# ============================================================
# Climate direct conversion (no LLM)
# ============================================================


def _climate_from_findings(findings: list[Finding]) -> list[ClimateRecord]:
    """Convert climate findings directly to ClimateRecord objects.

    Climate findings from Phase B already have structured data in raw_data
    (confidence=0.95, from direct HTML table parsing). No LLM needed.
    """
    climate_findings = [f for f in findings if f.domain == "climate"]
    records: list[ClimateRecord] = []
    next_id = 1

    for f in climate_findings:
        raw = f.raw_data

        # Parse month from entity_name ("Casamance month 7" -> 7)
        month = raw.get("month")
        if month is None:
            parts = f.entity_name.split()
            for j, part in enumerate(parts):
                if part == "month" and j + 1 < len(parts):
                    try:
                        month = int(parts[j + 1])
                    except ValueError:
                        pass
                    break

        if month is None or not (1 <= month <= 12):
            continue

        # Determine drought risk from rainfall if not in raw_data
        drought_risk = raw.get("drought_risk")
        if drought_risk is None:
            rainfall = raw.get("rainfall_mm")
            if rainfall is not None:
                if rainfall < 10:
                    drought_risk = "severe"
                elif rainfall < 30:
                    drought_risk = "high"
                elif rainfall < 100:
                    drought_risk = "medium"
                else:
                    drought_risk = "low"

        records.append(ClimateRecord(
            id=next_id,
            region=raw.get("region", "Casamance"),
            month=month,
            rainfall_mm=raw.get("rainfall_mm"),
            temperature_avg_c=raw.get("temperature_avg_c"),
            humidity_pct=raw.get("humidity_pct"),
            drought_risk=drought_risk,
            notes=raw.get("notes"),
            evapotranspiration_mm=raw.get("evapotranspiration_mm"),
            flooding_risk=raw.get("flooding_risk"),
            confidence=f.confidence,
            data_gaps=[],
        ))
        next_id += 1

    return records


# ============================================================
# Single table compilation (with retry)
# ============================================================


async def _compile_one_table(
    step: _StepConfig,
    findings: list[Finding],
    compiled_ids: dict[str, dict[int, str]],
) -> tuple[list[BaseModel], int]:
    """Compile one table with retry escalation.

    Attempt 1: 31B, temp=0.3, normal prompt
    Attempt 2: 31B, temp=0.3, prompt + validation error
    Attempt 3: 31B, temp=0.5, prompt + validation error

    Returns (records, llm_calls_made).
    """
    table = step.table_name
    relevant = _filter_findings(findings, step.domain_filter)
    guidance = _TABLE_GUIDANCE.get(table, {"fk_instructions": "", "expected_range": "5-15"})

    findings_ctx = _build_findings_context(relevant)
    id_ctx = _build_id_context(compiled_ids, step.fk_fields)

    base_prompt = _COMPILATION_PROMPT.format(
        table_name=table,
        fk_instructions=guidance["fk_instructions"],
        findings_context=findings_ctx,
        id_context=f"\n--- VALID FK REFERENCES ---\n{id_ctx}\n--- END FK REFERENCES ---" if id_ctx else "",
        expected_range=guidance["expected_range"],
    )

    list_model = _LIST_MODEL_MAP[table]
    last_error: str = ""

    log.log_step(Step.AGENT_FARM_COMPILE, "compile_step_start", details={
        "table": table,
        "relevant_findings": len(relevant),
        "fk_deps": list(step.fk_fields.keys()),
    })

    for attempt in range(1, _MAX_RETRIES + 1):
        # Build prompt — append error on retry
        prompt = base_prompt
        if last_error:
            prompt += (
                f"\n\n--- PREVIOUS ATTEMPT FAILED ---\n"
                f"Fix these validation errors and try again:\n{last_error}\n"
                f"--- END ERRORS ---"
            )

        # Select temperature for this attempt
        temperature = 0.5 if attempt == 3 else 0.3

        log.log_step(Step.AGENT_FARM_COMPILE, "compile_attempt", details={
            "table": table,
            "attempt": attempt,
            "temperature": temperature,
            "has_error_context": bool(last_error),
        })

        await rate_limiter.wait(settings.online_model_large)

        try:
            llm = get_planner_llm(temperature=temperature)

            with log.timed(Step.AGENT_FARM_COMPILE, "compile_llm_call") as t:
                result = await invoke_structured(llm, prompt, list_model, max_retries=0)
                records = result.records
                t.set(details={
                    "table": table,
                    "attempt": attempt,
                    "records_returned": len(records),
                })

            rate_limiter.on_success(settings.online_model_large)

            # FK validation
            valid_records, skipped = _validate_fks(
                records, step.fk_fields, compiled_ids, table,
            )

            if skipped > 0:
                log.log_step(Step.AGENT_FARM_COMPILE, "compile_fk_validation",
                             level="WARNING", details={
                                 "table": table,
                                 "valid": len(valid_records),
                                 "skipped": skipped,
                             })

            log.log_step(Step.AGENT_FARM_COMPILE, "compile_step_complete", details={
                "table": table,
                "records": len(valid_records),
                "skipped_fk": skipped,
                "attempt": attempt,
            })

            return valid_records, attempt

        except (ValidationError, ValueError) as exc:
            last_error = str(exc)[:1000]
            log.log_step(Step.AGENT_FARM_COMPILE, "compile_retry",
                         level="WARNING", details={
                             "table": table,
                             "attempt": attempt,
                             "temperature": temperature,
                             "error": last_error[:300],
                         })

        except Exception as exc:
            error_str = str(exc)
            if "429" in error_str or "rate" in error_str.lower():
                rate_limiter.on_rate_limit(settings.online_model_large)

            last_error = error_str[:1000]
            log.log_step(Step.AGENT_FARM_COMPILE, "compile_retry",
                         level="WARNING", details={
                             "table": table,
                             "attempt": attempt,
                             "error_type": type(exc).__name__,
                             "error": error_str[:300],
                         })

    # All retries exhausted
    log.log_step(Step.AGENT_FARM_COMPILE, "compile_step_failed",
                 level="ERROR", details={
                     "table": table,
                     "attempts": _MAX_RETRIES,
                     "last_error": last_error[:300],
                 })
    return [], _MAX_RETRIES


# ============================================================
# Extract IDs from compiled records
# ============================================================


def _extract_ids(table_name: str, records: list[BaseModel]) -> dict[int, str]:
    """Extract {id: name} mapping from compiled records for FK context."""
    ids: dict[int, str] = {}

    for record in records:
        data = record.model_dump()
        record_id = data.get("id")
        if record_id is None:
            continue

        # Use the most descriptive name field available
        name = data.get("name") or data.get("method") or data.get("activity") or str(record_id)
        ids[record_id] = name

    return ids


# ============================================================
# Main phase function (LangGraph node)
# ============================================================


async def compilation(state: AgentFarmState) -> dict[str, Any]:
    """Phase D: Compile all findings into 11 structured JSON tables.

    Reads from state: findings
    Writes to state: compilation, json_output_dir, status_messages, current_phase
    """
    findings = state.get("findings", [])
    messages: list[str] = list(state.get("status_messages", []))
    messages.append(f"Phase D: Compiling {len(findings)} findings into structured records...")

    log.log_step(Step.AGENT_FARM_COMPILE, "phase_start", details={
        "total_findings": len(findings),
        "domain_counts": _count_domains(findings),
    })

    phase_start = time.perf_counter()

    # Create temp directory for JSON output
    json_dir = tempfile.mkdtemp(prefix="fieldpack_compile_")
    json_path = Path(json_dir)

    # Track compiled IDs for FK references across steps
    compiled_ids: dict[str, dict[int, str]] = {}

    # Track all compiled records for CompilationOutput
    all_records: dict[str, list[BaseModel]] = {}
    total_llm_calls = 0

    for step in _COMPILATION_STEPS:
        table = step.table_name

        # Climate: direct conversion, no LLM
        if table == "climate":
            records = _climate_from_findings(findings)
            log.log_step(Step.AGENT_FARM_COMPILE, "compile_step_complete", details={
                "table": table,
                "records": len(records),
                "method": "direct_conversion",
            })
        else:
            records, calls_made = await _compile_one_table(step, findings, compiled_ids)
            total_llm_calls += calls_made

        all_records[table] = records

        # Extract IDs for downstream FK references
        ids = _extract_ids(table, records)
        compiled_ids[table] = ids

        # Write JSON file
        rows = [record_to_sqlite_row(table, r) for r in records]
        out_file = json_path / f"{table}.json"
        out_file.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")

        log.log_step(Step.AGENT_FARM_COMPILE, "json_written", details={
            "table": table,
            "records": len(records),
            "file": str(out_file),
        })

    # Build CompilationOutput
    output = CompilationOutput(
        crops=all_records.get("crops", []),
        diseases=all_records.get("diseases", []),
        crop_diseases=all_records.get("crop_diseases", []),
        treatments=all_records.get("treatments", []),
        climate=all_records.get("climate", []),
        pests=all_records.get("pests", []),
        varieties=all_records.get("varieties", []),
        fertilization_schedule=all_records.get("fertilization_schedule", []),
        planting_calendar=all_records.get("planting_calendar", []),
        storage_guidelines=all_records.get("storage_guidelines", []),
        soil_requirements=all_records.get("soil_requirements", []),
    )

    # Summary
    phase_duration_ms = (time.perf_counter() - phase_start) * 1000
    table_counts = {table: len(recs) for table, recs in all_records.items()}
    total_records = sum(table_counts.values())

    messages.append(
        f"Compiled {total_records} records across 11 tables "
        f"({total_llm_calls} LLM calls, {phase_duration_ms/1000:.1f}s)"
    )

    log.log_step(Step.AGENT_FARM_COMPILE, "phase_complete", details={
        "total_records": total_records,
        "table_counts": table_counts,
        "total_llm_calls": total_llm_calls,
        "duration_ms": round(phase_duration_ms, 1),
        "json_dir": json_dir,
    })

    return {
        "compilation": output,
        "json_output_dir": json_dir,
        "status_messages": messages,
        "current_phase": "compiling",
    }


# ============================================================
# Chunk generation (called separately by graph after compilation)
# ============================================================


def _make_id(entity: str, record_id: int, topic: str, chunk_type: str) -> str:
    """Generate a human-readable document ID for ChromaDB."""
    return f"{entity}_{record_id:03d}_{topic}_{chunk_type}"


def _get_crop_name(crop_id: int, crops: list[CropRecord]) -> str:
    """Look up crop name by ID."""
    for c in crops:
        if c.id == crop_id:
            return c.name.lower()
    return "unknown"


def generate_chunks_from_compilation(
    comp: CompilationOutput,
) -> dict[str, list[dict]]:
    """Generate ChromaDB parent/child chunk pairs from compiled records.

    Follows seed_chunks.py patterns exactly:
    - _make_id() convention for IDs
    - Parent/child pairs per topic
    - All metadata values are strings
    - Returns dict[collection_name, list[chunk_dict]]
    """
    log.log_step(Step.AGENT_FARM_COMPILE, "chunks_generation_start", details={
        "diseases": len(comp.diseases),
        "treatments": len(comp.treatments),
        "crops": len(comp.crops),
        "varieties": len(comp.varieties),
        "climate": len(comp.climate),
    })

    disease_knowledge: list[dict] = []
    treatment_guides: list[dict] = []
    farming_practices: list[dict] = []
    regional_context: list[dict] = []

    # --- Disease knowledge chunks ---

    # Build crop-disease lookup (first crop wins — deterministic)
    crop_for_disease: dict[int, str] = {}
    for cd in comp.crop_diseases:
        if cd.disease_id not in crop_for_disease:
            crop_name = _get_crop_name(cd.crop_id, comp.crops)
            crop_for_disease[cd.disease_id] = crop_name

    for disease in comp.diseases:
        d_id = disease.id
        crop = crop_for_disease.get(d_id, "unknown")
        short_name = disease.name.lower().replace(" ", "_")[:20]
        severity = disease.severity_scale
        d_type = disease.type

        # Symptoms pair
        symptoms_child = (
            f"My {crop} plant looks sick. {disease.visual_markers[:200]}"
        ).strip()

        disease_knowledge.append({
            "id": _make_id(short_name, d_id, "symptoms", "child"),
            "content": symptoms_child,
            "metadata": {
                "disease_id": str(d_id),
                "disease_name": disease.name,
                "crop": crop,
                "type": d_type,
                "severity": severity,
                "topic_id": f"{short_name}_{d_id:03d}_symptoms",
                "chunk_type": "child",
            },
        })

        symptoms_parent = (
            f"{disease.name}\n"
            f"Type: {d_type}\n"
            f"Severity: {severity}\n"
            f"Crops affected: {crop}\n\n"
            f"Symptoms:\n{disease.symptoms_text}\n\n"
            f"Visual identification:\n{disease.visual_markers}\n\n"
            f"How it spreads:\n{disease.spread_mechanism or 'Unknown'}"
        )

        disease_knowledge.append({
            "id": _make_id(short_name, d_id, "symptoms", "parent"),
            "content": symptoms_parent,
            "metadata": {
                "disease_id": str(d_id),
                "disease_name": disease.name,
                "crop": crop,
                "type": d_type,
                "severity": severity,
                "topic_id": f"{short_name}_{d_id:03d}_symptoms",
                "chunk_type": "parent",
            },
        })

        # Prevention pair
        if disease.prevention_notes:
            prevention_child = (
                f"How to prevent {disease.name.lower()} in {crop}. "
                f"{disease.prevention_notes[:150]}"
            ).strip()

            disease_knowledge.append({
                "id": _make_id(short_name, d_id, "prevention", "child"),
                "content": prevention_child,
                "metadata": {
                    "disease_id": str(d_id),
                    "disease_name": disease.name,
                    "crop": crop,
                    "type": d_type,
                    "severity": severity,
                    "topic_id": f"{short_name}_{d_id:03d}_prevention",
                    "chunk_type": "child",
                },
            })

            prevention_parent = (
                f"Prevention of {disease.name}\n"
                f"Crop: {crop}\n\n"
                f"{disease.prevention_notes}\n\n"
                f"Disease type: {d_type}\n"
                f"Spread mechanism: {disease.spread_mechanism or 'Unknown'}"
            )

            disease_knowledge.append({
                "id": _make_id(short_name, d_id, "prevention", "parent"),
                "content": prevention_parent,
                "metadata": {
                    "disease_id": str(d_id),
                    "disease_name": disease.name,
                    "crop": crop,
                    "type": d_type,
                    "severity": severity,
                    "topic_id": f"{short_name}_{d_id:03d}_prevention",
                    "chunk_type": "parent",
                },
            })

    log.log_step(Step.AGENT_FARM_COMPILE, "chunks_collection_generated", details={
        "collection": "disease_knowledge",
        "chunks": len(disease_knowledge),
    })

    # --- Treatment guide chunks ---

    for treatment in comp.treatments:
        t_id = treatment.id
        d_id = treatment.disease_id

        # Find disease name
        disease_name = "unknown disease"
        disease_crop = "unknown"
        for d in comp.diseases:
            if d.id == d_id:
                disease_name = d.name
                disease_crop = crop_for_disease.get(d_id, "unknown")
                break

        t_short = treatment.method.lower().replace(" ", "_")[:20]

        treatment_child = (
            f"How to treat {disease_name.lower()} in {disease_crop}. "
            f"{treatment.method}. {treatment.description[:120]}"
        ).strip()

        treatment_guides.append({
            "id": _make_id(t_short, t_id, "treatment", "child"),
            "content": treatment_child,
            "metadata": {
                "disease_id": str(d_id),
                "disease_name": disease_name,
                "crop": disease_crop,
                "treatment_id": str(t_id),
                "is_organic": str(treatment.is_organic).lower(),
                "difficulty": treatment.difficulty,
                "topic_id": f"{t_short}_{t_id:03d}_treatment",
                "chunk_type": "child",
            },
        })

        materials = json.dumps(treatment.materials_needed) if treatment.materials_needed else "[]"

        treatment_parent = (
            f"Treatment: {treatment.method}\n"
            f"For: {disease_name} in {disease_crop}\n"
            f"Difficulty: {treatment.difficulty}\n"
            f"Organic: {'Yes' if treatment.is_organic else 'No'}\n"
            f"Effectiveness: {treatment.effectiveness}\n\n"
            f"Description:\n{treatment.description}\n\n"
            f"Materials needed:\n{materials}\n\n"
            f"Local availability:\n{treatment.local_availability or 'Unknown'}\n\n"
            f"When to apply:\n{treatment.application_timing or 'See description'}\n\n"
            f"Safety notes:\n{treatment.safety_notes or 'None'}"
        )

        treatment_guides.append({
            "id": _make_id(t_short, t_id, "treatment", "parent"),
            "content": treatment_parent,
            "metadata": {
                "disease_id": str(d_id),
                "disease_name": disease_name,
                "crop": disease_crop,
                "treatment_id": str(t_id),
                "is_organic": str(treatment.is_organic).lower(),
                "difficulty": treatment.difficulty,
                "topic_id": f"{t_short}_{t_id:03d}_treatment",
                "chunk_type": "parent",
            },
        })

    log.log_step(Step.AGENT_FARM_COMPILE, "chunks_collection_generated", details={
        "collection": "treatment_guides",
        "chunks": len(treatment_guides),
    })

    # --- Farming practices chunks ---

    # Variety chunks
    for var in comp.varieties:
        crop = _get_crop_name(var.crop_id, comp.crops)
        v_short = var.name.lower().replace(" ", "_")[:20]

        variety_child = (
            f"{var.name} variety of {crop} for Casamance. "
            f"{'Drought tolerant. ' if var.drought_tolerance in ('medium', 'high') else ''}"
            f"{'Disease resistant. ' if var.disease_resistance else ''}"
            f"{f'Matures in {var.days_to_maturity} days. ' if var.days_to_maturity else ''}"
        ).strip()

        farming_practices.append({
            "id": _make_id(v_short, var.id, "variety", "child"),
            "content": variety_child,
            "metadata": {
                "topic": "variety",
                "crop": crop,
                "season": "all",
                "practice_type": "planting",
                "growth_stage": "planning",
                "topic_id": f"{v_short}_{var.id:03d}_variety",
                "chunk_type": "child",
            },
        })

        resistance = ", ".join(var.disease_resistance) if var.disease_resistance else "None listed"
        variety_parent = (
            f"Variety: {var.name}\n"
            f"Crop: {crop}\n"
            f"Drought tolerance: {var.drought_tolerance or 'unknown'}\n"
            f"Disease resistance: {resistance}\n"
            f"Days to maturity: {var.days_to_maturity or 'unknown'}\n"
            f"Yield potential: {var.yield_potential_kg_per_ha or 'unknown'} kg/ha\n"
            f"Seed source: {var.seed_source_in_region or 'Unknown'}\n"
            f"Planting density: {var.planting_density or 'Unknown'}\n"
            f"Notes: {var.notes or 'None'}"
        )

        farming_practices.append({
            "id": _make_id(v_short, var.id, "variety", "parent"),
            "content": variety_parent,
            "metadata": {
                "topic": "variety",
                "crop": crop,
                "season": "all",
                "practice_type": "planting",
                "growth_stage": "planning",
                "topic_id": f"{v_short}_{var.id:03d}_variety",
                "chunk_type": "parent",
            },
        })

    # Fertilization chunks (grouped by crop)
    crop_ferts: dict[int, list[FertilizationRecord]] = {}
    for f in comp.fertilization_schedule:
        crop_ferts.setdefault(f.crop_id, []).append(f)

    for crop_id, ferts in crop_ferts.items():
        crop = _get_crop_name(crop_id, comp.crops)
        c_short = crop[:10]

        fert_child = (
            f"Fertilization schedule for {crop} in Casamance. "
            f"{'Organic alternatives available. ' if any(f.organic_alternative for f in ferts) else ''}"
            f"{len(ferts)} growth stages covered."
        ).strip()

        stages = "\n".join(
            f"- {f.growth_stage}: {f.fertilizer_type}, {f.dose_per_ha or 'dose unknown'}"
            f"{f' (organic alt: {f.organic_alternative})' if f.organic_alternative else ''}"
            for f in ferts
        )

        fert_parent = (
            f"Fertilization Schedule for {crop.title()} in Casamance\n\n"
            f"{stages}"
        )

        # Use first fert ID as representative
        fert_id = ferts[0].id

        farming_practices.append({
            "id": _make_id(c_short, fert_id, "fertilization", "child"),
            "content": fert_child,
            "metadata": {
                "topic": "fertilization",
                "crop": crop,
                "season": "all",
                "practice_type": "soil",
                "growth_stage": "all",
                "topic_id": f"{c_short}_{fert_id:03d}_fertilization",
                "chunk_type": "child",
            },
        })

        farming_practices.append({
            "id": _make_id(c_short, fert_id, "fertilization", "parent"),
            "content": fert_parent,
            "metadata": {
                "topic": "fertilization",
                "crop": crop,
                "season": "all",
                "practice_type": "soil",
                "growth_stage": "all",
                "topic_id": f"{c_short}_{fert_id:03d}_fertilization",
                "chunk_type": "parent",
            },
        })

    # Storage chunks
    for stor in comp.storage_guidelines:
        crop = _get_crop_name(stor.crop_id, comp.crops)
        s_short = stor.method.lower().replace(" ", "_")[:20]

        storage_child = (
            f"How to store {crop} after harvest. {stor.method}. "
            f"{f'Keep at {stor.optimal_temp_c}C. ' if stor.optimal_temp_c else ''}"
            f"{f'Lasts {stor.max_duration_months} months. ' if stor.max_duration_months else ''}"
        ).strip()

        storage_parent = (
            f"Storage: {stor.method}\n"
            f"Crop: {crop}\n"
            f"Temperature: {stor.optimal_temp_c or 'Unknown'}C\n"
            f"Moisture target: {stor.moisture_target_pct or 'Unknown'}%\n"
            f"Max duration: {stor.max_duration_months or 'Unknown'} months\n"
            f"Pest risks: {stor.pest_risks or 'None listed'}\n"
            f"Quality indicators: {stor.quality_indicators or 'None listed'}\n"
            f"Local materials: {stor.local_materials or 'Unknown'}"
        )

        farming_practices.append({
            "id": _make_id(s_short, stor.id, "storage", "child"),
            "content": storage_child,
            "metadata": {
                "topic": "storage",
                "crop": crop,
                "season": "post_harvest",
                "practice_type": "storage",
                "growth_stage": "harvest",
                "topic_id": f"{s_short}_{stor.id:03d}_storage",
                "chunk_type": "child",
            },
        })

        farming_practices.append({
            "id": _make_id(s_short, stor.id, "storage", "parent"),
            "content": storage_parent,
            "metadata": {
                "topic": "storage",
                "crop": crop,
                "season": "post_harvest",
                "practice_type": "storage",
                "growth_stage": "harvest",
                "topic_id": f"{s_short}_{stor.id:03d}_storage",
                "chunk_type": "parent",
            },
        })

    # Soil requirement chunks
    for soil in comp.soil_requirements:
        crop = _get_crop_name(soil.crop_id, comp.crops)
        so_short = crop[:10]

        amendments = ", ".join(soil.amendments_needed) if soil.amendments_needed else "none listed"

        soil_child = (
            f"Soil requirements for {crop} in Casamance. "
            f"pH {soil.ph_min or '?'}-{soil.ph_max or '?'}. "
            f"{soil.preferred_texture or 'Any texture'}. "
            f"Amendments: {amendments}."
        ).strip()

        soil_parent = (
            f"Soil Requirements for {crop.title()}\n\n"
            f"pH range: {soil.ph_min or '?'} - {soil.ph_max or '?'}\n"
            f"Preferred texture: {soil.preferred_texture or 'Unknown'}\n"
            f"Drainage: {soil.drainage_needs or 'Unknown'}\n"
            f"Amendments needed: {amendments}\n"
            f"Preparation: {soil.preparation_notes or 'None specified'}"
        )

        farming_practices.append({
            "id": _make_id(so_short, soil.id, "soil", "child"),
            "content": soil_child,
            "metadata": {
                "topic": "soil",
                "crop": crop,
                "season": "pre_planting",
                "practice_type": "soil",
                "growth_stage": "planning",
                "topic_id": f"{so_short}_{soil.id:03d}_soil",
                "chunk_type": "child",
            },
        })

        farming_practices.append({
            "id": _make_id(so_short, soil.id, "soil", "parent"),
            "content": soil_parent,
            "metadata": {
                "topic": "soil",
                "crop": crop,
                "season": "pre_planting",
                "practice_type": "soil",
                "growth_stage": "planning",
                "topic_id": f"{so_short}_{soil.id:03d}_soil",
                "chunk_type": "parent",
            },
        })

    # Pest chunks
    for pest in comp.pests:
        crop = _get_crop_name(pest.crop_id, comp.crops)
        p_short = pest.name.lower().replace(" ", "_")[:20]

        pest_child = (
            f"{pest.name} attacking {crop}. "
            f"{pest.damage_description[:150]}"
        ).strip()

        pest_parent = (
            f"Pest: {pest.name}\n"
            f"Type: {pest.type}\n"
            f"Crop: {crop}\n"
            f"Season peak: {pest.season_peak or 'Unknown'}\n\n"
            f"Damage:\n{pest.damage_description}\n\n"
            f"Identification:\n{pest.identification_notes or 'None'}\n\n"
            f"Organic control:\n{pest.control_organic or 'None listed'}\n\n"
            f"Chemical control:\n{pest.control_chemical or 'None listed'}\n\n"
            f"Prevention:\n{pest.prevention_notes or 'None listed'}"
        )

        farming_practices.append({
            "id": _make_id(p_short, pest.id, "pest", "child"),
            "content": pest_child,
            "metadata": {
                "topic": "pest",
                "crop": crop,
                "season": pest.season_peak or "all",
                "practice_type": "pest",
                "growth_stage": "vegetative",
                "topic_id": f"{p_short}_{pest.id:03d}_pest",
                "chunk_type": "child",
            },
        })

        farming_practices.append({
            "id": _make_id(p_short, pest.id, "pest", "parent"),
            "content": pest_parent,
            "metadata": {
                "topic": "pest",
                "crop": crop,
                "season": pest.season_peak or "all",
                "practice_type": "pest",
                "growth_stage": "vegetative",
                "topic_id": f"{p_short}_{pest.id:03d}_pest",
                "chunk_type": "parent",
            },
        })

    # Planting calendar chunks (grouped by crop)
    crop_cals: dict[int, list[PlantingCalendarRecord]] = {}
    for cal in comp.planting_calendar:
        crop_cals.setdefault(cal.crop_id, []).append(cal)

    for crop_id, cals in crop_cals.items():
        crop = _get_crop_name(crop_id, comp.crops)
        c_short = crop[:10]

        # Sort by month for readable output
        cals_sorted = sorted(cals, key=lambda c: c.month)

        cal_child = (
            f"Planting calendar for {crop} in Casamance. "
            f"{len(cals_sorted)} activities across the year. "
            f"{'Critical timing activities included. ' if any(c.is_critical for c in cals_sorted) else ''}"
        ).strip()

        activities = "\n".join(
            f"- {_MONTH_NAMES[c.month] if 1 <= c.month <= 12 else f'Month {c.month}'}: "
            f"{c.activity}{' (CRITICAL)' if c.is_critical else ''}"
            f"{f' — {c.details[:100]}' if c.details else ''}"
            for c in cals_sorted
        )

        cal_parent = (
            f"Planting Calendar for {crop.title()} in Casamance\n\n"
            f"{activities}"
        )

        # Use first calendar entry ID as representative
        cal_id = cals_sorted[0].id

        farming_practices.append({
            "id": _make_id(c_short, cal_id, "calendar", "child"),
            "content": cal_child,
            "metadata": {
                "topic": "planting_calendar",
                "crop": crop,
                "season": "all",
                "practice_type": "planning",
                "growth_stage": "all",
                "topic_id": f"{c_short}_{cal_id:03d}_calendar",
                "chunk_type": "child",
            },
        })

        farming_practices.append({
            "id": _make_id(c_short, cal_id, "calendar", "parent"),
            "content": cal_parent,
            "metadata": {
                "topic": "planting_calendar",
                "crop": crop,
                "season": "all",
                "practice_type": "planning",
                "growth_stage": "all",
                "topic_id": f"{c_short}_{cal_id:03d}_calendar",
                "chunk_type": "parent",
            },
        })

    log.log_step(Step.AGENT_FARM_COMPILE, "chunks_collection_generated", details={
        "collection": "farming_practices",
        "chunks": len(farming_practices),
    })

    # --- Regional context chunks (climate) ---

    for clim in comp.climate:
        month_name = _MONTH_NAMES[clim.month] if 1 <= clim.month <= 12 else f"Month {clim.month}"
        c_short = f"casamance_m{clim.month:02d}"

        climate_child = (
            f"Weather in Casamance in {month_name}. "
            f"{'Rainy season. ' if clim.rainfall_mm and clim.rainfall_mm > 50 else 'Dry season. '}"
            f"{f'Rainfall {clim.rainfall_mm}mm. ' if clim.rainfall_mm else ''}"
            f"{f'Temperature {clim.temperature_avg_c}C. ' if clim.temperature_avg_c else ''}"
            f"{f'Drought risk: {clim.drought_risk}. ' if clim.drought_risk else ''}"
        ).strip()

        climate_parent = (
            f"Climate: {month_name} in Casamance, Senegal\n\n"
            f"Rainfall: {clim.rainfall_mm or 'unknown'} mm\n"
            f"Temperature: {clim.temperature_avg_c or 'unknown'}C\n"
            f"Humidity: {clim.humidity_pct or 'unknown'}%\n"
            f"Drought risk: {clim.drought_risk or 'unknown'}\n"
            f"Flooding risk: {clim.flooding_risk or 'unknown'}\n"
            f"Evapotranspiration: {clim.evapotranspiration_mm or 'unknown'} mm\n"
            f"{f'Notes: {clim.notes}' if clim.notes else ''}"
        )

        regional_context.append({
            "id": _make_id(c_short, clim.id, "climate", "child"),
            "content": climate_child,
            "metadata": {
                "region": clim.region,
                "topic": "climate",
                "data_type": "monthly",
                "topic_id": f"{c_short}_{clim.id:03d}_climate",
                "chunk_type": "child",
            },
        })

        regional_context.append({
            "id": _make_id(c_short, clim.id, "climate", "parent"),
            "content": climate_parent,
            "metadata": {
                "region": clim.region,
                "topic": "climate",
                "data_type": "monthly",
                "topic_id": f"{c_short}_{clim.id:03d}_climate",
                "chunk_type": "parent",
            },
        })

    log.log_step(Step.AGENT_FARM_COMPILE, "chunks_collection_generated", details={
        "collection": "regional_context",
        "chunks": len(regional_context),
    })

    result = {
        "disease_knowledge": disease_knowledge,
        "treatment_guides": treatment_guides,
        "farming_practices": farming_practices,
        "regional_context": regional_context,
    }

    total_chunks = sum(len(v) for v in result.values())
    log.log_step(Step.AGENT_FARM_COMPILE, "chunks_generation_complete", details={
        "total_chunks": total_chunks,
        "disease_knowledge": len(disease_knowledge),
        "treatment_guides": len(treatment_guides),
        "farming_practices": len(farming_practices),
        "regional_context": len(regional_context),
    })

    return result


# ============================================================
# Helpers
# ============================================================


def _count_domains(findings: list[Finding]) -> dict[str, int]:
    """Count findings by domain for logging."""
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.domain] = counts.get(f.domain, 0) + 1
    return counts
