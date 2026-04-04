"""SQLite structured query builder tool.

Builds parameterized SQL queries from Python condition dicts.
NO raw SQL from LLM — all queries are constructed programmatically
with an allowlist of tables, validated columns, and parameterized values.

Supports flat AND conditions with operators: =, $gt, $gte, $lt, $lte, $like, $ne.
Includes fuzzy name matching cascade: exact → LIKE → per-word LIKE.
"""

import sqlite3

from langchain_core.tools import tool

from app.agents.models import ResultType, SearchResult
from app.knowledge_pack.loader import get_active_pack
from app.knowledge_pack.schema_sqlite import TABLE_JOINS, VALID_TABLES
from app.logger import Step, pipeline_logger as log


# Operator mapping: condition dict operators → SQL
_OPERATORS = {
    "$gt": ">",
    "$gte": ">=",
    "$lt": "<",
    "$lte": "<=",
    "$like": "LIKE",
    "$ne": "!=",
}


def _get_table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """Get column names for a table via PRAGMA table_info."""
    try:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        return [row[1] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []


def _build_where_clause(
    conditions: dict,
    valid_columns: list[str],
) -> tuple[str, list]:
    """Build a WHERE clause from a flat conditions dict.

    Supports:
      - Simple equality: {"name": "cassava"} → name = ?
      - Operators: {"severity_scale": {"$gte": "medium"}} → severity_scale >= ?

    Returns (where_sql, params) tuple. Empty conditions = no WHERE clause.
    """
    if not conditions:
        return "", []

    clauses = []
    params = []

    for key, value in conditions.items():
        if isinstance(value, dict):
            # Operator condition: {"$gte": "medium"}
            for op_key, op_value in value.items():
                sql_op = _OPERATORS.get(op_key)
                if sql_op and key in valid_columns:
                    clauses.append(f"{key} {sql_op} ?")
                    params.append(op_value)
        else:
            # Simple equality
            if key in valid_columns:
                clauses.append(f"{key} = ?")
                params.append(value)

    if not clauses:
        return "", []

    return "WHERE " + " AND ".join(clauses), params


def _build_join_clause(base_table: str, join_with: str) -> str | None:
    """Build a JOIN clause using known FK paths.

    Returns the JOIN SQL string, or None if the join is not valid.
    """
    joins = TABLE_JOINS.get(base_table, {})
    join_info = joins.get(join_with)
    if join_info:
        return f"JOIN {join_with} ON {join_info['on']}"

    # Try reverse direction
    reverse_joins = TABLE_JOINS.get(join_with, {})
    reverse_info = reverse_joins.get(base_table)
    if reverse_info:
        return f"JOIN {join_with} ON {reverse_info['on']}"

    return None


def _rows_to_search_results(
    rows: list[dict],
    source_table: str,
) -> list[SearchResult]:
    """Convert raw SQL row dicts to SearchResult objects."""
    results = []
    for row in rows:
        # Build readable content from key fields
        content_parts = []
        for key in ["name", "method", "description", "symptoms_text",
                     "region", "type", "details"]:
            if key in row and row[key]:
                content_parts.append(f"{key}: {row[key]}")
        content = " | ".join(content_parts) if content_parts else str(row)

        metadata = {k: str(v) for k, v in row.items() if v is not None}

        results.append(SearchResult(
            content=content,
            source=f"{source_table}:{row.get('id', '?')}",
            metadata=metadata,
            score=1.0,  # Structured queries are exact matches
            result_type=ResultType.STRUCTURED,
        ))

    return results


def structured_query(
    table: str,
    conditions: dict | None = None,
    join_with: str | None = None,
    columns: list[str] | None = None,
    limit: int = 10,
) -> list[SearchResult]:
    """Execute a parameterized structured query against a Knowledge Pack table.

    All queries are built from Python condition dicts — NO raw SQL accepted.
    Tables are validated against VALID_TABLES allowlist. Columns are validated
    via PRAGMA table_info.

    Args:
        table: Base table name (must be in VALID_TABLES).
        conditions: Flat dict of conditions. Keys are column names.
            Simple: {"name": "cassava"}
            Operator: {"severity_scale": {"$gte": "medium"}}
        join_with: Optional table to JOIN with (validated against TABLE_JOINS).
        columns: Optional list of columns to SELECT. None = all columns.
        limit: Max rows returned (default 10).
    """
    pack = get_active_pack()
    if pack is None:
        log.log_step(Step.SEARCH, "structured_query_no_pack", level="ERROR",
                     details={"error": "No active pack loaded"})
        return []

    if table not in VALID_TABLES:
        log.log_step(Step.SEARCH, "structured_query_invalid_table", level="ERROR",
                     details={"table": table, "valid": VALID_TABLES})
        raise ValueError(f"Invalid table: {table}. Must be one of: {VALID_TABLES}")

    conn = pack.sqlite_conn

    with log.timed(Step.SEARCH, "search_structured") as t:
        # Validate columns
        valid_columns = _get_table_columns(conn, table)
        if not valid_columns:
            t.set(details={"error": f"Could not read columns for {table}"})
            return []

        # Build SELECT columns
        if columns:
            select_cols = [c for c in columns if c in valid_columns]
            if not select_cols:
                select_cols = valid_columns
            select_clause = ", ".join(f"{table}.{c}" for c in select_cols)
        else:
            select_clause = f"{table}.*"

        # Build JOIN
        join_clause = ""
        if join_with:
            if join_with not in VALID_TABLES:
                raise ValueError(f"Invalid join table: {join_with}. Must be one of: {VALID_TABLES}")
            jc = _build_join_clause(table, join_with)
            if jc:
                join_clause = jc
                # Add joined table columns to SELECT
                join_columns = _get_table_columns(conn, join_with)
                if join_columns:
                    join_cols_sql = ", ".join(f"{join_with}.{c} AS {join_with}_{c}"
                                             for c in join_columns)
                    select_clause += f", {join_cols_sql}"

        # Build WHERE
        where_clause, params = _build_where_clause(conditions or {}, valid_columns)

        # Assemble query
        sql = f"SELECT {select_clause} FROM {table}"
        if join_clause:
            sql += f" {join_clause}"
        if where_clause:
            sql += f" {where_clause}"
        sql += " LIMIT ?"
        params.append(limit)

        try:
            cursor = conn.execute(sql, params)
            col_names = [desc[0] for desc in cursor.description]
            rows = [dict(zip(col_names, row)) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            log.log_step(Step.SEARCH, "structured_query_error", level="ERROR",
                         details={"error": str(e), "sql_preview": sql[:200]})
            rows = []

        results = _rows_to_search_results(rows, table)

        t.set(details={
            "table": table,
            "conditions": conditions or {},
            "join_with": join_with,
            "columns": columns,
            "results_count": len(results),
            "sql_preview": sql[:200],
        })

    log.log_search(
        engine="structured",
        query=str(conditions or {}),
        collection_or_table=table,
        results_count=len(results),
    )

    return results


def fuzzy_structured_query(
    table: str,
    name_query: str,
    name_column: str = "name",
    limit: int = 10,
) -> list[SearchResult]:
    """Structured query with 3-tier fuzzy name matching.

    Tier 1: Exact match (name = query)
    Tier 2: LIKE %query% (contains)
    Tier 3: Per-word LIKE (each word in query matched separately)

    Args:
        table: Table to search.
        name_query: Name or partial name to search for.
        name_column: Column to match against (default "name").
        limit: Max results.
    """
    pack = get_active_pack()
    if pack is None:
        log.log_step(Step.SEARCH, "fuzzy_query_no_pack", level="ERROR",
                     details={"error": "No active pack loaded"})
        return []

    if table not in VALID_TABLES:
        raise ValueError(f"Invalid table: {table}. Must be one of: {VALID_TABLES}")

    with log.timed(Step.SEARCH, "fuzzy_structured_query") as t:
        # Tier 1: Exact match
        results = structured_query(table, {name_column: name_query}, limit=limit)
        if results:
            t.set(details={"tier": "exact", "table": table, "results_count": len(results)})
            return results

        # Tier 2: LIKE %query%
        results = structured_query(
            table,
            {name_column: {"$like": f"%{name_query}%"}},
            limit=limit,
        )
        if results:
            t.set(details={"tier": "like", "table": table, "results_count": len(results)})
            return results

        # Tier 3: Per-word LIKE
        words = name_query.strip().split()
        if len(words) > 1:
            for word in words:
                if len(word) >= 3:
                    results = structured_query(
                        table,
                        {name_column: {"$like": f"%{word}%"}},
                        limit=limit,
                    )
                    if results:
                        t.set(details={
                            "tier": "per_word",
                            "table": table,
                            "matched_word": word,
                            "results_count": len(results),
                        })
                        return results

        t.set(details={"tier": "none", "table": table, "results_count": 0})
        return []


# ============================================================
# @tool wrappers for LangGraph
# ============================================================

@tool
def structured_query_tool(
    table: str,
    conditions: str = "",
    join_with: str = "",
    limit: int = 10,
) -> str:
    """Query the structured database for exact data lookups.

    Use this for precise information: specific crops, disease details,
    treatment materials, climate data. Returns tabular data.

    Args:
        table: Table to query. One of: crops, diseases, treatments, climate,
            crop_diseases, image_refs, field_observations.
        conditions: JSON string of filter conditions.
            Simple: '{"name": "cassava"}'
            Operator: '{"severity_scale": {"$gte": "medium"}}'
        join_with: Optional table to JOIN (e.g., "diseases" when querying treatments).
        limit: Max rows (default 10).
    """
    import json as _json

    parsed_conditions = None
    if conditions and conditions.strip():
        try:
            parsed_conditions = _json.loads(conditions)
        except _json.JSONDecodeError:
            pass

    jw = join_with if join_with and join_with.strip() else None

    try:
        results = structured_query(table, parsed_conditions, jw, limit=limit)
    except ValueError as e:
        return f"Error: {e}"

    if not results:
        return "No results found."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] {r.content}")
    return "\n\n".join(parts)


@tool
def fuzzy_structured_query_tool(
    table: str,
    name_query: str,
    name_column: str = "name",
    limit: int = 10,
) -> str:
    """Search the database by name with fuzzy matching.

    Handles exact names, partial names, and multi-word searches.
    Good for finding entities when you're not sure of the exact spelling.

    Args:
        table: Table to search. One of: crops, diseases, treatments, climate.
        name_query: Name or partial name to find.
        name_column: Column to search in (default "name").
        limit: Max results (default 10).
    """
    try:
        results = fuzzy_structured_query(table, name_query, name_column, limit)
    except ValueError as e:
        return f"Error: {e}"

    if not results:
        return "No results found."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] {r.content}")
    return "\n\n".join(parts)
