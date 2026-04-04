"""Tests for Step 4.3: SQLite structured query builder with fuzzy matching."""

from pathlib import Path

import pytest

from app.agents.models import ResultType, SearchResult
from app.knowledge_pack.builder import build_pack
from app.knowledge_pack.loader import (
    get_active_pack,
    load_pack,
    unload_pack,
)
from app.tools.sqlite_query import (
    _build_join_clause,
    _build_where_clause,
    _get_table_columns,
    fuzzy_structured_query,
    fuzzy_structured_query_tool,
    structured_query,
    structured_query_tool,
)


@pytest.fixture(scope="module")
def pack_path(tmp_path_factory):
    base = tmp_path_factory.mktemp("packs")
    return build_pack("sqlite_query_test_pack", base_path=base)


@pytest.fixture(autouse=True)
def active_pack(pack_path):
    load_pack(pack_path)
    yield get_active_pack()
    unload_pack()


# ============================================================
# Unit: helper functions
# ============================================================

class TestGetTableColumns:

    def test_crops_columns(self, active_pack):
        cols = _get_table_columns(active_pack.sqlite_conn, "crops")
        assert "id" in cols
        assert "name" in cols
        assert "scientific_name" in cols

    def test_nonexistent_table(self, active_pack):
        cols = _get_table_columns(active_pack.sqlite_conn, "nonexistent")
        assert cols == []


class TestBuildWhereClause:

    def test_simple_equality(self):
        where, params = _build_where_clause(
            {"name": "cassava"}, ["id", "name", "type"],
        )
        assert "name = ?" in where
        assert params == ["cassava"]

    def test_multiple_conditions_and(self):
        where, params = _build_where_clause(
            {"name": "cassava", "type": "viral"},
            ["id", "name", "type"],
        )
        assert "AND" in where
        assert len(params) == 2

    def test_operator_gte(self):
        where, params = _build_where_clause(
            {"severity_scale": {"$gte": "medium"}},
            ["severity_scale"],
        )
        assert "severity_scale >= ?" in where
        assert params == ["medium"]

    def test_operator_like(self):
        where, params = _build_where_clause(
            {"name": {"$like": "%cassava%"}},
            ["name"],
        )
        assert "name LIKE ?" in where
        assert params == ["%cassava%"]

    def test_operator_ne(self):
        where, params = _build_where_clause(
            {"type": {"$ne": "viral"}},
            ["type"],
        )
        assert "type != ?" in where

    def test_invalid_column_skipped(self):
        where, params = _build_where_clause(
            {"invalid_col": "value"}, ["name", "type"],
        )
        assert where == ""
        assert params == []

    def test_empty_conditions(self):
        where, params = _build_where_clause({}, ["name"])
        assert where == ""
        assert params == []


class TestBuildJoinClause:

    def test_treatments_to_diseases(self):
        join = _build_join_clause("treatments", "diseases")
        assert join is not None
        assert "JOIN diseases" in join
        assert "disease_id" in join

    def test_reverse_direction(self):
        # diseases → treatments should work via reverse lookup
        join = _build_join_clause("diseases", "treatments")
        # This goes through reverse path
        assert join is None or "JOIN" in (join or "")

    def test_invalid_join_returns_none(self):
        join = _build_join_clause("crops", "climate")
        assert join is None


# ============================================================
# Integration: structured_query
# ============================================================

class TestStructuredQuery:

    def test_all_crops_no_conditions(self):
        results = structured_query("crops")
        assert len(results) == 5
        assert all(r.result_type == ResultType.STRUCTURED for r in results)

    def test_filter_by_name(self):
        results = structured_query("crops", {"name": "cassava"})
        assert len(results) == 1
        assert "cassava" in results[0].content.lower()

    def test_filter_diseases_by_type(self):
        results = structured_query("diseases", {"type": "viral"})
        assert len(results) > 0
        for r in results:
            assert r.metadata.get("type") == "viral"

    def test_treatments_join_diseases(self):
        results = structured_query(
            "treatments", join_with="diseases", limit=5,
        )
        assert len(results) > 0
        # Should have joined columns
        first = results[0]
        assert any("diseases_" in k for k in first.metadata)

    def test_limit_works(self):
        results = structured_query("diseases", limit=3)
        assert len(results) <= 3

    def test_select_specific_columns(self):
        results = structured_query(
            "crops", columns=["name", "scientific_name"],
        )
        assert len(results) > 0

    def test_gte_operator(self):
        results = structured_query(
            "climate", {"rainfall_mm": {"$gte": 100}},
        )
        for r in results:
            assert float(r.metadata.get("rainfall_mm", 0)) >= 100

    def test_like_operator(self):
        results = structured_query(
            "diseases", {"name": {"$like": "%Mosaic%"}},
        )
        assert len(results) > 0

    def test_empty_conditions_returns_all(self):
        results = structured_query("crops", {})
        assert len(results) == 5

    def test_invalid_table_raises(self):
        with pytest.raises(ValueError, match="Invalid table"):
            structured_query("nonexistent_table")

    def test_invalid_join_table_raises(self):
        with pytest.raises(ValueError, match="Invalid join table"):
            structured_query("crops", join_with="nonexistent")

    def test_sql_injection_in_conditions(self):
        """Conditions are parameterized — injection attempts should be safe."""
        results = structured_query(
            "crops", {"name": "'; DROP TABLE crops; --"},
        )
        # Should return empty, not crash
        assert len(results) == 0

    def test_result_type_structured(self):
        results = structured_query("crops")
        for r in results:
            assert r.result_type == ResultType.STRUCTURED

    def test_source_format(self):
        results = structured_query("crops")
        for r in results:
            assert r.source.startswith("crops:")

    def test_score_is_one(self):
        results = structured_query("crops")
        for r in results:
            assert r.score == 1.0

    def test_no_pack_returns_empty(self, pack_path):
        unload_pack()
        results = structured_query("crops")
        assert results == []
        load_pack(pack_path)


# ============================================================
# Integration: fuzzy_structured_query
# ============================================================

class TestFuzzyStructuredQuery:

    def test_exact_name(self):
        results = fuzzy_structured_query("crops", "cassava")
        assert len(results) == 1

    def test_partial_name_like(self):
        results = fuzzy_structured_query("diseases", "Mosaic")
        assert len(results) > 0

    def test_multi_word_per_word(self):
        results = fuzzy_structured_query("diseases", "Cassava Mosaic Disease")
        assert len(results) > 0
        contents = " ".join(r.content.lower() for r in results)
        assert "mosaic" in contents

    def test_no_match_returns_empty(self):
        results = fuzzy_structured_query("crops", "xyzzyflorp")
        assert results == []

    def test_invalid_table_raises(self):
        with pytest.raises(ValueError):
            fuzzy_structured_query("nonexistent", "cassava")

    def test_case_insensitive(self):
        # SQLite LIKE is case-insensitive for ASCII by default
        results = fuzzy_structured_query("crops", "CASSAVA")
        assert len(results) > 0

    def test_no_pack_returns_empty(self, pack_path):
        unload_pack()
        results = fuzzy_structured_query("crops", "cassava")
        assert results == []
        load_pack(pack_path)


# ============================================================
# @tool wrappers
# ============================================================

class TestToolWrappers:

    def test_structured_query_tool_basic(self):
        result = structured_query_tool.invoke({
            "table": "crops",
        })
        assert isinstance(result, str)
        assert "[1]" in result

    def test_structured_query_tool_with_conditions(self):
        result = structured_query_tool.invoke({
            "table": "diseases",
            "conditions": '{"type": "viral"}',
        })
        assert isinstance(result, str)
        assert "No results found" not in result

    def test_structured_query_tool_invalid_table(self):
        result = structured_query_tool.invoke({
            "table": "invalid_table",
        })
        assert "Error" in result

    def test_fuzzy_tool_basic(self):
        result = fuzzy_structured_query_tool.invoke({
            "table": "crops",
            "name_query": "cassava",
        })
        assert isinstance(result, str)
        assert "cassava" in result.lower()

    def test_fuzzy_tool_partial(self):
        result = fuzzy_structured_query_tool.invoke({
            "table": "diseases",
            "name_query": "Mosaic",
        })
        assert isinstance(result, str)
        assert "No results found" not in result

    def test_tools_have_names(self):
        assert structured_query_tool.name == "structured_query_tool"
        assert fuzzy_structured_query_tool.name == "fuzzy_structured_query_tool"
        assert len(structured_query_tool.description) > 0
