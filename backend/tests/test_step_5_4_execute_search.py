"""Tests for Step 5.4: EXECUTE SEARCHES node (parallel Python)."""

import asyncio
from pathlib import Path

import pytest

from app.agents.models import (
    ClassifyExtractOutput,
    CraftedQuery,
    IntentType,
    ResultType,
    SearchEngineType,
    SearchResult,
    SearchRoute,
)
from app.agents.nodes.execute_search import (
    _deduplicate_results,
    _get_fts_keywords,
    _normalize_bm25_scores,
    execute_searches,
    execute_searches_sync,
)
from app.knowledge_pack.builder import build_pack
from app.knowledge_pack.loader import get_active_pack, load_pack, unload_pack


@pytest.fixture(scope="module")
def pack_path(tmp_path_factory):
    base = tmp_path_factory.mktemp("packs")
    return build_pack("exec_search_test_pack", base_path=base)


@pytest.fixture(autouse=True)
def active_pack(pack_path):
    load_pack(pack_path)
    yield get_active_pack()
    unload_pack()


# ============================================================
# Unit: helpers
# ============================================================

class TestNormalizeBm25Scores:

    def test_normalizes_fts_scores(self):
        results = [
            SearchResult(content="a", score=10.0, result_type=ResultType.FTS),
            SearchResult(content="b", score=5.0, result_type=ResultType.FTS),
            SearchResult(content="c", score=2.5, result_type=ResultType.FTS),
        ]
        normalized = _normalize_bm25_scores(results)
        assert normalized[0].score == 1.0
        assert normalized[1].score == 0.5
        assert normalized[2].score == 0.25

    def test_leaves_chroma_scores_unchanged(self):
        results = [
            SearchResult(content="a", score=0.7, result_type=ResultType.CHROMA),
            SearchResult(content="b", score=5.0, result_type=ResultType.FTS),
        ]
        normalized = _normalize_bm25_scores(results)
        assert normalized[0].score == 0.7  # unchanged
        assert normalized[1].score == 1.0  # normalized

    def test_no_fts_results_unchanged(self):
        results = [
            SearchResult(content="a", score=0.8, result_type=ResultType.CHROMA),
        ]
        normalized = _normalize_bm25_scores(results)
        assert normalized[0].score == 0.8

    def test_empty_list(self):
        assert _normalize_bm25_scores([]) == []


class TestDeduplicateResults:

    def test_removes_exact_source_duplicates(self):
        results = [
            SearchResult(content="a", source="diseases:1", score=0.9),
            SearchResult(content="b", source="diseases:1", score=0.5),
            SearchResult(content="c", source="diseases:2", score=0.7),
        ]
        deduped = _deduplicate_results(results)
        assert len(deduped) == 2
        assert deduped[0].score == 0.9  # kept first (higher score)

    def test_no_duplicates(self):
        results = [
            SearchResult(content="a", source="src1", score=0.9),
            SearchResult(content="b", source="src2", score=0.7),
        ]
        deduped = _deduplicate_results(results)
        assert len(deduped) == 2


class TestGetFtsKeywords:

    def test_from_crafted_query(self):
        state = {
            "crafted_query": CraftedQuery(fts_keywords=["cassava", "mosaic"]),
            "classify_result": ClassifyExtractOutput(keywords=["other"]),
        }
        assert _get_fts_keywords(state) == ["cassava", "mosaic"]

    def test_fallback_to_classify(self):
        state = {
            "crafted_query": CraftedQuery(fts_keywords=[]),
            "classify_result": ClassifyExtractOutput(keywords=["cassava", "yellow"]),
        }
        assert _get_fts_keywords(state) == ["cassava", "yellow"]

    def test_fallback_to_user_message(self):
        state = {
            "crafted_query": None,
            "classify_result": None,
            "user_message": "My cassava has yellow leaves",
        }
        keywords = _get_fts_keywords(state)
        assert "cassava" in keywords


# ============================================================
# Integration: execute_searches
# ============================================================

class TestExecuteSearches:

    def _make_state(self, engines, collections=None, tables=None, query="cassava mosaic disease"):
        return {
            "user_message": "My cassava has yellow mosaic leaves",
            "classify_result": ClassifyExtractOutput(
                intent=IntentType.DIAGNOSE_DISEASE,
                crop="cassava",
                keywords=["cassava", "mosaic", "yellow"],
            ),
            "route": SearchRoute(
                engines=engines,
                collections=collections or ["disease_knowledge"],
                tables=tables or ["diseases"],
                metadata_filters={"crop": "cassava"},
            ),
            "crafted_query": CraftedQuery(
                embedding_query=query,
                fts_keywords=["cassava", "mosaic"],
            ),
            "tool_calls_log": [],
        }

    def test_chroma_search_returns_results(self):
        state = self._make_state(
            engines=[SearchEngineType.CHROMA_EMBEDDING],
        )
        result = execute_searches_sync(state)
        assert len(result["search_results"]) > 0
        assert all(isinstance(r, SearchResult) for r in result["search_results"])

    def test_fts_search_returns_results(self):
        state = self._make_state(
            engines=[SearchEngineType.SQLITE_FTS],
            tables=["diseases"],
        )
        result = execute_searches_sync(state)
        assert len(result["search_results"]) > 0

    def test_combined_engines(self):
        state = self._make_state(
            engines=[SearchEngineType.CHROMA_EMBEDDING, SearchEngineType.SQLITE_FTS],
        )
        result = execute_searches_sync(state)
        results = result["search_results"]
        assert len(results) > 0
        # Should have results from both engines
        types = {r.result_type for r in results}
        # At minimum chroma should return results
        assert ResultType.CHROMA in types

    def test_results_sorted_by_score(self):
        state = self._make_state(
            engines=[SearchEngineType.CHROMA_EMBEDDING, SearchEngineType.SQLITE_FTS],
        )
        result = execute_searches_sync(state)
        results = result["search_results"]
        if len(results) >= 2:
            for i in range(len(results) - 1):
                assert results[i].score >= results[i + 1].score

    def test_tool_calls_log_populated(self):
        state = self._make_state(
            engines=[SearchEngineType.CHROMA_EMBEDDING],
        )
        result = execute_searches_sync(state)
        assert len(result["tool_calls_log"]) > 0
        log_entry = result["tool_calls_log"][-1]
        assert log_entry["step"] == "search"
        assert "total_results" in log_entry

    def test_no_route_returns_empty(self):
        state = {"route": None, "tool_calls_log": []}
        result = execute_searches_sync(state)
        assert result["search_results"] == []

    def test_empty_engines_returns_empty(self):
        state = {
            "route": SearchRoute(engines=[]),
            "tool_calls_log": [],
        }
        result = execute_searches_sync(state)
        assert result["search_results"] == []

    def test_structured_search(self):
        state = self._make_state(
            engines=[SearchEngineType.SQLITE_STRUCTURED],
            tables=["crops"],
        )
        result = execute_searches_sync(state)
        assert len(result["search_results"]) > 0

    def test_scores_normalized(self):
        state = self._make_state(
            engines=[SearchEngineType.CHROMA_EMBEDDING, SearchEngineType.SQLITE_FTS],
        )
        result = execute_searches_sync(state)
        for r in result["search_results"]:
            assert 0.0 <= r.score <= 1.0 or r.result_type == ResultType.STRUCTURED

    def test_deduplication(self):
        state = self._make_state(
            engines=[SearchEngineType.CHROMA_EMBEDDING],
            collections=["disease_knowledge", "disease_knowledge"],
        )
        result = execute_searches_sync(state)
        sources = [r.source for r in result["search_results"]]
        assert len(sources) == len(set(sources))
