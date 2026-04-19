"""Node 2: ROUTE (Python only, no LLM call).

Deterministic routing: casts a wide net across all retrieval engines,
collections, and tables for every search-bearing intent. Rerank is the
single source of truth for relevance — the router's job is to avoid
classifier errors hiding data the user actually needs.

Metadata filters are built from high-signal classifier output (crop,
disease_name). Softer signals (season, growth_stage, topic_subtype) are
deliberately NOT converted into hard filters — they'd exclude useful
chunks when the classifier guesses wrong.
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
# Broad default route — used for every intent that needs search.
# ============================================================

ALL_ENGINES = [
    SearchEngineType.CHROMA_EMBEDDING,
    SearchEngineType.SQLITE_FTS,
    SearchEngineType.SQLITE_STRUCTURED,
]

ALL_COLLECTIONS = [
    "disease_knowledge",
    "treatment_guides",
    "farming_practices",
    "regional_context",
]

ALL_TABLES = [
    "diseases", "crop_diseases", "treatments", "pests",
    "crops", "varieties", "climate",
    "fertilization_schedule", "planting_calendar",
    "storage_guidelines", "soil_requirements",
]

BROAD_ROUTE = {
    "engines": ALL_ENGINES,
    "collections": ALL_COLLECTIONS,
    "tables": ALL_TABLES,
}

# Intents that skip retrieval entirely. Everything else gets the broad route.
NO_SEARCH_INTENTS = frozenset({IntentType.LOG_OBSERVATION})

# Kept as EXPANDED_ROUTE alias for expand_route back-compat — same set.
EXPANDED_ROUTE = BROAD_ROUTE


def _build_metadata_filters(classify_result: ClassifyExtractOutput) -> dict:
    """Build ChromaDB metadata filters from classify output.

    Only high-signal identity fields (crop, disease_name) become hard
    filters. Softer signals are left to the reranker — a wrong
    topic_subtype filter is worse than no filter.
    """
    filters = {}

    if classify_result.crop:
        filters["crop"] = classify_result.crop.lower()

    if classify_result.disease_name:
        filters["disease_name"] = classify_result.disease_name

    return filters


def route_intent(state: FieldAssistantState) -> dict:
    """Route to retrieval: broad net for every search intent.

    Classifier output is used for metadata filters only, not to narrow
    which tables/collections get searched. This keeps the pipeline
    robust to classifier errors on unseen phrasings.

    Returns dict with: route.
    """
    classify_result = state.get("classify_result")

    if classify_result is None:
        log.log_step(Step.ROUTE, "route_no_classify", level="ERROR",
                     details={"error": "No classify_result in state"})
        return {
            "route": SearchRoute(
                engines=list(ALL_ENGINES),
                collections=list(ALL_COLLECTIONS),
                tables=list(ALL_TABLES),
            ),
        }

    intent = classify_result.intent

    if intent in NO_SEARCH_INTENTS:
        route = SearchRoute(engines=[], collections=[], tables=[])
        log.log_route(
            intent=intent.value,
            engines=[], collections=[], tables=[], filters={},
        )
        return {"route": route}

    metadata_filters = _build_metadata_filters(classify_result)

    route = SearchRoute(
        engines=list(ALL_ENGINES),
        collections=list(ALL_COLLECTIONS),
        tables=list(ALL_TABLES),
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

    With the broad default route, the main lever on retry is dropping
    metadata filters — the initial query may have over-constrained on
    crop/disease_name. Engines/collections/tables are already maximal.
    """
    new_engines = list(dict.fromkeys(
        list(current_route.engines) + ALL_ENGINES
    ))
    new_collections = list(dict.fromkeys(
        current_route.collections + ALL_COLLECTIONS
    ))
    new_tables = list(dict.fromkeys(
        current_route.tables + ALL_TABLES
    ))

    expanded = SearchRoute(
        engines=new_engines,
        collections=new_collections,
        tables=new_tables,
        metadata_filters={},
    )

    log.log_step(Step.ROUTE, "route_expanded", details={
        "engines": [e.value for e in expanded.engines],
        "collections": expanded.collections,
        "tables": expanded.tables,
        "dropped_filters": list(current_route.metadata_filters.keys()),
    })

    return expanded
