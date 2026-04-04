"""Tests for Step 2.3: Manifest schema validation."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.knowledge_pack.schema_manifest import (
    ManifestSchema,
    ModelsUsed,
    RegionInfo,
    Statistics,
    create_manifest,
    validate_manifest,
)


# --- ManifestSchema ---

def test_manifest_valid():
    manifest = ManifestSchema(
        name="Casamance Agriculture Pack",
        description="Agricultural knowledge for Casamance, Senegal",
        region=RegionInfo(
            name="Casamance",
            country="Senegal",
            coordinates={"lat": 12.55, "lon": -15.5},
            climate_zone="tropical_savanna",
        ),
        crops=["cassava", "rice", "maize"],
        statistics=Statistics(diseases_count=15, treatments_count=30),
        models_used=ModelsUsed(
            embedding_model="all-MiniLM-L6-v2",
            embedding_dimensions=384,
        ),
    )
    assert manifest.name == "Casamance Agriculture Pack"
    assert manifest.region.country == "Senegal"
    assert manifest.statistics.diseases_count == 15


def test_manifest_defaults():
    manifest = ManifestSchema(
        name="Test Pack",
        region=RegionInfo(name="Test", country="Test"),
    )
    assert manifest.version == "1.0.0"
    assert manifest.domain == "agriculture"
    assert manifest.license == "CC-BY-SA-4.0"
    assert manifest.crops == []
    assert manifest.statistics.diseases_count == 0


def test_manifest_missing_name():
    with pytest.raises(ValidationError):
        ManifestSchema(region=RegionInfo(name="Test", country="Test"))


def test_manifest_missing_region():
    with pytest.raises(ValidationError):
        ManifestSchema(name="Test Pack")


# --- JSON round-trip ---

def test_manifest_json_roundtrip():
    original = ManifestSchema(
        name="Test Pack",
        region=RegionInfo(name="Casamance", country="Senegal"),
        crops=["cassava"],
        statistics=Statistics(diseases_count=5),
    )
    json_str = original.model_dump_json(by_alias=True)
    restored = ManifestSchema.model_validate_json(json_str)
    assert restored.name == original.name
    assert restored.crops == original.crops


def test_manifest_schema_alias():
    """$schema field should serialize with the alias."""
    manifest = ManifestSchema(
        name="Test",
        region=RegionInfo(name="Test", country="Test"),
    )
    dumped = manifest.model_dump(by_alias=True)
    assert "$schema" in dumped
    assert dumped["$schema"] == "fieldpack-manifest-v1"


# --- RegionInfo ---

def test_region_info_with_coordinates():
    region = RegionInfo(
        name="Casamance",
        country="Senegal",
        coordinates={"lat": 12.55, "lon": -15.5},
        climate_zone="tropical_savanna",
    )
    assert region.coordinates["lat"] == 12.55


def test_region_info_minimal():
    region = RegionInfo(name="Test", country="Test")
    assert region.coordinates == {}
    assert region.climate_zone == ""


# --- Statistics ---

def test_statistics_defaults():
    stats = Statistics()
    assert stats.diseases_count == 0
    assert stats.total_size_mb == 0.0


def test_statistics_all_fields():
    stats = Statistics(
        diseases_count=15,
        treatments_count=30,
        farming_practices_count=10,
        text_chunks=90,
        images_count=50,
        total_size_mb=250.5,
    )
    assert stats.text_chunks == 90


# --- ModelsUsed ---

def test_models_used():
    models = ModelsUsed(
        research_agents="gemma-4-26b-a4b-it",
        knowledge_compiler="gemma-4-31b-it",
        embedding_model="all-MiniLM-L6-v2",
        embedding_dimensions=384,
    )
    assert models.embedding_dimensions == 384


# --- File I/O ---

def test_create_and_validate_manifest(tmp_path):
    """create_manifest writes a file that validate_manifest can read."""
    created = create_manifest(
        pack_path=tmp_path,
        name="Test Pack",
        description="A test knowledge pack",
        region=RegionInfo(name="Casamance", country="Senegal"),
        crops=["cassava", "rice"],
        statistics=Statistics(diseases_count=5, treatments_count=10),
        models_used=ModelsUsed(
            embedding_model="all-MiniLM-L6-v2",
            embedding_dimensions=384,
        ),
        sources=["FAO", "IITA"],
    )
    assert created.name == "Test Pack"

    # Verify file exists
    manifest_path = tmp_path / "manifest.json"
    assert manifest_path.exists()

    # Validate it back
    loaded = validate_manifest(manifest_path)
    assert loaded.name == "Test Pack"
    assert loaded.crops == ["cassava", "rice"]
    assert loaded.statistics.diseases_count == 5
    assert loaded.sources == ["FAO", "IITA"]


def test_create_manifest_has_timestamp(tmp_path):
    created = create_manifest(
        pack_path=tmp_path,
        name="Test",
        description="",
        region=RegionInfo(name="Test", country="Test"),
        crops=[],
        statistics=Statistics(),
        models_used=ModelsUsed(),
    )
    assert created.created_at != ""
    assert "T" in created.created_at  # ISO format


def test_validate_manifest_invalid_json(tmp_path):
    bad_file = tmp_path / "manifest.json"
    bad_file.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_manifest(bad_file)


def test_validate_manifest_missing_fields(tmp_path):
    bad_file = tmp_path / "manifest.json"
    bad_file.write_text('{"version": "1.0"}', encoding="utf-8")
    with pytest.raises(ValidationError):
        validate_manifest(bad_file)


def test_manifest_json_file_is_readable(tmp_path):
    """The manifest.json should be human-readable (pretty-printed)."""
    create_manifest(
        pack_path=tmp_path,
        name="Test Pack",
        description="Test",
        region=RegionInfo(name="Casamance", country="Senegal"),
        crops=["cassava"],
        statistics=Statistics(),
        models_used=ModelsUsed(),
    )
    raw = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    # Pretty-printed JSON has newlines
    assert "\n" in raw
    # And indentation
    assert "  " in raw
