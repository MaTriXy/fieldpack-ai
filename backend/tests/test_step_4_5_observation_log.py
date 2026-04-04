"""Tests for Step 4.5: Observation logging tool."""

from pathlib import Path

import pytest

from app.knowledge_pack.builder import build_pack
from app.knowledge_pack.loader import (
    get_active_pack,
    load_pack,
    unload_pack,
)
from app.tools.observation_log import (
    VALID_OBS_TYPES,
    get_observations,
    get_observations_tool,
    get_unsynced_observations,
    log_observation,
    log_observation_tool,
)


@pytest.fixture(scope="module")
def pack_path(tmp_path_factory):
    base = tmp_path_factory.mktemp("packs")
    return build_pack("obs_log_test_pack", base_path=base)


@pytest.fixture(autouse=True)
def active_pack(pack_path):
    load_pack(pack_path)
    yield get_active_pack()
    unload_pack()


# ============================================================
# log_observation
# ============================================================

class TestLogObservation:

    def test_basic_log(self):
        result = log_observation("disease_sighting", "Brown spots on cassava leaves")
        assert result["status"] == "saved"
        assert result["observation_id"] > 0
        assert "T" in result["timestamp"]  # ISO format

    def test_with_location(self):
        result = log_observation(
            "crop_condition", "Healthy rice growth",
            location="Field 3, near river",
        )
        assert result["status"] == "saved"

    def test_with_image_path(self):
        result = log_observation(
            "disease_sighting", "Yellow mosaic on cassava",
            image_path="/photos/cassava_001.jpg",
        )
        assert result["status"] == "saved"

    def test_all_valid_types(self):
        for obs_type in VALID_OBS_TYPES:
            result = log_observation(obs_type, f"Test observation for {obs_type}")
            assert result["status"] == "saved"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid observation type"):
            log_observation("invalid_type", "some details")

    def test_empty_details_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            log_observation("note", "")

    def test_whitespace_details_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            log_observation("note", "   ")

    def test_no_pack_raises(self, pack_path):
        unload_pack()
        with pytest.raises(RuntimeError, match="No active"):
            log_observation("note", "test")
        load_pack(pack_path)

    def test_long_details_no_limit(self):
        long_text = "A" * 10000
        result = log_observation("note", long_text)
        assert result["status"] == "saved"

        # Verify it was stored fully
        observations = get_observations("note", limit=1)
        found = [o for o in observations if o["details"] == long_text]
        assert len(found) == 1

    def test_unique_ids(self):
        r1 = log_observation("note", "First observation")
        r2 = log_observation("note", "Second observation")
        assert r1["observation_id"] != r2["observation_id"]


# ============================================================
# get_observations
# ============================================================

class TestGetObservations:

    def test_retrieve_logged_observation(self):
        log_observation("disease_sighting", "Test retrieval observation")
        observations = get_observations()
        assert len(observations) > 0
        details = [o["details"] for o in observations]
        assert "Test retrieval observation" in details

    def test_filter_by_type(self):
        log_observation("treatment_applied", "Applied neem oil spray")
        observations = get_observations(obs_type="treatment_applied")
        assert len(observations) > 0
        for obs in observations:
            assert obs["type"] == "treatment_applied"

    def test_limit_works(self):
        for i in range(5):
            log_observation("note", f"Limit test {i}")
        observations = get_observations(obs_type="note", limit=2)
        assert len(observations) <= 2

    def test_ordered_by_timestamp_desc(self):
        log_observation("note", "Older observation")
        log_observation("note", "Newer observation")
        observations = get_observations(obs_type="note")
        if len(observations) >= 2:
            assert observations[0]["timestamp"] >= observations[1]["timestamp"]

    def test_invalid_type_returns_empty(self):
        observations = get_observations(obs_type="invalid_type")
        assert observations == []

    def test_no_pack_returns_empty(self, pack_path):
        unload_pack()
        observations = get_observations()
        assert observations == []
        load_pack(pack_path)


# ============================================================
# get_unsynced_observations
# ============================================================

class TestGetUnsyncedObservations:

    def test_new_observations_are_unsynced(self):
        log_observation("note", "Unsynced test observation")
        unsynced = get_unsynced_observations()
        assert len(unsynced) > 0
        details = [o["details"] for o in unsynced]
        assert "Unsynced test observation" in details

    def test_all_have_synced_zero(self):
        log_observation("note", "Another unsynced")
        unsynced = get_unsynced_observations()
        for obs in unsynced:
            assert obs["synced"] == 0

    def test_no_pack_returns_empty(self, pack_path):
        unload_pack()
        unsynced = get_unsynced_observations()
        assert unsynced == []
        load_pack(pack_path)


# ============================================================
# @tool wrappers
# ============================================================

class TestToolWrappers:

    def test_log_tool_returns_string(self):
        result = log_observation_tool.invoke({
            "obs_type": "disease_sighting",
            "details": "Brown spots on cassava near field 2",
        })
        assert isinstance(result, str)
        assert "saved" in result.lower()
        assert "ID:" in result

    def test_log_tool_with_location(self):
        result = log_observation_tool.invoke({
            "obs_type": "crop_condition",
            "details": "Rice paddies looking healthy",
            "location": "Northern field",
        })
        assert "saved" in result.lower()

    def test_log_tool_invalid_type(self):
        result = log_observation_tool.invoke({
            "obs_type": "invalid",
            "details": "test",
        })
        assert "Error" in result

    def test_get_tool_returns_string(self):
        log_observation("note", "Tool retrieval test")
        result = get_observations_tool.invoke({})
        assert isinstance(result, str)
        assert "Tool retrieval test" in result

    def test_get_tool_filter_by_type(self):
        log_observation("treatment_applied", "Tool filter test")
        result = get_observations_tool.invoke({
            "obs_type": "treatment_applied",
        })
        assert isinstance(result, str)
        assert "treatment_applied" in result

    def test_tools_have_names(self):
        assert log_observation_tool.name == "log_observation_tool"
        assert get_observations_tool.name == "get_observations_tool"
        assert len(log_observation_tool.description) > 0
        assert len(get_observations_tool.description) > 0
