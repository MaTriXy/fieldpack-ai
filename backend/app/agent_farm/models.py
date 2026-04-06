"""Data models for the Phase 1 Agent Farm.

Three layers:
  1. Parsing models: PageSection, SourceConfig (Phase A)
  2. Extraction model: Finding (Phase B output, Phase C/D input)
  3. Compilation models: 11 Pydantic V2 schemas matching schema_sqlite.py tables
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Shared config for all Pydantic models used with LLM structured output.
# strict=False allows type coercion (e.g., "3" -> 3) from LLM responses.
_COMPILATION_CONFIG = ConfigDict(strict=False)


# ============================================================
# Phase A: Parsing models
# ============================================================


@dataclass
class PageSection:
    """A chunk of text extracted from an HTML page or PDF."""

    source_url: str
    source_name: str  # e.g., "PlantVillage", "FAO Cassava FFS Guide"
    heading: str  # section heading, or "page_N" for PDFs
    content: str  # 700-3000 chars of text
    crop: str = ""  # which crop this section relates to (set during gathering)
    section_type: str = ""  # optional hint: "disease", "pest", "treatment", etc.
    tables: list[list[list[str]]] = field(default_factory=list)  # extracted tables


@dataclass
class SourceConfig:
    """Configuration for a known data source."""

    name: str  # "PlantVillage", "Infonet-Biovision", etc.
    url_template: str  # with {slug} placeholder
    slug_map: dict[str, str]  # crop_name -> URL slug
    parser_type: Literal["html_headings", "pdf_pages", "climate_table"]
    tier: int = 1  # 1=known HTML, 2=PDF, 3=climate, 4=Tavily


# ============================================================
# Phase B: Extraction model (THE core data contract)
# ============================================================


@dataclass
class Finding:
    """One piece of knowledge gathered by a research agent.

    This is THE contract between Phase B (extraction) and Phases C/D
    (gap analysis + compilation). Research agents produce Finding objects.
    The compiler transforms Findings into strict Pydantic DB records.
    """

    domain: str  # "crop", "disease", "treatment", "pest", "variety",
    # "climate", "soil", "fertilization", "storage",
    # "planting", "practice", "regional"
    entity_name: str  # e.g., "Cassava Mosaic Disease"
    content: str  # 200-800 chars of rich extracted text
    related_entities: list[str] = field(default_factory=list)
    source: str = ""  # URL or "FAO Cassava FFS Guide p.23"
    confidence: float = 0.8
    raw_data: dict = field(default_factory=dict)


# ============================================================
# Phase B: Pydantic extraction schema (for LLM structured output)
#
# Mirror of Finding dataclass as Pydantic BaseModel so we can use
# ChatGoogleGenerativeAI.with_structured_output(). The LLM produces
# FindingExtract objects; we convert to Finding dataclasses downstream.
# ============================================================

_DOMAIN_LITERAL = Literal[
    "crop", "disease", "treatment", "pest", "variety", "climate",
    "soil", "fertilization", "storage", "planting", "practice", "regional",
]


class FindingExtract(BaseModel):
    """One piece of knowledge extracted from a page section."""

    model_config = _COMPILATION_CONFIG

    domain: _DOMAIN_LITERAL = Field(
        description="Knowledge domain category"
    )
    entity_name: str = Field(
        description="The specific entity this finding is about, "
        "e.g. 'Cassava Mosaic Disease', 'TME 419', 'Whitefly'"
    )
    content: str = Field(
        description="200-800 chars of rich, specific extracted knowledge. "
        "Include numbers, percentages, and concrete details. "
        "Do NOT summarize vaguely — extract actionable information."
    )
    related_entities: list[str] = Field(
        default_factory=list,
        description="Other entities mentioned in this finding, "
        "e.g. ['cassava', 'whitefly'] for a disease finding"
    )
    confidence: float = Field(
        0.8,
        description="Your confidence in this extraction, 0.0-1.0. "
        "Lower if the source is vague or contradictory."
    )
    raw_data: dict = Field(
        default_factory=dict,
        description="Any structured fields you can extract: "
        "numbers, percentages, ranges, lists. "
        "e.g. {'yield_loss_pct': 50, 'vector': 'whitefly'}"
    )


class ExtractionOutput(BaseModel):
    """Wrapper for LLM structured output: a list of findings from one section."""

    findings: list[FindingExtract] = Field(
        description="All knowledge nuggets extracted from this text section. "
        "Extract 1-5 findings per section. Each finding should be a "
        "distinct piece of knowledge about a specific entity."
    )


# ============================================================
# Phase C: Gap analysis schema (for LLM structured output)
# ============================================================


class IdentifiedGap(BaseModel):
    """A single knowledge gap identified by the planner LLM."""

    model_config = _COMPILATION_CONFIG

    domain: _DOMAIN_LITERAL = Field(
        description="Which domain is missing data"
    )
    entity_name: str = Field(
        description="The specific entity or topic that lacks coverage, "
        "e.g. 'rice varieties for Casamance', 'groundnut fertilization schedule'"
    )
    description: str = Field(
        description="What information is missing and why it matters, 1-2 sentences"
    )
    search_query: str = Field(
        description="A targeted web search query to fill this gap. "
        "Be specific: include crop name, region, and what data is needed. "
        "e.g. 'drought resistant rice varieties Casamance Senegal seed source'"
    )
    priority: Literal["high", "medium", "low"] = Field(
        "medium",
        description="How critical this gap is for a field worker. "
        "'high' = directly impacts diagnosis or treatment advice"
    )


class GapAnalysisOutput(BaseModel):
    """Structured output from the gap analysis LLM call."""

    gaps: list[IdentifiedGap] = Field(
        description="All identified knowledge gaps. Focus on gaps that would "
        "hurt a field worker's ability to diagnose diseases, recommend "
        "treatments, or advise on farming practices in Casamance, Senegal."
    )
    coverage_summary: str = Field(
        description="2-3 sentence summary of overall knowledge coverage quality"
    )


def finding_extract_to_dataclass(
    extract: FindingExtract,
    source: str,
) -> Finding:
    """Convert a Pydantic FindingExtract to a Finding dataclass."""
    return Finding(
        domain=extract.domain,
        entity_name=extract.entity_name,
        content=extract.content,
        related_entities=extract.related_entities,
        source=source,
        confidence=extract.confidence,
        raw_data=extract.raw_data,
    )


# ============================================================
# Phase D: Compilation models (one per SQLite table)
#
# Conventions:
#   - Optional fields with None for anything the LLM might not know
#   - Rich Field(description=...) to guide the LLM
#   - confidence + data_gaps on every record
#   - JSON array fields are Python lists here; json.dumps() in post-processing
#   - Literal types for constrained CHECK columns
#   - ConfigDict(strict=False) for type coercion from LLM output
# ============================================================


class CropRecord(BaseModel):
    model_config = _COMPILATION_CONFIG

    id: int = Field(description="Unique crop ID, starting from 1")
    name: str = Field(description="Common English name, e.g. 'Cassava'")
    scientific_name: str | None = Field(None, description="Latin binomial, e.g. 'Manihot esculenta'")
    family: str | None = Field(None, description="Plant family, e.g. 'Euphorbiaceae'")
    growing_season: str | None = Field(None, description="e.g. 'June-December (Casamance rainy season)'")
    water_needs_mm_per_week: float | None = Field(None, description="Do NOT guess — set null if unknown")
    drought_tolerance: Literal["low", "medium", "high"] | None = None
    region_suitability: str | None = Field(None, description="Suitability notes for Casamance region")
    planting_notes: str | None = None
    harvest_notes: str | None = None
    soil_ph_min: float | None = Field(None, description="Minimum soil pH. Do NOT guess.")
    soil_ph_max: float | None = Field(None, description="Maximum soil pH. Do NOT guess.")
    seed_rate_kg_per_ha: float | None = Field(None, description="Seeding rate in kg/ha. Do NOT guess.")
    intercrop_companions: list[str] = Field(default_factory=list, description="Companion crops for intercropping")
    confidence: float = Field(0.8, description="Your confidence in this record, 0.0-1.0")
    data_gaps: list[str] = Field(default_factory=list, description="List fields where you lack reliable data")


class DiseaseRecord(BaseModel):
    model_config = _COMPILATION_CONFIG

    id: int = Field(description="Unique disease ID, starting from 1")
    name: str = Field(description="Full disease name, e.g. 'Cassava Mosaic Disease'")
    common_names: list[str] = Field(default_factory=list, description="Alternative names including local names")
    type: Literal["viral", "bacterial", "fungal", "pest", "nutritional", "environmental"] = Field(
        description="Disease type category"
    )
    symptoms_text: str = Field(description="Detailed symptom description, 100-400 chars")
    visual_markers: str = Field(description="Visual identification cues for field diagnosis, 100-400 chars")
    severity_scale: Literal["low", "medium", "high", "critical"] = "medium"
    spread_mechanism: str | None = None
    prevention_notes: str | None = None
    affected_growth_stage: str | None = None
    season_risk_peak: str | None = None
    confidence: float = Field(0.8, description="Your confidence in this record, 0.0-1.0")
    data_gaps: list[str] = Field(default_factory=list, description="List fields where you lack reliable data")


class CropDiseaseRecord(BaseModel):
    model_config = _COMPILATION_CONFIG

    crop_id: int = Field(description="FK to crops.id — use IDs from the crops compilation step")
    disease_id: int = Field(description="FK to diseases.id — use IDs from the diseases compilation step")
    susceptibility: Literal["low", "medium", "high"] = "medium"
    confidence: float = Field(0.8, description="Your confidence in this record, 0.0-1.0")
    data_gaps: list[str] = Field(default_factory=list, description="List fields where you lack reliable data")


class TreatmentRecord(BaseModel):
    model_config = _COMPILATION_CONFIG

    id: int = Field(description="Unique treatment ID, starting from 1")
    disease_id: int = Field(description="FK to diseases.id")
    method: str = Field(description="Short treatment name, e.g. 'Neem oil spray'")
    description: str = Field(description="Full treatment procedure, 100-500 chars")
    materials_needed: list[str] = Field(default_factory=list, description="List of materials with quantities")
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    is_organic: bool = Field(True, description="True if no synthetic chemicals")
    local_availability: str | None = Field(None, description="Where to get materials in Casamance")
    effectiveness: Literal["low", "medium", "high"] = "medium"
    application_timing: str | None = None
    safety_notes: str | None = None
    cost_estimate_xof: int | None = Field(None, description="Cost in West African CFA francs (whole number). Do NOT guess.")
    treatment_type: Literal["preventive", "curative", "cultural"] = "curative"
    confidence: float = Field(0.8, description="Your confidence in this record, 0.0-1.0")
    data_gaps: list[str] = Field(default_factory=list, description="List fields where you lack reliable data")


class ClimateRecord(BaseModel):
    model_config = _COMPILATION_CONFIG

    id: int = Field(description="Unique climate record ID")
    region: str = Field("Casamance", description="Region name")
    month: int = Field(description="Month number 1-12", ge=1, le=12)
    rainfall_mm: float | None = Field(None, description="Average monthly rainfall in mm")
    temperature_avg_c: float | None = Field(None, description="Average temperature in Celsius")
    humidity_pct: float | None = Field(None, description="Average relative humidity percentage")
    drought_risk: Literal["low", "medium", "high", "severe"] | None = None
    notes: str | None = None
    evapotranspiration_mm: float | None = Field(None, description="Monthly ET in mm. Do NOT guess.")
    flooding_risk: Literal["none", "low", "moderate", "high"] | None = None
    confidence: float = Field(0.8, description="Your confidence in this record, 0.0-1.0")
    data_gaps: list[str] = Field(default_factory=list, description="List fields where you lack reliable data")


class PestRecord(BaseModel):
    model_config = _COMPILATION_CONFIG

    id: int = Field(description="Unique pest ID")
    name: str = Field(description="Common name, e.g. 'Cassava Green Mite'")
    common_names: list[str] = Field(default_factory=list)
    crop_id: int = Field(description="FK to crops.id")
    type: Literal["insect", "rodent", "bird", "nematode", "mollusk"] = "insect"
    damage_description: str = Field(description="What damage this pest causes")
    season_peak: str | None = None
    identification_notes: str | None = None
    control_organic: str | None = None
    control_chemical: str | None = None
    economic_threshold: str | None = None
    prevention_notes: str | None = None
    confidence: float = Field(0.8, description="Your confidence in this record, 0.0-1.0")
    data_gaps: list[str] = Field(default_factory=list, description="List fields where you lack reliable data")


class VarietyRecord(BaseModel):
    model_config = _COMPILATION_CONFIG

    id: int = Field(description="Unique variety ID")
    crop_id: int = Field(description="FK to crops.id")
    name: str = Field(description="Variety name, e.g. 'TME 419'")
    local_names: list[str] = Field(default_factory=list)
    days_to_maturity: int | None = Field(None, description="Days from planting to harvest. Do NOT guess.")
    yield_potential_kg_per_ha: float | None = Field(None, description="Potential yield in kg/ha. Do NOT guess.")
    disease_resistance: list[str] = Field(default_factory=list, description="Diseases this variety resists")
    drought_tolerance: Literal["low", "medium", "high"] | None = None
    seed_source_in_region: str | None = Field(None, description="Where to get seeds in Casamance")
    planting_density: str | None = None
    notes: str | None = None
    confidence: float = Field(0.8, description="Your confidence in this record, 0.0-1.0")
    data_gaps: list[str] = Field(default_factory=list, description="List fields where you lack reliable data")


class FertilizationRecord(BaseModel):
    model_config = _COMPILATION_CONFIG

    id: int = Field(description="Unique fertilization schedule ID")
    crop_id: int = Field(description="FK to crops.id")
    growth_stage: str = Field(description="e.g. 'planting', 'vegetative', 'flowering'")
    fertilizer_type: str = Field(description="e.g. 'NPK 15-15-15', 'compost'")
    dose_per_ha: str | None = Field(None, description="Dose with units, e.g. '200 kg/ha'")
    application_method: str | None = None
    timing_notes: str | None = None
    organic_alternative: str | None = None
    cost_estimate_xof: int | None = Field(None, description="Cost in XOF (whole number). Do NOT guess.")
    confidence: float = Field(0.8, description="Your confidence in this record, 0.0-1.0")
    data_gaps: list[str] = Field(default_factory=list, description="List fields where you lack reliable data")


class PlantingCalendarRecord(BaseModel):
    model_config = _COMPILATION_CONFIG

    id: int = Field(description="Unique planting calendar ID")
    crop_id: int = Field(description="FK to crops.id")
    month: int = Field(description="Month number 1-12", ge=1, le=12)
    activity: str = Field(description="e.g. 'Land preparation', 'Planting', 'Weeding'")
    details: str = Field(description="Specific instructions for this activity")
    is_critical: bool = Field(False, description="True if timing is critical for yield")
    confidence: float = Field(0.8, description="Your confidence in this record, 0.0-1.0")
    data_gaps: list[str] = Field(default_factory=list, description="List fields where you lack reliable data")


class StorageRecord(BaseModel):
    model_config = _COMPILATION_CONFIG

    id: int = Field(description="Unique storage guideline ID")
    crop_id: int = Field(description="FK to crops.id")
    method: str = Field(description="Storage method name")
    optimal_temp_c: str | None = Field(None, description="Optimal storage temp, e.g. '25-30' or 'ambient (25-35)'. Do NOT guess.")
    moisture_target_pct: float | None = Field(None, description="Target moisture percentage. Do NOT guess.")
    max_duration_months: int | None = Field(None, description="Max storage duration in months. Do NOT guess.")
    pest_risks: str | None = None
    quality_indicators: str | None = None
    local_materials: str | None = Field(None, description="Locally available storage materials in Casamance")
    confidence: float = Field(0.8, description="Your confidence in this record, 0.0-1.0")
    data_gaps: list[str] = Field(default_factory=list, description="List fields where you lack reliable data")


class SoilRecord(BaseModel):
    model_config = _COMPILATION_CONFIG

    id: int = Field(description="Unique soil requirement ID")
    crop_id: int = Field(description="FK to crops.id")
    ph_min: float | None = Field(None, description="Minimum soil pH")
    ph_max: float | None = Field(None, description="Maximum soil pH")
    preferred_texture: str | None = Field(None, description="e.g. 'sandy loam', 'clay loam'")
    drainage_needs: str | None = None
    amendments_needed: list[str] = Field(default_factory=list, description="Soil amendments needed")
    preparation_notes: str | None = None
    confidence: float = Field(0.8, description="Your confidence in this record, 0.0-1.0")
    data_gaps: list[str] = Field(default_factory=list, description="List fields where you lack reliable data")


# ============================================================
# Compilation output wrapper
# ============================================================


class CompilationOutput(BaseModel):
    """Holds all 11 compiled tables. Each is a list of records."""

    crops: list[CropRecord] = Field(default_factory=list)
    diseases: list[DiseaseRecord] = Field(default_factory=list)
    crop_diseases: list[CropDiseaseRecord] = Field(default_factory=list)
    treatments: list[TreatmentRecord] = Field(default_factory=list)
    climate: list[ClimateRecord] = Field(default_factory=list)
    pests: list[PestRecord] = Field(default_factory=list)
    varieties: list[VarietyRecord] = Field(default_factory=list)
    fertilization_schedule: list[FertilizationRecord] = Field(default_factory=list)
    planting_calendar: list[PlantingCalendarRecord] = Field(default_factory=list)
    storage_guidelines: list[StorageRecord] = Field(default_factory=list)
    soil_requirements: list[SoilRecord] = Field(default_factory=list)


# ============================================================
# JSON serialization helpers (for SQLite insert post-processing)
# ============================================================

# Fields that store JSON arrays in SQLite TEXT columns
JSON_ARRAY_FIELDS: dict[str, list[str]] = {
    "crops": ["intercrop_companions"],
    "diseases": ["common_names"],
    "treatments": ["materials_needed"],
    "pests": ["common_names"],
    "varieties": ["local_names", "disease_resistance"],
    "soil_requirements": ["amendments_needed"],
}


def record_to_sqlite_row(table_name: str, record: BaseModel) -> dict:
    """Convert a Pydantic record to a SQLite-ready dict.

    - Strips confidence and data_gaps (not in SQLite schema)
    - Applies json.dumps() to JSON array fields
    """
    row = record.model_dump()
    row.pop("confidence", None)
    row.pop("data_gaps", None)

    for field_name in JSON_ARRAY_FIELDS.get(table_name, []):
        if field_name in row and isinstance(row[field_name], list):
            row[field_name] = json.dumps(row[field_name])

    return row
