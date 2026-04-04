"""Tests for Step 5.5: RE-RANK node (LLM call #3)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.models import ResultType, ScoredResult, SearchResult
from app.agents.nodes.rerank import (
    KEEP_THRESHOLD,
    MAX_RESULTS_FOR_RERANK,
    SUFFICIENT_MIN_COUNT,
    SUFFICIENT_THRESHOLD,
    _parse_rerank_response,
    _truncate_for_context,
    rerank_results,
)


def _make_search_results(count=5, base_score=0.7):
    return [
        SearchResult(
            content=f"Child content {i}",
            source=f"src_{i}",
            score=max(0.0, base_score - (i * 0.05)),
            result_type=ResultType.CHROMA,
            parent_id=f"parent_{i}",
            parent_content=f"Full parent content for result {i} with detailed info about cassava diseases.",
        )
        for i in range(count)
    ]


# ============================================================
# Unit: _truncate_for_context
# ============================================================

class TestTruncateForContext:

    def test_short_content_unchanged(self):
        results = _make_search_results(1)
        truncated = _truncate_for_context(results)
        assert len(truncated) == 1
        assert truncated[0]["index"] == 1

    def test_long_content_truncated(self):
        results = [SearchResult(
            content="word " * 500,
            parent_content="word " * 500,
            source="src",
            score=0.8,
        )]
        truncated = _truncate_for_context(results, max_words=200)
        word_count = len(truncated[0]["content"].split())
        assert word_count <= 201  # 200 + "..."

    def test_uses_parent_content(self):
        results = [SearchResult(
            content="child",
            parent_content="parent content here",
            source="src",
            score=0.8,
        )]
        truncated = _truncate_for_context(results)
        assert "parent content" in truncated[0]["content"]

    def test_fallback_to_content(self):
        results = [SearchResult(
            content="child content only",
            source="src",
            score=0.8,
        )]
        truncated = _truncate_for_context(results)
        assert "child content" in truncated[0]["content"]


# ============================================================
# Unit: _parse_rerank_response
# ============================================================

class TestParseRerankResponse:

    def test_valid_json_array(self):
        results = _make_search_results(3)
        response = json.dumps([
            {"index": 1, "score": 0.9, "keep": True},
            {"index": 2, "score": 0.6, "keep": True},
            {"index": 3, "score": 0.2, "keep": False},
        ])
        scored, is_sufficient = _parse_rerank_response(response, results)
        assert len(scored) == 2  # index 3 filtered (score < 0.4)
        assert scored[0].relevance_score == 0.9
        assert is_sufficient is True  # 2 results >= 0.5

    def test_filters_below_threshold(self):
        results = _make_search_results(3)
        response = json.dumps([
            {"index": 1, "score": 0.3, "keep": False},
            {"index": 2, "score": 0.2, "keep": False},
            {"index": 3, "score": 0.1, "keep": False},
        ])
        scored, is_sufficient = _parse_rerank_response(response, results)
        assert len(scored) == 0
        assert is_sufficient is False

    def test_insufficient_when_too_few_high_scores(self):
        results = _make_search_results(3)
        response = json.dumps([
            {"index": 1, "score": 0.8, "keep": True},
            {"index": 2, "score": 0.3, "keep": False},
            {"index": 3, "score": 0.2, "keep": False},
        ])
        scored, is_sufficient = _parse_rerank_response(response, results)
        assert len(scored) == 1
        assert is_sufficient is False  # only 1 result >= 0.5

    def test_sorted_by_score_descending(self):
        results = _make_search_results(3)
        response = json.dumps([
            {"index": 1, "score": 0.5, "keep": True},
            {"index": 2, "score": 0.9, "keep": True},
            {"index": 3, "score": 0.7, "keep": True},
        ])
        scored, _ = _parse_rerank_response(response, results)
        for i in range(len(scored) - 1):
            assert scored[i].relevance_score >= scored[i + 1].relevance_score

    def test_malformed_json_fallback(self):
        results = _make_search_results(3)
        response = "I think results 1 and 2 are relevant"
        scored, is_sufficient = _parse_rerank_response(response, results)
        # Fallback keeps all with original scores
        assert len(scored) == 3

    def test_empty_response_fallback(self):
        results = _make_search_results(2)
        scored, _ = _parse_rerank_response("", results)
        assert len(scored) == 2

    def test_json_array_in_text(self):
        results = _make_search_results(2)
        response = 'Here are scores: [{"index": 1, "score": 0.8, "keep": true}] done.'
        scored, _ = _parse_rerank_response(response, results)
        assert len(scored) >= 1

    def test_uses_parent_content_in_scored(self):
        results = _make_search_results(1)
        response = json.dumps([{"index": 1, "score": 0.9, "keep": True}])
        scored, _ = _parse_rerank_response(response, results)
        assert scored[0].parent_content is not None
        assert "parent content" in scored[0].parent_content.lower()

    def test_scores_clamped(self):
        results = _make_search_results(1)
        response = json.dumps([{"index": 1, "score": 1.5, "keep": True}])
        scored, _ = _parse_rerank_response(response, results)
        assert scored[0].relevance_score <= 1.0


# ============================================================
# Integration: rerank_results (mocked LLM)
# ============================================================

class TestRerankResults:

    def _make_state(self, result_count=5, attempts=0):
        return {
            "user_message": "My cassava has yellow mosaic leaves",
            "search_results": _make_search_results(result_count),
            "retrieval_attempts": attempts,
        }

    def test_basic_rerank(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {"index": 1, "score": 0.9, "keep": True},
            {"index": 2, "score": 0.7, "keep": True},
            {"index": 3, "score": 0.5, "keep": True},
            {"index": 4, "score": 0.3, "keep": False},
            {"index": 5, "score": 0.1, "keep": False},
        ])

        with patch("app.agents.nodes.rerank.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = rerank_results(self._make_state())

        assert "ranked_results" in result
        assert len(result["ranked_results"]) == 3  # 3 kept
        assert result["is_sufficient"] is True  # 3 >= 0.5
        assert result["retrieval_attempts"] == 1

    def test_empty_results(self):
        state = {
            "user_message": "test",
            "search_results": [],
            "retrieval_attempts": 0,
        }
        result = rerank_results(state)
        assert result["ranked_results"] == []
        assert result["is_sufficient"] is False
        assert result["retrieval_attempts"] == 1

    def test_attempts_increment(self):
        state = self._make_state(attempts=2)
        mock_response = MagicMock()
        mock_response.content = "[]"

        with patch("app.agents.nodes.rerank.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = rerank_results(state)

        assert result["retrieval_attempts"] == 3

    def test_llm_error_fallback(self):
        with patch("app.agents.nodes.rerank.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = Exception("Ollama down")
            result = rerank_results(self._make_state())

        # Keeps all with original scores
        assert len(result["ranked_results"]) == 5
        assert result["retrieval_attempts"] == 1

    def test_caps_at_max_results(self):
        state = self._make_state(result_count=15)
        mock_response = MagicMock()
        # Only 8 items scored (capped)
        mock_response.content = json.dumps([
            {"index": i + 1, "score": 0.8, "keep": True}
            for i in range(MAX_RESULTS_FOR_RERANK)
        ])

        with patch("app.agents.nodes.rerank.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = rerank_results(state)

        assert len(result["ranked_results"]) <= MAX_RESULTS_FOR_RERANK

    def test_ranked_results_are_scored_result(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {"index": 1, "score": 0.9, "keep": True},
        ])

        with patch("app.agents.nodes.rerank.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = rerank_results(self._make_state(1))

        assert all(isinstance(r, ScoredResult) for r in result["ranked_results"])
