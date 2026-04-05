"""SQLite FTS5 keyword search tool.

Full-text search with BM25 ranking, query sanitization,
and a 3-tier fuzzy matching cascade: exact → ED1 typo variants → LIKE fallback.

Query sanitization: strip non-alnum, skip words <3 chars,
build OR with prefix matching (word1* OR word2*), cap at 8 words.
"""

import re
import sqlite3
import string

from langchain_core.tools import tool

from app.agents.models import ResultType, SearchResult
from app.knowledge_pack.loader import get_active_pack
from app.knowledge_pack.schema_sqlite import FTS_TABLE_MAP, VALID_TABLES
from app.logger import Step, pipeline_logger as log


# FTS5 special characters that must be stripped from user input
_FTS5_SPECIAL = set('"*()+-^:{}~')

# Common stop words to skip in FTS queries
_STOP_WORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all",
    "can", "had", "her", "was", "one", "our", "out", "has",
    "its", "let", "may", "who", "how", "what", "when", "why",
    "this", "that", "with", "from", "have", "been", "will",
    "they", "them", "then", "than", "each", "make", "like",
    "into", "over", "such", "about", "some",
}

# Maximum number of words in an FTS query to prevent performance issues
_MAX_QUERY_WORDS = 8


def _sanitize_fts_query(query: str) -> str:
    """Sanitize a raw query string into a safe FTS5 MATCH expression.

    Steps:
      1. Strip FTS5 special characters
      2. Lowercase, tokenize on whitespace
      3. Remove words < 3 chars and stop words
      4. Keep top 8 words (longest first for best signal)
      5. Join with OR + prefix matching: word1* OR word2*

    Returns empty string if no valid tokens remain.
    """
    # Strip FTS5 special chars
    cleaned = "".join(c for c in query if c not in _FTS5_SPECIAL)
    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()

    if not cleaned:
        return ""

    # Tokenize, filter
    words = cleaned.split()
    words = [w for w in words if len(w) >= 3 and w not in _STOP_WORDS]

    if not words:
        return ""

    # Cap at max words, prioritizing longer words (more signal)
    if len(words) > _MAX_QUERY_WORDS:
        words.sort(key=len, reverse=True)
        words = words[:_MAX_QUERY_WORDS]

    # Build FTS5 MATCH with OR + prefix matching
    return " OR ".join(f"{w}*" for w in words)


def _generate_typo_variants(word: str) -> list[str]:
    """Generate edit-distance-1 variants of a word.

    Three operations:
      - Adjacent character swaps (transpositions)
      - Single character deletions
      - Single character insertions

    Returns deduplicated list excluding the original word.
    """
    if len(word) < 2:
        return []

    variants: set[str] = set()
    letters = string.ascii_lowercase

    # Swaps: swap adjacent characters
    for i in range(len(word) - 1):
        swapped = word[:i] + word[i + 1] + word[i] + word[i + 2:]
        variants.add(swapped)

    # Deletions: remove one character
    for i in range(len(word)):
        deleted = word[:i] + word[i + 1:]
        if len(deleted) >= 2:  # Don't generate 1-char words
            variants.add(deleted)

    # Insertions: add one character at each position
    for i in range(len(word) + 1):
        for c in letters:
            inserted = word[:i] + c + word[i:]
            variants.add(inserted)

    variants.discard(word)
    return sorted(variants)


def _get_base_table_for_fts(fts_table: str) -> str | None:
    """Get the base table name for an FTS5 virtual table."""
    for base, fts in FTS_TABLE_MAP.items():
        if fts == fts_table:
            return base
    return None


def _fts_match_query(
    conn: sqlite3.Connection,
    fts_table: str,
    match_expr: str,
    top_k: int,
) -> list[dict]:
    """Execute an FTS5 MATCH query with BM25 ranking.

    Returns list of dicts with all columns from the base table plus bm25 score.
    """
    base_table = _get_base_table_for_fts(fts_table)
    if not base_table:
        return []

    try:
        sql = (
            f"SELECT {base_table}.*, bm25({fts_table}) AS bm25_score "
            f"FROM {fts_table} "
            f"JOIN {base_table} ON {fts_table}.rowid = {base_table}.id "
            f"WHERE {fts_table} MATCH ? "
            f"ORDER BY bm25({fts_table}) "
            f"LIMIT ?"
        )
        cursor = conn.execute(sql, (match_expr, top_k))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []


def _like_fallback(
    conn: sqlite3.Connection,
    base_table: str,
    query_words: list[str],
    top_k: int,
) -> list[dict]:
    """LIKE fallback when FTS5 finds nothing.

    Searches all text columns of the base table using LIKE %word%.
    OR across words, AND would be too restrictive for a fallback.
    """
    if base_table not in VALID_TABLES:
        return []

    # Get text columns for the table
    try:
        cursor = conn.execute(f"PRAGMA table_info({base_table})")
        columns_info = cursor.fetchall()
    except sqlite3.OperationalError:
        return []

    text_cols = [col[1] for col in columns_info if col[2] in ("TEXT", "")]

    if not text_cols or not query_words:
        return []

    # Build WHERE: any word LIKE in any text column
    conditions = []
    params = []
    for word in query_words[:_MAX_QUERY_WORDS]:
        col_conditions = []
        escaped = word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        for col in text_cols:
            col_conditions.append(f'"{col}" LIKE ? ESCAPE \'\\\'')
            params.append(f"%{escaped}%")
        conditions.append(f"({' OR '.join(col_conditions)})")

    where = " OR ".join(conditions)
    try:
        sql = f"SELECT * FROM {base_table} WHERE {where} LIMIT ?"
        params.append(top_k)
        cursor = conn.execute(sql, params)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []


def _rows_to_search_results(rows: list[dict], source_table: str) -> list[SearchResult]:
    """Convert raw SQL rows to SearchResult objects."""
    results = []
    for row in rows:
        # Build content from the most informative text fields
        content_parts = []
        for key in [
            "name", "method", "description", "symptoms_text", "visual_markers",
            "planting_notes", "harvest_notes", "growing_season",
            "water_needs_mm_per_week", "region_suitability",
            "prevention_notes", "local_availability", "materials_needed",
            "application_timing", "damage_description", "identification_notes",
            "control_organic", "control_chemical", "common_names",
            "local_names", "disease_resistance", "seed_source_in_region",
        ]:
            if key in row and row[key]:
                content_parts.append(f"{key}: {row[key]}")

        content = " | ".join(content_parts) if content_parts else str(row)

        # BM25 scores are negative (more negative = better match)
        # Convert to positive score: we use abs and normalize loosely
        bm25 = row.get("bm25_score")
        score = abs(bm25) if bm25 is not None else 0.0

        metadata = {k: str(v) for k, v in row.items()
                    if k != "bm25_score" and v is not None}

        results.append(SearchResult(
            content=content,
            source=f"{source_table}:{row.get('id', '?')}",
            metadata=metadata,
            score=score,
            result_type=ResultType.FTS,
        ))

    return results


def fts_search(
    query: str,
    table: str = "diseases_fts",
    top_k: int = 5,
) -> list[SearchResult]:
    """Search an FTS5 virtual table using BM25 ranking.

    Sanitizes the query, executes FTS5 MATCH, joins with the base table
    for full row data, and returns SearchResult list.

    Args:
        query: Raw search query (will be sanitized).
        table: FTS5 table name (diseases_fts, treatments_fts, crops_fts).
        top_k: Maximum results.
    """
    pack = get_active_pack()
    if pack is None:
        log.log_step(Step.SEARCH, "search_fts_no_pack", level="ERROR",
                     details={"error": "No active pack loaded"})
        return []

    if table not in FTS_TABLE_MAP.values():
        log.log_step(Step.SEARCH, "search_fts_invalid_table", level="ERROR",
                     details={"table": table, "valid": list(FTS_TABLE_MAP.values())})
        return []

    match_expr = _sanitize_fts_query(query)
    if not match_expr:
        return []

    base_table = _get_base_table_for_fts(table)

    with log.timed(Step.SEARCH, "search_fts") as t:
        rows = _fts_match_query(pack.sqlite_conn, table, match_expr, top_k)
        results = _rows_to_search_results(rows, base_table or table)

        t.set(details={
            "fts_table": table,
            "base_table": base_table,
            "raw_query": query[:200],
            "sanitized_query": match_expr,
            "results_count": len(results),
            "top_scores": [round(r.score, 3) for r in results[:5]],
        })

    log.log_search(
        engine="fts",
        query=match_expr,
        collection_or_table=table,
        results_count=len(results),
        top_scores=[r.score for r in results[:5]],
    )

    return results


def fuzzy_fts_search(
    query: str,
    table: str = "diseases_fts",
    top_k: int = 5,
) -> list[SearchResult]:
    """FTS5 search with 3-tier fuzzy matching cascade.

    Tier 1: Exact FTS5 MATCH (sanitized query)
    Tier 2: ED1 typo variants per word → retry FTS5
    Tier 3: LIKE fallback on base table

    Args:
        query: Raw search query.
        table: FTS5 table name.
        top_k: Maximum results.
    """
    pack = get_active_pack()
    if pack is None:
        log.log_step(Step.SEARCH, "fuzzy_fts_no_pack", level="ERROR",
                     details={"error": "No active pack loaded"})
        return []

    if table not in FTS_TABLE_MAP.values():
        log.log_step(Step.SEARCH, "fuzzy_fts_invalid_table", level="ERROR",
                     details={"table": table, "valid": list(FTS_TABLE_MAP.values())})
        return []

    base_table = _get_base_table_for_fts(table)

    with log.timed(Step.SEARCH, "fuzzy_fts_search") as t:
        tier_used = "exact"

        # Tier 1: Exact FTS5 match
        results = fts_search(query, table, top_k)
        if results:
            t.set(details={
                "tier": "exact",
                "fts_table": table,
                "results_count": len(results),
            })
            return results

        # Tier 2: ED1 typo variants
        tier_used = "ed1"
        raw_query = re.sub(r"\s+", " ", query).strip().lower()
        words = [w for w in raw_query.split() if len(w) >= 3 and w not in _STOP_WORDS]

        for i, word in enumerate(words):
            variants = _generate_typo_variants(word)
            for variant in variants:
                # Replace word with variant and try
                trial_words = words.copy()
                trial_words[i] = variant
                trial_query = " ".join(trial_words)
                results = fts_search(trial_query, table, top_k)
                if results:
                    t.set(details={
                        "tier": "ed1",
                        "fts_table": table,
                        "original_word": word,
                        "matched_variant": variant,
                        "results_count": len(results),
                    })
                    return results

        # Tier 3: LIKE fallback
        tier_used = "like"
        if base_table:
            rows = _like_fallback(pack.sqlite_conn, base_table, words, top_k)
            results = _rows_to_search_results(rows, base_table)

        t.set(details={
            "tier": tier_used,
            "fts_table": table,
            "base_table": base_table,
            "results_count": len(results),
        })

    log.log_search(
        engine="fts_fuzzy",
        query=query,
        collection_or_table=table,
        results_count=len(results),
    )

    return results


# ============================================================
# @tool wrappers for LangGraph
# ============================================================

@tool
def fts_search_tool(
    query: str,
    table: str = "diseases_fts",
    top_k: int = 5,
) -> str:
    """Search by keywords using full-text search with BM25 ranking.

    Fast keyword-based search across disease descriptions, treatment info,
    crop details, pest information, or variety data. Good for finding specific terms or names.

    Args:
        query: Keywords to search for.
        table: Which data to search. One of: diseases_fts, treatments_fts, crops_fts, pests_fts, varieties_fts.
        top_k: Maximum results (default 5).
    """
    results = fts_search(query, table, top_k)
    if not results:
        return "No results found."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] (score: {r.score:.2f}) {r.content}")
    return "\n\n".join(parts)


@tool
def fuzzy_fts_search_tool(
    query: str,
    table: str = "diseases_fts",
    top_k: int = 5,
) -> str:
    """Search by keywords with typo tolerance.

    Like fts_search_tool but handles misspellings by trying typo variants
    and falling back to partial text matching if needed.

    Args:
        query: Keywords to search (typos OK).
        table: Which data to search. One of: diseases_fts, treatments_fts, crops_fts, pests_fts, varieties_fts.
        top_k: Maximum results (default 5).
    """
    results = fuzzy_fts_search(query, table, top_k)
    if not results:
        return "No results found."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] (score: {r.score:.2f}) {r.content}")
    return "\n\n".join(parts)
