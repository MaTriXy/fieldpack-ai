"""Tests for Step 5.3: CRAFT SEARCH QUERY node.

First attempt uses a template (no LLM). Retry uses LLM for variants.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.models import (
    ClassifyExtractOutput,
    CraftedQuery,
    GrowthStage,
    IntentType,
    SearchEngineType,
    SearchRoute,
)
from app.agents.nodes.craft_query import (
    _parse_craft_response,
    _template_query,
    craft_search_query,
)


# ============================================================
# Unit: _parse_craft_response (still used by retry path)
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
# Unit: _template_query
# ============================================================

class TestTemplateQuery:

    def test_includes_crop_and_keywords(self):
        classify = ClassifyExtractOutput(
            intent=IntentType.DIAGNOSE_DISEASE,
            crop="cassava",
            keywords=["yellow", "leaves", "curling"],
        )
        result = _template_query("My cassava has yellow leaves", classify)
        assert "cassava" in result.embedding_query
        assert "yellow" in result.embedding_query
        assert "cassava" in result.fts_keywords
        assert "yellow" in result.fts_keywords
        # Raw user message excluded when classify provides fields
        assert "My cassava has" not in result.embedding_query

    def test_includes_disease_name(self):
        classify = ClassifyExtractOutput(
            intent=IntentType.GET_TREATMENT,
            crop="rice",
            disease_name="Rice Blast",
            keywords=["rice", "blast", "treatment"],
        )
        result = _template_query("How to treat rice blast?", classify)
        assert "Rice Blast" in result.embedding_query
        assert "Rice Blast" in result.fts_keywords

    def test_includes_growth_stage(self):
        classify = ClassifyExtractOutput(
            intent=IntentType.FARMING_ADVICE,
            crop="cassava",
            keywords=["cassava", "planting"],
            growth_stage=GrowthStage.VEGETATIVE,
        )
        result = _template_query("How much water?", classify)
        assert "vegetative" in result.embedding_query

    def test_deduplicates_keywords(self):
        classify = ClassifyExtractOutput(
            crop="cassava",
            keywords=["cassava", "yellow", "cassava"],
        )
        result = _template_query("cassava problem", classify)
        assert result.fts_keywords.count("cassava") == 1

    def test_no_classify_result_falls_back_to_user_message(self):
        result = _template_query("help with my crops", None)
        assert "help with my crops" in result.embedding_query

    def test_empty_classify_falls_back_to_user_message(self):
        classify = ClassifyExtractOutput()
        result = _template_query("help with my crops", classify)
        assert "help with my crops" in result.embedding_query

    def test_reasoning_mentions_template(self):
        classify = ClassifyExtractOutput(crop="rice")
        result = _template_query("test", classify)
        assert "template" in result.reasoning.lower()


# ============================================================
# Integration: craft_search_query
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

    def test_first_attempt_uses_template_not_llm(self):
        """First attempt should use template — no LLM call."""
        with patch("app.agents.nodes.craft_query.get_field_llm") as mock_llm:
            result = craft_search_query(self._make_state())
            mock_llm.assert_not_called()

        query = result["crafted_query"]
        assert isinstance(query, CraftedQuery)
        assert "cassava" in query.embedding_query
        assert "yellow" in query.fts_keywords
        assert "template" in query.reasoning.lower()

    def test_skipped_when_no_chroma(self):
        result = craft_search_query(self._make_state(has_chroma=False))
        query = result["crafted_query"]
        assert query.embedding_query == ""
        assert "skipped" in query.reasoning.lower()
        assert query.fts_keywords == ["cassava", "yellow", "leaves"]

    def test_no_route_skips(self):
        state = {
            "user_message": "test",
            "classify_result": ClassifyExtractOutput(),
            "route": None,
        }
        result = craft_search_query(state)
        assert result["crafted_query"].embedding_query == ""

    def test_first_attempt_includes_crop_in_query(self):
        result = craft_search_query(self._make_state(crop="rice"))
        assert "rice" in result["crafted_query"].embedding_query.lower()
