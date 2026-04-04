"""Node 4: EXECUTE SEARCHES (Python, parallel, no LLM).

Runs search tools concurrently based on the route. Merges results
from all engines, normalizes BM25 scores to [0, 1], deduplicates
by source ID, and sorts by score descending.

Uses asyncio.gather + to_thread for parallel sync tool execution.
"""

import asyncio

from app.agents.models import ResultType, SearchEngineType, SearchResult
from app.agents.state import FieldAssistantState
from app.knowledge_pack.schema_sqlite import FTS_TABLE_MAP
from app.logger import Step, pipeline_logger as log
from app.tools.chroma_search import chroma_search
from app.tools.fts_search import fts_search
from app.tools.sqlite_query import structured_query


def _normalize_bm25_scores(results: list[SearchResult]) -> list[SearchResult]:
    """Normalize BM25 scores to [0, 1] range.

    BM25 scores are unbounded positive floats (higher = better).
    Divide by max score in the batch so scores become relative.
    ChromaDB and structured results are left unchanged.
    """
    fts_results = [r for r in results if r.result_type == ResultType.FTS]
    if not fts_results:
        return results

    max_score = max(r.score for r in fts_results) if fts_results else 1.0
    if max_score <= 0:
        max_score = 1.0

    normalized = []
    for r in results:
        if r.result_type == ResultType.FTS and max_score > 0:
            normalized.append(r.model_copy(update={"score": r.score / max_score}))
        else:
            normalized.append(r)

    return normalized


def _deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
    """Deduplicate results by source ID. Keep first occurrence (higher score)."""
    seen: set[str] = set()
    deduped = []
    for r in results:
        if r.source not in seen:
            seen.add(r.source)
            deduped.append(r)
    return deduped


def _get_fts_keywords(state: FieldAssistantState) -> list[str]:
    """Get FTS keywords: crafted_query.fts_keywords with classify fallback."""
    crafted = state.get("crafted_query")
    if crafted and crafted.fts_keywords:
        return crafted.fts_keywords

    classify = state.get("classify_result")
    if classify and classify.keywords:
        return classify.keywords

    # Last resort: words from user message
    user_msg = state.get("user_message", "")
    return [w for w in user_msg.split() if len(w) >= 3][:5]


def _run_chroma_searches(
    query: str,
    collections: list[str],
    filters: dict,
    top_k: int = 5,
) -> list[SearchResult]:
    """Run ChromaDB embedding search across specified collections."""
    all_results = []
    for collection in collections:
        results = chroma_search(
            query=query,
            collection_name=collection,
            filters=filters or None,
            top_k=top_k,
        )
        all_results.extend(results)
    return all_results


def _run_fts_searches(
    keywords: list[str],
    tables: list[str],
    top_k: int = 5,
) -> list[SearchResult]:
    """Run FTS5 search across specified tables."""
    query = " ".join(keywords)
    all_results = []

    for table in tables:
        fts_table = FTS_TABLE_MAP.get(table)
        if fts_table:
            results = fts_search(query=query, table=fts_table, top_k=top_k)
            all_results.extend(results)

    return all_results


def _run_structured_searches(
    tables: list[str],
    filters: dict,
    top_k: int = 5,
) -> list[SearchResult]:
    """Run structured SQL queries on specified tables."""
    all_results = []

    # Build conditions from classify filters
    conditions = {}
    if filters.get("crop"):
        conditions["name"] = {"$like": f"%{filters['crop']}%"}

    for table in tables:
        table_conditions = dict(conditions)

        # Table-specific conditions
        if table == "treatments" and filters.get("disease_name"):
            # Find disease_id first, then filter treatments
            pass  # Let the query return all with limit — re-ranker filters

        results = structured_query(
            table=table,
            conditions=table_conditions if table_conditions else None,
            limit=top_k,
        )
        all_results.extend(results)

    return all_results


async def execute_searches(state: FieldAssistantState) -> dict:
    """Execute search tools in parallel based on the route.

    Runs ChromaDB, FTS5, and structured queries concurrently
    using asyncio.gather. Normalizes scores, deduplicates,
    and sorts results.

    Returns dict with: search_results, tool_calls_log updates.
    """
    route = state.get("route")
    crafted_query = state.get("crafted_query")
    existing_log = state.get("tool_calls_log", [])

    if route is None or not route.engines:
        log.log_step(Step.SEARCH, "execute_no_route", level="WARNING",
                     details={"reason": "No route or empty engines"})
        return {"search_results": [], "tool_calls_log": existing_log}

    embedding_query = ""
    if crafted_query and crafted_query.embedding_query:
        embedding_query = crafted_query.embedding_query
    elif state.get("user_message"):
        embedding_query = state["user_message"]

    fts_keywords = _get_fts_keywords(state)
    metadata_filters = route.metadata_filters or {}

    with log.timed(Step.SEARCH, "execute_searches") as t:
        # Build search coroutines
        tasks = []

        if SearchEngineType.CHROMA_EMBEDDING in route.engines and embedding_query:
            tasks.append(asyncio.to_thread(
                _run_chroma_searches,
                embedding_query,
                route.collections,
                metadata_filters,
            ))

        if SearchEngineType.SQLITE_FTS in route.engines and fts_keywords:
            # FTS uses tables that have FTS mirrors
            fts_tables = [t for t in route.tables if t in FTS_TABLE_MAP]
            if not fts_tables:
                # Default FTS tables based on collections
                fts_tables = ["diseases"]
            tasks.append(asyncio.to_thread(
                _run_fts_searches,
                fts_keywords,
                fts_tables,
            ))

        if SearchEngineType.SQLITE_STRUCTURED in route.engines:
            tasks.append(asyncio.to_thread(
                _run_structured_searches,
                route.tables,
                metadata_filters,
            ))

        # Execute all in parallel
        if tasks:
            results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results_lists = []

        # Flatten, skip exceptions
        all_results: list[SearchResult] = []
        for result_or_error in results_lists:
            if isinstance(result_or_error, Exception):
                log.log_step(Step.SEARCH, "search_engine_error", level="ERROR",
                             details={"error": str(result_or_error)})
            elif isinstance(result_or_error, list):
                all_results.extend(result_or_error)

        # Normalize BM25 scores
        all_results = _normalize_bm25_scores(all_results)

        # Deduplicate by source ID
        all_results = _deduplicate_results(all_results)

        # Sort by score descending
        all_results.sort(key=lambda r: r.score, reverse=True)

        # Build tool calls log entry
        engine_counts = {}
        for r in all_results:
            engine_counts[r.result_type.value] = engine_counts.get(r.result_type.value, 0) + 1

        t.set(details={
            "total_results": len(all_results),
            "engines_used": [e.value for e in route.engines],
            "engine_counts": engine_counts,
            "top_scores": [round(r.score, 3) for r in all_results[:5]],
        })

    # Update tool_calls_log
    new_log_entry = {
        "step": "search",
        "engines": [e.value for e in route.engines],
        "total_results": len(all_results),
        "engine_counts": engine_counts,
    }

    return {
        "search_results": all_results,
        "tool_calls_log": existing_log + [new_log_entry],
    }


def execute_searches_sync(state: FieldAssistantState) -> dict:
    """Synchronous wrapper for execute_searches.

    Use this when calling from synchronous code or tests.
    """
    return asyncio.run(execute_searches(state))
