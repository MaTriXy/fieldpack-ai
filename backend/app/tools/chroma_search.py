"""ChromaDB embedding search tool.

Searches child chunks by semantic similarity, resolves parent chunks
for full context. Supports single-collection and multi-collection search.

Score conversion: cosine distance → relevance = min(1.0, max(0.0, 1.0 - distance)).
Child→parent resolution: search hits children, LLM receives parents.
"""

import time

from langchain_core.tools import tool

from app.agents.models import ResultType, SearchResult
from app.knowledge_pack.loader import get_active_pack
from app.knowledge_pack.schema_chroma import CHROMA_COLLECTIONS
from app.logger import Step, pipeline_logger as log


def _distance_to_score(distance: float) -> float:
    """Convert ChromaDB cosine distance to relevance score [0, 1]."""
    return min(1.0, max(0.0, 1.0 - distance))


def _resolve_parents_batch(
    collection,
    child_ids: list[str],
    child_metadatas: list[dict],
) -> dict[str, tuple[str | None, str | None]]:
    """Batch-fetch parent documents for a list of child chunks.

    Returns a dict mapping topic_id -> (parent_id, parent_content).
    Falls back to per-item queries if batch fails.
    """
    # Collect unique topic_ids
    topic_ids = list({
        m.get("topic_id") for m in child_metadatas if m.get("topic_id")
    })

    if not topic_ids:
        return {}

    parent_map: dict[str, tuple[str | None, str | None]] = {}

    try:
        if len(topic_ids) == 1:
            where = {"$and": [
                {"topic_id": {"$eq": topic_ids[0]}},
                {"chunk_type": {"$eq": "parent"}},
            ]}
        else:
            where = {"$and": [
                {"topic_id": {"$in": topic_ids}},
                {"chunk_type": {"$eq": "parent"}},
            ]}

        parent_results = collection.get(
            where=where,
            include=["documents", "metadatas"],
        )
        if parent_results and parent_results["ids"]:
            for i, pid in enumerate(parent_results["ids"]):
                meta = parent_results["metadatas"][i] or {}
                tid = meta.get("topic_id")
                if tid:
                    parent_map[tid] = (pid, parent_results["documents"][i])
    except Exception as e:
        log.log_step(Step.SEARCH, "resolve_parents_batch_error", level="WARNING",
                     details={"topic_ids_count": len(topic_ids), "error": str(e)})

    return parent_map


def _resolve_parent(collection, child_id: str, child_metadata: dict) -> tuple[str | None, str | None]:
    """Fetch parent document for a single child chunk.

    Thin wrapper around _resolve_parents_batch for backward compat.
    """
    topic_id = child_metadata.get("topic_id")
    if not topic_id:
        return None, None
    parent_map = _resolve_parents_batch(collection, [child_id], [child_metadata])
    return parent_map.get(topic_id, (None, None))


def chroma_search(
    query: str,
    collection_name: str,
    filters: dict | None = None,
    top_k: int = 5,
) -> list[SearchResult]:
    """Search a ChromaDB collection by semantic similarity.

    Queries child chunks, resolves parent chunks for each hit.
    Returns SearchResult list sorted by relevance score (descending).

    Args:
        query: Natural language search query.
        collection_name: One of the 4 collection names.
        filters: Optional ChromaDB where-clause dict for metadata filtering.
        top_k: Maximum number of results to return.
    """
    pack = get_active_pack()
    if pack is None:
        log.log_step(Step.SEARCH, "search_chroma_no_pack", level="ERROR",
                     details={"error": "No active pack loaded"})
        return []

    if collection_name not in CHROMA_COLLECTIONS:
        log.log_step(Step.SEARCH, "search_chroma_invalid_collection", level="ERROR",
                     details={"collection": collection_name,
                              "valid": list(CHROMA_COLLECTIONS.keys())})
        return []

    if not query or not query.strip():
        return []

    with log.timed(Step.SEARCH, "search_chroma") as t:
        collection = pack.get_collection(collection_name)

        # Build where clause: always filter for child chunks + optional user filters
        where_clause: dict | None = None
        if filters:
            rejected = [k for k in filters if k.startswith("$")]
            if rejected:
                log.log_step(Step.SEARCH, "filter_keys_rejected",
                             level="WARNING", details={"keys": rejected})
            safe_filters = {k: v for k, v in filters.items() if not k.startswith("$")}
            where_clause = {"$and": [
                {"chunk_type": {"$eq": "child"}},
                *[{k: {"$eq": v}} for k, v in safe_filters.items()],
            ]}
        else:
            where_clause = {"chunk_type": {"$eq": "child"}}

        try:
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            log.log_step(Step.SEARCH, "search_chroma_query_error", level="ERROR",
                         details={"error": str(e), "collection": collection_name})
            t.set(details={"error": str(e), "collection": collection_name})
            return []

        search_results: list[SearchResult] = []

        if results and results["ids"] and results["ids"][0]:
            ids = results["ids"][0]
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]

            # Batch-resolve parents in one call
            parent_map = _resolve_parents_batch(collection, ids, metadatas)

            for i, doc_id in enumerate(ids):
                score = _distance_to_score(distances[i])
                metadata = metadatas[i] or {}

                # Look up parent from batch result
                topic_id = metadata.get("topic_id")
                parent_id, parent_content = parent_map.get(topic_id, (None, None)) if topic_id else (None, None)

                # Fallback: if parent missing, use child content as parent
                if parent_content is None:
                    parent_content = documents[i]
                    parent_id = doc_id

                search_results.append(SearchResult(
                    content=documents[i],
                    source=doc_id,
                    metadata=metadata,
                    score=score,
                    result_type=ResultType.CHROMA,
                    parent_id=parent_id,
                    parent_content=parent_content,
                ))

        # Sort by score descending
        search_results.sort(key=lambda r: r.score, reverse=True)

        top_scores = [r.score for r in search_results[:5]]
        t.set(details={
            "collection": collection_name,
            "query_preview": query[:200],
            "filters": filters or {},
            "results_count": len(search_results),
            "top_scores": [round(s, 3) for s in top_scores],
        })

    log.log_search(
        engine="chroma",
        query=query,
        collection_or_table=collection_name,
        results_count=len(search_results),
        top_scores=top_scores,
        filters=filters,
    )

    return search_results


def multi_collection_search(
    query: str,
    collections: list[str],
    filters: dict | None = None,
    top_k: int = 3,
) -> list[SearchResult]:
    """Search across multiple ChromaDB collections and merge results.

    Searches each collection with top_k, merges all results,
    deduplicates by source ID, and returns sorted by score.

    Args:
        query: Natural language search query.
        collections: List of collection names to search.
        filters: Optional metadata filters (applied to all collections).
        top_k: Results per collection.
    """
    if not query or not query.strip():
        return []

    with log.timed(Step.SEARCH, "multi_collection_search") as t:
        all_results: list[SearchResult] = []
        seen_sources: set[str] = set()
        per_collection: dict[str, int] = {c: 0 for c in collections}

        for collection_name in collections:
            results = chroma_search(
                query=query,
                collection_name=collection_name,
                filters=filters,
                top_k=top_k,
            )
            for r in results:
                if r.source not in seen_sources:
                    seen_sources.add(r.source)
                    all_results.append(r)
                    per_collection[collection_name] += 1

        all_results.sort(key=lambda r: r.score, reverse=True)

        t.set(details={
            "collections": collections,
            "query_preview": query[:200],
            "total_results": len(all_results),
            "per_collection": per_collection,
        })

    return all_results


# ============================================================
# @tool wrappers for LangGraph
# ============================================================

@tool
def chroma_search_tool(
    query: str,
    collection_name: str,
    filters: str = "",
    top_k: int = 5,
) -> str:
    """Search the knowledge base using semantic similarity.

    Searches the vector database for information matching the query.
    Use this when you need to find knowledge about diseases, treatments,
    farming practices, or regional context.

    Args:
        query: Natural language search query describing what you're looking for.
        collection_name: Which knowledge area to search. One of:
            disease_knowledge, treatment_guides, farming_practices, regional_context.
        filters: Optional JSON string of metadata filters, e.g. '{"crop": "cassava"}'.
        top_k: Maximum number of results to return (default 5).
    """
    import json as _json

    parsed_filters = None
    if filters and filters.strip():
        try:
            parsed_filters = _json.loads(filters)
        except _json.JSONDecodeError:
            pass

    results = chroma_search(query, collection_name, parsed_filters, top_k)

    if not results:
        return "No results found."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[{i}] (score: {r.score:.2f}) {r.parent_content or r.content}"
        )
    return "\n\n".join(parts)


@tool
def multi_collection_search_tool(
    query: str,
    collections: str = "disease_knowledge,treatment_guides",
    top_k: int = 3,
) -> str:
    """Search across multiple knowledge areas at once.

    Useful when a question spans diseases and treatments, or farming
    practices and regional context.

    Args:
        query: Natural language search query.
        collections: Comma-separated collection names to search.
        top_k: Results per collection (default 3).
    """
    collection_list = [c.strip() for c in collections.split(",") if c.strip()]
    results = multi_collection_search(query, collection_list, top_k=top_k)

    if not results:
        return "No results found."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[{i}] ({r.metadata.get('chunk_type', 'unknown')}, "
            f"score: {r.score:.2f}) {r.parent_content or r.content}"
        )
    return "\n\n".join(parts)
