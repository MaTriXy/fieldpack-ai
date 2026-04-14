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
    """Deduplicate results by source ID. Keep highest score on collision."""
    best: dict[str, SearchResult] = {}
    for r in results:
        existing = best.get(r.source)
        if existing is None or r.score > existing.score:
            best[r.source] = r
    return list(best.values())


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


# Tables that use crop_id FK instead of a name column for crop filtering
_CROP_ID_TABLES = {
    "pests", "varieties", "fertilization_schedule", "planting_calendar",
    "storage_guidelines", "soil_requirements", "field_observations",
    "image_refs", "crop_diseases",
}


def _resolve_crop_id(crop_name: str) -> int | None:
    """Look up crop_id from crop name. Returns None if not found."""
    from app.knowledge_pack.loader import get_active_pack

    pack = get_active_pack()
    if pack is None:
        return None
    cursor = pack.sqlite_conn.execute(
        "SELECT id FROM crops WHERE LOWER(name) = LOWER(?) LIMIT 1",
        (crop_name,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _run_structured_searches(
    tables: list[str],
    filters: dict,
    top_k: int = 5,
) -> list[SearchResult]:
    """Run structured SQL queries on specified tables."""
    all_results = []

    crop_name = filters.get("crop")
    crop_id = _resolve_crop_id(crop_name) if crop_name else None

    for table in tables:
        conditions = {}

        # Use crop_id FK for tables that have it, name LIKE for crops table
        if crop_name:
            if table in _CROP_ID_TABLES and crop_id is not None:
                conditions["crop_id"] = crop_id
            elif table not in _CROP_ID_TABLES:
                conditions["name"] = {"$like": f"%{crop_name}%"}

        results = structured_query(
            table=table,
            conditions=conditions if conditions else None,
            limit=top_k,
        )
        all_results.extend(results)

    return all_results


def _collect_embedding_queries(state: FieldAssistantState) -> list[str]:
    """Collect all embedding queries from crafted_queries or single crafted_query."""
    queries = []

    # Prefer multi-query list (retry path)
    crafted_queries = state.get("crafted_queries", [])
    if crafted_queries:
        for cq in crafted_queries:
            if cq.embedding_query:
                queries.append(cq.embedding_query)

    # Fall back to single query
    if not queries:
        crafted_query = state.get("crafted_query")
        if crafted_query and crafted_query.embedding_query:
            queries.append(crafted_query.embedding_query)

    # Last resort: user message
    if not queries and state.get("user_message"):
        queries.append(state["user_message"])

    return queries


def _collect_fts_keywords(state: FieldAssistantState) -> list[str]:
    """Collect FTS keywords from all crafted queries, deduplicated."""
    keywords: list[str] = []
    seen: set[str] = set()

    crafted_queries = state.get("crafted_queries", [])
    if crafted_queries:
        for cq in crafted_queries:
            for kw in cq.fts_keywords:
                if kw.lower() not in seen:
                    seen.add(kw.lower())
                    keywords.append(kw)

    if not keywords:
        keywords = _get_fts_keywords(state)

    return keywords


async def execute_searches(state: FieldAssistantState) -> dict:
    """Execute search tools in parallel based on the route.

    Supports multiple crafted queries (retry variants). Runs all
    queries across all engines concurrently, deduplicates with
    highest-score-wins, normalizes BM25 scores, and sorts.

    Returns dict with: search_results, tool_calls_log updates.
    """
    route = state.get("route")
    existing_log = state.get("tool_calls_log", [])

    if route is None or not route.engines:
        log.log_step(Step.SEARCH, "execute_no_route", level="WARNING",
                     details={"reason": "No route or empty engines"})
        return {"search_results": [], "tool_calls_log": existing_log}

    embedding_queries = _collect_embedding_queries(state)
    fts_keywords = _collect_fts_keywords(state)
    metadata_filters = route.metadata_filters or {}

    # Build crop filter for ChromaDB, but also search WITHOUT it.
    # Chunks tagged crop="general" or missing crop field (regional_context)
    # would be silently dropped by a strict crop filter — but they often
    # contain the most relevant content (planting calendars, regional info).
    # We search both ways and let the reranker sort by relevance.
    crop_filter = metadata_filters.get("crop")
    chroma_filters_with_crop = {"crop": crop_filter} if crop_filter is not None else {}

    log.log_step(Step.SEARCH, "execute_start", details={
        "query_count": len(embedding_queries),
        "fts_keyword_count": len(fts_keywords),
        "engines": [e.value for e in route.engines],
    })

    with log.timed(Step.SEARCH, "execute_searches") as t:
        tasks = []
        task_labels = []

        # ChromaDB: search with crop filter AND without, merge results.
        # Filtered search boosts precision; unfiltered catches general chunks.
        if SearchEngineType.CHROMA_EMBEDDING in route.engines:
            for eq in embedding_queries:
                if chroma_filters_with_crop:
                    # Filtered search (crop-specific chunks)
                    tasks.append(asyncio.to_thread(
                        _run_chroma_searches,
                        eq,
                        route.collections,
                        chroma_filters_with_crop,
                    ))
                    task_labels.append(f"chroma_filtered:{','.join(route.collections)}")
                # Unfiltered search (general + cross-crop chunks)
                tasks.append(asyncio.to_thread(
                    _run_chroma_searches,
                    eq,
                    route.collections,
                    {},
                ))
                task_labels.append(f"chroma:{','.join(route.collections)}")

        # FTS: combined keywords, single search
        if SearchEngineType.SQLITE_FTS in route.engines and fts_keywords:
            fts_tables = [tb for tb in route.tables if tb in FTS_TABLE_MAP]
            if fts_tables:
                tasks.append(asyncio.to_thread(
                    _run_fts_searches,
                    fts_keywords,
                    fts_tables,
                ))
                task_labels.append(f"fts:{','.join(fts_tables)}")
            else:
                log.log_step(Step.SEARCH, "fts_skipped", level="WARNING",
                             details={"reason": "no FTS-capable tables in route",
                                      "route_tables": route.tables})

        # Structured: unchanged
        if SearchEngineType.SQLITE_STRUCTURED in route.engines:
            tasks.append(asyncio.to_thread(
                _run_structured_searches,
                route.tables,
                metadata_filters,
            ))
            task_labels.append(f"structured:{','.join(route.tables)}")

        if tasks:
            results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results_lists = []

        all_results: list[SearchResult] = []
        for i, result_or_error in enumerate(results_lists):
            if isinstance(result_or_error, Exception):
                label = task_labels[i] if i < len(task_labels) else "unknown"
                log.log_step(Step.SEARCH, "search_engine_error", level="ERROR",
                             details={"engine": label, "error": str(result_or_error)})
            elif isinstance(result_or_error, list):
                all_results.extend(result_or_error)

        all_results = _normalize_bm25_scores(all_results)
        all_results = _deduplicate_results(all_results)
        all_results.sort(key=lambda r: r.score, reverse=True)

        engine_counts = {}
        for r in all_results:
            engine_counts[r.result_type.value] = engine_counts.get(r.result_type.value, 0) + 1

        t.set(details={
            "total_results": len(all_results),
            "query_count": len(embedding_queries),
            "engines_used": [e.value for e in route.engines],
            "engine_counts": engine_counts,
            "top_scores": [round(r.score, 3) for r in all_results[:5]],
        })

    new_log_entry = {
        "step": "search",
        "engines": [e.value for e in route.engines],
        "query_count": len(embedding_queries),
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
    Note: blocks the calling thread. Do NOT call from async contexts
    (FastAPI routes, etc.) — use the async execute_searches directly.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, execute_searches(state))
            return future.result()
    return asyncio.run(execute_searches(state))
