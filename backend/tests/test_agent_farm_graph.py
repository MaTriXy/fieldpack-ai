"""Tests for the Agent Farm LangGraph wiring and entry points.

Covers:
  - build_agent_farm_graph(): node count, topology
  - generate_chunks node: with/without compilation
  - download_images node: empty URLs, mocked downloads
  - run_agent_farm(): end-to-end with all phases mocked
  - run_agent_farm_stream(): yields correct event types
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.agent_farm.graph as graph_module
from app.agent_farm.graph import (
    build_agent_farm_graph,
    download_images,
    generate_chunks,
)
from app.agent_farm.models import (
    CompilationOutput,
    CropDiseaseRecord,
    CropRecord,
    DiseaseRecord,
    TreatmentRecord,
)


# ============================================================
# Reset graph singleton between tests
# ============================================================


@pytest.fixture(autouse=True)
def _reset_graph():
    graph_module._graph = None
    yield
    graph_module._graph = None


# ============================================================
# generate_chunks node
# ============================================================


class TestGenerateChunks:
    async def test_with_compilation(self):
        comp = CompilationOutput(
            crops=[CropRecord(id=1, name="Cassava")],
            diseases=[DiseaseRecord(
                id=1, name="CMD", type="viral",
                symptoms_text="Mosaic", visual_markers="Yellow",
            )],
            crop_diseases=[CropDiseaseRecord(crop_id=1, disease_id=1)],
        )
        state = {"compilation": comp, "status_messages": []}

        result = await generate_chunks(state)

        assert "chunks" in result
        assert isinstance(result["chunks"], dict)
        assert result["current_phase"] == "chunks"
        # 1 disease with no prevention → 2 symptom chunks (child+parent)
        assert "disease_knowledge" in result["chunks"]
        assert len(result["chunks"]["disease_knowledge"]) == 2

    async def test_without_compilation(self):
        state = {"compilation": None, "status_messages": []}

        result = await generate_chunks(state)

        assert result["chunks"] == {}
        assert result["current_phase"] == "chunks"

    async def test_missing_compilation_key(self):
        state = {"status_messages": []}

        result = await generate_chunks(state)

        assert result["chunks"] == {}


# ============================================================
# download_images node
# ============================================================


class TestDownloadImages:
    async def test_empty_urls(self):
        state = {"image_urls": [], "json_output_dir": "", "status_messages": []}

        result = await download_images(state)

        assert result["downloaded_images"] == []
        assert result["current_phase"] == "images"

    async def test_missing_urls_key(self):
        state = {"status_messages": []}

        result = await download_images(state)

        assert result["downloaded_images"] == []

    async def test_successful_download(self, tmp_path):
        state = {
            "image_urls": [
                {"url": "https://example.com/img.jpg", "category": "diseases", "entity": "CMD"},
            ],
            "json_output_dir": str(tmp_path),
            "status_messages": [],
        }

        mock_path = tmp_path / "images" / "diseases" / "cmd" / "img.jpg"
        mock_path.parent.mkdir(parents=True, exist_ok=True)
        mock_path.write_bytes(b"fake image")

        with patch("app.agent_farm.graph.download_image",
                    new_callable=AsyncMock, return_value=mock_path):
            result = await download_images(state)

        assert len(result["downloaded_images"]) == 1
        assert result["downloaded_images"][0]["category"] == "diseases"
        assert result["downloaded_images"][0]["local_path"] == str(mock_path)

    async def test_failed_download(self, tmp_path):
        state = {
            "image_urls": [
                {"url": "https://example.com/fail.jpg", "category": "diseases", "entity": "CMD"},
            ],
            "json_output_dir": str(tmp_path),
            "status_messages": [],
        }

        with patch("app.agent_farm.graph.download_image",
                    new_callable=AsyncMock, return_value=None):
            result = await download_images(state)

        assert result["downloaded_images"] == []

    async def test_download_exception_counted_as_failure(self, tmp_path):
        state = {
            "image_urls": [
                {"url": "https://example.com/err.jpg", "category": "diseases", "entity": "CMD"},
            ],
            "json_output_dir": str(tmp_path),
            "status_messages": [],
        }

        with patch("app.agent_farm.graph.download_image",
                    new_callable=AsyncMock, side_effect=Exception("network error")):
            result = await download_images(state)

        assert result["downloaded_images"] == []
        assert any("failed" in m for m in result["status_messages"])


# ============================================================
# build_agent_farm_graph()
# ============================================================


class TestBuildGraph:
    def test_builds_successfully(self):
        graph = build_agent_farm_graph()
        assert graph is not None

    def test_has_six_nodes(self):
        graph = build_agent_farm_graph()
        # LangGraph compiled graphs expose nodes via get_graph()
        g = graph.get_graph()
        # Filter out __start__ and __end__ virtual nodes
        real_nodes = [n for n in g.nodes if n not in ("__start__", "__end__")]
        assert len(real_nodes) == 6

    def test_node_names(self):
        graph = build_agent_farm_graph()
        g = graph.get_graph()
        node_names = {n for n in g.nodes if n not in ("__start__", "__end__")}
        expected = {
            "source_gathering", "knowledge_extraction", "gap_analysis",
            "compilation", "generate_chunks", "download_images",
        }
        assert node_names == expected


# ============================================================
# run_agent_farm() with all phases mocked
# ============================================================


class TestRunAgentFarm:
    async def test_end_to_end(self):
        from app.agent_farm.graph import run_agent_farm

        async def mock_source_gathering(state):
            return {"sections": [], "climate_records": [],
                    "status_messages": ["gathered"], "current_phase": "gathering"}

        async def mock_extraction(state):
            return {"findings": [], "status_messages": state.get("status_messages", []) + ["extracted"],
                    "current_phase": "extracting"}

        async def mock_gap(state):
            return {"findings": [], "identified_gaps": [], "gap_search_queries": [],
                    "image_urls": [],
                    "status_messages": state.get("status_messages", []) + ["gaps"],
                    "current_phase": "gap_analysis"}

        async def mock_compilation(state):
            return {"compilation": CompilationOutput(),
                    "json_output_dir": "/tmp/test",
                    "status_messages": state.get("status_messages", []) + ["compiled"],
                    "current_phase": "compiling"}

        with patch("app.agent_farm.graph.source_gathering", side_effect=mock_source_gathering), \
             patch("app.agent_farm.graph.knowledge_extraction", side_effect=mock_extraction), \
             patch("app.agent_farm.graph.gap_analysis", side_effect=mock_gap), \
             patch("app.agent_farm.graph.compilation", side_effect=mock_compilation), \
             patch("app.agent_farm.graph.download_image",
                    new_callable=AsyncMock, return_value=None):

            result = await run_agent_farm(crops=["cassava"], region="Casamance")

        assert "status_messages" in result
        assert result["current_phase"] == "images"

    async def test_raises_on_failure(self):
        from app.agent_farm.graph import run_agent_farm

        with patch("app.agent_farm.graph.source_gathering",
                    side_effect=RuntimeError("Pipeline exploded")):
            with pytest.raises(RuntimeError, match="Pipeline exploded"):
                await run_agent_farm(crops=["cassava"])


# ============================================================
# run_agent_farm_stream()
# ============================================================


class TestRunAgentFarmStream:
    async def test_yields_events(self):
        from app.agent_farm.graph import run_agent_farm_stream

        async def mock_source_gathering(state):
            return {"sections": [], "climate_records": [],
                    "status_messages": ["gathered"], "current_phase": "gathering"}

        async def mock_extraction(state):
            return {"findings": [],
                    "status_messages": state.get("status_messages", []) + ["extracted"],
                    "current_phase": "extracting"}

        async def mock_gap(state):
            return {"findings": [], "identified_gaps": [], "gap_search_queries": [],
                    "image_urls": [],
                    "status_messages": state.get("status_messages", []) + ["gaps"],
                    "current_phase": "gap_analysis"}

        async def mock_compilation(state):
            return {"compilation": CompilationOutput(),
                    "json_output_dir": "/tmp/test",
                    "status_messages": state.get("status_messages", []) + ["compiled"],
                    "current_phase": "compiling"}

        with patch("app.agent_farm.graph.source_gathering", side_effect=mock_source_gathering), \
             patch("app.agent_farm.graph.knowledge_extraction", side_effect=mock_extraction), \
             patch("app.agent_farm.graph.gap_analysis", side_effect=mock_gap), \
             patch("app.agent_farm.graph.compilation", side_effect=mock_compilation), \
             patch("app.agent_farm.graph.download_image",
                    new_callable=AsyncMock, return_value=None):

            events = []
            async for event in run_agent_farm_stream(crops=["cassava"]):
                events.append(event)

        event_types = [e["type"] for e in events]
        assert "done" in event_types
        # "done" should be the last event
        assert event_types[-1] == "done"
        # "done" event must have summary with required keys
        done_event = [e for e in events if e["type"] == "done"][0]
        assert "summary" in done_event
        for key in ("total_latency_ms", "tables", "chunks", "images", "json_output_dir"):
            assert key in done_event["summary"], f"missing key '{key}' in done summary"

    async def test_error_event_on_failure(self):
        from app.agent_farm.graph import run_agent_farm_stream

        with patch("app.agent_farm.graph.source_gathering",
                    side_effect=RuntimeError("Boom")):
            events = []
            async for event in run_agent_farm_stream(crops=["cassava"]):
                events.append(event)

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) >= 1
        assert "Boom" in error_events[0]["message"]
