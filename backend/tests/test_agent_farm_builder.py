"""Tests for the Knowledge Pack builder's Agent Farm entry points.

Covers:
  - _get_table_columns(): PRAGMA-based column discovery
  - _insert_sqlite_rows(): dict-to-table insertion with column filtering
  - _slugify_entity(): slug generation
  - _build_image_ref_rows(): category mapping, sequential IDs, path format
  - build_pack_from_json(): full flow with real SQLite + ChromaDB

All tests use real SQLite databases in tmp_path. No LLM calls.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app.knowledge_pack.builder import (
    _build_image_ref_rows,
    _get_table_columns,
    _insert_sqlite_rows,
    _slugify_entity,
    build_pack_from_json,
)
from app.knowledge_pack.schema_sqlite import init_sqlite_db


# ============================================================
# Helpers
# ============================================================


@pytest.fixture
def db_conn(tmp_path):
    """Create a real SQLite DB with schema and return the connection."""
    db_path = tmp_path / "knowledge.db"
    conn = init_sqlite_db(db_path)
    yield conn
    conn.close()


def _make_json_dir(tmp_path, table_data=None):
    """Create a json_dir with JSON files for each table."""
    json_dir = tmp_path / "json_output"
    json_dir.mkdir(exist_ok=True)

    default_data = {
        "crops": [{"id": 1, "name": "Cassava"}],
        "diseases": [
            {"id": 1, "name": "CMD", "type": "viral",
             "symptoms_text": "Mosaic pattern", "visual_markers": "Yellow leaves",
             "common_names": json.dumps(["CMD"])}
        ],
        "crop_diseases": [{"crop_id": 1, "disease_id": 1, "susceptibility": "high"}],
        "treatments": [
            {"id": 1, "disease_id": 1, "method": "Neem oil",
             "description": "Spray on leaves",
             "materials_needed": json.dumps(["neem", "water"])}
        ],
        "climate": [
            {"id": 1, "region": "Casamance", "month": 7,
             "rainfall_mm": 350.0, "temperature_avg_c": 27.0}
        ],
        "pests": [],
        "varieties": [],
        "fertilization_schedule": [],
        "planting_calendar": [],
        "storage_guidelines": [],
        "soil_requirements": [],
    }

    data = default_data if table_data is None else {**default_data, **table_data}

    for table_name, rows in data.items():
        (json_dir / f"{table_name}.json").write_text(
            json.dumps(rows, indent=2), encoding="utf-8",
        )

    return json_dir


# ============================================================
# _get_table_columns()
# ============================================================


class TestGetTableColumns:
    def test_known_table(self, db_conn):
        columns = _get_table_columns(db_conn, "crops")
        assert "id" in columns
        assert "name" in columns
        assert "scientific_name" in columns

    def test_unknown_table(self, db_conn):
        columns = _get_table_columns(db_conn, "nonexistent_table")
        assert columns == []

    def test_diseases_table(self, db_conn):
        columns = _get_table_columns(db_conn, "diseases")
        assert "common_names" in columns
        assert "type" in columns


# ============================================================
# _insert_sqlite_rows()
# ============================================================


class TestInsertSqliteRows:
    def test_basic_insert(self, db_conn):
        rows = [{"id": 1, "name": "Cassava"}]
        count = _insert_sqlite_rows(db_conn, "crops", rows)
        db_conn.commit()

        assert count == 1
        result = db_conn.execute("SELECT name FROM crops WHERE id = 1").fetchone()
        assert result[0] == "Cassava"

    def test_filters_unknown_columns(self, db_conn):
        rows = [{"id": 1, "name": "Cassava", "nonexistent_field": "ignored"}]
        count = _insert_sqlite_rows(db_conn, "crops", rows)
        db_conn.commit()

        assert count == 1

    def test_empty_rows(self, db_conn):
        count = _insert_sqlite_rows(db_conn, "crops", [])
        assert count == 0

    def test_unknown_table(self, db_conn):
        count = _insert_sqlite_rows(db_conn, "nonexistent", [{"a": 1}])
        assert count == 0

    def test_multiple_rows(self, db_conn):
        rows = [
            {"id": 1, "name": "Cassava"},
            {"id": 2, "name": "Rice"},
            {"id": 3, "name": "Maize"},
        ]
        count = _insert_sqlite_rows(db_conn, "crops", rows)
        db_conn.commit()

        assert count == 3
        result = db_conn.execute("SELECT COUNT(*) FROM crops").fetchone()
        assert result[0] == 3

    def test_does_not_commit(self, db_conn):
        _insert_sqlite_rows(db_conn, "crops", [{"id": 1, "name": "Test"}])
        # Don't commit — open new connection should see nothing
        db_path = db_conn.execute("PRAGMA database_list").fetchone()[2]
        conn2 = sqlite3.connect(db_path)
        result = conn2.execute("SELECT COUNT(*) FROM crops").fetchone()
        conn2.close()
        assert result[0] == 0


# ============================================================
# _slugify_entity()
# ============================================================


class TestSlugifyEntity:
    def test_basic(self):
        assert _slugify_entity("Cassava Mosaic Disease") == "cassava_mosaic_disease"

    def test_special_chars(self):
        assert _slugify_entity("CMD (viral)") == "cmd_viral"

    def test_strips_underscores(self):
        assert _slugify_entity("___test___") == "test"

    def test_empty(self):
        assert _slugify_entity("") == ""

    def test_unicode(self):
        result = _slugify_entity("mosaïque du manioc")
        assert "mosa" in result


# ============================================================
# _build_image_ref_rows()
# ============================================================


class TestBuildImageRefRows:
    def test_category_mapping(self):
        images = [
            {"local_path": "/tmp/img1.jpg", "category": "diseases", "entity": "CMD"},
            {"local_path": "/tmp/img2.jpg", "category": "healthy", "entity": "Cassava"},
            {"local_path": "/tmp/img3.jpg", "category": "treatments", "entity": "Neem"},
        ]
        rows = _build_image_ref_rows(images)

        assert rows[0]["type"] == "disease_symptom"
        assert rows[1]["type"] == "healthy_reference"
        assert rows[2]["type"] == "treatment_demo"

    def test_unknown_category_defaults(self):
        images = [
            {"local_path": "/tmp/img.jpg", "category": "unknown", "entity": "X"},
        ]
        rows = _build_image_ref_rows(images)
        assert rows[0]["type"] == "disease_symptom"

    def test_sequential_ids(self):
        images = [
            {"local_path": "/tmp/a.jpg", "category": "diseases", "entity": "A"},
            {"local_path": "/tmp/b.jpg", "category": "diseases", "entity": "B"},
        ]
        rows = _build_image_ref_rows(images)
        assert rows[0]["id"] == 1
        assert rows[1]["id"] == 2

    def test_path_format(self):
        images = [
            {"local_path": "/tmp/photo.jpg", "category": "diseases", "entity": "CMD"},
        ]
        rows = _build_image_ref_rows(images)
        assert rows[0]["file_path"] == "images/diseases/cmd/photo.jpg"

    def test_empty_list(self):
        rows = _build_image_ref_rows([])
        assert rows == []


# ============================================================
# build_pack_from_json() integration test
# ============================================================


@pytest.mark.integration
class TestBuildPackFromJson:
    def test_full_flow(self, tmp_path):
        json_dir = _make_json_dir(tmp_path)
        chunks = {
            "disease_knowledge": [
                {"id": "cmd_001_symptoms_child", "content": "Leaf curl",
                 "metadata": {"disease_id": "1", "disease_name": "CMD",
                              "crop": "cassava", "type": "viral",
                              "severity": "high", "topic_id": "cmd_001_symptoms",
                              "chunk_type": "child"}},
                {"id": "cmd_001_symptoms_parent", "content": "Full CMD info",
                 "metadata": {"disease_id": "1", "disease_name": "CMD",
                              "crop": "cassava", "type": "viral",
                              "severity": "high", "topic_id": "cmd_001_symptoms",
                              "chunk_type": "parent"}},
            ],
            "treatment_guides": [],
            "farming_practices": [],
            "regional_context": [],
        }

        pack_path = build_pack_from_json(
            json_dir=json_dir,
            pack_name="test_pack",
            chunks=chunks,
            sources=["PlantVillage", "FAO"],
            base_path=tmp_path / "packs",
        )

        assert pack_path.exists()
        assert (pack_path / "knowledge.db").exists()
        assert (pack_path / "chroma_db").exists()
        assert (pack_path / "manifest.json").exists()
        assert (pack_path / "README.md").exists()
        assert (pack_path / "SOURCES.md").exists()

    def test_sqlite_populated(self, tmp_path):
        json_dir = _make_json_dir(tmp_path)
        chunks = {"disease_knowledge": [], "treatment_guides": [],
                  "farming_practices": [], "regional_context": []}

        pack_path = build_pack_from_json(
            json_dir=json_dir, pack_name="test_pack",
            chunks=chunks, base_path=tmp_path / "packs",
        )

        conn = sqlite3.connect(str(pack_path / "knowledge.db"))
        crops = conn.execute("SELECT COUNT(*) FROM crops").fetchone()[0]
        diseases = conn.execute("SELECT COUNT(*) FROM diseases").fetchone()[0]
        climate = conn.execute("SELECT COUNT(*) FROM climate").fetchone()[0]
        conn.close()

        assert crops == 1
        assert diseases == 1
        assert climate == 1

    def test_chroma_populated(self, tmp_path):
        json_dir = _make_json_dir(tmp_path)
        chunks = {
            "disease_knowledge": [
                {"id": "test_child", "content": "Test content for searching",
                 "metadata": {"disease_id": "1", "disease_name": "CMD",
                              "crop": "cassava", "type": "viral",
                              "severity": "high", "topic_id": "test_001",
                              "chunk_type": "child"}},
            ],
            "treatment_guides": [],
            "farming_practices": [],
            "regional_context": [],
        }

        pack_path = build_pack_from_json(
            json_dir=json_dir, pack_name="test_pack",
            chunks=chunks, base_path=tmp_path / "packs",
        )

        import chromadb
        client = chromadb.PersistentClient(path=str(pack_path / "chroma_db"))
        collections = client.list_collections()
        assert len(collections) == 4

        dk = client.get_collection("disease_knowledge")
        assert dk.count() == 1

    def test_missing_json_file_warning(self, tmp_path):
        json_dir = tmp_path / "json_output"
        json_dir.mkdir()
        # Only write crops.json — all others missing
        (json_dir / "crops.json").write_text(
            json.dumps([{"id": 1, "name": "Cassava"}]), encoding="utf-8",
        )

        chunks = {"disease_knowledge": [], "treatment_guides": [],
                  "farming_practices": [], "regional_context": []}

        pack_path = build_pack_from_json(
            json_dir=json_dir, pack_name="test_pack",
            chunks=chunks, base_path=tmp_path / "packs",
        )

        assert pack_path.exists()
        conn = sqlite3.connect(str(pack_path / "knowledge.db"))
        crops = conn.execute("SELECT COUNT(*) FROM crops").fetchone()[0]
        diseases = conn.execute("SELECT COUNT(*) FROM diseases").fetchone()[0]
        conn.close()
        assert crops == 1
        assert diseases == 0

    def test_images_copied(self, tmp_path):
        json_dir = _make_json_dir(tmp_path)
        chunks = {"disease_knowledge": [], "treatment_guides": [],
                  "farming_practices": [], "regional_context": []}

        # Create a fake image file
        img_dir = tmp_path / "downloaded_images"
        img_dir.mkdir()
        img_file = img_dir / "test_photo.jpg"
        img_file.write_bytes(b"\xff\xd8" + b"\x00" * 100)

        pack_path = build_pack_from_json(
            json_dir=json_dir, pack_name="test_pack",
            chunks=chunks,
            downloaded_images=[{
                "local_path": str(img_file),
                "category": "diseases",
                "entity": "CMD",
            }],
            base_path=tmp_path / "packs",
        )

        # Check image was copied
        expected_dir = pack_path / "images" / "diseases" / "cmd"
        assert expected_dir.exists()
        copied_files = list(expected_dir.iterdir())
        assert len(copied_files) == 1

        # Check image_refs table — verify content, not just count
        conn = sqlite3.connect(str(pack_path / "knowledge.db"))
        refs = conn.execute("SELECT COUNT(*) FROM image_refs").fetchone()[0]
        assert refs == 1
        row = conn.execute(
            "SELECT file_path, type, description FROM image_refs WHERE id=1"
        ).fetchone()
        conn.close()
        assert row[0] == "images/diseases/cmd/test_photo.jpg"
        assert row[1] == "disease_symptom"

    def test_missing_image_skipped(self, tmp_path):
        json_dir = _make_json_dir(tmp_path)
        chunks = {"disease_knowledge": [], "treatment_guides": [],
                  "farming_practices": [], "regional_context": []}

        pack_path = build_pack_from_json(
            json_dir=json_dir, pack_name="test_pack",
            chunks=chunks,
            downloaded_images=[{
                "local_path": "/nonexistent/image.jpg",
                "category": "diseases",
                "entity": "CMD",
            }],
            base_path=tmp_path / "packs",
        )

        conn = sqlite3.connect(str(pack_path / "knowledge.db"))
        refs = conn.execute("SELECT COUNT(*) FROM image_refs").fetchone()[0]
        conn.close()
        assert refs == 0

    def test_manifest_has_crop_names(self, tmp_path):
        json_dir = _make_json_dir(tmp_path)
        chunks = {"disease_knowledge": [], "treatment_guides": [],
                  "farming_practices": [], "regional_context": []}

        pack_path = build_pack_from_json(
            json_dir=json_dir, pack_name="test_pack",
            chunks=chunks, base_path=tmp_path / "packs",
        )

        manifest = json.loads((pack_path / "manifest.json").read_text(encoding="utf-8"))
        assert "Cassava" in manifest["crops"]
