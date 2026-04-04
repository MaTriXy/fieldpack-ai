"""Tests for Step 1.1: Pipeline Pydantic models."""

import json

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


# --- IntentType enum ---

def test_intent_type_values():
    assert IntentType.DIAGNOSE_DISEASE == "diagnose_disease"
    assert IntentType.LOG_OBSERVATION == "log_observation"
    assert len(IntentType) == 7


# --- ClassifyExtractOutput ---

def test_classify_valid():
    output = ClassifyExtractOutput(
        intent=IntentType.DIAGNOSE_DISEASE,
        crop="cassava",
        disease_name=None,
        keywords=["brown spots", "curling"],
        needs_image=False,
        confidence=0.85,
    )
    assert output.intent == IntentType.DIAGNOSE_DISEASE
    assert output.crop == "cassava"
    assert output.confidence == 0.85


def test_classify_defaults():
    output = ClassifyExtractOutput(intent=IntentType.GENERAL_QUESTION)
    assert output.crop is None
    assert output.disease_name is None
    assert output.keywords == []
    assert output.needs_image is False
    assert output.confidence == 0.5


def test_classify_confidence_too_high():
    with pytest.raises(ValidationError):
        ClassifyExtractOutput(intent=IntentType.DIAGNOSE_DISEASE, confidence=1.5)


def test_classify_confidence_too_low():
    with pytest.raises(ValidationError):
        ClassifyExtractOutput(intent=IntentType.DIAGNOSE_DISEASE, confidence=-0.1)


def test_classify_invalid_intent():
    with pytest.raises(ValidationError):
        ClassifyExtractOutput(intent="not_a_real_intent")


def test_classify_defaults():
    """ClassifyExtractOutput has safe defaults for all fields (fallback-friendly)."""
    output = ClassifyExtractOutput()
    assert output.intent == IntentType.GENERAL_QUESTION
    assert output.crop is None
    assert output.confidence == 0.5


# --- SearchRoute ---

def test_search_route_valid():
    route = SearchRoute(
        engines=[SearchEngineType.CHROMA_EMBEDDING, SearchEngineType.SQLITE_FTS],
        collections=["disease_knowledge"],
        tables=["diseases"],
        metadata_filters={"crop": "cassava"},
    )
    assert len(route.engines) == 2
    assert route.metadata_filters["crop"] == "cassava"


def test_search_route_defaults():
    route = SearchRoute()
    assert route.engines == []
    assert route.collections == []
    assert route.tables == []
    assert route.metadata_filters == {}


# --- CraftedQuery ---

def test_crafted_query_valid():
    query = CraftedQuery(
        embedding_query="cassava plant brown spots curling leaves yellowing",
        fts_keywords=["cassava", "mosaic", "brown spots"],
        reasoning="User described visual symptoms on cassava leaves",
    )
    assert "cassava" in query.embedding_query
    assert len(query.fts_keywords) == 3


def test_crafted_query_defaults():
    query = CraftedQuery()
    assert query.embedding_query == ""
    assert query.fts_keywords == []
    assert query.reasoning == ""


# --- SearchResult ---

def test_search_result_valid():
    result = SearchResult(
        content="Cassava Mosaic Disease symptoms...",
        source="disease_knowledge",
        metadata={"crop": "cassava", "disease_id": 1},
        score=0.92,
        result_type=ResultType.CHROMA,
        parent_id="CMD_001_parent",
        parent_content="Full description of CMD...",
    )
    assert result.result_type == ResultType.CHROMA
    assert result.parent_id == "CMD_001_parent"


def test_search_result_minimal():
    result = SearchResult(content="Some content")
    assert result.source == ""
    assert result.score == 0.0
    assert result.result_type == ResultType.CHROMA
    assert result.parent_id is None


def test_search_result_negative_score_rejected():
    with pytest.raises(ValidationError):
        SearchResult(content="x", score=-0.5)


# --- ScoredResult ---

def test_scored_result_valid():
    result = ScoredResult(
        content="Neem oil treatment for CMD",
        source="treatment_guides",
        relevance_score=0.88,
        parent_content="Full treatment protocol...",
    )
    assert result.relevance_score == 0.88


def test_scored_result_score_bounds():
    with pytest.raises(ValidationError):
        ScoredResult(content="x", relevance_score=1.5)
    with pytest.raises(ValidationError):
        ScoredResult(content="x", relevance_score=-0.1)


# --- ReRankOutput ---

def test_rerank_output_valid():
    output = ReRankOutput(
        ranked_results=[
            ScoredResult(content="Result 1", relevance_score=0.9),
            ScoredResult(content="Result 2", relevance_score=0.6),
        ],
        is_sufficient=True,
        reasoning="Two high-quality results found",
    )
    assert len(output.ranked_results) == 2
    assert output.is_sufficient is True


def test_rerank_output_defaults():
    output = ReRankOutput()
    assert output.ranked_results == []
    assert output.is_sufficient is False


# --- GenerateAnswerInput ---

def test_generate_answer_input_valid():
    inp = GenerateAnswerInput(
        query="How do I treat cassava mosaic?",
        context_chunks=["Chunk 1 content", "Chunk 2 content"],
        conversation_history=[{"role": "user", "content": "previous message"}],
        intent=IntentType.GET_TREATMENT,
    )
    assert inp.intent == IntentType.GET_TREATMENT
    assert len(inp.context_chunks) == 2


# --- JSON round-trip ---

@pytest.mark.parametrize("model_cls,data", [
    (ClassifyExtractOutput, {"intent": "diagnose_disease", "crop": "cassava", "confidence": 0.8}),
    (SearchRoute, {"engines": ["chroma_embedding"], "collections": ["disease_knowledge"]}),
    (CraftedQuery, {"embedding_query": "test query", "fts_keywords": ["test"]}),
    (SearchResult, {"content": "test", "score": 0.5, "result_type": "chroma"}),
    (ScoredResult, {"content": "test", "relevance_score": 0.7}),
    (ReRankOutput, {"ranked_results": [], "is_sufficient": False}),
    (GenerateAnswerInput, {"query": "test", "intent": "general_question"}),
])
def test_json_round_trip(model_cls, data):
    instance = model_cls(**data)
    json_str = instance.model_dump_json()
    restored = model_cls.model_validate_json(json_str)
    assert instance == restored
