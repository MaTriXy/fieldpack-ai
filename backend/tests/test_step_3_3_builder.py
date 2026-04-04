"""Tests for Step 3.3: Knowledge Pack builder.

NOTE: These tests are slower (~30-60s) because they generate real embeddings.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from app.knowledge_pack.builder import build_pack
from app.knowledge_pack.schema_manifest import validate_manifest


@pytest.fixture(scope="module")
def built_pack(tmp_path_factory):
    """Build a pack once for all tests in this module."""
    base = tmp_path_factory.mktemp("packs")
    pack_path = build_pack("test_pack", base_path=base)
    return pack_path


class TestDirectoryStructure:

    def test_pack_dir_exists(self, built_pack):
        assert built_pack.exists()

    def test_manifest_exists(self, built_pack):
        assert (built_pack / "manifest.json").exists()

    def test_knowledge_db_exists(self, built_pack):
        assert (built_pack / "knowledge.db").exists()

    def test_chroma_db_exists(self, built_pack):
        assert (built_pack / "chroma_db").exists()

    def test_images_dirs_exist(self, built_pack):
        assert (built_pack / "images" / "diseases").exists()
        assert (built_pack / "images" / "healthy").exists()
        assert (built_pack / "images" / "treatments").exists()

    def test_readme_exists(self, built_pack):
        assert (built_pack / "README.md").exists()
        content = (built_pack / "README.md").read_text(encoding="utf-8")
        assert "Casamance" in content

    def test_sources_exists(self, built_pack):
        assert (built_pack / "SOURCES.md").exists()
        content = (built_pack / "SOURCES.md").read_text(encoding="utf-8")
        assert "FAO" in content


class TestSQLiteContent:

    def test_crops_count(self, built_pack):
        conn = sqlite3.connect(str(built_pack / "knowledge.db"))
        count = conn.execute("SELECT COUNT(*) FROM crops").fetchone()[0]
        conn.close()
        assert count == 5

    def test_diseases_count(self, built_pack):
        conn = sqlite3.connect(str(built_pack / "knowledge.db"))
        count = conn.execute("SELECT COUNT(*) FROM diseases").fetchone()[0]
        conn.close()
        assert count == 15

    def test_treatments_count(self, built_pack):
        conn = sqlite3.connect(str(built_pack / "knowledge.db"))
        count = conn.execute("SELECT COUNT(*) FROM treatments").fetchone()[0]
        conn.close()
        assert count >= 30

    def test_crop_diseases_count(self, built_pack):
        conn = sqlite3.connect(str(built_pack / "knowledge.db"))
        count = conn.execute("SELECT COUNT(*) FROM crop_diseases").fetchone()[0]
        conn.close()
        assert count == 15

    def test_climate_count(self, built_pack):
        conn = sqlite3.connect(str(built_pack / "knowledge.db"))
        count = conn.execute("SELECT COUNT(*) FROM climate").fetchone()[0]
        conn.close()
        assert count == 12

    def test_fts5_diseases_populated(self, built_pack):
        conn = sqlite3.connect(str(built_pack / "knowledge.db"))
        results = conn.execute(
            "SELECT * FROM diseases_fts WHERE diseases_fts MATCH 'mosaic'"
        ).fetchall()
        conn.close()
        assert len(results) >= 1

    def test_fts5_treatments_populated(self, built_pack):
        conn = sqlite3.connect(str(built_pack / "knowledge.db"))
        results = conn.execute(
            "SELECT * FROM treatments_fts WHERE treatments_fts MATCH 'neem'"
        ).fetchall()
        conn.close()
        assert len(results) >= 1

    def test_json_fields_queryable(self, built_pack):
        conn = sqlite3.connect(str(built_pack / "knowledge.db"))
        results = conn.execute(
            "SELECT t.method, j.value FROM treatments t, json_each(t.materials_needed) j "
            "WHERE j.value LIKE '%neem%'"
        ).fetchall()
        conn.close()
        assert len(results) >= 1


class TestChromaDBContent:

    def test_four_collections(self, built_pack):
        import chromadb
        client = chromadb.PersistentClient(path=str(built_pack / "chroma_db"))
        collections = client.list_collections()
        names = {c.name for c in collections}
        assert names == {"disease_knowledge", "treatment_guides", "farming_practices", "regional_context"}

    def test_disease_knowledge_has_docs(self, built_pack):
        import chromadb
        client = chromadb.PersistentClient(path=str(built_pack / "chroma_db"))
        col = client.get_collection("disease_knowledge")
        assert col.count() >= 50

    def test_treatment_guides_has_docs(self, built_pack):
        import chromadb
        client = chromadb.PersistentClient(path=str(built_pack / "chroma_db"))
        col = client.get_collection("treatment_guides")
        assert col.count() >= 60

    def test_can_query_disease_knowledge(self, built_pack):
        import chromadb
        from app.knowledge_pack.schema_chroma import get_embedding_function
        client = chromadb.PersistentClient(path=str(built_pack / "chroma_db"))
        col = client.get_collection("disease_knowledge", embedding_function=get_embedding_function())
        results = col.query(
            query_texts=["cassava yellow mosaic curling leaves"],
            n_results=3,
            where={"chunk_type": "child"},
        )
        assert len(results["ids"][0]) >= 1


class TestManifest:

    def test_manifest_valid(self, built_pack):
        manifest = validate_manifest(built_pack / "manifest.json")
        assert manifest.name == "Casamance Agriculture Pack"
        assert manifest.region.country == "Senegal"

    def test_manifest_statistics(self, built_pack):
        manifest = validate_manifest(built_pack / "manifest.json")
        assert manifest.statistics.diseases_count == 15
        assert manifest.statistics.treatments_count >= 30
        assert manifest.statistics.text_chunks >= 100

    def test_manifest_crops(self, built_pack):
        manifest = validate_manifest(built_pack / "manifest.json")
        assert set(manifest.crops) == {"cassava", "rice", "maize", "groundnut", "tomato"}
