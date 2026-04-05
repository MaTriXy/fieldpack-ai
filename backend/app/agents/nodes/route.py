"""Node 2: ROUTE (Python only, no LLM call).

Deterministic routing: maps classified intent to search engines,
ChromaDB collections, and SQLite tables. Builds metadata filters
from extracted crop/disease info.

Routes are narrow by default — the retry loop broadens on failure.
NOTE: If recall is low in Phase 7 testing, broaden default routes.
"""

from app.agents.models import (
    ClassifyExtractOutput,
    IntentType,
    SearchEngineType,
    SearchRoute,
)
from app.agents.state import FieldAssistantState
from app.logger import Step, pipeline_logger as log


# ============================================================
# Routing rules: intent → engines, collections, tables
# ============================================================

ROUTING_RULES: dict[IntentType, dict] = {
    IntentType.DIAGNOSE_DISEASE: {
        "engines": [SearchEngineType.CHROMA_EMBEDDING, SearchEngineType.SQLITE_FTS],
        "collections": ["disease_knowledge"],
        "tables": ["diseases", "crop_diseases"],
    },
    IntentType.GET_TREATMENT: {
        "engines": [SearchEngineType.CHROMA_EMBEDDING, SearchEngineType.SQLITE_STRUCTURED],
        "collections": ["treatment_guides"],
        "tables": ["treatments"],
    },
    IntentType.FARMING_ADVICE: {
        "engines": [
            SearchEngineType.CHROMA_EMBEDDING,
            SearchEngineType.SQLITE_STRUCTURED,
            SearchEngineType.SQLITE_FTS,
        ],
        "collections": ["farming_practices", "regional_context"],
        "tables": ["crops", "climate"],
    },
    IntentType.IDENTIFY_IMAGE: {
        "engines": [SearchEngineType.CHROMA_EMBEDDING, SearchEngineType.SQLITE_FTS],
        "collections": ["disease_knowledge"],
        "tables": ["diseases"],
    },
    IntentType.LOG_OBSERVATION: {
        "engines": [],
        "collections": [],
        "tables": [],
    },
    IntentType.GENERAL_QUESTION: {
        "engines": [SearchEngineType.CHROMA_EMBEDDING],
        "collections": [
            "disease_knowledge", "treatment_guides",
            "farming_practices", "regional_context",
        ],
        "tables": [],
    },
    IntentType.FOLLOW_UP: {
        # Shouldn't normally reach here — classify resolves follow-ups.
        # Fallback: use general_question route.
        "engines": [SearchEngineType.CHROMA_EMBEDDING],
        "collections": [
            "disease_knowledge", "treatment_guides",
            "farming_practices", "regional_context",
        ],
        "tables": [],
    },
}

# Full expansion for retry #2: all engines, all collections, key tables
EXPANDED_ROUTE = {
    "engines": [
        SearchEngineType.CHROMA_EMBEDDING,
        SearchEngineType.SQLITE_FTS,
        SearchEngineType.SQLITE_STRUCTURED,
    ],
    "collections": [
        "disease_knowledge", "treatment_guides",
        "farming_practices", "regional_context",
    ],
    "tables": ["diseases", "treatments", "crops", "climate"],
}


def _build_metadata_filters(classify_result: ClassifyExtractOutput) -> dict:
    """Build ChromaDB metadata filters from classify output.

    Filters are conservative — only add filters we're confident about.
    Over-filtering is worse than under-filtering (re-rank handles noise).
    """
    filters = {}

    if classify_result.crop:
        filters["crop"] = classify_result.crop.lower()

    if classify_result.disease_name:
        filters["disease_name"] = classify_result.disease_name

    if classify_result.season:
        filters["season"] = classify_result.season.value

    if classify_result.growth_stage:
        filters["growth_stage"] = classify_result.growth_stage.value

    if classify_result.topic_subtype:
        filters["practice_type"] = classify_result.topic_subtype.value

    return filters


def route_intent(state: FieldAssistantState) -> dict:
    """Route the classified intent to search engines and collections.

    Pure Python — no LLM call. Reads classify_result from state,
    applies deterministic rules, builds metadata filters.

    For follow_up intent that wasn't resolved by classify,
    falls back to general_question routing.

    Returns dict with: route.
    """
    classify_result = state.get("classify_result")
    if classify_result is None:
        log.log_step(Step.ROUTE, "route_no_classify", level="ERROR",
                     details={"error": "No classify_result in state"})
        # Fallback: general question route
        return {
            "route": SearchRoute(
                engines=[SearchEngineType.CHROMA_EMBEDDING],
                collections=["disease_knowledge", "treatment_guides",
                              "farming_practices", "regional_context"],
            ),
        }

    intent = classify_result.intent
    rules = ROUTING_RULES.get(intent, ROUTING_RULES[IntentType.GENERAL_QUESTION])

    # Build metadata filters
    metadata_filters = _build_metadata_filters(classify_result)

    route = SearchRoute(
        engines=list(rules["engines"]),
        collections=list(rules["collections"]),
        tables=list(rules["tables"]),
        metadata_filters=metadata_filters,
    )

    log.log_route(
        intent=intent.value,
        engines=[e.value for e in route.engines],
        collections=route.collections,
        tables=route.tables,
        filters=metadata_filters,
    )

    return {"route": route}


def expand_route(current_route: SearchRoute) -> SearchRoute:
    """Expand a route for retry attempt #2.

    Adds all engines, all collections, and key tables.
    Used when is_sufficient=False after first retry.
    """
    new_engines = list(dict.fromkeys(
        list(current_route.engines) + EXPANDED_ROUTE["engines"]
    ))
    new_collections = list(dict.fromkeys(
        current_route.collections + EXPANDED_ROUTE["collections"]
    ))
    new_tables = list(dict.fromkeys(
        current_route.tables + EXPANDED_ROUTE["tables"]
    ))

    expanded = SearchRoute(
        engines=new_engines,
        collections=new_collections,
        tables=new_tables,
        metadata_filters=current_route.metadata_filters,
    )

    log.log_step(Step.ROUTE, "route_expanded", details={
        "engines": [e.value for e in expanded.engines],
        "collections": expanded.collections,
        "tables": expanded.tables,
    })

    return expanded
