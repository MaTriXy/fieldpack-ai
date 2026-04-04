"""Tests for Step 3.4: Knowledge Pack loader."""

from pathlib import Path

import pytest

from app.knowledge_pack.builder import build_pack
from app.knowledge_pack.loader import (
    KnowledgePack,
    get_active_pack,
    load_pack,
    unload_pack,
)


@pytest.fixture(scope="module")
def pack_path(tmp_path_factory):
    """Build a pack once for all loader tests."""
    base = tmp_path_factory.mktemp("packs")
    return build_pack("loader_test_pack", base_path=base)


@pytest.fixture
def pack(pack_path):
    """Fresh KnowledgePack instance per test."""
    kp = KnowledgePack(pack_path)
    yield kp
    kp.close()


# --- KnowledgePack class ---

class TestKnowledgePack:

    def test_manifest_loads(self, pack):
        assert pack.manifest.name == "Casamance Agriculture Pack"
        assert pack.manifest.region.country == "Senegal"

    def test_sqlite_conn_works(self, pack):
        result = pack.sqlite_conn.execute("SELECT COUNT(*) FROM crops").fetchone()
        assert result[0] == 5

    def test_sqlite_row_factory(self, pack):
        row = pack.sqlite_conn.execute("SELECT * FROM crops WHERE name='cassava'").fetchone()
        assert row["name"] == "cassava"
        assert row["scientific_name"] == "Manihot esculenta"

    def test_chroma_client_works(self, pack):
        collections = pack.chroma_client.list_collections()
        assert len(collections) == 4

    def test_get_collection(self, pack):
        col = pack.get_collection("disease_knowledge")
        assert col.count() > 0

    def test_get_invalid_collection_raises(self, pack):
        with pytest.raises(ValueError, match="Unknown collection"):
            pack.get_collection("nonexistent")

    def test_health_check(self, pack):
        health = pack.health_check()
        assert health["pack_name"] == "Casamance Agriculture Pack"
        assert health["sqlite_tables"]["crops"] == 5
        assert health["sqlite_tables"]["diseases"] == 15
        assert health["chroma_collections"]["disease_knowledge"] > 0

    def test_context_manager(self, pack_path):
        with KnowledgePack(pack_path) as kp:
            assert kp.manifest.name == "Casamance Agriculture Pack"
            count = kp.sqlite_conn.execute("SELECT COUNT(*) FROM diseases").fetchone()[0]
            assert count == 15

    def test_close(self, pack_path):
        kp = KnowledgePack(pack_path)
        _ = kp.sqlite_conn  # Open connection
        kp.close()
        assert kp._sqlite_conn is None
        assert kp._chroma_client is None

    def test_path_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            KnowledgePack(tmp_path / "nonexistent")

    def test_missing_manifest(self, tmp_path):
        (tmp_path / "fake_pack").mkdir()
        with pytest.raises(FileNotFoundError, match="manifest"):
            KnowledgePack(tmp_path / "fake_pack")


# --- Module-level singleton ---

class TestSingleton:

    def test_load_and_get(self, pack_path):
        try:
            pack = load_pack(pack_path)
            assert get_active_pack() is pack
            assert pack.manifest.name == "Casamance Agriculture Pack"
        finally:
            unload_pack()

    def test_unload(self, pack_path):
        load_pack(pack_path)
        unload_pack()
        assert get_active_pack() is None

    def test_reload_replaces(self, pack_path):
        try:
            pack1 = load_pack(pack_path)
            pack2 = load_pack(pack_path)
            assert get_active_pack() is pack2
            assert pack1 is not pack2
        finally:
            unload_pack()

    def test_get_when_none(self):
        unload_pack()
        assert get_active_pack() is None
