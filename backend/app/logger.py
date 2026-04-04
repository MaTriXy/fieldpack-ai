"""Centralized pipeline logger for FieldPack AI.

Dual output:
  - JSON lines to file (machine-parseable, for analysis)
  - Pretty colored text to console (human-readable, for live debugging)
  - In-memory ring buffer (for API exposure to frontend)

The logger tracks every pipeline step with full detail:
  - LLM calls (prompt, response, tokens, latency)
  - Search operations (engine, query, results, scores, latency)
  - Routing decisions (intent, engines, collections)
  - Pipeline lifecycle (start, end, total duration, retry count)

Two audiences:
  - Developer logs: full detail, JSON + console
  - User-facing events: step progress for UI gamification (tool_calls_log)
"""

import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings


# ============================================================
# Pipeline step names (used throughout the system)
# ============================================================

class Step:
    CLASSIFY = "classify"
    ROUTE = "route"
    CRAFT_QUERY = "craft_query"
    SEARCH = "search"
    RERANK = "rerank"
    GENERATE = "generate"
    IMAGE_ANALYSIS = "image_analysis"
    OBSERVATION = "observation"
    PACK_LOAD = "pack_load"
    PACK_BUILD = "pack_build"
    SYSTEM = "system"


# ============================================================
# Log entry structure
# ============================================================

def _make_entry(
    step: str,
    event: str,
    level: str = "INFO",
    duration_ms: float | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    details: dict | None = None,
    user_message: str | None = None,
) -> dict:
    """Create a structured log entry."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": step,
        "event": event,
        "level": level,
    }
    if duration_ms is not None:
        entry["duration_ms"] = round(duration_ms, 1)
    if tokens_in is not None:
        entry["tokens_in"] = tokens_in
    if tokens_out is not None:
        entry["tokens_out"] = tokens_out
    if details:
        entry["details"] = details
    if user_message:
        entry["user_message"] = user_message
    return entry


# ============================================================
# Console formatter (human-readable, colored)
# ============================================================

_STEP_COLORS = {
    Step.CLASSIFY: "\033[36m",       # cyan
    Step.ROUTE: "\033[33m",          # yellow
    Step.CRAFT_QUERY: "\033[35m",    # magenta
    Step.SEARCH: "\033[32m",         # green
    Step.RERANK: "\033[34m",         # blue
    Step.GENERATE: "\033[97m",       # bright white
    Step.IMAGE_ANALYSIS: "\033[95m", # bright magenta
    Step.OBSERVATION: "\033[90m",    # gray
    Step.PACK_LOAD: "\033[33m",      # yellow
    Step.PACK_BUILD: "\033[33m",     # yellow
    Step.SYSTEM: "\033[90m",         # gray
}
_RESET = "\033[0m"


def _format_console(entry: dict) -> str:
    """Format a log entry for console output."""
    ts = entry["timestamp"][11:19]  # HH:MM:SS
    step = entry["step"].upper().ljust(14)
    color = _STEP_COLORS.get(entry["step"], "")
    event = entry["event"]

    parts = [f"{color}[{ts}] {step}{_RESET} {event}"]

    if "duration_ms" in entry:
        duration = entry["duration_ms"]
        if duration >= 1000:
            parts.append(f"({duration/1000:.1f}s)")
        else:
            parts.append(f"({duration:.0f}ms)")

    if "tokens_in" in entry or "tokens_out" in entry:
        tin = entry.get("tokens_in", "?")
        tout = entry.get("tokens_out", "?")
        parts.append(f"[{tin}→{tout} tok]")

    details = entry.get("details", {})
    if details:
        # Show key details inline, skip large values
        inline = []
        for k, v in details.items():
            if isinstance(v, str) and len(v) > 80:
                inline.append(f"{k}=({len(v)} chars)")
            elif isinstance(v, list) and len(v) > 5:
                inline.append(f"{k}=({len(v)} items)")
            elif isinstance(v, dict) and len(v) > 3:
                inline.append(f"{k}=({len(v)} keys)")
            else:
                inline.append(f"{k}={v}")
        if inline:
            parts.append("| " + " ".join(inline))

    return " ".join(parts)


# ============================================================
# PipelineLogger
# ============================================================

class PipelineLogger:
    """Centralized logger for the entire FieldPack AI pipeline.

    Usage:
        from app.logger import pipeline_logger as log

        log.log_step(Step.CLASSIFY, "start", details={"message": user_msg})

        with log.timed(Step.CLASSIFY, "llm_call") as t:
            result = llm.invoke(prompt)
            t.set(tokens_in=450, tokens_out=120, details={"intent": "diagnose"})

        log.log_llm_call(Step.CLASSIFY, prompt="...", response="...",
                         duration_ms=3200, tokens_in=450, tokens_out=120)
    """

    def __init__(
        self,
        log_dir: Path | None = None,
        level: str = "DEBUG",
        buffer_size: int = 500,
    ):
        self._buffer: deque[dict] = deque(maxlen=buffer_size)
        self._session_id: str | None = None
        self._pipeline_start: float | None = None
        self._total_llm_calls: int = 0
        self._total_tokens_in: int = 0
        self._total_tokens_out: int = 0

        # File logger (JSON lines)
        self._file_logger = logging.getLogger("fieldpack.pipeline.file")
        self._file_logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        self._file_logger.propagate = False

        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(
                log_dir / "pipeline.jsonl",
                encoding="utf-8",
            )
            fh.setFormatter(logging.Formatter("%(message)s"))
            self._file_logger.addHandler(fh)

        # Console logger (pretty)
        self._console_logger = logging.getLogger("fieldpack.pipeline.console")
        self._console_logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        self._console_logger.propagate = False

        if not self._console_logger.handlers:
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter("%(message)s"))
            self._console_logger.addHandler(ch)

    # --- Core logging ---

    def log_step(
        self,
        step: str,
        event: str,
        level: str = "INFO",
        duration_ms: float | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        details: dict | None = None,
        user_message: str | None = None,
    ):
        """Log a pipeline step event."""
        entry = _make_entry(
            step=step,
            event=event,
            level=level,
            duration_ms=duration_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            details=details,
            user_message=user_message,
        )
        if self._session_id:
            entry["session_id"] = self._session_id

        # Track totals
        if tokens_in:
            self._total_tokens_in += tokens_in
        if tokens_out:
            self._total_tokens_out += tokens_out

        self._buffer.append(entry)

        log_level = getattr(logging, level.upper(), logging.INFO)
        self._file_logger.log(log_level, json.dumps(entry, default=str))
        self._console_logger.log(log_level, _format_console(entry))

    # --- Convenience methods ---

    def log_llm_call(
        self,
        step: str,
        prompt: str,
        response: str,
        duration_ms: float,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        model: str | None = None,
        details: dict | None = None,
    ):
        """Log an LLM call with full details."""
        self._total_llm_calls += 1
        call_details = {
            "prompt_preview": prompt[:300] + "..." if len(prompt) > 300 else prompt,
            "prompt_length": len(prompt),
            "response_preview": response[:300] + "..." if len(response) > 300 else response,
            "response_length": len(response),
            "model": model or settings.ollama_model,
            "llm_call_number": self._total_llm_calls,
        }
        if details:
            call_details.update(details)

        self.log_step(
            step=step,
            event="llm_call",
            duration_ms=duration_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            details=call_details,
        )

    def log_search(
        self,
        engine: str,
        query: str,
        collection_or_table: str,
        results_count: int,
        top_scores: list[float] | None = None,
        filters: dict | None = None,
        duration_ms: float | None = None,
    ):
        """Log a search operation (ChromaDB, FTS5, or structured SQL)."""
        self.log_step(
            step=Step.SEARCH,
            event=f"search_{engine}",
            duration_ms=duration_ms,
            details={
                "engine": engine,
                "query_preview": query[:200] if query else "",
                "target": collection_or_table,
                "results_count": results_count,
                "top_scores": [round(s, 3) for s in (top_scores or [])[:5]],
                "filters": filters or {},
            },
        )

    def log_route(
        self,
        intent: str,
        engines: list[str],
        collections: list[str],
        tables: list[str],
        filters: dict | None = None,
    ):
        """Log a routing decision."""
        self.log_step(
            step=Step.ROUTE,
            event="route_decision",
            details={
                "intent": intent,
                "engines": engines,
                "collections": collections,
                "tables": tables,
                "filters": filters or {},
            },
        )

    def log_rerank(
        self,
        total_input: int,
        total_kept: int,
        is_sufficient: bool,
        top_scores: list[float] | None = None,
        duration_ms: float | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
    ):
        """Log a re-ranking result."""
        self.log_step(
            step=Step.RERANK,
            event="rerank_complete",
            duration_ms=duration_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            details={
                "input_results": total_input,
                "kept_results": total_kept,
                "filtered_out": total_input - total_kept,
                "is_sufficient": is_sufficient,
                "top_scores": [round(s, 3) for s in (top_scores or [])[:5]],
            },
        )

    # --- Pipeline lifecycle ---

    def pipeline_start(self, user_message: str, session_id: str | None = None):
        """Mark the start of a pipeline run."""
        self._session_id = session_id
        self._pipeline_start = time.perf_counter()
        self._total_llm_calls = 0
        self._total_tokens_in = 0
        self._total_tokens_out = 0

        self.log_step(
            step=Step.SYSTEM,
            event="pipeline_start",
            user_message=user_message,
            details={"session_id": session_id},
        )

    def pipeline_end(self, success: bool = True, error: str | None = None):
        """Mark the end of a pipeline run with summary stats."""
        duration_ms = None
        if self._pipeline_start:
            duration_ms = (time.perf_counter() - self._pipeline_start) * 1000

        self.log_step(
            step=Step.SYSTEM,
            event="pipeline_end",
            level="INFO" if success else "ERROR",
            duration_ms=duration_ms,
            details={
                "success": success,
                "total_llm_calls": self._total_llm_calls,
                "total_tokens_in": self._total_tokens_in,
                "total_tokens_out": self._total_tokens_out,
                "error": error,
            },
        )

    # --- Timer context manager ---

    def timed(self, step: str, event: str) -> "TimedContext":
        """Context manager for timing operations.

        Usage:
            with log.timed(Step.CLASSIFY, "llm_call") as t:
                result = llm.invoke(prompt)
                t.set(tokens_in=450, tokens_out=120, details={"intent": "diagnose"})
        """
        return TimedContext(self, step, event)

    # --- Buffer access (for API) ---

    def get_buffer(self, last_n: int | None = None) -> list[dict]:
        """Get recent log entries from the in-memory ring buffer."""
        entries = list(self._buffer)
        if last_n:
            entries = entries[-last_n:]
        return entries

    def get_session_entries(self) -> list[dict]:
        """Get all entries for the current session/pipeline run."""
        if not self._session_id:
            return list(self._buffer)
        return [e for e in self._buffer if e.get("session_id") == self._session_id]

    def to_tool_calls_log(self) -> list[dict]:
        """Convert current session entries to user-facing tool_calls_log format.

        This is what gets shown in the UI to gamify the wait.
        Simplified, non-technical, progress-oriented.
        """
        user_events = []
        for entry in self.get_session_entries():
            step = entry.get("step", "")
            event = entry.get("event", "")

            # Map to user-friendly descriptions
            label = _USER_STEP_LABELS.get((step, event))
            if not label:
                continue

            user_event = {
                "step": step,
                "label": label,
                "timestamp": entry.get("timestamp", ""),
            }
            if "duration_ms" in entry:
                user_event["duration_ms"] = entry["duration_ms"]
            if "tokens_in" in entry or "tokens_out" in entry:
                user_event["tokens_in"] = entry.get("tokens_in")
                user_event["tokens_out"] = entry.get("tokens_out")

            # Add step-specific user-facing details
            details = entry.get("details", {})
            if step == Step.CLASSIFY and "intent" in details:
                user_event["detail"] = f"Detected: {details['intent']}"
            elif step == Step.SEARCH:
                count = details.get("results_count", 0)
                engine = details.get("engine", "")
                user_event["detail"] = f"Found {count} results via {engine}"
            elif step == Step.RERANK:
                kept = details.get("kept_results", 0)
                user_event["detail"] = f"Selected {kept} most relevant results"
            elif step == Step.SYSTEM and event == "pipeline_end":
                user_event["detail"] = (
                    f"Completed in {entry.get('duration_ms', 0)/1000:.1f}s "
                    f"using {details.get('total_llm_calls', 0)} AI calls"
                )

            user_events.append(user_event)

        return user_events

    # --- Reset ---

    def clear_buffer(self):
        """Clear the in-memory buffer."""
        self._buffer.clear()

    @property
    def stats(self) -> dict:
        """Current session statistics."""
        return {
            "total_llm_calls": self._total_llm_calls,
            "total_tokens_in": self._total_tokens_in,
            "total_tokens_out": self._total_tokens_out,
            "buffer_size": len(self._buffer),
        }


# ============================================================
# Timer context manager
# ============================================================

class TimedContext:
    """Context manager that times an operation and logs it on exit."""

    def __init__(self, logger: PipelineLogger, step: str, event: str):
        self._logger = logger
        self._step = step
        self._event = event
        self._start: float = 0
        self._tokens_in: int | None = None
        self._tokens_out: int | None = None
        self._details: dict | None = None
        self._level: str = "INFO"

    def set(
        self,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        details: dict | None = None,
        level: str | None = None,
    ):
        """Set additional data to include in the log entry."""
        if tokens_in is not None:
            self._tokens_in = tokens_in
        if tokens_out is not None:
            self._tokens_out = tokens_out
        if details:
            self._details = {**(self._details or {}), **details}
        if level:
            self._level = level

    def __enter__(self) -> "TimedContext":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self._start) * 1000
        if exc_type:
            self._level = "ERROR"
            self._details = {**(self._details or {}), "error": str(exc_val)}

        self._logger.log_step(
            step=self._step,
            event=self._event,
            level=self._level,
            duration_ms=duration_ms,
            tokens_in=self._tokens_in,
            tokens_out=self._tokens_out,
            details=self._details,
        )
        return False  # Don't suppress exceptions


# ============================================================
# User-facing step labels (for UI gamification)
# ============================================================

_USER_STEP_LABELS = {
    (Step.SYSTEM, "pipeline_start"): "Starting analysis...",
    (Step.CLASSIFY, "llm_call"): "Understanding your question...",
    (Step.ROUTE, "route_decision"): "Planning search strategy...",
    (Step.CRAFT_QUERY, "llm_call"): "Preparing search query...",
    (Step.SEARCH, "search_chroma"): "Searching knowledge base...",
    (Step.SEARCH, "search_fts"): "Searching by keywords...",
    (Step.SEARCH, "search_structured"): "Looking up database...",
    (Step.IMAGE_ANALYSIS, "llm_call"): "Analyzing plant image...",
    (Step.RERANK, "rerank_complete"): "Evaluating relevance...",
    (Step.GENERATE, "llm_call"): "Generating answer...",
    (Step.OBSERVATION, "logged"): "Observation saved.",
    (Step.SYSTEM, "pipeline_end"): "Done!",
}


# ============================================================
# Global singleton
# ============================================================

pipeline_logger = PipelineLogger(
    log_dir=settings.logs_path,
    level=settings.log_level,
    buffer_size=settings.log_buffer_size,
)
