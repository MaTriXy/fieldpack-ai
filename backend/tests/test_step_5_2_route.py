"""Tests for Step 5.2: ROUTE node (Python only, no LLM).

Routing casts a wide net for every retrieval intent; only LOG_OBSERVATION
skips search. Classifier output feeds metadata filters (crop, disease_name)
only — softer signals (season, growth_stage, topic_subtype) are not
converted into hard filters so rerank remains the source of truth.
"""

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
    ALL_COLLECTIONS,
    ALL_ENGINES,
    ALL_TABLES,
    BROAD_ROUTE,
    EXPANDED_ROUTE,
    NO_SEARCH_INTENTS,
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

    def test_soft_signals_are_not_hard_filters(self):
        """Season/growth_stage/topic_subtype are NOT converted into filters.

        Rerank is the source of truth; over-filtering on classifier-emitted
        soft signals hides chunks when the classifier guesses wrong.
        """
        classify = ClassifyExtractOutput(
            intent=IntentType.FARMING_ADVICE,
            season=SeasonType.WET,
            growth_stage=GrowthStage.FLOWERING,
            topic_subtype=TopicSubtype.FERTILIZATION,
        )
        filters = _build_metadata_filters(classify)
        assert "season" not in filters
        assert "growth_stage" not in filters
        assert "practice_type" not in filters

    def test_hard_and_soft_mixed(self):
        classify = ClassifyExtractOutput(
            intent=IntentType.FARMING_ADVICE,
            crop="rice",
            season=SeasonType.WET,
            topic_subtype=TopicSubtype.PLANTING,
        )
        filters = _build_metadata_filters(classify)
        assert filters == {"crop": "rice"}

    def test_no_filters(self):
        classify = ClassifyExtractOutput(intent=IntentType.GENERAL_QUESTION)
        filters = _build_metadata_filters(classify)
        assert filters == {}


# ============================================================
# Unit: route_intent — broad route for every search intent
# ============================================================

SEARCH_INTENTS = [
    IntentType.DIAGNOSE_DISEASE,
    IntentType.GET_TREATMENT,
    IntentType.FARMING_ADVICE,
    IntentType.IDENTIFY_IMAGE,
    IntentType.GENERAL_QUESTION,
    IntentType.FOLLOW_UP,
]


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

    @pytest.mark.parametrize("intent", SEARCH_INTENTS)
    def test_search_intents_get_broad_route(self, intent):
        """Every retrieval intent receives the same broad route.

        The classifier can't narrow tables/collections — it only
        contributes metadata filters. This is the core invariant
        preventing classifier-error bugs like the tomato-pests case.
        """
        result = route_intent(self._make_state(intent))
        route = result["route"]

        assert set(route.engines) == set(ALL_ENGINES)
        assert set(route.collections) == set(ALL_COLLECTIONS)
        assert set(route.tables) == set(ALL_TABLES)

    def test_pests_table_is_reachable_from_farming_advice(self):
        """Regression: the tomato-pests bug was FARMING_ADVICE skipping pests."""
        result = route_intent(self._make_state(IntentType.FARMING_ADVICE))
        assert "pests" in result["route"].tables
        assert "diseases" in result["route"].tables

    def test_pests_table_is_reachable_from_general_question(self):
        """GENERAL_QUESTION used to route to Chroma only — now broad."""
        result = route_intent(self._make_state(IntentType.GENERAL_QUESTION))
        route = result["route"]
        assert "pests" in route.tables
        assert SearchEngineType.SQLITE_FTS in route.engines

    def test_log_observation_skips_retrieval(self):
        result = route_intent(self._make_state(IntentType.LOG_OBSERVATION))
        route = result["route"]
        assert route.engines == []
        assert route.collections == []
        assert route.tables == []

    def test_log_observation_in_no_search_intents(self):
        assert IntentType.LOG_OBSERVATION in NO_SEARCH_INTENTS

    def test_no_classify_result_falls_back_to_broad(self):
        result = route_intent({})
        route = result["route"]
        assert set(route.engines) == set(ALL_ENGINES)
        assert set(route.collections) == set(ALL_COLLECTIONS)
        assert set(route.tables) == set(ALL_TABLES)

    def test_metadata_filters_with_crop(self):
        result = route_intent(
            self._make_state(IntentType.DIAGNOSE_DISEASE, crop="Rice"),
        )
        assert result["route"].metadata_filters["crop"] == "rice"

    def test_metadata_filters_with_disease(self):
        result = route_intent(
            self._make_state(
                IntentType.GET_TREATMENT,
                disease_name="Cassava Mosaic Disease",
            ),
        )
        assert result["route"].metadata_filters["disease_name"] == "Cassava Mosaic Disease"

    def test_result_is_search_route(self):
        result = route_intent(self._make_state(IntentType.DIAGNOSE_DISEASE))
        assert isinstance(result["route"], SearchRoute)


# ============================================================
# Unit: expand_route
# ============================================================

class TestExpandRoute:

    def test_retry_drops_metadata_filters(self):
        """On retry, over-constrained crop/disease filters are dropped.

        With a broad default route, the engines/collections/tables are
        already maximal — the remaining lever is relaxing filters that
        may have over-constrained the initial query.
        """
        narrow = SearchRoute(
            engines=list(ALL_ENGINES),
            collections=list(ALL_COLLECTIONS),
            tables=list(ALL_TABLES),
            metadata_filters={"crop": "cassava", "disease_name": "CMD"},
        )
        expanded = expand_route(narrow)
        assert expanded.metadata_filters == {}

    def test_preserves_broad_coverage(self):
        narrow = SearchRoute(
            engines=[SearchEngineType.CHROMA_EMBEDDING],
            collections=["disease_knowledge"],
            tables=["diseases"],
        )
        expanded = expand_route(narrow)
        assert set(expanded.engines) == set(ALL_ENGINES)
        assert set(expanded.collections) == set(ALL_COLLECTIONS)
        assert set(expanded.tables) == set(ALL_TABLES)

    def test_no_duplicates(self):
        narrow = SearchRoute(
            engines=list(ALL_ENGINES),
            collections=list(ALL_COLLECTIONS),
            tables=list(ALL_TABLES),
        )
        expanded = expand_route(narrow)
        assert len(expanded.engines) == len(set(expanded.engines))
        assert len(expanded.collections) == len(set(expanded.collections))
        assert len(expanded.tables) == len(set(expanded.tables))
