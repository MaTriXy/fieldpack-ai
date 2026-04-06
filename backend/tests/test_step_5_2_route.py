"""Tests for Step 5.2: ROUTE node (Python only, no LLM)."""

import pytest

from app.agents.models import (
    ClassifyExtractOutput,
    GrowthStage,
    IntentType,
    SeasonType,
    SearchEngineType,
    SearchRoute,
    TopicSubtype,
)
from app.agents.nodes.route import (
    EXPANDED_ROUTE,
    ROUTING_RULES,
    _build_metadata_filters,
    expand_route,
    route_intent,
)


# ============================================================
# Unit: _build_metadata_filters
# ============================================================

class TestBuildMetadataFilters:

    def test_with_crop(self):
        classify = ClassifyExtractOutput(
            intent=IntentType.DIAGNOSE_DISEASE,
            crop="Cassava",
        )
        filters = _build_metadata_filters(classify)
        assert filters["crop"] == "cassava"

    def test_with_disease_name(self):
        classify = ClassifyExtractOutput(
            intent=IntentType.GET_TREATMENT,
            disease_name="Cassava Mosaic Disease",
        )
        filters = _build_metadata_filters(classify)
        assert filters["disease_name"] == "Cassava Mosaic Disease"

    def test_with_both(self):
        classify = ClassifyExtractOutput(
            intent=IntentType.DIAGNOSE_DISEASE,
            crop="rice",
            disease_name="Rice Blast",
        )
        filters = _build_metadata_filters(classify)
        assert filters["crop"] == "rice"
        assert filters["disease_name"] == "Rice Blast"

    def test_with_season(self):
        classify = ClassifyExtractOutput(
            intent=IntentType.FARMING_ADVICE,
            season=SeasonType.WET,
        )
        filters = _build_metadata_filters(classify)
        assert filters["season"] == "wet"

    def test_with_growth_stage(self):
        classify = ClassifyExtractOutput(
            intent=IntentType.FARMING_ADVICE,
            growth_stage=GrowthStage.FLOWERING,
        )
        filters = _build_metadata_filters(classify)
        assert filters["growth_stage"] == "flowering"

    def test_with_topic_subtype(self):
        classify = ClassifyExtractOutput(
            intent=IntentType.FARMING_ADVICE,
            topic_subtype=TopicSubtype.FERTILIZATION,
        )
        filters = _build_metadata_filters(classify)
        assert filters["practice_type"] == "fertilization"

    def test_farming_full_filters(self):
        classify = ClassifyExtractOutput(
            intent=IntentType.FARMING_ADVICE,
            crop="rice",
            season=SeasonType.WET,
            growth_stage=GrowthStage.PLANNING,
            topic_subtype=TopicSubtype.PLANTING,
        )
        filters = _build_metadata_filters(classify)
        assert filters["crop"] == "rice"
        assert filters["season"] == "wet"
        assert filters["growth_stage"] == "planning"
        assert filters["practice_type"] == "planting"

    def test_no_filters(self):
        classify = ClassifyExtractOutput(intent=IntentType.GENERAL_QUESTION)
        filters = _build_metadata_filters(classify)
        assert filters == {}


# ============================================================
# Unit: route_intent for each intent
# ============================================================

class TestRouteIntent:

    def _make_state(self, intent, crop=None, disease_name=None):
        return {
            "classify_result": ClassifyExtractOutput(
                intent=intent,
                crop=crop,
                disease_name=disease_name,
                confidence=0.8,
            ),
        }

    def test_diagnose_disease(self):
        result = route_intent(self._make_state(IntentType.DIAGNOSE_DISEASE, crop="cassava"))
        route = result["route"]
        assert SearchEngineType.CHROMA_EMBEDDING in route.engines
        assert SearchEngineType.SQLITE_FTS in route.engines
        assert "disease_knowledge" in route.collections
        assert "diseases" in route.tables
        assert "pests" in route.tables
        assert route.metadata_filters.get("crop") == "cassava"

    def test_get_treatment(self):
        result = route_intent(self._make_state(IntentType.GET_TREATMENT))
        route = result["route"]
        assert SearchEngineType.CHROMA_EMBEDDING in route.engines
        assert SearchEngineType.SQLITE_STRUCTURED in route.engines
        assert "treatment_guides" in route.collections
        assert "treatments" in route.tables

    def test_farming_advice(self):
        result = route_intent(self._make_state(IntentType.FARMING_ADVICE))
        route = result["route"]
        assert SearchEngineType.CHROMA_EMBEDDING in route.engines
        assert SearchEngineType.SQLITE_STRUCTURED in route.engines
        assert SearchEngineType.SQLITE_FTS in route.engines
        assert "farming_practices" in route.collections
        assert "regional_context" in route.collections
        assert "crops" in route.tables
        assert "climate" in route.tables
        assert "varieties" in route.tables
        assert "fertilization_schedule" in route.tables
        assert "planting_calendar" in route.tables
        assert "storage_guidelines" in route.tables
        assert "soil_requirements" in route.tables

    def test_identify_image(self):
        result = route_intent(self._make_state(IntentType.IDENTIFY_IMAGE))
        route = result["route"]
        assert SearchEngineType.CHROMA_EMBEDDING in route.engines
        assert SearchEngineType.SQLITE_FTS in route.engines
        assert "disease_knowledge" in route.collections
        assert "pests" in route.tables

    def test_log_observation(self):
        result = route_intent(self._make_state(IntentType.LOG_OBSERVATION))
        route = result["route"]
        assert route.engines == []
        assert route.collections == []
        assert route.tables == []

    def test_general_question(self):
        result = route_intent(self._make_state(IntentType.GENERAL_QUESTION))
        route = result["route"]
        assert len(route.collections) == 4  # all collections
        assert SearchEngineType.CHROMA_EMBEDDING in route.engines

    def test_follow_up_fallback(self):
        result = route_intent(self._make_state(IntentType.FOLLOW_UP))
        route = result["route"]
        assert len(route.collections) == 4  # general question fallback

    def test_no_classify_result(self):
        result = route_intent({})
        route = result["route"]
        # Fallback to general question
        assert SearchEngineType.CHROMA_EMBEDDING in route.engines
        assert len(route.collections) == 4

    def test_metadata_filters_with_crop(self):
        result = route_intent(
            self._make_state(IntentType.DIAGNOSE_DISEASE, crop="Rice"),
        )
        route = result["route"]
        assert route.metadata_filters["crop"] == "rice"

    def test_metadata_filters_with_disease(self):
        result = route_intent(
            self._make_state(
                IntentType.GET_TREATMENT,
                disease_name="Cassava Mosaic Disease",
            ),
        )
        route = result["route"]
        assert route.metadata_filters["disease_name"] == "Cassava Mosaic Disease"

    def test_result_is_search_route(self):
        result = route_intent(self._make_state(IntentType.DIAGNOSE_DISEASE))
        assert isinstance(result["route"], SearchRoute)

    def test_all_intents_have_routing_rules(self):
        for intent in IntentType:
            assert intent in ROUTING_RULES


# ============================================================
# Unit: expand_route
# ============================================================

class TestExpandRoute:

    def test_expands_engines(self):
        narrow = SearchRoute(
            engines=[SearchEngineType.CHROMA_EMBEDDING],
            collections=["disease_knowledge"],
            tables=["diseases"],
        )
        expanded = expand_route(narrow)
        assert SearchEngineType.CHROMA_EMBEDDING in expanded.engines
        assert SearchEngineType.SQLITE_FTS in expanded.engines
        assert SearchEngineType.SQLITE_STRUCTURED in expanded.engines

    def test_expands_collections(self):
        narrow = SearchRoute(
            engines=[SearchEngineType.CHROMA_EMBEDDING],
            collections=["disease_knowledge"],
        )
        expanded = expand_route(narrow)
        assert "treatment_guides" in expanded.collections
        assert "farming_practices" in expanded.collections
        assert "regional_context" in expanded.collections

    def test_expands_tables(self):
        narrow = SearchRoute(
            engines=[SearchEngineType.SQLITE_FTS],
            collections=[],
            tables=["diseases"],
        )
        expanded = expand_route(narrow)
        assert "treatments" in expanded.tables
        assert "crops" in expanded.tables
        assert "pests" in expanded.tables
        assert "varieties" in expanded.tables
        assert "fertilization_schedule" in expanded.tables
        assert "planting_calendar" in expanded.tables
        assert "storage_guidelines" in expanded.tables
        assert "soil_requirements" in expanded.tables

    def test_preserves_metadata_filters(self):
        narrow = SearchRoute(
            engines=[SearchEngineType.CHROMA_EMBEDDING],
            collections=["disease_knowledge"],
            metadata_filters={"crop": "cassava"},
        )
        expanded = expand_route(narrow)
        assert expanded.metadata_filters == {"crop": "cassava"}

    def test_no_duplicates(self):
        narrow = SearchRoute(
            engines=[SearchEngineType.CHROMA_EMBEDDING, SearchEngineType.SQLITE_FTS],
            collections=["disease_knowledge", "treatment_guides"],
            tables=["diseases"],
        )
        expanded = expand_route(narrow)
        assert len(expanded.engines) == len(set(expanded.engines))
        assert len(expanded.collections) == len(set(expanded.collections))
        assert len(expanded.tables) == len(set(expanded.tables))
