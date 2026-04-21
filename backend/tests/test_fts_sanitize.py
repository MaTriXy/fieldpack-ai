"""Unit tests for _sanitize_fts_query in fts_search.py.

Tests the length gate and stop-word filter logic in isolation,
no database or pack required.
"""

import pytest

from app.tools.fts_search import _sanitize_fts_query


class TestSanitizeFtsQuery:
    def test_single_char_token_drops(self):
        # "E" is 1 char after lowercasing; must be dropped
        result = _sanitize_fts_query("E coli")
        tokens = result.split(" OR ")
        # "e" (1 char) should be gone; "coli" should survive
        assert any("coli" in t for t in tokens), f"expected 'coli' in result: {result!r}"
        assert not any(t.strip() == "e*" for t in tokens), (
            f"single-char 'e' should be dropped, got: {result!r}"
        )

    def test_two_char_non_stop_word_survives(self):
        # "dr" is 2 chars and not a stop word -- must survive
        result = _sanitize_fts_query("DR pest")
        tokens = result.split(" OR ")
        assert any("dr" in t for t in tokens), f"expected 'dr' in result: {result!r}"
        assert any("pest" in t for t in tokens), f"expected 'pest' in result: {result!r}"

    def test_two_char_stop_words_drop(self):
        # "it", "is", "in" are 2-char stop words; only "pest" should survive
        result = _sanitize_fts_query("it is in pest")
        tokens = result.split(" OR ")
        surviving = [t.rstrip("*") for t in tokens]
        assert surviving == ["pest"], (
            f"expected only ['pest'], got: {surviving!r}"
        )

    def test_empty_after_filtering_returns_empty_string(self):
        # All tokens are single chars or 2-char stop words
        result = _sanitize_fts_query("I it is")
        assert result == "", f"expected empty string, got: {result!r}"

    def test_prefix_wildcard_appended(self):
        # Each surviving token must end with '*' for FTS5 prefix matching
        result = _sanitize_fts_query("DR pest")
        assert all(t.endswith("*") for t in result.split(" OR ")), (
            f"all tokens must end with '*': {result!r}"
        )
