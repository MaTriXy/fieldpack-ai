"""Tests for the centralized PipelineLogger."""

import json
import time
from pathlib import Path

import pytest

from app.logger import PipelineLogger, Step, TimedContext, _format_console, _make_entry


@pytest.fixture
def logger(tmp_path):
    """Create a logger with file output for testing."""
    return PipelineLogger(
        log_dir=tmp_path / "logs",
        level="DEBUG",
        buffer_size=50,
    )


@pytest.fixture
def memory_logger():
    """Create a logger without file output (buffer only)."""
    return PipelineLogger(log_dir=None, level="DEBUG", buffer_size=50)


# ============================================================
# Core logging
# ============================================================

class TestLogStep:

    def test_basic_log(self, logger):
        logger.log_step(Step.CLASSIFY, "start")
        entries = logger.get_buffer()
        assert len(entries) == 1
        assert entries[0]["step"] == "classify"
        assert entries[0]["event"] == "start"
        assert "timestamp" in entries[0]

    def test_log_with_all_fields(self, logger):
        logger.log_step(
            step=Step.CLASSIFY,
            event="llm_call",
            level="INFO",
            duration_ms=3200.5,
            tokens_in=450,
            tokens_out=120,
            details={"intent": "diagnose_disease", "confidence": 0.85},
            user_message="my cassava has brown spots",
        )
        entry = logger.get_buffer()[0]
        assert entry["duration_ms"] == 3200.5
        assert entry["tokens_in"] == 450
        assert entry["tokens_out"] == 120
        assert entry["details"]["intent"] == "diagnose_disease"
        assert entry["user_message"] == "my cassava has brown spots"

    def test_optional_fields_omitted_when_none(self, logger):
        logger.log_step(Step.ROUTE, "route_decision")
        entry = logger.get_buffer()[0]
        assert "duration_ms" not in entry
        assert "tokens_in" not in entry
        assert "tokens_out" not in entry
        assert "details" not in entry

    def test_token_tracking(self, logger):
        logger.log_step(Step.CLASSIFY, "llm_call", tokens_in=100, tokens_out=50)
        logger.log_step(Step.GENERATE, "llm_call", tokens_in=200, tokens_out=150)
        assert logger.stats["total_tokens_in"] == 300
        assert logger.stats["total_tokens_out"] == 200


# ============================================================
# Convenience methods
# ============================================================

class TestConvenienceMethods:

    def test_log_llm_call(self, logger):
        logger.log_llm_call(
            step=Step.CLASSIFY,
            prompt="Classify this: my cassava is sick",
            response='{"intent": "diagnose_disease"}',
            duration_ms=3200,
            tokens_in=50,
            tokens_out=20,
        )
        entry = logger.get_buffer()[0]
        assert entry["event"] == "llm_call"
        assert entry["details"]["llm_call_number"] == 1
        assert "prompt_preview" in entry["details"]
        assert "response_preview" in entry["details"]

    def test_log_llm_call_truncates_long_prompt(self, logger):
        long_prompt = "x" * 500
        logger.log_llm_call(
            step=Step.CLASSIFY,
            prompt=long_prompt,
            response="short",
            duration_ms=1000,
        )
        entry = logger.get_buffer()[0]
        assert len(entry["details"]["prompt_preview"]) == 303  # 300 + "..."
        assert entry["details"]["prompt_length"] == 500

    def test_log_llm_call_tracks_count(self, logger):
        for i in range(3):
            logger.log_llm_call(Step.CLASSIFY, "p", "r", 100)
        assert logger.stats["total_llm_calls"] == 3

    def test_log_search(self, logger):
        logger.log_search(
            engine="chroma",
            query="cassava mosaic symptoms",
            collection_or_table="disease_knowledge",
            results_count=3,
            top_scores=[0.92, 0.85, 0.71],
            filters={"crop": "cassava"},
            duration_ms=150,
        )
        entry = logger.get_buffer()[0]
        assert entry["event"] == "search_chroma"
        assert entry["details"]["results_count"] == 3
        assert entry["details"]["top_scores"] == [0.92, 0.85, 0.71]

    def test_log_route(self, logger):
        logger.log_route(
            intent="diagnose_disease",
            engines=["chroma_embedding", "sqlite_fts"],
            collections=["disease_knowledge"],
            tables=["diseases"],
            filters={"crop": "cassava"},
        )
        entry = logger.get_buffer()[0]
        assert entry["details"]["intent"] == "diagnose_disease"
        assert "chroma_embedding" in entry["details"]["engines"]

    def test_log_rerank(self, logger):
        logger.log_rerank(
            total_input=5,
            total_kept=3,
            is_sufficient=True,
            top_scores=[0.95, 0.82, 0.71],
            duration_ms=2800,
            tokens_in=400,
            tokens_out=80,
        )
        entry = logger.get_buffer()[0]
        assert entry["details"]["input_results"] == 5
        assert entry["details"]["kept_results"] == 3
        assert entry["details"]["filtered_out"] == 2
        assert entry["details"]["is_sufficient"] is True


# ============================================================
# Pipeline lifecycle
# ============================================================

class TestPipelineLifecycle:

    def test_pipeline_start_end(self, logger):
        logger.pipeline_start("my cassava has spots", session_id="sess-001")
        time.sleep(0.01)  # Tiny delay to ensure measurable duration
        logger.pipeline_end(success=True)

        entries = logger.get_buffer()
        assert entries[0]["event"] == "pipeline_start"
        assert entries[0]["user_message"] == "my cassava has spots"
        assert entries[1]["event"] == "pipeline_end"
        assert entries[1]["details"]["success"] is True
        assert entries[1]["duration_ms"] > 0

    def test_pipeline_end_with_error(self, logger):
        logger.pipeline_start("test")
        logger.pipeline_end(success=False, error="Ollama connection failed")
        entry = logger.get_buffer()[-1]
        assert entry["level"] == "ERROR"
        assert entry["details"]["error"] == "Ollama connection failed"

    def test_session_id_propagated(self, logger):
        logger.pipeline_start("test", session_id="sess-123")
        logger.log_step(Step.CLASSIFY, "start")
        logger.log_step(Step.ROUTE, "done")

        for entry in logger.get_buffer():
            assert entry.get("session_id") == "sess-123"

    def test_stats_reset_on_new_pipeline(self, logger):
        logger.pipeline_start("first query")
        logger.log_step(Step.CLASSIFY, "llm", tokens_in=100, tokens_out=50)
        logger.pipeline_end()

        logger.pipeline_start("second query")
        assert logger.stats["total_tokens_in"] == 0
        assert logger.stats["total_llm_calls"] == 0


# ============================================================
# Timer context manager
# ============================================================

class TestTimedContext:

    def test_basic_timing(self, logger):
        with logger.timed(Step.CLASSIFY, "llm_call") as t:
            time.sleep(0.02)
            t.set(tokens_in=100, tokens_out=50)

        entry = logger.get_buffer()[0]
        assert entry["duration_ms"] >= 15  # At least ~20ms
        assert entry["tokens_in"] == 100
        assert entry["tokens_out"] == 50

    def test_timed_with_details(self, logger):
        with logger.timed(Step.SEARCH, "search_chroma") as t:
            t.set(details={"results_count": 3, "collection": "disease_knowledge"})

        entry = logger.get_buffer()[0]
        assert entry["details"]["results_count"] == 3

    def test_timed_on_exception(self, logger):
        with pytest.raises(ValueError):
            with logger.timed(Step.CLASSIFY, "llm_call") as t:
                raise ValueError("parse error")

        entry = logger.get_buffer()[0]
        assert entry["level"] == "ERROR"
        assert "parse error" in entry["details"]["error"]

    def test_timed_accumulates_details(self, logger):
        with logger.timed(Step.SEARCH, "search") as t:
            t.set(details={"phase": "query"})
            t.set(details={"results": 5})

        entry = logger.get_buffer()[0]
        assert entry["details"]["phase"] == "query"
        assert entry["details"]["results"] == 5


# ============================================================
# Buffer and API access
# ============================================================

class TestBufferAccess:

    def test_buffer_limit(self):
        logger = PipelineLogger(log_dir=None, level="DEBUG", buffer_size=5)
        for i in range(10):
            logger.log_step(Step.SYSTEM, f"event_{i}")
        entries = logger.get_buffer()
        assert len(entries) == 5
        assert entries[0]["event"] == "event_5"  # Oldest kept

    def test_get_buffer_last_n(self, logger):
        for i in range(10):
            logger.log_step(Step.SYSTEM, f"event_{i}")
        last3 = logger.get_buffer(last_n=3)
        assert len(last3) == 3
        assert last3[0]["event"] == "event_7"

    def test_get_session_entries(self, logger):
        logger.log_step(Step.SYSTEM, "no_session")
        logger.pipeline_start("test", session_id="sess-1")
        logger.log_step(Step.CLASSIFY, "classify")
        logger.log_step(Step.ROUTE, "route")

        session = logger.get_session_entries()
        # Should include pipeline_start + classify + route (all have sess-1)
        assert all(e.get("session_id") == "sess-1" for e in session)
        assert len(session) == 3

    def test_clear_buffer(self, logger):
        logger.log_step(Step.SYSTEM, "test")
        logger.clear_buffer()
        assert len(logger.get_buffer()) == 0


# ============================================================
# User-facing tool_calls_log
# ============================================================

class TestToolCallsLog:

    def test_produces_user_friendly_events(self, logger):
        logger.pipeline_start("test", session_id="s1")
        logger.log_llm_call(Step.CLASSIFY, "prompt", '{"intent":"diagnose"}',
                            3000, tokens_in=100, tokens_out=50)
        logger.log_route("diagnose_disease", ["chroma"], ["disease_knowledge"], [])
        logger.log_search("chroma", "query", "disease_knowledge", 3,
                          [0.9, 0.8], duration_ms=200)
        logger.log_rerank(3, 2, True, [0.9, 0.8], 2000, 200, 50)
        logger.log_llm_call(Step.GENERATE, "prompt", "answer", 3000,
                            tokens_in=300, tokens_out=200)
        logger.pipeline_end()

        events = logger.to_tool_calls_log()
        labels = [e["label"] for e in events]

        assert "Starting analysis..." in labels
        assert "Understanding your question..." in labels
        assert "Planning search strategy..." in labels
        assert "Searching knowledge base..." in labels
        assert "Evaluating relevance..." in labels
        assert "Generating answer..." in labels
        assert "Done!" in labels

    def test_tool_calls_log_has_durations(self, logger):
        logger.pipeline_start("test", session_id="s1")
        logger.log_llm_call(Step.CLASSIFY, "p", "r", 3000, 100, 50)

        events = logger.to_tool_calls_log()
        llm_event = [e for e in events if e["label"] == "Understanding your question..."]
        assert len(llm_event) == 1
        assert llm_event[0]["duration_ms"] == 3000

    def test_tool_calls_log_has_detail(self, logger):
        logger.pipeline_start("test", session_id="s1")
        logger.log_rerank(5, 3, True, duration_ms=2000)

        events = logger.to_tool_calls_log()
        rerank = [e for e in events if "Evaluating" in e["label"]]
        assert rerank[0]["detail"] == "Selected 3 most relevant results"

    def test_empty_session_returns_empty(self, memory_logger):
        events = memory_logger.to_tool_calls_log()
        assert events == []


# ============================================================
# File output
# ============================================================

class TestFileOutput:

    def test_writes_jsonl_file(self, tmp_path):
        logger = PipelineLogger(log_dir=tmp_path / "logs", level="DEBUG")
        logger.log_step(Step.SYSTEM, "test_event")
        logger.log_step(Step.CLASSIFY, "another_event")

        log_file = tmp_path / "logs" / "pipeline.jsonl"
        assert log_file.exists()

        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

        # Each line is valid JSON
        for line in lines:
            entry = json.loads(line)
            assert "timestamp" in entry
            assert "step" in entry

    def test_log_dir_created_automatically(self, tmp_path):
        log_dir = tmp_path / "nested" / "deep" / "logs"
        PipelineLogger(log_dir=log_dir, level="DEBUG")
        assert log_dir.exists()


# ============================================================
# Console formatting
# ============================================================

class TestConsoleFormatting:

    def test_format_basic(self):
        entry = _make_entry(Step.CLASSIFY, "start")
        formatted = _format_console(entry)
        assert "CLASSIFY" in formatted
        assert "start" in formatted

    def test_format_with_duration_seconds(self):
        entry = _make_entry(Step.CLASSIFY, "llm_call", duration_ms=3200)
        formatted = _format_console(entry)
        assert "3.2s" in formatted

    def test_format_with_duration_milliseconds(self):
        entry = _make_entry(Step.SEARCH, "search_chroma", duration_ms=150)
        formatted = _format_console(entry)
        assert "150ms" in formatted

    def test_format_with_tokens(self):
        entry = _make_entry(Step.CLASSIFY, "llm", tokens_in=100, tokens_out=50)
        formatted = _format_console(entry)
        assert "100→50 tok" in formatted

    def test_format_truncates_long_values(self):
        entry = _make_entry(
            Step.CLASSIFY, "test",
            details={"long_field": "x" * 100},
        )
        formatted = _format_console(entry)
        assert "100 chars" in formatted

    def test_format_summarizes_large_lists(self):
        entry = _make_entry(
            Step.SEARCH, "test",
            details={"results": list(range(20))},
        )
        formatted = _format_console(entry)
        assert "20 items" in formatted


# ============================================================
# Entry creation
# ============================================================

class TestMakeEntry:

    def test_timestamp_is_utc_iso(self):
        entry = _make_entry(Step.SYSTEM, "test")
        ts = entry["timestamp"]
        assert "T" in ts
        assert "+" in ts or "Z" in ts  # UTC marker

    def test_required_fields(self):
        entry = _make_entry(Step.CLASSIFY, "start")
        assert entry["step"] == "classify"
        assert entry["event"] == "start"
        assert entry["level"] == "INFO"

    def test_duration_rounded(self):
        entry = _make_entry(Step.CLASSIFY, "test", duration_ms=3200.5678)
        assert entry["duration_ms"] == 3200.6
