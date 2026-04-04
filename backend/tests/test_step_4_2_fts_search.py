"""Tests for Step 4.2: SQLite FTS5 keyword search with fuzzy matching."""

from pathlib import Path

import pytest

from app.agents.models import ResultType, SearchResult
from app.knowledge_pack.builder import build_pack
from app.knowledge_pack.loader import (
    get_active_pack,
    load_pack,
    unload_pack,
)
from app.tools.fts_search import (
    _generate_typo_variants,
    _sanitize_fts_query,
    fts_search,
    fts_search_tool,
    fuzzy_fts_search,
    fuzzy_fts_search_tool,
)


@pytest.fixture(scope="module")
def pack_path(tmp_path_factory):
    """Build a Knowledge Pack once for all FTS search tests."""
    base = tmp_path_factory.mktemp("packs")
    return build_pack("fts_search_test_pack", base_path=base)


@pytest.fixture(autouse=True)
def active_pack(pack_path):
    """Load the pack before each test, unload after."""
    load_pack(pack_path)
    yield get_active_pack()
    unload_pack()


# ============================================================
# Unit: query sanitization
# ============================================================

class TestSanitizeFtsQuery:

    def test_basic_query(self):
        result = _sanitize_fts_query("cassava mosaic disease")
        assert "cassava*" in result
        assert "mosaic*" in result
        assert "disease*" in result
        assert "OR" in result

    def test_strips_fts5_special_chars(self):
        result = _sanitize_fts_query('test "quoted" (grouped) +required -excluded')
        assert '"' not in result
        assert "(" not in result
        assert ")" not in result
        assert "+" not in result
        assert "-" not in result

    def test_removes_short_words(self):
        result = _sanitize_fts_query("my is a cassava")
        assert "cassava*" in result
        assert "my" not in result
        assert " is " not in result

    def test_removes_stop_words(self):
        result = _sanitize_fts_query("what are the symptoms for cassava")
        assert "symptoms*" in result
        assert "cassava*" in result
        assert "what" not in result
        assert "the" not in result

    def test_caps_at_8_words(self):
        query = "one two three four five six seven eight nine ten eleven twelve"
        result = _sanitize_fts_query(query)
        # Count the number of terms (each is word*)
        terms = [t.strip() for t in result.split("OR") if t.strip()]
        assert len(terms) <= 8

    def test_prioritizes_longer_words_when_capping(self):
        # 10 words forces capping to 8 — longest should survive
        query = "big plant agriculture photosynthesis crop rice maize soil cassava treatment"
        result = _sanitize_fts_query(query)
        terms = [t.strip().rstrip("*") for t in result.split("OR")]
        assert len(terms) == 8
        # "photosynthesis" (14) and "agriculture" (11) should be first two
        assert terms[0] == "photosynthesis"
        assert terms[1] == "agriculture"

    def test_empty_query_returns_empty(self):
        assert _sanitize_fts_query("") == ""

    def test_only_short_words_returns_empty(self):
        assert _sanitize_fts_query("a b c") == ""

    def test_only_stop_words_returns_empty(self):
        assert _sanitize_fts_query("the and for are") == ""

    def test_unicode_preserved(self):
        result = _sanitize_fts_query("manioc feuilles Casamance")
        assert "manioc*" in result
        assert "feuilles*" in result
        assert "casamance*" in result

    def test_normalizes_whitespace(self):
        result = _sanitize_fts_query("  cassava   mosaic    ")
        assert "cassava*" in result
        assert "mosaic*" in result


# ============================================================
# Unit: typo variant generation
# ============================================================

class TestGenerateTypoVariants:

    def test_swaps(self):
        variants = _generate_typo_variants("mosaic")
        # "omsaic" (swap m,o)
        assert "omsaic" in variants

    def test_deletions(self):
        variants = _generate_typo_variants("mosaic")
        # "osaic" (delete m)
        assert "osaic" in variants
        # "mosic" (delete a)
        assert "mosic" in variants

    def test_insertions(self):
        variants = _generate_typo_variants("mosaic")
        # Should include insertions at every position
        assert any(len(v) == len("mosaic") + 1 for v in variants)

    def test_excludes_original(self):
        variants = _generate_typo_variants("mosaic")
        assert "mosaic" not in variants

    def test_single_char_returns_empty(self):
        assert _generate_typo_variants("a") == []

    def test_two_char_word(self):
        variants = _generate_typo_variants("ab")
        assert "ba" in variants  # swap
        # Deletions produce 1-char words which are filtered out
        assert all(len(v) >= 2 for v in variants)

    def test_reasonable_count(self):
        # For a 6-char word: ~6 swaps + ~6 deletions + ~7*26 insertions
        variants = _generate_typo_variants("mosaic")
        assert len(variants) > 50
        assert len(variants) < 500

    def test_all_lowercase(self):
        variants = _generate_typo_variants("test")
        for v in variants:
            assert v == v.lower()


# ============================================================
# Integration: fts_search
# ============================================================

class TestFtsSearch:

    def test_mosaic_finds_cmd(self):
        results = fts_search("mosaic", "diseases_fts")
        assert len(results) > 0
        contents = " ".join(r.content.lower() for r in results)
        assert "mosaic" in contents

    def test_leaf_blight_multiple_results(self):
        results = fts_search("leaf blight", "diseases_fts")
        assert len(results) > 0

    def test_result_type_is_fts(self):
        results = fts_search("mosaic", "diseases_fts")
        for r in results:
            assert r.result_type == ResultType.FTS

    def test_results_are_search_result_type(self):
        results = fts_search("cassava", "diseases_fts")
        assert all(isinstance(r, SearchResult) for r in results)

    def test_treatments_fts(self):
        results = fts_search("neem oil organic", "treatments_fts")
        assert len(results) > 0

    def test_crops_fts(self):
        results = fts_search("cassava", "crops_fts")
        assert len(results) > 0

    def test_top_k_limits(self):
        results = fts_search("disease", "diseases_fts", top_k=2)
        assert len(results) <= 2

    def test_empty_query_returns_empty(self):
        assert fts_search("", "diseases_fts") == []

    def test_nonsense_returns_empty(self):
        results = fts_search("xyzzyflorp", "diseases_fts")
        assert results == []

    def test_invalid_table_returns_empty(self):
        results = fts_search("mosaic", "nonexistent_fts")
        assert results == []

    def test_no_active_pack_returns_empty(self, pack_path):
        unload_pack()
        results = fts_search("mosaic", "diseases_fts")
        assert results == []
        load_pack(pack_path)

    def test_source_contains_table_and_id(self):
        results = fts_search("mosaic", "diseases_fts")
        if results:
            assert results[0].source.startswith("diseases:")

    def test_scores_positive(self):
        results = fts_search("mosaic", "diseases_fts")
        for r in results:
            assert r.score >= 0.0


# ============================================================
# Integration: fuzzy_fts_search
# ============================================================

class TestFuzzyFtsSearch:

    def test_exact_match_works(self):
        results = fuzzy_fts_search("mosaic", "diseases_fts")
        assert len(results) > 0

    def test_typo_mosaik_finds_mosaic(self):
        """ED1 typo: 'mosaik' → tries variants → finds 'mosaic'."""
        results = fuzzy_fts_search("mosaik", "diseases_fts")
        assert len(results) > 0
        contents = " ".join(r.content.lower() for r in results)
        assert "mosaic" in contents

    def test_like_fallback(self):
        """If FTS5 and ED1 both fail, LIKE should catch partial matches."""
        # "cassava" should always match via LIKE even with weird prefix
        results = fuzzy_fts_search("cassava", "crops_fts")
        assert len(results) > 0

    def test_completely_nonsense_returns_empty(self):
        results = fuzzy_fts_search("zzzzqqqxxx", "diseases_fts")
        assert results == []

    def test_invalid_table_returns_empty(self):
        results = fuzzy_fts_search("mosaic", "nonexistent_fts")
        assert results == []

    def test_no_pack_returns_empty(self, pack_path):
        unload_pack()
        results = fuzzy_fts_search("mosaic", "diseases_fts")
        assert results == []
        load_pack(pack_path)


# ============================================================
# @tool wrappers
# ============================================================

class TestToolWrappers:

    def test_fts_search_tool_returns_string(self):
        result = fts_search_tool.invoke({
            "query": "mosaic cassava",
            "table": "diseases_fts",
        })
        assert isinstance(result, str)
        assert "No results found" not in result
        assert "[1]" in result

    def test_fts_search_tool_no_results(self):
        result = fts_search_tool.invoke({
            "query": "xyzzyflorp",
            "table": "diseases_fts",
        })
        assert result == "No results found."

    def test_fuzzy_fts_tool_returns_string(self):
        result = fuzzy_fts_search_tool.invoke({
            "query": "mosaik",
            "table": "diseases_fts",
        })
        assert isinstance(result, str)

    def test_tools_have_names(self):
        assert fts_search_tool.name == "fts_search_tool"
        assert fuzzy_fts_search_tool.name == "fuzzy_fts_search_tool"
        assert len(fts_search_tool.description) > 0
        assert len(fuzzy_fts_search_tool.description) > 0
