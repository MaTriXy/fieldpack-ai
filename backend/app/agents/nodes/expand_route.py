"""Node: EXPAND ROUTE (retry micro-node).

Called on retry attempt 2 to broaden the search strategy.
Widens engines, collections, and tables to maximum coverage.

This is a pure Python node — no LLM call.
"""

from app.agents.models import SearchRoute
from app.agents.nodes.route import EXPANDED_ROUTE, expand_route
from app.agents.state import FieldAssistantState
from app.logger import Step, pipeline_logger as log


def expand_route_node(state: FieldAssistantState) -> dict:
    """Expand the current route for broader retry search.

    Adds all engines, all collections, and key tables.
    Drops metadata filters — the original filters already failed to
    produce sufficient results, so keeping them repeats zero-result searches.

    Returns dict with: route.
    """
    current_route = state.get("route")
    attempts = state.get("retrieval_attempts", 0)

    if current_route is None:
        log.log_step(Step.EXPAND_ROUTE, "no_route", level="WARNING",
                     details={"error": "No route to expand, using full expansion"})
        return {
            "route": SearchRoute(
                engines=list(EXPANDED_ROUTE["engines"]),
                collections=list(EXPANDED_ROUTE["collections"]),
                tables=list(EXPANDED_ROUTE["tables"]),
                metadata_filters={},
            ),
        }

    log.log_step(Step.EXPAND_ROUTE, "start", details={
        "attempt": attempts,
        "current_engines": [e.value for e in current_route.engines],
        "current_collections": current_route.collections,
    })

    # Detect the no-op case: the current route is already a superset of
    # EXPANDED_ROUTE, so expand_route() won't widen the search space. The
    # filter-drop below still helps, but be loud so we can measure the waste.
    route_already_maxed = (
        set(EXPANDED_ROUTE["engines"]) <= set(current_route.engines)
        and set(EXPANDED_ROUTE["collections"]) <= set(current_route.collections)
        and set(EXPANDED_ROUTE["tables"]) <= set(current_route.tables)
    )
    had_metadata_filters = bool(current_route.metadata_filters)
    if route_already_maxed and not had_metadata_filters:
        log.log_step(Step.EXPAND_ROUTE, "retry_noop_risk", level="WARNING",
                     details={"reason": "route already at max and no filters to drop — retry will likely repeat prior attempt"})

    expanded = expand_route(current_route)

    # Drop metadata filters on expansion — the original filters already
    # failed to produce sufficient results, so keeping them just repeats
    # the same zero-result searches (e.g. crop="cassava" misses general chunks).
    expanded.metadata_filters = {}

    log.log_step(Step.EXPAND_ROUTE, "expanding", details={
        "engines": [e.value for e in expanded.engines],
        "collections": expanded.collections,
        "tables": expanded.tables,
        "filters_dropped": had_metadata_filters,
        "route_already_maxed": route_already_maxed,
    })

    return {"route": expanded}
