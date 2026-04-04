"""Tests for Step 5.3: CRAFT SEARCH QUERY node (LLM call #2)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.models import (
    ClassifyExtractOutput,
    CraftedQuery,
    IntentType,
    SearchEngineType,
    SearchRoute,
)
from app.agents.nodes.craft_query import (
    _parse_craft_response,
    craft_search_query,
)


# ============================================================
# Unit: _parse_craft_response
# ============================================================

class TestParseCraftResponse:

    def test_clean_json(self):
        data = {
            "embedding_query": "cassava yellow mosaic leaves sick",
            "fts_keywords": ["cassava", "mosaic", "yellow"],
            "reasoning": "Matches child chunk style",
        }
        result = _parse_craft_response(json.dumps(data))
        assert result.embedding_query == "cassava yellow mosaic leaves sick"
        assert result.fts_keywords == ["cassava", "mosaic", "yellow"]

    def test_json_in_code_block(self):
        text = '```json\n{"embedding_query": "rice blast treatment", "fts_keywords": ["rice", "blast"]}\n```'
        result = _parse_craft_response(text)
        assert result.embedding_query == "rice blast treatment"

    def test_json_with_surrounding_text(self):
        text = 'Here: {"embedding_query": "test query", "fts_keywords": ["test"]} done'
        result = _parse_craft_response(text)
        assert result.embedding_query == "test query"

    def test_malformed_fallback_uses_raw_text(self):
        text = "cassava yellow mosaic pattern on leaves"
        result = _parse_craft_response(text)
        assert result.embedding_query == text
        assert len(result.fts_keywords) > 0

    def test_empty_response(self):
        result = _parse_craft_response("")
        assert isinstance(result, CraftedQuery)

    def test_partial_json_fills_defaults(self):
        text = '{"embedding_query": "cassava mosaic"}'
        result = _parse_craft_response(text)
        assert result.embedding_query == "cassava mosaic"
        assert result.fts_keywords == []


# ============================================================
# Integration: craft_search_query (mocked LLM)
# ============================================================

class TestCraftSearchQuery:

    def _make_state(self, has_chroma=True, crop="cassava", keywords=None):
        engines = [SearchEngineType.CHROMA_EMBEDDING] if has_chroma else [SearchEngineType.SQLITE_FTS]
        return {
            "user_message": "My cassava has yellow leaves",
            "classify_result": ClassifyExtractOutput(
                intent=IntentType.DIAGNOSE_DISEASE,
                crop=crop,
                keywords=keywords or ["cassava", "yellow", "leaves"],
            ),
            "route": SearchRoute(
                engines=engines,
                collections=["disease_knowledge"],
            ),
        }

    def test_basic_craft(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "embedding_query": "cassava plant sick yellow mosaic leaves curling",
            "fts_keywords": ["cassava", "mosaic", "yellow"],
            "reasoning": "Farmer-style description of symptoms",
        })

        with patch("app.agents.nodes.craft_query.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = craft_search_query(self._make_state())

        assert "crafted_query" in result
        query = result["crafted_query"]
        assert isinstance(query, CraftedQuery)
        assert len(query.embedding_query) > 0
        assert len(query.fts_keywords) > 0

    def test_skipped_when_no_chroma(self):
        result = craft_search_query(self._make_state(has_chroma=False))
        query = result["crafted_query"]
        assert query.embedding_query == ""
        assert "skipped" in query.reasoning.lower()
        # Should use classify keywords as fts fallback
        assert query.fts_keywords == ["cassava", "yellow", "leaves"]

    def test_llm_error_fallback(self):
        with patch("app.agents.nodes.craft_query.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = Exception("Ollama down")
            result = craft_search_query(self._make_state())

        query = result["crafted_query"]
        # Uses user message as embedding query
        assert "cassava" in query.embedding_query.lower()
        # Uses classify keywords
        assert query.fts_keywords == ["cassava", "yellow", "leaves"]

    def test_no_route_skips(self):
        state = {
            "user_message": "test",
            "classify_result": ClassifyExtractOutput(),
            "route": None,
        }
        result = craft_search_query(state)
        assert result["crafted_query"].embedding_query == ""

    def test_includes_classify_context_in_prompt(self):
        """Verify the LLM receives crop/disease context."""
        captured_messages = []

        def capture_invoke(messages):
            captured_messages.extend(messages)
            mock_resp = MagicMock()
            mock_resp.content = '{"embedding_query": "test", "fts_keywords": ["test"]}'
            return mock_resp

        with patch("app.agents.nodes.craft_query.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = capture_invoke
            craft_search_query(self._make_state(crop="rice"))

        all_text = " ".join(m.content for m in captured_messages)
        assert "rice" in all_text.lower()
