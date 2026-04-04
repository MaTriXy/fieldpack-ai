"""Edge case and adversarial tests for Phase 1 models and state.

These simulate real-world conditions: messy LLM output, boundary values,
type coercion, and runtime state access patterns.
"""

import pytest
from pydantic import ValidationError

from app.agents.models import (
    ClassifyExtractOutput,
    CraftedQuery,
    GenerateAnswerInput,
    IntentType,
    ReRankOutput,
    ResultType,
    ScoredResult,
    SearchEngineType,
    SearchResult,
    SearchRoute,
)
from app.agents.state import (
    FieldAssistantState,
    trim_conversation_history,
)


# ============================================================
# ClassifyExtractOutput — LLM output resilience
# ============================================================

class TestClassifyLLMResilience:
    """E4B is a 4.5B model. It WILL produce messy output."""

    def test_intent_uppercase_rejected(self):
        """StrEnum is case-sensitive. LLM might return 'DIAGNOSE_DISEASE'."""
        with pytest.raises(ValidationError):
            ClassifyExtractOutput(intent="DIAGNOSE_DISEASE")

    def test_intent_mixed_case_rejected(self):
        with pytest.raises(ValidationError):
            ClassifyExtractOutput(intent="Diagnose_Disease")

    def test_confidence_as_string_coerced(self):
        """Pydantic v2 coerces '0.85' to 0.85. Verify this works since LLMs
        often return numbers as strings in JSON."""
        output = ClassifyExtractOutput(intent="diagnose_disease", confidence="0.85")
        assert output.confidence == 0.85
        assert isinstance(output.confidence, float)

    def test_confidence_as_int_coerced(self):
        """LLM might return confidence: 1 instead of 1.0."""
        output = ClassifyExtractOutput(intent="diagnose_disease", confidence=1)
        assert output.confidence == 1.0

    def test_confidence_boundary_zero(self):
        output = ClassifyExtractOutput(intent="diagnose_disease", confidence=0.0)
        assert output.confidence == 0.0

    def test_confidence_boundary_one(self):
        output = ClassifyExtractOutput(intent="diagnose_disease", confidence=1.0)
        assert output.confidence == 1.0

    def test_extra_fields_ignored(self):
        """LLM might return fields we didn't ask for."""
        output = ClassifyExtractOutput(
            intent="diagnose_disease",
            crop="cassava",
            extra_field="surprise",
            another_one=42,
        )
        assert output.intent == IntentType.DIAGNOSE_DISEASE
        assert not hasattr(output, "extra_field")

    def test_empty_string_crop_accepted(self):
        """BUG CHECK: empty string is not None. Is '' a valid crop?
        Currently accepted — we should decide if this is correct."""
        output = ClassifyExtractOutput(intent="diagnose_disease", crop="")
        # This passes, but '' is semantically wrong. Downstream code
        # checking `if state.crop:` will treat '' as falsy, but
        # `if state.crop is not None:` will treat it as truthy.
        assert output.crop == ""

    def test_empty_string_disease_name_accepted(self):
        """Same concern as crop — '' vs None."""
        output = ClassifyExtractOutput(intent="get_treatment", disease_name="")
        assert output.disease_name == ""

    def test_keywords_with_empty_strings(self):
        """LLM might output ['spots', '', 'curl']. Empty strings are noise."""
        output = ClassifyExtractOutput(
            intent="diagnose_disease",
            keywords=["brown spots", "", "curling", ""],
        )
        assert "" in output.keywords  # Currently accepted

    def test_keywords_with_duplicates(self):
        output = ClassifyExtractOutput(
            intent="diagnose_disease",
            keywords=["mosaic", "mosaic", "yellow"],
        )
        assert len(output.keywords) == 3  # Duplicates not stripped

    def test_unicode_crop_names(self):
        """Senegalese farmers use Wolof/French names."""
        output = ClassifyExtractOutput(
            intent="diagnose_disease",
            crop="manioc",  # French for cassava
        )
        assert output.crop == "manioc"

    def test_unicode_disease_names(self):
        output = ClassifyExtractOutput(
            intent="get_treatment",
            disease_name="mosaïque du manioc",
        )
        assert output.disease_name == "mosaïque du manioc"

    def test_very_long_keywords_list(self):
        """LLM goes haywire and returns 100 keywords."""
        keywords = [f"keyword_{i}" for i in range(100)]
        output = ClassifyExtractOutput(
            intent="diagnose_disease",
            keywords=keywords,
        )
        assert len(output.keywords) == 100

    def test_needs_image_as_string_coerced(self):
        """LLM returns 'true' instead of true."""
        output = ClassifyExtractOutput(intent="identify_image", needs_image="true")
        assert output.needs_image is True

    def test_from_raw_llm_json(self):
        """Simulate parsing a realistic LLM JSON response."""
        raw = {
            "intent": "diagnose_disease",
            "crop": "cassava",
            "disease_name": None,
            "keywords": ["brown spots", "leaf curl", "yellowing"],
            "needs_image": False,
            "confidence": 0.78,
        }
        output = ClassifyExtractOutput.model_validate(raw)
        assert output.intent == IntentType.DIAGNOSE_DISEASE


# ============================================================
# SearchResult — score and content edge cases
# ============================================================

class TestSearchResultEdgeCases:

    def test_score_no_upper_bound(self):
        """ChromaDB L2 distance can exceed 1.0. Should this be allowed?"""
        result = SearchResult(content="test", score=2.5)
        assert result.score == 2.5  # Currently no upper bound

    def test_score_very_large(self):
        """Extreme distance scores from bad queries."""
        result = SearchResult(content="test", score=999.0)
        assert result.score == 999.0

    def test_empty_content(self):
        """Should we allow empty content? Currently yes."""
        result = SearchResult(content="")
        assert result.content == ""

    def test_parent_id_without_parent_content(self):
        """This happens during search before parent resolution.
        The child is found, parent_id is set, but parent hasn't been fetched yet."""
        result = SearchResult(
            content="child chunk",
            parent_id="CMD_001_parent",
            parent_content=None,
        )
        assert result.parent_id is not None
        assert result.parent_content is None

    def test_parent_content_without_parent_id(self):
        """Shouldn't happen but should be valid structurally."""
        result = SearchResult(
            content="some result",
            parent_id=None,
            parent_content="orphaned parent content",
        )
        assert result.parent_id is None
        assert result.parent_content is not None

    def test_nested_metadata(self):
        """ChromaDB where clauses can be nested."""
        result = SearchResult(
            content="test",
            metadata={
                "crop": "cassava",
                "$and": [
                    {"severity": {"$gte": "medium"}},
                    {"type": "viral"},
                ],
            },
        )
        assert "$and" in result.metadata

    def test_very_long_content(self):
        """Parent chunks can be 400+ words."""
        long_content = "word " * 500
        result = SearchResult(content=long_content)
        assert len(result.content.split()) == 500


# ============================================================
# ScoredResult vs SearchResult — score consistency
# ============================================================

class TestScoreConsistency:

    def test_scored_result_capped_at_1(self):
        """ScoredResult.relevance_score is [0, 1] but SearchResult.score is [0, inf)."""
        with pytest.raises(ValidationError):
            ScoredResult(content="test", relevance_score=1.5)

    def test_search_result_uncapped(self):
        """SearchResult.score allows > 1.0 for raw distance scores."""
        result = SearchResult(content="test", score=1.5)
        assert result.score == 1.5


# ============================================================
# CraftedQuery — FTS5 injection concerns
# ============================================================

class TestCraftedQueryEdgeCases:

    def test_fts5_special_chars_in_keywords(self):
        """Keywords could contain FTS5 operators that break queries downstream."""
        query = CraftedQuery(
            embedding_query="cassava disease",
            fts_keywords=["OR", "AND", "NOT", "NEAR", "*", '"mosaic"'],
        )
        assert "OR" in query.fts_keywords  # Accepted — downstream must sanitize

    def test_very_long_embedding_query(self):
        """LLM ignores our 'under 50 words' instruction."""
        long_query = "cassava " * 200
        query = CraftedQuery(embedding_query=long_query)
        assert len(query.embedding_query.split()) == 200

    def test_empty_embedding_query_with_keywords(self):
        """LLM might fill keywords but not the embedding query."""
        query = CraftedQuery(
            embedding_query="",
            fts_keywords=["cassava", "mosaic"],
        )
        assert query.embedding_query == ""
        assert len(query.fts_keywords) == 2


# ============================================================
# SearchRoute — routing edge cases
# ============================================================

class TestSearchRouteEdgeCases:

    def test_empty_engines_for_observation(self):
        """log_observation intent routes with no search engines."""
        route = SearchRoute(engines=[], collections=[], tables=[])
        assert len(route.engines) == 0

    def test_all_engines_selected(self):
        route = SearchRoute(
            engines=[
                SearchEngineType.CHROMA_EMBEDDING,
                SearchEngineType.SQLITE_FTS,
                SearchEngineType.SQLITE_STRUCTURED,
            ],
        )
        assert len(route.engines) == 3

    def test_invalid_collection_name_accepted(self):
        """We don't validate collection names at the model level.
        Downstream code must check against CHROMA_COLLECTIONS."""
        route = SearchRoute(collections=["nonexistent_collection"])
        assert route.collections[0] == "nonexistent_collection"

    def test_duplicate_engines(self):
        route = SearchRoute(
            engines=[SearchEngineType.CHROMA_EMBEDDING, SearchEngineType.CHROMA_EMBEDDING],
        )
        assert len(route.engines) == 2  # Duplicates not prevented


# ============================================================
# ReRankOutput — edge cases
# ============================================================

class TestReRankEdgeCases:

    def test_empty_results_not_sufficient(self):
        output = ReRankOutput(ranked_results=[], is_sufficient=False)
        assert not output.is_sufficient

    def test_many_results(self):
        results = [
            ScoredResult(content=f"result {i}", relevance_score=0.5)
            for i in range(50)
        ]
        output = ReRankOutput(ranked_results=results, is_sufficient=True)
        assert len(output.ranked_results) == 50

    def test_all_zero_scores(self):
        results = [
            ScoredResult(content="junk", relevance_score=0.0)
            for _ in range(5)
        ]
        output = ReRankOutput(ranked_results=results, is_sufficient=False)
        assert all(r.relevance_score == 0.0 for r in output.ranked_results)


# ============================================================
# trim_conversation_history — boundary bugs
# ============================================================

class TestTrimEdgeCases:

    def test_max_messages_zero(self):
        """max_messages=0 should return empty list."""
        history = [{"role": "user", "content": "hello"}]
        result = trim_conversation_history(history, max_messages=0)
        assert result == []

    def test_max_messages_negative(self):
        """BUG: max_messages=-1 causes history[-(-1):] = history[1:]
        which silently drops the first message instead of erroring."""
        history = [
            {"role": "user", "content": "msg 0"},
            {"role": "user", "content": "msg 1"},
            {"role": "user", "content": "msg 2"},
        ]
        result = trim_conversation_history(history, max_messages=-1)
        # This is a BUG — it returns [msg 1, msg 2] instead of raising an error
        # After fix, this should raise ValueError
        assert result == []  # Expected after fix

    def test_max_messages_one(self):
        history = [
            {"role": "user", "content": "msg 0"},
            {"role": "user", "content": "msg 1"},
        ]
        result = trim_conversation_history(history, max_messages=1)
        assert len(result) == 1
        assert result[0]["content"] == "msg 1"

    def test_single_message(self):
        history = [{"role": "user", "content": "only one"}]
        result = trim_conversation_history(history, max_messages=10)
        assert len(result) == 1

    def test_preserves_message_structure(self):
        """Messages might have extra fields beyond role/content."""
        history = [
            {"role": "user", "content": "hi", "timestamp": "2026-04-04T10:00:00Z", "extra": True},
        ]
        result = trim_conversation_history(history, max_messages=10)
        assert result[0]["extra"] is True

    def test_alternating_roles(self):
        """Real conversation alternates user/assistant."""
        history = []
        for i in range(12):
            role = "user" if i % 2 == 0 else "assistant"
            history.append({"role": role, "content": f"msg {i}"})
        result = trim_conversation_history(history, max_messages=10)
        assert len(result) == 10
        # The window should start with an assistant message (msg 2)
        # and end with assistant (msg 11)
        assert result[0]["content"] == "msg 2"
        assert result[-1]["content"] == "msg 11"


# ============================================================
# State access patterns — runtime safety
# ============================================================

class TestStateAccess:

    def test_missing_key_raises_keyerror(self):
        """total=False TypedDict allows partial creation, but accessing
        missing keys at runtime raises KeyError. LangGraph state management
        handles this, but we should be aware."""
        state: FieldAssistantState = {"user_message": "hello"}
        with pytest.raises(KeyError):
            _ = state["classify_result"]

    def test_get_with_default_avoids_keyerror(self):
        """Safe access pattern for optional state fields."""
        state: FieldAssistantState = {"user_message": "hello"}
        result = state.get("classify_result")
        assert result is None

    def test_state_update_via_dict_merge(self):
        """LangGraph nodes return partial dicts that get merged into state."""
        state: FieldAssistantState = {
            "user_message": "hello",
            "retrieval_attempts": 0,
        }
        update = {"classify_result": ClassifyExtractOutput(intent="diagnose_disease")}
        state.update(update)
        assert state["classify_result"].intent == IntentType.DIAGNOSE_DISEASE
        assert state["user_message"] == "hello"

    def test_state_retrieval_attempts_increment(self):
        """Simulates the retry loop incrementing attempts."""
        state: FieldAssistantState = {"retrieval_attempts": 0}
        for i in range(3):
            state["retrieval_attempts"] = state.get("retrieval_attempts", 0) + 1
        assert state["retrieval_attempts"] == 3


# ============================================================
# model_validate from dict — LLM JSON parsing simulation
# ============================================================

class TestModelValidateFromDict:

    def test_classify_from_dict_with_extra_fields(self):
        """LLM returns extra keys in JSON."""
        raw = {
            "intent": "diagnose_disease",
            "crop": "cassava",
            "hallucinated_field": "not real",
            "confidence": 0.7,
        }
        output = ClassifyExtractOutput.model_validate(raw)
        assert output.crop == "cassava"

    def test_classify_from_dict_missing_optional_fields(self):
        """LLM omits optional fields entirely."""
        raw = {"intent": "general_question"}
        output = ClassifyExtractOutput.model_validate(raw)
        assert output.crop is None
        assert output.keywords == []

    def test_search_result_from_dict(self):
        raw = {
            "content": "Cassava Mosaic Disease...",
            "source": "disease_knowledge",
            "score": 0.92,
            "result_type": "chroma",
        }
        result = SearchResult.model_validate(raw)
        assert result.result_type == ResultType.CHROMA

    def test_scored_result_from_dict_string_score(self):
        """Score comes as string from JSON."""
        raw = {"content": "test", "relevance_score": "0.75"}
        result = ScoredResult.model_validate(raw)
        assert result.relevance_score == 0.75
