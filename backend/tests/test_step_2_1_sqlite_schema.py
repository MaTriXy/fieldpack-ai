"""Tests for Step 2.1: SQLite DDL + FTS5 + triggers + indexes."""

import json
import sqlite3
from pathlib import Path

import pytest

from app.knowledge_pack.schema_sqlite import (
    FTS_TABLE_MAP,
    TABLE_JOINS,
    VALID_TABLES,
    init_sqlite_db,
    verify_sqlite_schema,
)


@pytest.fixture
def db(tmp_path):
    """Create a fresh test database."""
    db_path = tmp_path / "test_knowledge.db"
    conn = init_sqlite_db(db_path)
    yield conn
    conn.close()


# --- Table creation ---

def test_all_tables_created(db):
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    table_names = {t[0] for t in tables}
    expected = {
        "crops", "diseases", "crop_diseases", "treatments", "climate",
        "image_refs", "field_observations",
        "pests", "varieties", "fertilization_schedule",
        "planting_calendar", "storage_guidelines", "soil_requirements",
    }
    assert expected.issubset(table_names)


def test_fts5_tables_created(db):
    """FTS5 tables appear in sqlite_master as type='table'."""
    for fts_table in FTS_TABLE_MAP.values():
        result = db.execute(f"SELECT * FROM {fts_table} LIMIT 0").fetchall()
        assert result == []


def test_db_file_created(tmp_path):
    db_path = tmp_path / "test.db"
    conn = init_sqlite_db(db_path)
    conn.close()
    assert db_path.exists()
    assert db_path.stat().st_size > 0


def test_wal_mode_enabled(db):
    result = db.execute("PRAGMA journal_mode").fetchone()
    assert result[0] == "wal"


def test_foreign_keys_enabled(db):
    result = db.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1


# --- Column structure ---

def test_crops_table_columns(db):
    cols = db.execute("PRAGMA table_info(crops)").fetchall()
    col_names = [c[1] for c in cols]
    assert "name" in col_names
    assert "scientific_name" in col_names
    assert "drought_tolerance" in col_names
    assert "soil_ph_min" in col_names
    assert "soil_ph_max" in col_names
    assert "seed_rate_kg_per_ha" in col_names
    assert "intercrop_companions" in col_names
    assert len(cols) == 14


def test_diseases_table_columns(db):
    cols = db.execute("PRAGMA table_info(diseases)").fetchall()
    col_names = [c[1] for c in cols]
    assert "visual_markers" in col_names
    assert "common_names" in col_names
    assert "affected_growth_stage" in col_names
    assert "season_risk_peak" in col_names
    assert len(cols) == 11


def test_treatments_table_columns(db):
    cols = db.execute("PRAGMA table_info(treatments)").fetchall()
    col_names = [c[1] for c in cols]
    assert "materials_needed" in col_names
    assert "is_organic" in col_names
    assert "cost_estimate_xof" in col_names
    assert "treatment_type" in col_names
    assert len(cols) == 13


# --- Unique constraints ---

def test_duplicate_crop_name_rejected(db):
    db.execute("INSERT INTO crops (name) VALUES ('cassava')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO crops (name) VALUES ('cassava')")


def test_duplicate_disease_name_rejected(db):
    db.execute(
        "INSERT INTO diseases (name, symptoms_text, visual_markers) "
        "VALUES ('CMD', 'symptoms', 'markers')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO diseases (name, symptoms_text, visual_markers) "
            "VALUES ('CMD', 'other symptoms', 'other markers')"
        )


# --- CHECK constraints ---

def test_disease_type_check(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO diseases (name, type, symptoms_text, visual_markers) "
            "VALUES ('test', 'invalid_type', 's', 'v')"
        )


def test_severity_scale_check(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO diseases (name, severity_scale, symptoms_text, visual_markers) "
            "VALUES ('test', 'extreme', 's', 'v')"
        )


def test_drought_tolerance_check(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO crops (name, drought_tolerance) VALUES ('test', 'extreme')")


# --- FTS5 trigger sync ---

def test_fts5_insert_trigger(db):
    """Insert into diseases → should appear in diseases_fts."""
    db.execute(
        "INSERT INTO diseases (id, name, common_names, symptoms_text, visual_markers, prevention_notes) "
        "VALUES (1, 'Cassava Mosaic Disease', 'CMD', 'yellow mosaic on leaves', 'mosaic pattern curling', 'use clean cuttings')"
    )
    db.commit()
    results = db.execute(
        "SELECT * FROM diseases_fts WHERE diseases_fts MATCH 'mosaic'"
    ).fetchall()
    assert len(results) >= 1
    assert "Cassava Mosaic Disease" in results[0][0]


def test_fts5_delete_trigger(db):
    """Delete from diseases → should disappear from diseases_fts."""
    db.execute(
        "INSERT INTO diseases (id, name, symptoms_text, visual_markers) "
        "VALUES (1, 'Test Disease', 'test symptoms', 'test markers')"
    )
    db.commit()
    db.execute("DELETE FROM diseases WHERE id = 1")
    db.commit()
    results = db.execute(
        "SELECT * FROM diseases_fts WHERE diseases_fts MATCH 'test'"
    ).fetchall()
    assert len(results) == 0


def test_fts5_update_trigger(db):
    """Update diseases → FTS5 should reflect the change."""
    db.execute(
        "INSERT INTO diseases (id, name, symptoms_text, visual_markers) "
        "VALUES (1, 'Old Name', 'old symptoms', 'old markers')"
    )
    db.commit()
    db.execute(
        "UPDATE diseases SET name = 'New Name', symptoms_text = 'new symptoms', "
        "visual_markers = 'new markers' WHERE id = 1"
    )
    db.commit()
    old = db.execute("SELECT * FROM diseases_fts WHERE diseases_fts MATCH 'old'").fetchall()
    new = db.execute("SELECT * FROM diseases_fts WHERE diseases_fts MATCH 'new'").fetchall()
    assert len(old) == 0
    assert len(new) >= 1


def test_fts5_treatments_trigger(db):
    """Treatments FTS5 sync works."""
    db.execute(
        "INSERT INTO diseases (id, name, symptoms_text, visual_markers) VALUES (1, 'd1', 's', 'v')"
    )
    db.execute(
        "INSERT INTO treatments (id, disease_id, method, description, materials_needed) "
        "VALUES (1, 1, 'Neem oil spray', 'Apply neem oil to affected plants', "
        "'[\"neem seeds\", \"water\", \"cloth filter\"]')"
    )
    db.commit()
    results = db.execute(
        "SELECT * FROM treatments_fts WHERE treatments_fts MATCH 'neem'"
    ).fetchall()
    assert len(results) >= 1


def test_fts5_crops_trigger(db):
    """Crops FTS5 sync works."""
    db.execute(
        "INSERT INTO crops (id, name, scientific_name, region_suitability) "
        "VALUES (1, 'cassava', 'Manihot esculenta', 'tropical lowlands')"
    )
    db.commit()
    results = db.execute(
        "SELECT * FROM crops_fts WHERE crops_fts MATCH 'cassava'"
    ).fetchall()
    assert len(results) >= 1


# --- FTS5 prefix search ---

def test_fts5_prefix_search(db):
    """Prefix indexing should allow 'cass*' to match 'cassava'."""
    db.execute(
        "INSERT INTO crops (id, name, scientific_name) VALUES (1, 'cassava', 'Manihot esculenta')"
    )
    db.commit()
    results = db.execute(
        "SELECT * FROM crops_fts WHERE crops_fts MATCH 'cass*'"
    ).fetchall()
    assert len(results) >= 1


# --- JSON field support ---

def test_json_materials_needed(db):
    """materials_needed stores JSON arrays. Verify json_each works."""
    db.execute(
        "INSERT INTO diseases (id, name, symptoms_text, visual_markers) VALUES (1, 'd1', 's', 'v')"
    )
    materials = json.dumps(["neem seeds", "water", "cloth filter"])
    db.execute(
        "INSERT INTO treatments (id, disease_id, method, description, materials_needed) "
        "VALUES (1, 1, 'spray', 'desc', ?)", (materials,)
    )
    db.commit()
    results = db.execute(
        "SELECT t.method, j.value FROM treatments t, json_each(t.materials_needed) j "
        "WHERE j.value = 'neem seeds'"
    ).fetchall()
    assert len(results) == 1
    assert results[0][1] == "neem seeds"


def test_json_common_names(db):
    """common_names stores JSON arrays."""
    names = json.dumps(["CMD", "mosaïque du manioc", "cassava mosaic"])
    db.execute(
        "INSERT INTO diseases (id, name, common_names, symptoms_text, visual_markers) "
        "VALUES (1, 'Cassava Mosaic Disease', ?, 'symptoms', 'markers')", (names,)
    )
    db.commit()
    results = db.execute(
        "SELECT d.name, j.value FROM diseases d, json_each(d.common_names) j "
        "WHERE j.value LIKE '%manioc%'"
    ).fetchall()
    assert len(results) == 1


# --- verify_sqlite_schema ---

def test_verify_schema(db):
    schema = verify_sqlite_schema(db)
    assert "crops" in schema
    assert "diseases" in schema
    assert "treatments" in schema
    assert schema["crops"] == 14
    assert schema["diseases"] == 11


# --- Constants ---

def test_valid_tables_list():
    assert "crops" in VALID_TABLES
    assert "diseases" in VALID_TABLES
    assert "pests" in VALID_TABLES
    assert "varieties" in VALID_TABLES
    assert "fertilization_schedule" in VALID_TABLES
    assert "planting_calendar" in VALID_TABLES
    assert "storage_guidelines" in VALID_TABLES
    assert "soil_requirements" in VALID_TABLES
    assert len(VALID_TABLES) == 13


def test_fts_table_map():
    assert FTS_TABLE_MAP["diseases"] == "diseases_fts"
    assert FTS_TABLE_MAP["treatments"] == "treatments_fts"
    assert FTS_TABLE_MAP["crops"] == "crops_fts"
    assert FTS_TABLE_MAP["pests"] == "pests_fts"
    assert FTS_TABLE_MAP["varieties"] == "varieties_fts"
    assert FTS_TABLE_MAP["fertilization_schedule"] == "fertilization_schedule_fts"
    assert FTS_TABLE_MAP["storage_guidelines"] == "storage_guidelines_fts"
    assert FTS_TABLE_MAP["planting_calendar"] == "planting_calendar_fts"
    assert len(FTS_TABLE_MAP) == 8


def test_table_joins():
    assert "diseases" in TABLE_JOINS["treatments"]
    assert "crops" in TABLE_JOINS["crop_diseases"]
    assert "crops" in TABLE_JOINS["pests"]
    assert "crops" in TABLE_JOINS["varieties"]
    assert "crops" in TABLE_JOINS["fertilization_schedule"]
    assert "crops" in TABLE_JOINS["planting_calendar"]
    assert "crops" in TABLE_JOINS["storage_guidelines"]
    assert "crops" in TABLE_JOINS["soil_requirements"]
    assert "crops" in TABLE_JOINS["field_observations"]


# --- New table structure ---

def test_pests_table_columns(db):
    cols = db.execute("PRAGMA table_info(pests)").fetchall()
    col_names = [c[1] for c in cols]
    assert "name" in col_names
    assert "crop_id" in col_names
    assert "damage_description" in col_names
    assert "control_organic" in col_names
    assert len(cols) == 12


def test_varieties_table_columns(db):
    cols = db.execute("PRAGMA table_info(varieties)").fetchall()
    col_names = [c[1] for c in cols]
    assert "crop_id" in col_names
    assert "days_to_maturity" in col_names
    assert "yield_potential_kg_per_ha" in col_names
    assert "disease_resistance" in col_names
    assert len(cols) == 11


def test_fertilization_schedule_columns(db):
    cols = db.execute("PRAGMA table_info(fertilization_schedule)").fetchall()
    col_names = [c[1] for c in cols]
    assert "crop_id" in col_names
    assert "growth_stage" in col_names
    assert "fertilizer_type" in col_names
    assert "organic_alternative" in col_names
    assert len(cols) == 9


def test_planting_calendar_columns(db):
    cols = db.execute("PRAGMA table_info(planting_calendar)").fetchall()
    col_names = [c[1] for c in cols]
    assert "crop_id" in col_names
    assert "month" in col_names
    assert "activity" in col_names
    assert "is_critical" in col_names
    assert len(cols) == 6


def test_storage_guidelines_columns(db):
    cols = db.execute("PRAGMA table_info(storage_guidelines)").fetchall()
    col_names = [c[1] for c in cols]
    assert "crop_id" in col_names
    assert "method" in col_names
    assert "max_duration_months" in col_names
    assert "local_materials" in col_names
    assert len(cols) == 9


def test_soil_requirements_columns(db):
    cols = db.execute("PRAGMA table_info(soil_requirements)").fetchall()
    col_names = [c[1] for c in cols]
    assert "crop_id" in col_names
    assert "ph_min" in col_names
    assert "ph_max" in col_names
    assert "preferred_texture" in col_names
    assert len(cols) == 8


# --- New FTS5 tables ---

def test_pests_fts_trigger(db):
    db.execute("INSERT INTO crops (id, name) VALUES (1, 'cassava')")
    db.execute(
        "INSERT INTO pests (id, name, crop_id, damage_description, control_organic) "
        "VALUES (1, 'Cassava Whitefly', 1, 'Transmits mosaic virus', 'Yellow sticky traps')"
    )
    db.commit()
    results = db.execute(
        "SELECT * FROM pests_fts WHERE pests_fts MATCH 'whitefly'"
    ).fetchall()
    assert len(results) >= 1


def test_varieties_fts_trigger(db):
    db.execute("INSERT INTO crops (id, name) VALUES (1, 'cassava')")
    db.execute(
        "INSERT INTO varieties (id, crop_id, name, local_names, disease_resistance) "
        "VALUES (1, 1, 'TME 419', 'Improved variety', 'CMD resistant')"
    )
    db.commit()
    results = db.execute(
        "SELECT * FROM varieties_fts WHERE varieties_fts MATCH 'TME'"
    ).fetchall()
    assert len(results) >= 1


def test_fertilization_schedule_fts_trigger(db):
    db.execute("INSERT INTO crops (id, name) VALUES (1, 'cassava')")
    db.execute(
        "INSERT INTO fertilization_schedule (id, crop_id, growth_stage, fertilizer_type, organic_alternative) "
        "VALUES (1, 1, 'vegetative', 'NPK 15-15-15', 'Compost and wood ash')"
    )
    db.commit()
    results = db.execute(
        "SELECT * FROM fertilization_schedule_fts WHERE fertilization_schedule_fts MATCH 'compost'"
    ).fetchall()
    assert len(results) >= 1


def test_storage_guidelines_fts_trigger(db):
    db.execute("INSERT INTO crops (id, name) VALUES (1, 'cassava')")
    db.execute(
        "INSERT INTO storage_guidelines (id, crop_id, method, pest_risks, local_materials) "
        "VALUES (1, 1, 'Sun drying', 'Weevil infestation', 'Woven baskets and jute bags')"
    )
    db.commit()
    results = db.execute(
        "SELECT * FROM storage_guidelines_fts WHERE storage_guidelines_fts MATCH 'weevil'"
    ).fetchall()
    assert len(results) >= 1


# --- New table constraints ---

def test_planting_calendar_month_check(db):
    db.execute("INSERT INTO crops (id, name) VALUES (1, 'cassava')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO planting_calendar (crop_id, month, activity) "
            "VALUES (1, 13, 'plant')"
        )


def test_pest_type_check(db):
    db.execute("INSERT INTO crops (id, name) VALUES (1, 'cassava')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO pests (name, crop_id, type) VALUES ('test', 1, 'invalid')"
        )


def test_treatment_type_check(db):
    db.execute(
        "INSERT INTO diseases (id, name, symptoms_text, visual_markers) VALUES (1, 'd1', 's', 'v')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO treatments (disease_id, method, description, treatment_type) "
            "VALUES (1, 'm', 'd', 'invalid')"
        )


def test_flooding_risk_check(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO climate (region, flooding_risk) VALUES ('test', 'extreme')"
        )


def test_severity_observed_check(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO field_observations (timestamp, severity_observed) "
            "VALUES ('2026-01-01', 'extreme')"
        )
