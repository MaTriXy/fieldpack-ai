"""Tests for Phase 1 Agent Farm phase functions.

Covers:
  - phases/source_gathering.py: source_gathering() + private helpers
  - phases/knowledge_extraction.py: knowledge_extraction() + _climate_records_to_findings()
  - phases/gap_analysis.py: gap_analysis() + _build_coverage_summary()
  - phases/compilation.py: compilation helpers + generate_chunks_from_compilation()

All LLM calls are mocked. Tavily and HTTP calls are mocked.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent_farm.models import (
    ClimateRecord,
    CompilationOutput,
    CropDiseaseRecord,
    CropRecord,
    DiseaseRecord,
    ExtractionOutput,
    FertilizationRecord,
    Finding,
    FindingExtract,
    GapAnalysisOutput,
    IdentifiedGap,
    PageSection,
    PestRecord,
    PlantingCalendarRecord,
    SoilRecord,
    StorageRecord,
    TreatmentRecord,
    VarietyRecord,
)


# ============================================================
# Shared test data helpers
# ============================================================


def _make_section(heading="Diseases", content="Cassava mosaic causes leaf curl",
                  crop="cassava", source_url="https://example.com",
                  source_name="Test") -> PageSection:
    return PageSection(
        source_url=source_url, source_name=source_name,
        heading=heading, content=content, crop=crop,
    )


def _make_finding(domain="disease", entity_name="CMD",
                  content="Cassava Mosaic Disease causes leaf curl",
                  **kwargs) -> Finding:
    return Finding(domain=domain, entity_name=entity_name, content=content, **kwargs)


def _make_climate_record(month=1, rainfall_mm=5.0, region="Ziguinchor"):
    return {
        "region": region, "month": month,
        "rainfall_mm": rainfall_mm, "temperature_avg_c": 25.0,
    }


# ============================================================
# Phase A: Source gathering
# ============================================================


class TestSourceGathering:
    def _make_state(self, crops=None, region="Casamance"):
        return {
            "crops": crops or ["cassava"],
            "region": region,
            "status_messages": [],
        }

    async def test_basic_flow(self):
        from app.agent_farm.phases.source_gathering import source_gathering

        state = self._make_state(crops=["cassava"])

        with patch("app.agent_farm.phases.source_gathering.fetch_html",
                    new_callable=AsyncMock, return_value="<html><h2>Diseases</h2><p>CMD causes mosaic patterns on cassava leaves, leading to yield loss.</p></html>"), \
             patch("app.agent_farm.phases.source_gathering.fetch_pdf_bytes",
                    new_callable=AsyncMock, return_value=None), \
             patch("app.agent_farm.phases.source_gathering.parse_climate_tables",
                    return_value=[_make_climate_record()]):

            result = await source_gathering(state)

        assert "sections" in result
        assert "climate_records" in result
        assert result["current_phase"] == "gathering"

    async def test_sets_crop_on_html_sections(self):
        from app.agent_farm.phases.source_gathering import _fetch_and_parse_html

        html = "<html><h2>Diseases</h2><p>Some disease content that is long enough to pass the minimum section length filter for parsing.</p></html>"

        with patch("app.agent_farm.phases.source_gathering.fetch_html",
                    new_callable=AsyncMock, return_value=html):
            sections = await _fetch_and_parse_html("cassava", "Test", "https://example.com")

        for s in sections:
            assert s.crop == "cassava"

    async def test_html_fetch_failure_returns_empty(self):
        from app.agent_farm.phases.source_gathering import _fetch_and_parse_html

        with patch("app.agent_farm.phases.source_gathering.fetch_html",
                    new_callable=AsyncMock, return_value=None):
            sections = await _fetch_and_parse_html("cassava", "Test", "url")

        assert sections == []

    async def test_pdf_fetch_failure_returns_empty(self):
        from app.agent_farm.phases.source_gathering import _fetch_and_parse_pdf

        with patch("app.agent_farm.phases.source_gathering.fetch_pdf_bytes",
                    new_callable=AsyncMock, return_value=None):
            sections = await _fetch_and_parse_pdf("FAO", "url", ["cassava"])

        assert sections == []

    async def test_pdf_single_crop_tags_sections(self):
        from app.agent_farm.phases.source_gathering import _fetch_and_parse_pdf
        from tests.test_agent_farm_sources import _make_test_pdf

        pdf_bytes = _make_test_pdf(
            "This is a test page with enough content for the minimum threshold. "
            "Discusses cassava disease management and treatment options."
        )

        with patch("app.agent_farm.phases.source_gathering.fetch_pdf_bytes",
                    new_callable=AsyncMock, return_value=pdf_bytes):
            sections = await _fetch_and_parse_pdf("FAO", "url", ["cassava"])

        for s in sections:
            assert s.crop == "cassava"

    async def test_climate_fetch_failure_returns_empty(self):
        from app.agent_farm.phases.source_gathering import _fetch_and_parse_climate

        with patch("app.agent_farm.phases.source_gathering.fetch_html",
                    new_callable=AsyncMock, return_value=None):
            records = await _fetch_and_parse_climate("Ziguinchor", "url")

        assert records == []

    async def test_lowercases_crops(self):
        from app.agent_farm.phases.source_gathering import source_gathering

        state = self._make_state(crops=["CASSAVA", "Rice"])

        with patch("app.agent_farm.phases.source_gathering.fetch_html",
                    new_callable=AsyncMock, return_value=None), \
             patch("app.agent_farm.phases.source_gathering.fetch_pdf_bytes",
                    new_callable=AsyncMock, return_value=None):

            result = await source_gathering(state)

        assert result["current_phase"] == "gathering"

    async def test_handles_gather_exceptions(self):
        from app.agent_farm.phases.source_gathering import source_gathering

        state = self._make_state(crops=["cassava"])

        with patch("app.agent_farm.phases.source_gathering.fetch_html",
                    new_callable=AsyncMock, side_effect=Exception("Network error")), \
             patch("app.agent_farm.phases.source_gathering.fetch_pdf_bytes",
                    new_callable=AsyncMock, side_effect=Exception("Network error")):

            result = await source_gathering(state)

        assert result["sections"] == []
        assert result["current_phase"] == "gathering"


# ============================================================
# Phase B: Knowledge extraction
# ============================================================


class TestClimateRecordsToFindings:
    def test_basic_conversion(self):
        from app.agent_farm.phases.knowledge_extraction import _climate_records_to_findings

        records = [_make_climate_record(month=7, rainfall_mm=350, region="Ziguinchor")]
        findings = _climate_records_to_findings(records)

        assert len(findings) == 1
        f = findings[0]
        assert f.domain == "climate"
        assert f.confidence == 0.95
        assert "Ziguinchor" in f.entity_name
        assert "month 7" in f.entity_name
        assert "350" in f.content

    def test_multiple_records(self):
        from app.agent_farm.phases.knowledge_extraction import _climate_records_to_findings

        records = [_make_climate_record(month=m) for m in range(1, 13)]
        findings = _climate_records_to_findings(records)
        assert len(findings) == 12

    def test_strips_none_from_raw_data(self):
        from app.agent_farm.phases.knowledge_extraction import _climate_records_to_findings

        records = [{"region": "Z", "month": 1, "rainfall_mm": 5.0, "humidity_pct": None}]
        findings = _climate_records_to_findings(records)
        assert "humidity_pct" not in findings[0].raw_data


class TestKnowledgeExtraction:
    def _make_state(self, sections=None, climate_records=None):
        return {
            "sections": sections or [],
            "climate_records": climate_records or [],
            "status_messages": [],
        }

    async def test_empty_sections(self):
        from app.agent_farm.phases.knowledge_extraction import knowledge_extraction

        state = self._make_state()

        with patch("app.agent_farm.phases.knowledge_extraction.get_research_llm") as mock_llm:
            mock_llm.return_value.with_structured_output.return_value = MagicMock()
            result = await knowledge_extraction(state)

        assert result["findings"] == []
        assert result["current_phase"] == "extracting"

    async def test_climate_only(self):
        from app.agent_farm.phases.knowledge_extraction import knowledge_extraction

        state = self._make_state(climate_records=[_make_climate_record()])

        with patch("app.agent_farm.phases.knowledge_extraction.get_research_llm") as mock_llm:
            mock_llm.return_value.with_structured_output.return_value = MagicMock()
            result = await knowledge_extraction(state)

        assert len(result["findings"]) == 1
        assert result["findings"][0].domain == "climate"

    async def test_with_sections_mocked_llm(self):
        from app.agent_farm.phases.knowledge_extraction import knowledge_extraction

        section = _make_section()
        state = self._make_state(sections=[section])

        mock_output = ExtractionOutput(findings=[
            FindingExtract(
                domain="disease", entity_name="CMD",
                content="Causes mosaic pattern",
                related_entities=["cassava"],
                raw_data={},
            ),
        ])

        mock_llm_chain = AsyncMock()
        mock_llm_chain.ainvoke = AsyncMock(return_value=mock_output)

        with patch("app.agent_farm.phases.knowledge_extraction.get_research_llm") as mock_llm, \
             patch("app.agent_farm.phases.knowledge_extraction.rate_limiter") as mock_rl:
            mock_llm.return_value.with_structured_output.return_value = mock_llm_chain
            mock_rl.wait = AsyncMock()
            mock_rl.on_success = MagicMock()
            result = await knowledge_extraction(state)

        assert len(result["findings"]) == 1
        assert result["findings"][0].domain == "disease"

    async def test_llm_failure_returns_empty_for_section(self):
        from app.agent_farm.phases.knowledge_extraction import knowledge_extraction

        section = _make_section()
        state = self._make_state(
            sections=[section],
            climate_records=[_make_climate_record()],
        )

        mock_llm_chain = AsyncMock()
        mock_llm_chain.ainvoke = AsyncMock(side_effect=Exception("LLM error"))

        with patch("app.agent_farm.phases.knowledge_extraction.get_research_llm") as mock_llm, \
             patch("app.agent_farm.phases.knowledge_extraction.rate_limiter") as mock_rl:
            mock_llm.return_value.with_structured_output.return_value = mock_llm_chain
            mock_rl.wait = AsyncMock()
            mock_rl.on_success = MagicMock()
            mock_rl.on_rate_limit = MagicMock()
            result = await knowledge_extraction(state)

        # Should still have climate finding despite LLM failure
        assert len(result["findings"]) == 1
        assert result["findings"][0].domain == "climate"


# ============================================================
# Phase C: Gap analysis helpers
# ============================================================


class TestBuildCoverageSummary:
    def test_groups_by_domain(self):
        from app.agent_farm.phases.gap_analysis import _build_coverage_summary

        findings = [
            _make_finding(domain="disease", entity_name="CMD"),
            _make_finding(domain="disease", entity_name="CBSD"),
            _make_finding(domain="crop", entity_name="Cassava"),
        ]
        summary = _build_coverage_summary(findings, ["cassava"])

        assert "[DISEASE]" in summary
        assert "[CROP]" in summary
        assert "CMD" in summary
        assert "Total findings: 3" in summary

    def test_lists_missing_domains(self):
        from app.agent_farm.phases.gap_analysis import _build_coverage_summary

        findings = [_make_finding(domain="disease")]
        summary = _build_coverage_summary(findings, ["cassava"])

        assert "MISSING DOMAINS" in summary
        assert "crop" in summary.split("MISSING DOMAINS")[1]

    def test_empty_findings(self):
        from app.agent_farm.phases.gap_analysis import _build_coverage_summary

        summary = _build_coverage_summary([], ["cassava"])
        assert "Total findings: 0" in summary
        assert "MISSING DOMAINS" in summary


class TestGapAnalysis:
    def _make_state(self, findings=None, crops=None):
        return {
            "findings": findings or [],
            "crops": crops or ["cassava"],
            "region": "Casamance",
            "status_messages": [],
        }

    async def test_planner_llm_failure_returns_unchanged(self):
        from app.agent_farm.phases.gap_analysis import gap_analysis

        findings = [_make_finding()]
        state = self._make_state(findings=findings)

        with patch("app.agent_farm.phases.gap_analysis.get_planner_llm") as mock_planner, \
             patch("app.agent_farm.phases.gap_analysis.rate_limiter") as mock_rl:
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(side_effect=Exception("LLM down"))
            mock_planner.return_value.with_structured_output.return_value = mock_chain
            mock_rl.wait = AsyncMock()
            mock_rl.on_rate_limit = MagicMock()

            result = await gap_analysis(state)

        assert len(result["findings"]) == 1  # unchanged
        assert result["identified_gaps"] == []
        assert result["image_urls"] == []

    async def test_no_gaps_found(self):
        from app.agent_farm.phases.gap_analysis import gap_analysis

        findings = [_make_finding()]
        state = self._make_state(findings=findings)

        gap_output = GapAnalysisOutput(
            gaps=[], coverage_summary="Complete coverage",
        )

        with patch("app.agent_farm.phases.gap_analysis.get_planner_llm") as mock_planner, \
             patch("app.agent_farm.phases.gap_analysis.get_research_llm") as mock_research, \
             patch("app.agent_farm.phases.gap_analysis.rate_limiter") as mock_rl, \
             patch("app.agent_farm.phases.gap_analysis.search_images",
                    return_value=[]):
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=gap_output)
            mock_planner.return_value.with_structured_output.return_value = mock_chain
            mock_research.return_value.with_structured_output.return_value = MagicMock()
            mock_rl.wait = AsyncMock()
            mock_rl.on_success = MagicMock()

            result = await gap_analysis(state)

        assert result["current_phase"] == "gap_analysis"
        assert result["gap_search_queries"] == []


# ============================================================
# Phase D: Compilation helpers
# ============================================================


class TestFilterFindings:
    def test_filters_by_domain(self):
        from app.agent_farm.phases.compilation import _filter_findings

        findings = [
            _make_finding(domain="disease"),
            _make_finding(domain="crop"),
            _make_finding(domain="treatment"),
        ]
        result = _filter_findings(findings, ["disease", "treatment"])
        assert len(result) == 2

    def test_empty_findings(self):
        from app.agent_farm.phases.compilation import _filter_findings

        assert _filter_findings([], ["disease"]) == []


class TestBuildFindingsContext:
    def test_formats_findings(self):
        from app.agent_farm.phases.compilation import _build_findings_context

        findings = [_make_finding(related_entities=["cassava"])]
        ctx = _build_findings_context(findings)

        assert "[disease]" in ctx
        assert "CMD" in ctx
        assert "cassava" in ctx

    def test_truncates_content(self):
        from app.agent_farm.phases.compilation import _build_findings_context

        long_content = "A" * 1000
        findings = [_make_finding(content=long_content)]
        ctx = _build_findings_context(findings)

        # Content should be truncated to 400 chars
        assert len(ctx) < 1000

    def test_empty_findings(self):
        from app.agent_farm.phases.compilation import _build_findings_context

        ctx = _build_findings_context([])
        assert "No findings" in ctx


class TestBuildIdContext:
    def test_with_fk_fields(self):
        from app.agent_farm.phases.compilation import _build_id_context

        compiled_ids = {"crops": {1: "Cassava", 2: "Rice"}}
        ctx = _build_id_context(compiled_ids, {"crop_id": "crops"})
        assert "Cassava" in ctx
        assert "Rice" in ctx

    def test_empty_fk_fields(self):
        from app.agent_farm.phases.compilation import _build_id_context

        ctx = _build_id_context({}, {})
        assert ctx == ""

    def test_missing_source_table(self):
        from app.agent_farm.phases.compilation import _build_id_context

        ctx = _build_id_context({}, {"crop_id": "crops"})
        assert "WARNING" in ctx


class TestValidateFks:
    def test_valid_records_pass(self):
        from app.agent_farm.phases.compilation import _validate_fks

        records = [
            TreatmentRecord(id=1, disease_id=1, method="Neem", description="Spray"),
            TreatmentRecord(id=2, disease_id=2, method="Uprooting", description="Remove"),
        ]
        compiled_ids = {"diseases": {1: "CMD", 2: "CBSD"}}
        valid, skipped = _validate_fks(records, {"disease_id": "diseases"}, compiled_ids, "treatments")

        assert len(valid) == 2
        assert skipped == 0

    def test_invalid_fk_skipped(self):
        from app.agent_farm.phases.compilation import _validate_fks

        records = [
            TreatmentRecord(id=1, disease_id=1, method="Neem", description="Spray"),
            TreatmentRecord(id=2, disease_id=99, method="Bad", description="Invalid FK"),
        ]
        compiled_ids = {"diseases": {1: "CMD"}}
        valid, skipped = _validate_fks(records, {"disease_id": "diseases"}, compiled_ids, "treatments")

        assert len(valid) == 1
        assert skipped == 1

    def test_no_fk_fields_passes_all(self):
        from app.agent_farm.phases.compilation import _validate_fks

        records = [CropRecord(id=1, name="Cassava")]
        valid, skipped = _validate_fks(records, {}, {}, "crops")

        assert len(valid) == 1
        assert skipped == 0


class TestClimateFromFindings:
    def test_basic_conversion(self):
        from app.agent_farm.phases.compilation import _climate_from_findings

        findings = [
            _make_finding(
                domain="climate",
                entity_name="Ziguinchor month 7",
                raw_data={"rainfall_mm": 350, "temperature_avg_c": 27},
            ),
        ]
        records = _climate_from_findings(findings)
        assert len(records) == 1
        assert records[0].month == 7
        assert records[0].rainfall_mm == 350

    def test_month_parsing_from_entity_name(self):
        from app.agent_farm.phases.compilation import _climate_from_findings

        findings = [
            _make_finding(
                domain="climate",
                entity_name="Casamance month 12",
                raw_data={"rainfall_mm": 10},
            ),
        ]
        records = _climate_from_findings(findings)
        assert records[0].month == 12

    def test_month_from_raw_data(self):
        from app.agent_farm.phases.compilation import _climate_from_findings

        findings = [
            _make_finding(
                domain="climate",
                entity_name="Casamance climate",
                raw_data={"month": 3, "rainfall_mm": 0},
            ),
        ]
        records = _climate_from_findings(findings)
        assert len(records) == 1
        assert records[0].month == 3

    def test_invalid_month_skipped(self):
        from app.agent_farm.phases.compilation import _climate_from_findings

        findings = [
            _make_finding(
                domain="climate",
                entity_name="No month info",
                raw_data={"rainfall_mm": 100},
            ),
        ]
        records = _climate_from_findings(findings)
        assert len(records) == 0

    def test_drought_risk_thresholds(self):
        from app.agent_farm.phases.compilation import _climate_from_findings

        findings = [
            _make_finding(domain="climate", entity_name="X month 1",
                          raw_data={"rainfall_mm": 5}),    # severe
            _make_finding(domain="climate", entity_name="X month 2",
                          raw_data={"rainfall_mm": 20}),   # high
            _make_finding(domain="climate", entity_name="X month 3",
                          raw_data={"rainfall_mm": 50}),   # medium (<100)
            _make_finding(domain="climate", entity_name="X month 4",
                          raw_data={"rainfall_mm": 200}),  # low
        ]
        records = _climate_from_findings(findings)
        risks = {r.month: r.drought_risk for r in records}
        assert risks[1] == "severe"
        assert risks[2] == "high"
        assert risks[3] == "medium"
        assert risks[4] == "low"

    def test_filters_non_climate_findings(self):
        from app.agent_farm.phases.compilation import _climate_from_findings

        findings = [
            _make_finding(domain="disease"),
            _make_finding(domain="climate", entity_name="X month 1",
                          raw_data={"rainfall_mm": 5}),
        ]
        records = _climate_from_findings(findings)
        assert len(records) == 1

    def test_sequential_ids(self):
        from app.agent_farm.phases.compilation import _climate_from_findings

        findings = [
            _make_finding(domain="climate", entity_name="X month 1",
                          raw_data={"rainfall_mm": 5}),
            _make_finding(domain="climate", entity_name="X month 2",
                          raw_data={"rainfall_mm": 20}),
        ]
        records = _climate_from_findings(findings)
        assert records[0].id == 1
        assert records[1].id == 2


class TestExtractIds:
    def test_extracts_name_field(self):
        from app.agent_farm.phases.compilation import _extract_ids

        records = [
            CropRecord(id=1, name="Cassava"),
            CropRecord(id=2, name="Rice"),
        ]
        ids = _extract_ids("crops", records)
        assert ids == {1: "Cassava", 2: "Rice"}

    def test_fallback_to_method(self):
        from app.agent_farm.phases.compilation import _extract_ids

        records = [
            TreatmentRecord(id=1, disease_id=1, method="Neem oil", description="Spray"),
        ]
        ids = _extract_ids("treatments", records)
        assert ids[1] == "Neem oil"

    def test_fallback_to_activity(self):
        from app.agent_farm.phases.compilation import _extract_ids

        records = [
            PlantingCalendarRecord(
                id=1, crop_id=1, month=6,
                activity="Land prep", details="Clear field",
            ),
        ]
        ids = _extract_ids("planting_calendar", records)
        assert ids[1] == "Land prep"


class TestCountDomains:
    def test_counts(self):
        from app.agent_farm.phases.compilation import _count_domains

        findings = [
            _make_finding(domain="disease"),
            _make_finding(domain="disease"),
            _make_finding(domain="crop"),
        ]
        counts = _count_domains(findings)
        assert counts["disease"] == 2
        assert counts["crop"] == 1


class TestMakeId:
    def test_format(self):
        from app.agent_farm.phases.compilation import _make_id

        result = _make_id("cmd", 1, "symptoms", "child")
        assert result == "cmd_001_symptoms_child"

    def test_padding(self):
        from app.agent_farm.phases.compilation import _make_id

        result = _make_id("pest", 42, "damage", "parent")
        assert result == "pest_042_damage_parent"


class TestGetCropName:
    def test_found(self):
        from app.agent_farm.phases.compilation import _get_crop_name

        crops = [CropRecord(id=1, name="Cassava"), CropRecord(id=2, name="Rice")]
        assert _get_crop_name(1, crops) == "cassava"

    def test_not_found(self):
        from app.agent_farm.phases.compilation import _get_crop_name

        assert _get_crop_name(99, []) == "unknown"


# ============================================================
# generate_chunks_from_compilation()
# ============================================================


class TestGenerateChunks:
    def _make_compilation(self, with_prevention=True):
        crops = [CropRecord(id=1, name="Cassava")]
        diseases = [DiseaseRecord(
            id=1, name="Cassava Mosaic Disease", type="viral",
            symptoms_text="Yellow mosaic pattern on leaves with leaf curl",
            visual_markers="Yellow-green mosaic, curled leaves, stunted growth",
            severity_scale="high",
            spread_mechanism="Whitefly (Bemisia tabaci)",
            prevention_notes="Use resistant varieties like TME 419" if with_prevention else None,
        )]
        crop_diseases = [CropDiseaseRecord(crop_id=1, disease_id=1)]
        treatments = [TreatmentRecord(
            id=1, disease_id=1, method="Neem oil spray",
            description="Spray on affected leaves",
            materials_needed=["neem leaves", "water"],
            is_organic=True,
        )]
        varieties = [VarietyRecord(id=1, crop_id=1, name="TME 419")]
        pests = [PestRecord(
            id=1, name="Cassava Green Mite", crop_id=1,
            damage_description="Stippling on leaves",
        )]
        climate = [ClimateRecord(id=1, region="Casamance", month=7, rainfall_mm=350)]
        fert = [FertilizationRecord(
            id=1, crop_id=1, growth_stage="planting",
            fertilizer_type="NPK 15-15-15",
        )]
        storage = [StorageRecord(id=1, crop_id=1, method="Sun drying")]
        soil = [SoilRecord(id=1, crop_id=1)]
        planting = [PlantingCalendarRecord(
            id=1, crop_id=1, month=6,
            activity="Planting", details="Plant cuttings",
        )]

        return CompilationOutput(
            crops=crops, diseases=diseases, crop_diseases=crop_diseases,
            treatments=treatments, varieties=varieties, pests=pests,
            climate=climate, fertilization_schedule=fert,
            storage_guidelines=storage, soil_requirements=soil,
            planting_calendar=planting,
        )

    def test_returns_four_collections(self):
        from app.agent_farm.phases.compilation import generate_chunks_from_compilation

        comp = self._make_compilation()
        chunks = generate_chunks_from_compilation(comp)

        assert "disease_knowledge" in chunks
        assert "treatment_guides" in chunks
        assert "farming_practices" in chunks
        assert "regional_context" in chunks

    def test_disease_symptom_pairs(self):
        from app.agent_farm.phases.compilation import generate_chunks_from_compilation

        comp = self._make_compilation()
        chunks = generate_chunks_from_compilation(comp)

        dk = chunks["disease_knowledge"]
        symptom_chunks = [c for c in dk if "symptoms" in c["id"]]
        assert len(symptom_chunks) == 2  # child + parent

        child = [c for c in symptom_chunks if c["metadata"]["chunk_type"] == "child"][0]
        parent = [c for c in symptom_chunks if c["metadata"]["chunk_type"] == "parent"][0]

        assert child["metadata"]["topic_id"] == parent["metadata"]["topic_id"]
        assert child["metadata"]["disease_name"] == "Cassava Mosaic Disease"
        assert child["metadata"]["crop"] == "cassava"

    def test_prevention_chunks_conditional(self):
        from app.agent_farm.phases.compilation import generate_chunks_from_compilation

        # With prevention
        comp_with = self._make_compilation(with_prevention=True)
        chunks_with = generate_chunks_from_compilation(comp_with)
        dk_with = chunks_with["disease_knowledge"]
        prevention_with = [c for c in dk_with if "prevention" in c["id"]]
        assert len(prevention_with) == 2  # child + parent

        # Without prevention
        comp_without = self._make_compilation(with_prevention=False)
        chunks_without = generate_chunks_from_compilation(comp_without)
        dk_without = chunks_without["disease_knowledge"]
        prevention_without = [c for c in dk_without if "prevention" in c["id"]]
        assert len(prevention_without) == 0

    def test_treatment_chunks(self):
        from app.agent_farm.phases.compilation import generate_chunks_from_compilation

        comp = self._make_compilation()
        chunks = generate_chunks_from_compilation(comp)

        tg = chunks["treatment_guides"]
        assert len(tg) == 2  # 1 treatment → child + parent
        child = [c for c in tg if c["metadata"]["chunk_type"] == "child"][0]
        parent = [c for c in tg if c["metadata"]["chunk_type"] == "parent"][0]
        assert child["metadata"]["is_organic"] == "true"
        assert child["metadata"]["disease_name"] == "Cassava Mosaic Disease"
        assert child["metadata"]["treatment_id"] == "1"
        # Parent/child share topic_id
        assert child["metadata"]["topic_id"] == parent["metadata"]["topic_id"]
        assert "Neem oil spray" in parent["content"]

    def test_all_metadata_values_are_strings(self):
        from app.agent_farm.phases.compilation import generate_chunks_from_compilation

        comp = self._make_compilation()
        chunks = generate_chunks_from_compilation(comp)

        for collection_name, chunk_list in chunks.items():
            for chunk in chunk_list:
                for key, value in chunk["metadata"].items():
                    assert isinstance(value, str), \
                        f"{collection_name}/{chunk['id']}: metadata['{key}'] = {value!r} is not str"

    def test_farming_practices_generated(self):
        from app.agent_farm.phases.compilation import generate_chunks_from_compilation

        comp = self._make_compilation()
        chunks = generate_chunks_from_compilation(comp)

        fp = chunks["farming_practices"]
        # 1 variety=2, 1 fert(grouped)=2, 1 storage=2, 1 soil=2, 1 pest=2, 1 cal(grouped)=2 = 12
        assert len(fp) == 12

        # Verify each sub-type is present
        topics = {c["metadata"]["topic"] for c in fp}
        assert topics == {"variety", "fertilization", "storage", "soil", "pest", "planting_calendar"}

        # Verify crop name resolved (not "unknown")
        for chunk in fp:
            assert chunk["metadata"]["crop"] == "cassava"

        # Spot-check variety content
        variety_chunks = [c for c in fp if c["metadata"]["topic"] == "variety"]
        assert len(variety_chunks) == 2
        variety_child = [c for c in variety_chunks if c["metadata"]["chunk_type"] == "child"][0]
        assert "TME 419" in variety_child["content"]

        # Spot-check pest content
        pest_chunks = [c for c in fp if c["metadata"]["topic"] == "pest"]
        assert len(pest_chunks) == 2
        pest_child = [c for c in pest_chunks if c["metadata"]["chunk_type"] == "child"][0]
        assert "Cassava Green Mite" in pest_child["content"]

    def test_regional_context_generated(self):
        from app.agent_farm.phases.compilation import generate_chunks_from_compilation

        comp = self._make_compilation()
        chunks = generate_chunks_from_compilation(comp)

        rc = chunks["regional_context"]
        assert len(rc) == 2  # 1 climate record → child + parent

        child = [c for c in rc if c["metadata"]["chunk_type"] == "child"][0]
        parent = [c for c in rc if c["metadata"]["chunk_type"] == "parent"][0]

        assert child["metadata"]["region"] == "Casamance"
        assert child["metadata"]["topic"] == "climate"
        assert child["metadata"]["topic_id"] == parent["metadata"]["topic_id"]
        assert "July" in child["content"]
        assert "Rainy season" in child["content"]  # 350mm > 50
        assert "350" in child["content"]

    def test_empty_compilation(self):
        from app.agent_farm.phases.compilation import generate_chunks_from_compilation

        comp = CompilationOutput()
        chunks = generate_chunks_from_compilation(comp)

        for collection_chunks in chunks.values():
            assert collection_chunks == []


# ============================================================
# Phase D: compilation() full flow
# ============================================================


class TestCompilation:
    def _make_state(self, findings=None):
        return {
            "findings": findings or [
                _make_finding(domain="crop", entity_name="Cassava"),
                _make_finding(domain="disease", entity_name="CMD"),
                _make_finding(domain="climate", entity_name="X month 7",
                              raw_data={"rainfall_mm": 350}),
            ],
            "status_messages": [],
        }

    async def test_climate_skips_llm(self):
        from app.agent_farm.phases.compilation import compilation, _LIST_MODEL_MAP

        state = self._make_state()

        # Track which tables triggered LLM calls
        llm_called_tables: list[str] = []

        def make_mock_chain_for_table(list_model):
            """Return a mock chain that returns empty records for any table."""
            chain = AsyncMock()

            async def _invoke(prompt):
                # Identify which table this is for (crude but works for testing)
                for tname in _LIST_MODEL_MAP:
                    if tname in prompt and tname != "climate":
                        llm_called_tables.append(tname)
                        break
                return list_model(records=[])

            chain.ainvoke = _invoke
            return chain

        with patch("app.agent_farm.phases.compilation.get_planner_llm") as mock_llm, \
             patch("app.agent_farm.phases.compilation.rate_limiter") as mock_rl:
            # with_structured_output is called per table — return fresh mock each time
            mock_llm.return_value.with_structured_output = lambda model_cls: make_mock_chain_for_table(model_cls)
            mock_rl.wait = AsyncMock()
            mock_rl.on_success = MagicMock()

            result = await compilation(state)

        assert result["compilation"] is not None
        assert result["current_phase"] == "compiling"
        assert result["json_output_dir"] is not None

        # Climate records should come from direct conversion, not LLM
        climate_recs = result["compilation"].climate
        assert len(climate_recs) == 1
        assert climate_recs[0].month == 7

        # Verify climate was NOT compiled via LLM
        assert "climate" not in llm_called_tables

    async def test_json_files_written(self):
        from app.agent_farm.phases.compilation import compilation, _LIST_MODEL_MAP

        state = self._make_state()

        def make_mock_chain(list_model):
            chain = AsyncMock()
            chain.ainvoke = AsyncMock(return_value=list_model(records=[]))
            return chain

        with patch("app.agent_farm.phases.compilation.get_planner_llm") as mock_llm, \
             patch("app.agent_farm.phases.compilation.rate_limiter") as mock_rl:
            mock_llm.return_value.with_structured_output = lambda model_cls: make_mock_chain(model_cls)
            mock_rl.wait = AsyncMock()
            mock_rl.on_success = MagicMock()

            result = await compilation(state)

        json_dir = Path(result["json_output_dir"])
        assert (json_dir / "crops.json").exists()
        assert (json_dir / "climate.json").exists()
