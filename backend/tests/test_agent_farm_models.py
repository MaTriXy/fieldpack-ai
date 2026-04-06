"""Tests for Phase 1 Agent Farm data models.

Covers:
  - Dataclasses: PageSection, SourceConfig, Finding
  - Pydantic extraction models: FindingExtract, ExtractionOutput
  - Pydantic gap analysis models: IdentifiedGap, GapAnalysisOutput
  - Pydantic compilation models: all 11 table records + CompilationOutput
  - Helpers: finding_extract_to_dataclass(), record_to_sqlite_row()
"""

import json
from dataclasses import asdict

import pytest
from pydantic import ValidationError

from app.agent_farm.models import (
    CompilationOutput,
    ClimateRecord,
    CropDiseaseRecord,
    CropRecord,
    DiseaseRecord,
    ExtractionOutput,
    FertilizationRecord,
    Finding,
    FindingExtract,
    GapAnalysisOutput,
    IdentifiedGap,
    JSON_ARRAY_FIELDS,
    PageSection,
    PestRecord,
    PlantingCalendarRecord,
    SoilRecord,
    SourceConfig,
    StorageRecord,
    TreatmentRecord,
    VarietyRecord,
    finding_extract_to_dataclass,
    record_to_sqlite_row,
)


# ============================================================
# Dataclasses
# ============================================================


class TestPageSection:
    def test_required_fields(self):
        s = PageSection(
            source_url="https://example.com",
            source_name="Test",
            heading="Diseases",
            content="Some content about diseases",
        )
        assert s.source_url == "https://example.com"
        assert s.heading == "Diseases"

    def test_defaults(self):
        s = PageSection(
            source_url="u", source_name="n", heading="h", content="c",
        )
        assert s.crop == ""
        assert s.section_type == ""
        assert s.tables == []

    def test_crop_field_settable(self):
        s = PageSection(
            source_url="u", source_name="n", heading="h", content="c",
        )
        s.crop = "cassava"
        assert s.crop == "cassava"

    def test_tables_default_is_independent(self):
        s1 = PageSection(source_url="u", source_name="n", heading="h", content="c")
        s2 = PageSection(source_url="u", source_name="n", heading="h", content="c")
        s1.tables.append([["a", "b"]])
        assert s2.tables == []


class TestSourceConfig:
    def test_construction(self):
        sc = SourceConfig(
            name="Test",
            url_template="https://example.com/{slug}",
            slug_map={"cassava": "cas"},
            parser_type="html_headings",
        )
        assert sc.tier == 1
        assert sc.parser_type == "html_headings"

    def test_url_template_substitution(self):
        sc = SourceConfig(
            name="Test",
            url_template="https://example.com/{slug}/info",
            slug_map={"rice": "rice-page"},
            parser_type="pdf_pages",
            tier=2,
        )
        url = sc.url_template.format(slug=sc.slug_map["rice"])
        assert url == "https://example.com/rice-page/info"


class TestFinding:
    def test_required_fields(self):
        f = Finding(domain="disease", entity_name="CMD", content="Causes leaf curl")
        assert f.domain == "disease"
        assert f.entity_name == "CMD"

    def test_defaults(self):
        f = Finding(domain="crop", entity_name="Cassava", content="Staple crop")
        assert f.related_entities == []
        assert f.source == ""
        assert f.confidence == 0.8
        assert f.raw_data == {}

    def test_related_entities_default_is_independent(self):
        f1 = Finding(domain="crop", entity_name="A", content="c")
        f2 = Finding(domain="crop", entity_name="B", content="c")
        f1.related_entities.append("whitefly")
        assert f2.related_entities == []

    def test_all_fields(self):
        f = Finding(
            domain="treatment",
            entity_name="Neem oil",
            content="Organic pest control",
            related_entities=["whitefly", "cassava"],
            source="FAO p.23",
            confidence=0.9,
            raw_data={"cost_xof": 500},
        )
        assert f.confidence == 0.9
        assert f.raw_data["cost_xof"] == 500

    def test_asdict(self):
        f = Finding(domain="pest", entity_name="Mite", content="Damages leaves")
        d = asdict(f)
        assert d["domain"] == "pest"
        assert isinstance(d["related_entities"], list)


# ============================================================
# Pydantic extraction models
# ============================================================


class TestFindingExtract:
    def test_valid_construction(self):
        fe = FindingExtract(
            domain="disease",
            entity_name="CMD",
            content="Causes mosaic pattern on cassava leaves",
            related_entities=["cassava"],
            raw_data={"vector": "whitefly"},
        )
        assert fe.domain == "disease"
        assert fe.confidence == 0.8

    def test_invalid_domain_rejected(self):
        with pytest.raises(ValidationError):
            FindingExtract(
                domain="invalid_domain",
                entity_name="X",
                content="Y",
                related_entities=[],
                raw_data={},
            )

    def test_all_valid_domains(self):
        valid_domains = [
            "crop", "disease", "treatment", "pest", "variety", "climate",
            "soil", "fertilization", "storage", "planting", "practice", "regional",
        ]
        for domain in valid_domains:
            fe = FindingExtract(
                domain=domain, entity_name="X", content="Y",
                related_entities=[], raw_data={},
            )
            assert fe.domain == domain

    def test_strict_false_coerces_confidence(self):
        fe = FindingExtract(
            domain="crop",
            entity_name="X",
            content="Y",
            related_entities=[],
            confidence="0.95",
            raw_data={},
        )
        assert fe.confidence == 0.95


class TestExtractionOutput:
    def test_empty_findings(self):
        eo = ExtractionOutput(findings=[])
        assert eo.findings == []

    def test_with_findings(self):
        fe = FindingExtract(
            domain="crop", entity_name="Rice", content="Staple",
            related_entities=[], raw_data={},
        )
        eo = ExtractionOutput(findings=[fe])
        assert len(eo.findings) == 1


# ============================================================
# Pydantic gap analysis models
# ============================================================


class TestIdentifiedGap:
    def test_valid_construction(self):
        gap = IdentifiedGap(
            domain="variety",
            entity_name="rice varieties for Casamance",
            description="No local variety data gathered",
            search_query="drought resistant rice varieties Casamance Senegal",
        )
        assert gap.priority == "medium"

    def test_invalid_priority_rejected(self):
        with pytest.raises(ValidationError):
            IdentifiedGap(
                domain="crop",
                entity_name="X",
                description="Y",
                search_query="Z",
                priority="urgent",
            )

    def test_high_priority(self):
        gap = IdentifiedGap(
            domain="treatment",
            entity_name="CMD treatment",
            description="Missing treatment protocols",
            search_query="cassava mosaic disease treatment",
            priority="high",
        )
        assert gap.priority == "high"


class TestGapAnalysisOutput:
    def test_construction(self):
        out = GapAnalysisOutput(
            gaps=[],
            coverage_summary="Good coverage across all domains",
        )
        assert out.gaps == []
        assert "coverage" in out.coverage_summary.lower()


# ============================================================
# finding_extract_to_dataclass()
# ============================================================


class TestFindingExtractToDataclass:
    def test_basic_conversion(self):
        fe = FindingExtract(
            domain="disease",
            entity_name="CMD",
            content="Leaf curl symptoms",
            related_entities=["cassava"],
            confidence=0.9,
            raw_data={"severity": "high"},
        )
        f = finding_extract_to_dataclass(fe, source="https://example.com")
        assert isinstance(f, Finding)
        assert f.domain == "disease"
        assert f.entity_name == "CMD"
        assert f.source == "https://example.com"
        assert f.confidence == 0.9
        assert f.raw_data == {"severity": "high"}
        assert f.related_entities == ["cassava"]

    def test_source_is_from_argument_not_extract(self):
        fe = FindingExtract(
            domain="crop", entity_name="X", content="Y",
            related_entities=[], raw_data={},
        )
        f = finding_extract_to_dataclass(fe, source="override_source")
        assert f.source == "override_source"


# ============================================================
# Compilation record models
# ============================================================


class TestCropRecord:
    def test_minimal(self):
        r = CropRecord(id=1, name="Cassava")
        assert r.id == 1
        assert r.scientific_name is None
        assert r.intercrop_companions == []
        assert r.confidence == 0.8
        assert r.data_gaps == []

    def test_full(self):
        r = CropRecord(
            id=1, name="Cassava", scientific_name="Manihot esculenta",
            family="Euphorbiaceae", growing_season="June-December",
            water_needs_mm_per_week=25.0, drought_tolerance="high",
            region_suitability="Well-suited", planting_notes="Use cuttings",
            harvest_notes="8-12 months", soil_ph_min=5.5, soil_ph_max=7.0,
            seed_rate_kg_per_ha=10000.0,
            intercrop_companions=["maize", "groundnut"],
            confidence=0.95, data_gaps=["water_needs"],
        )
        assert r.drought_tolerance == "high"
        assert len(r.intercrop_companions) == 2

    def test_invalid_drought_tolerance(self):
        with pytest.raises(ValidationError):
            CropRecord(id=1, name="X", drought_tolerance="extreme")

    def test_strict_false_coerces_id(self):
        r = CropRecord(id="3", name="Maize")
        assert r.id == 3


class TestDiseaseRecord:
    def test_minimal(self):
        r = DiseaseRecord(
            id=1, name="CMD", type="viral",
            symptoms_text="Leaf curl and mosaic",
            visual_markers="Yellow-green mosaic pattern",
        )
        assert r.severity_scale == "medium"
        assert r.common_names == []

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            DiseaseRecord(
                id=1, name="X", type="parasitic",
                symptoms_text="Y", visual_markers="Z",
            )

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError):
            DiseaseRecord(
                id=1, name="X", type="viral",
                symptoms_text="Y", visual_markers="Z",
                severity_scale="extreme",
            )


class TestCropDiseaseRecord:
    def test_construction(self):
        r = CropDiseaseRecord(crop_id=1, disease_id=2)
        assert r.susceptibility == "medium"

    def test_no_id_field(self):
        r = CropDiseaseRecord(crop_id=1, disease_id=1)
        assert not hasattr(r, "id")


class TestTreatmentRecord:
    def test_minimal(self):
        r = TreatmentRecord(
            id=1, disease_id=1, method="Neem oil",
            description="Spray on affected leaves",
        )
        assert r.is_organic is True
        assert r.treatment_type == "curative"
        assert r.materials_needed == []

    def test_invalid_difficulty(self):
        with pytest.raises(ValidationError):
            TreatmentRecord(
                id=1, disease_id=1, method="X", description="Y",
                difficulty="impossible",
            )


class TestClimateRecord:
    def test_minimal(self):
        r = ClimateRecord(id=1, region="Casamance", month=7)
        assert r.rainfall_mm is None

    def test_month_range_validation(self):
        with pytest.raises(ValidationError):
            ClimateRecord(id=1, region="X", month=0)
        with pytest.raises(ValidationError):
            ClimateRecord(id=1, region="X", month=13)

    def test_month_boundaries(self):
        ClimateRecord(id=1, region="X", month=1)
        ClimateRecord(id=2, region="X", month=12)


class TestPestRecord:
    def test_minimal(self):
        r = PestRecord(id=1, name="Mite", crop_id=1, damage_description="Leaf damage")
        assert r.type == "insect"

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            PestRecord(
                id=1, name="X", crop_id=1,
                damage_description="Y", type="fungus",
            )


class TestVarietyRecord:
    def test_minimal(self):
        r = VarietyRecord(id=1, crop_id=1, name="TME 419")
        assert r.local_names == []
        assert r.disease_resistance == []

    def test_strict_false_coerces_days(self):
        r = VarietyRecord(id=1, crop_id=1, name="X", days_to_maturity="180")
        assert r.days_to_maturity == 180


class TestFertilizationRecord:
    def test_minimal(self):
        r = FertilizationRecord(
            id=1, crop_id=1, growth_stage="planting",
            fertilizer_type="NPK 15-15-15",
        )
        assert r.dose_per_ha is None


class TestPlantingCalendarRecord:
    def test_minimal(self):
        r = PlantingCalendarRecord(
            id=1, crop_id=1, month=6,
            activity="Planting", details="Plant cuttings",
        )
        assert r.is_critical is False

    def test_month_validation(self):
        with pytest.raises(ValidationError):
            PlantingCalendarRecord(
                id=1, crop_id=1, month=13,
                activity="X", details="Y",
            )
        with pytest.raises(ValidationError):
            PlantingCalendarRecord(
                id=1, crop_id=1, month=0,
                activity="X", details="Y",
            )


class TestStorageRecord:
    def test_minimal(self):
        r = StorageRecord(id=1, crop_id=1, method="Sun drying")
        assert r.optimal_temp_c is None
        assert r.max_duration_months is None


class TestSoilRecord:
    def test_minimal(self):
        r = SoilRecord(id=1, crop_id=1)
        assert r.amendments_needed == []
        assert r.ph_min is None


class TestCompilationOutput:
    def test_empty_defaults(self):
        co = CompilationOutput()
        assert co.crops == []
        assert co.diseases == []
        assert co.treatments == []
        assert co.climate == []
        assert co.pests == []
        assert co.varieties == []
        assert co.fertilization_schedule == []
        assert co.planting_calendar == []
        assert co.storage_guidelines == []
        assert co.soil_requirements == []
        assert co.crop_diseases == []

    def test_with_records(self):
        co = CompilationOutput(
            crops=[CropRecord(id=1, name="Cassava")],
            diseases=[DiseaseRecord(
                id=1, name="CMD", type="viral",
                symptoms_text="Mosaic", visual_markers="Yellow",
            )],
        )
        assert len(co.crops) == 1
        assert len(co.diseases) == 1


# ============================================================
# record_to_sqlite_row()
# ============================================================


class TestRecordToSqliteRow:
    def test_strips_confidence_and_data_gaps(self):
        r = CropRecord(id=1, name="Cassava", confidence=0.95, data_gaps=["family"])
        row = record_to_sqlite_row("crops", r)
        assert "confidence" not in row
        assert "data_gaps" not in row
        assert row["name"] == "Cassava"

    def test_json_dumps_array_fields_crops(self):
        r = CropRecord(id=1, name="Cassava", intercrop_companions=["maize", "beans"])
        row = record_to_sqlite_row("crops", r)
        assert row["intercrop_companions"] == json.dumps(["maize", "beans"])
        assert isinstance(row["intercrop_companions"], str)

    def test_json_dumps_array_fields_diseases(self):
        r = DiseaseRecord(
            id=1, name="CMD", type="viral",
            symptoms_text="Mosaic", visual_markers="Yellow",
            common_names=["CMD", "mosaique"],
        )
        row = record_to_sqlite_row("diseases", r)
        assert row["common_names"] == json.dumps(["CMD", "mosaique"])

    def test_json_dumps_array_fields_treatments(self):
        r = TreatmentRecord(
            id=1, disease_id=1, method="Neem", description="Spray",
            materials_needed=["neem leaves", "water"],
        )
        row = record_to_sqlite_row("treatments", r)
        assert row["materials_needed"] == json.dumps(["neem leaves", "water"])

    def test_json_dumps_array_fields_varieties(self):
        r = VarietyRecord(
            id=1, crop_id=1, name="TME 419",
            local_names=["local1"], disease_resistance=["CMD"],
        )
        row = record_to_sqlite_row("varieties", r)
        assert row["local_names"] == json.dumps(["local1"])
        assert row["disease_resistance"] == json.dumps(["CMD"])

    def test_json_dumps_array_fields_soil(self):
        r = SoilRecord(id=1, crop_id=1, amendments_needed=["lime", "compost"])
        row = record_to_sqlite_row("soil_requirements", r)
        assert row["amendments_needed"] == json.dumps(["lime", "compost"])

    def test_json_dumps_array_fields_pests(self):
        r = PestRecord(
            id=1, name="Mite", crop_id=1,
            damage_description="Leaf damage",
            common_names=["green mite"],
        )
        row = record_to_sqlite_row("pests", r)
        assert row["common_names"] == json.dumps(["green mite"])

    def test_unknown_table_skips_json_serialization(self):
        r = CropRecord(id=1, name="X", intercrop_companions=["a"])
        row = record_to_sqlite_row("unknown_table", r)
        # No JSON_ARRAY_FIELDS entry for "unknown_table" → list stays as-is
        assert row["intercrop_companions"] == ["a"]

    def test_empty_array_fields(self):
        r = CropRecord(id=1, name="Cassava", intercrop_companions=[])
        row = record_to_sqlite_row("crops", r)
        assert row["intercrop_companions"] == json.dumps([])

    def test_climate_no_array_fields(self):
        r = ClimateRecord(id=1, region="Casamance", month=7, rainfall_mm=250.0)
        row = record_to_sqlite_row("climate", r)
        assert row["region"] == "Casamance"
        assert row["rainfall_mm"] == 250.0
        assert "confidence" not in row

    def test_crop_disease_no_array_fields(self):
        r = CropDiseaseRecord(crop_id=1, disease_id=2, susceptibility="high")
        row = record_to_sqlite_row("crop_diseases", r)
        assert row["susceptibility"] == "high"
        assert "confidence" not in row
        assert "data_gaps" not in row

    def test_preserves_none_values(self):
        r = CropRecord(id=1, name="Cassava")
        row = record_to_sqlite_row("crops", r)
        assert row["scientific_name"] is None
        assert row["family"] is None

    def test_json_array_fields_constant_covers_all_tables(self):
        expected_tables = {
            "crops", "diseases", "treatments", "pests",
            "varieties", "soil_requirements",
        }
        assert set(JSON_ARRAY_FIELDS.keys()) == expected_tables
