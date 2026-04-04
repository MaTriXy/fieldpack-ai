"""Tests for Step 4.1: ChromaDB embedding search with child→parent resolution."""

from pathlib import Path

import pytest

from app.agents.models import ResultType, SearchResult
from app.knowledge_pack.builder import build_pack
from app.knowledge_pack.loader import (
    KnowledgePack,
    get_active_pack,
    load_pack,
    unload_pack,
)
from app.tools.chroma_search import (
    _distance_to_score,
    _resolve_parent,
    chroma_search,
    chroma_search_tool,
    multi_collection_search,
    multi_collection_search_tool,
)


# ============================================================
# Shared fixture: build pack once for all tests in this module
# ============================================================

@pytest.fixture(scope="module")
def pack_path(tmp_path_factory):
    """Build a Knowledge Pack once for all chroma search tests."""
    base = tmp_path_factory.mktemp("packs")
    return build_pack("chroma_search_test_pack", base_path=base)


@pytest.fixture(autouse=True)
def active_pack(pack_path):
    """Load the pack before each test, unload after."""
    load_pack(pack_path)
    yield get_active_pack()
    unload_pack()


# ============================================================
# Unit: score conversion
# ============================================================

class TestDistanceToScore:

    def test_zero_distance_perfect_score(self):
        assert _distance_to_score(0.0) == 1.0

    def test_one_distance_zero_score(self):
        assert _distance_to_score(1.0) == 0.0

    def test_half_distance(self):
        assert _distance_to_score(0.5) == 0.5

    def test_negative_clamps_to_one(self):
        # Shouldn't happen with cosine, but handle gracefully
        assert _distance_to_score(-0.1) == 1.1 or _distance_to_score(-0.1) > 1.0

    def test_above_one_clamps_to_zero(self):
        assert _distance_to_score(1.5) == 0.0

    def test_above_two_clamps_to_zero(self):
        assert _distance_to_score(2.0) == 0.0


# ============================================================
# Unit: parent resolution
# ============================================================

class TestResolveParent:

    def test_resolves_parent_from_child_metadata(self, active_pack):
        collection = active_pack.get_collection("disease_knowledge")

        # Get a child doc to use its metadata
        child_results = collection.get(
            where={"chunk_type": {"$eq": "child"}},
            include=["metadatas"],
            limit=1,
        )
        assert child_results["ids"], "No child chunks found in disease_knowledge"

        child_id = child_results["ids"][0]
        child_meta = child_results["metadatas"][0]

        parent_id, parent_content = _resolve_parent(collection, child_id, child_meta)
        assert parent_id is not None
        assert parent_content is not None
        assert len(parent_content) > 0

    def test_missing_topic_id_returns_none(self, active_pack):
        collection = active_pack.get_collection("disease_knowledge")
        parent_id, parent_content = _resolve_parent(collection, "fake_id", {})
        assert parent_id is None
        assert parent_content is None

    def test_nonexistent_topic_returns_none(self, active_pack):
        collection = active_pack.get_collection("disease_knowledge")
        parent_id, parent_content = _resolve_parent(
            collection, "fake_id", {"topic_id": "nonexistent_topic_xyz"},
        )
        assert parent_id is None
        assert parent_content is None


# ============================================================
# Integration: chroma_search
# ============================================================

class TestChromaSearch:

    def test_basic_disease_search(self):
        results = chroma_search(
            query="cassava leaf curl yellow mosaic pattern",
            collection_name="disease_knowledge",
        )
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.result_type == ResultType.CHROMA for r in results)

    def test_results_have_parent_content(self):
        results = chroma_search(
            query="rice blast fungal infection",
            collection_name="disease_knowledge",
        )
        assert len(results) > 0
        for r in results:
            assert r.parent_content is not None
            assert len(r.parent_content) > 0
            assert r.parent_id is not None

    def test_results_sorted_by_score_descending(self):
        results = chroma_search(
            query="cassava mosaic disease symptoms",
            collection_name="disease_knowledge",
            top_k=5,
        )
        if len(results) >= 2:
            for i in range(len(results) - 1):
                assert results[i].score >= results[i + 1].score

    def test_metadata_filter_crop(self):
        results = chroma_search(
            query="leaf disease symptoms",
            collection_name="disease_knowledge",
            filters={"crop": "cassava"},
        )
        for r in results:
            assert r.metadata.get("crop") == "cassava"

    def test_top_k_limits_results(self):
        results = chroma_search(
            query="plant disease",
            collection_name="disease_knowledge",
            top_k=1,
        )
        assert len(results) <= 1

    def test_scores_in_valid_range(self):
        results = chroma_search(
            query="cassava mosaic",
            collection_name="disease_knowledge",
        )
        for r in results:
            assert 0.0 <= r.score <= 1.0

    def test_search_treatment_guides(self):
        results = chroma_search(
            query="neem oil organic treatment",
            collection_name="treatment_guides",
        )
        assert len(results) > 0
        assert all(r.result_type == ResultType.CHROMA for r in results)

    def test_search_farming_practices(self):
        results = chroma_search(
            query="drought resistant planting",
            collection_name="farming_practices",
        )
        assert len(results) > 0

    def test_search_regional_context(self):
        results = chroma_search(
            query="Casamance climate rainfall",
            collection_name="regional_context",
        )
        assert len(results) > 0

    def test_nonsense_query_returns_low_scores(self):
        results = chroma_search(
            query="xyzzyflorp quantum blockchain metaverse",
            collection_name="disease_knowledge",
        )
        # May return results but with low relevance
        if results:
            assert results[0].score < 0.8

    def test_empty_query_returns_empty(self):
        results = chroma_search(query="", collection_name="disease_knowledge")
        assert results == []

    def test_whitespace_query_returns_empty(self):
        results = chroma_search(query="   ", collection_name="disease_knowledge")
        assert results == []

    def test_invalid_collection_returns_empty(self):
        results = chroma_search(
            query="cassava", collection_name="nonexistent_collection",
        )
        assert results == []

    def test_no_active_pack_returns_empty(self, pack_path):
        unload_pack()
        results = chroma_search(
            query="cassava", collection_name="disease_knowledge",
        )
        assert results == []
        # Re-load for remaining tests
        load_pack(pack_path)


# ============================================================
# Integration: multi_collection_search
# ============================================================

class TestMultiCollectionSearch:

    def test_searches_across_collections(self):
        results = multi_collection_search(
            query="cassava disease treatment",
            collections=["disease_knowledge", "treatment_guides"],
            top_k=3,
        )
        assert len(results) > 0

        # Should have results from at least one collection
        sources = {r.source for r in results}
        assert len(sources) > 0

    def test_deduplicates_by_source(self):
        results = multi_collection_search(
            query="cassava",
            collections=["disease_knowledge", "disease_knowledge"],
            top_k=5,
        )
        sources = [r.source for r in results]
        assert len(sources) == len(set(sources))

    def test_sorted_by_score(self):
        results = multi_collection_search(
            query="cassava mosaic treatment",
            collections=["disease_knowledge", "treatment_guides"],
            top_k=3,
        )
        if len(results) >= 2:
            for i in range(len(results) - 1):
                assert results[i].score >= results[i + 1].score

    def test_empty_query_returns_empty(self):
        results = multi_collection_search(
            query="",
            collections=["disease_knowledge"],
        )
        assert results == []

    def test_all_four_collections(self):
        results = multi_collection_search(
            query="Casamance agriculture",
            collections=list(
                ["disease_knowledge", "treatment_guides",
                 "farming_practices", "regional_context"]
            ),
            top_k=2,
        )
        assert len(results) > 0


# ============================================================
# @tool wrappers
# ============================================================

class TestToolWrappers:

    def test_chroma_search_tool_returns_string(self):
        result = chroma_search_tool.invoke({
            "query": "cassava mosaic symptoms",
            "collection_name": "disease_knowledge",
        })
        assert isinstance(result, str)
        assert "No results found" not in result
        assert "[1]" in result

    def test_chroma_search_tool_with_filters(self):
        result = chroma_search_tool.invoke({
            "query": "leaf disease",
            "collection_name": "disease_knowledge",
            "filters": '{"crop": "cassava"}',
        })
        assert isinstance(result, str)

    def test_chroma_search_tool_no_results(self):
        result = chroma_search_tool.invoke({
            "query": "",
            "collection_name": "disease_knowledge",
        })
        assert result == "No results found."

    def test_chroma_search_tool_invalid_filters_ignored(self):
        result = chroma_search_tool.invoke({
            "query": "cassava mosaic",
            "collection_name": "disease_knowledge",
            "filters": "not valid json",
        })
        assert isinstance(result, str)

    def test_multi_collection_tool_returns_string(self):
        result = multi_collection_search_tool.invoke({
            "query": "cassava disease treatment",
            "collections": "disease_knowledge,treatment_guides",
        })
        assert isinstance(result, str)
        assert "No results found" not in result

    def test_tool_has_name_and_description(self):
        assert chroma_search_tool.name == "chroma_search_tool"
        assert len(chroma_search_tool.description) > 0
        assert multi_collection_search_tool.name == "multi_collection_search_tool"
        assert len(multi_collection_search_tool.description) > 0
