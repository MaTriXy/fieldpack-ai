"""Tests for the observations REST router."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.knowledge_pack.builder import build_pack
from app.knowledge_pack.loader import get_active_pack, load_pack, unload_pack
from app.main import app
from app.tools.observation_log import log_observation


client = TestClient(app)


@pytest.fixture(scope="module")
def pack_path(tmp_path_factory):
    base = tmp_path_factory.mktemp("packs")
    return build_pack("obs_router_test_pack", base_path=base)


@pytest.fixture(autouse=True)
def active_pack(pack_path):
    load_pack(pack_path)
    yield get_active_pack()
    unload_pack()


# ── GET /observations/ ───────────────────────────────────────

class TestListObservations:

    def test_empty_list(self):
        # Fresh pack — may have observations from other tests in module,
        # but endpoint should return without error
        res = client.get("/observations/")
        assert res.status_code == 200
        data = res.json()
        assert "observations" in data
        assert "total" in data
        assert "unsynced_count" in data

    def test_list_with_data(self):
        log_observation("note", "Router list test")
        res = client.get("/observations/")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        details = [o["details"] for o in data["observations"]]
        assert "Router list test" in details

    def test_filter_by_type(self):
        log_observation("treatment_applied", "Neem spray test")
        res = client.get("/observations/?type=treatment_applied")
        assert res.status_code == 200
        data = res.json()
        for obs in data["observations"]:
            assert obs["type"] == "treatment_applied"

    def test_limit_param(self):
        for i in range(3):
            log_observation("note", f"Limit test {i}")
        res = client.get("/observations/?limit=2")
        assert res.status_code == 200
        assert len(res.json()["observations"]) <= 2


# ── GET /observations/stats ──────────────────────────────────

class TestObservationStats:

    def test_stats_response(self):
        log_observation("disease_sighting", "Stats test disease")
        res = client.get("/observations/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert "unsynced" in data
        assert "by_type" in data
        assert "recent" in data

    def test_stats_by_type_populated(self):
        log_observation("crop_condition", "Stats condition test")
        res = client.get("/observations/stats")
        data = res.json()
        assert "crop_condition" in data["by_type"]


# ── POST /observations/ ─────────────────────────────────────

class TestCreateObservation:

    def test_create_success(self):
        res = client.post("/observations/", json={
            "type": "note",
            "details": "Created via REST API",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "saved"
        assert data["observation_id"] > 0
        assert "timestamp" in data

    def test_create_with_location(self):
        res = client.post("/observations/", json={
            "type": "disease_sighting",
            "details": "Brown spots near river",
            "location": "Field 3",
        })
        assert res.status_code == 200

    def test_create_invalid_type(self):
        res = client.post("/observations/", json={
            "type": "invalid_type",
            "details": "Should fail",
        })
        assert res.status_code == 400

    def test_create_empty_details(self):
        res = client.post("/observations/", json={
            "type": "note",
            "details": "",
        })
        assert res.status_code == 400


# ── GET /observations/{id} ───────────────────────────────────

class TestGetObservation:

    def test_get_by_id(self):
        result = log_observation("note", "Get by ID test")
        obs_id = result["observation_id"]
        res = client.get(f"/observations/{obs_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == obs_id
        assert data["details"] == "Get by ID test"

    def test_get_not_found(self):
        res = client.get("/observations/999999")
        assert res.status_code == 404


# ── New utility functions ────────────────────────────────────

class TestNewUtilityFunctions:

    def test_count_observations(self):
        from app.tools.observation_log import count_observations
        initial = count_observations()
        log_observation("note", "Count test")
        assert count_observations() == initial + 1

    def test_count_by_type(self):
        from app.tools.observation_log import count_observations
        log_observation("crop_condition", "Count type test")
        count = count_observations(obs_type="crop_condition")
        assert count >= 1

    def test_get_observation_stats(self):
        from app.tools.observation_log import get_observation_stats
        log_observation("disease_sighting", "Stats func test")
        stats = get_observation_stats()
        assert stats["total_observations"] >= 1
        assert "unsynced" in stats
        assert "disease_sighting" in stats["by_type"]

    def test_get_observation_by_id(self):
        from app.tools.observation_log import get_observation_by_id
        result = log_observation("note", "By ID func test")
        obs = get_observation_by_id(result["observation_id"])
        assert obs is not None
        assert obs["details"] == "By ID func test"

    def test_get_observation_by_id_not_found(self):
        from app.tools.observation_log import get_observation_by_id
        assert get_observation_by_id(999999) is None
