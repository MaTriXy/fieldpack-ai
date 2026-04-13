"""Tests for Step 5.6: GENERATE ANSWER node (LLM call #4)."""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.models import ScoredResult
from app.agents.nodes.generate_answer import (
    _assemble_context,
    _format_conversation,
    generate_answer,
)


def _run_async(coro):
    """Run an async coroutine from sync test code."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


async def _astream_from_content(content):
    """Async generator that yields a single chunk with .content."""
    chunk = MagicMock()
    chunk.content = content
    yield chunk


def _patch_llm_for_astream(mock_llm, content):
    """Configure a mock LLM to work with both invoke() and astream()."""
    mock_response = MagicMock()
    mock_response.content = content
    mock_llm.return_value.invoke.return_value = mock_response
    mock_llm.return_value.astream = lambda msgs, _c=content: _astream_from_content(_c)
    return mock_response


def _patch_llm_capture_astream(mock_llm, content):
    """Configure a mock LLM that captures messages passed to astream()."""
    captured_messages = []

    async def capture_astream(messages):
        captured_messages.extend(messages)
        chunk = MagicMock()
        chunk.content = content
        yield chunk

    mock_llm.return_value.astream = capture_astream
    return captured_messages


def _make_ranked_results(count=3):
    return [
        ScoredResult(
            content=f"Child content {i}",
            source=f"src_{i}",
            relevance_score=0.9 - (i * 0.1),
            parent_id=f"parent_{i}",
            parent_content=f"Detailed parent information about cassava disease treatment method {i}. "
                           f"This includes step-by-step instructions for organic treatment "
                           f"using locally available materials in the Casamance region.",
        )
        for i in range(count)
    ]


# ============================================================
# Unit: _assemble_context
# ============================================================

class TestAssembleContext:

    def test_basic_assembly(self):
        results = _make_ranked_results(3)
        context = _assemble_context(results)
        assert "[Source 1]" in context
        assert "[Source 2]" in context
        assert "[Source 3]" in context

    def test_uses_parent_content(self):
        results = _make_ranked_results(1)
        context = _assemble_context(results)
        assert "Detailed parent information" in context
        assert "Child content" not in context

    def test_score_proportional_allocation(self):
        results = [
            ScoredResult(content="a", relevance_score=0.9,
                         parent_content="word " * 500),
            ScoredResult(content="b", relevance_score=0.1,
                         parent_content="word " * 500),
        ]
        context = _assemble_context(results, max_total_words=200)
        parts = context.split("---")
        # First source (0.9) should get more words than second (0.1)
        assert len(parts[0].split()) > len(parts[1].split())

    def test_empty_results(self):
        assert _assemble_context([]) == ""

    def test_total_word_budget_respected(self):
        results = _make_ranked_results(5)
        context = _assemble_context(results, max_total_words=100)
        # Should be roughly within budget (plus some overhead from source labels)
        word_count = len(context.split())
        assert word_count < 200  # generous upper bound

    def test_fallback_to_content_when_no_parent(self):
        results = [ScoredResult(
            content="Only child content available",
            relevance_score=0.8,
        )]
        context = _assemble_context(results)
        assert "Only child content available" in context


# ============================================================
# Unit: _format_conversation
# ============================================================

class TestFormatConversation:

    def test_basic_formatting(self):
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        result = _format_conversation(history)
        assert "Farmer: Hello" in result
        assert "Assistant: Hi there" in result

    def test_empty_history(self):
        assert _format_conversation([]) == ""

    def test_trims_to_max(self):
        history = [{"role": "user", "content": f"msg {i}"} for i in range(15)]
        result = _format_conversation(history, max_messages=10)
        lines = [l for l in result.split("\n") if l.strip()]
        assert len(lines) == 10

    def test_trims_to_max_with_summary(self):
        history = [{"role": "user", "content": f"msg {i}"} for i in range(15)]
        result = _format_conversation(history, max_messages=10, summary="discussing cassava disease")
        lines = [l for l in result.split("\n") if l.strip()]
        # 10 messages + 1 summary context line
        assert len(lines) == 11
        assert "Previous conversation" in lines[0] or "cassava" in lines[0]


# ============================================================
# Integration: generate_answer (mocked LLM)
# ============================================================

class TestGenerateAnswer:

    def _make_state(self, results=None, history=None, message="My cassava has yellow leaves"):
        return {
            "user_message": message,
            "ranked_results": results if results is not None else _make_ranked_results(3),
            "conversation_history": history or [],
        }

    def test_basic_generation(self):
        content = (
            "Based on the symptoms you describe, your cassava may have Cassava Mosaic Disease. "
            "Here are recommended treatment steps:\n"
            "- Remove and burn infected plants\n"
            "- Use resistant varieties like TME 419"
        )
        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            _patch_llm_for_astream(mock_llm, content)
            result = _run_async(generate_answer(self._make_state()))

        assert "final_answer" in result
        assert len(result["final_answer"]) > 0
        assert "cassava" in result["final_answer"].lower()

    def test_conversation_history_updated(self):
        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            _patch_llm_for_astream(mock_llm, "Test answer")
            result = _run_async(generate_answer(self._make_state()))

        history = result["conversation_history"]
        assert len(history) >= 2
        assert history[-2]["role"] == "user"
        assert history[-1]["role"] == "assistant"
        assert history[-1]["content"] == "Test answer"

    def test_history_trimmed_to_max(self):
        existing = [{"role": "user", "content": f"msg {i}"} for i in range(9)]
        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            _patch_llm_for_astream(mock_llm, "Answer")
            result = _run_async(generate_answer(self._make_state(history=existing)))

        # 9 existing + 2 new = 11, trimmed to 5 (default max_messages)
        assert len(result["conversation_history"]) <= 5

    def test_empty_results_honest_answer(self):
        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            _patch_llm_for_astream(mock_llm, "I don't have enough information to answer this.")
            result = _run_async(generate_answer(self._make_state(results=[])))
        assert result["final_answer"]
        assert len(result["final_answer"]) > 0

    def test_llm_error_fallback(self):
        async def _error_astream(messages):
            raise Exception("Ollama down")
            yield  # make it a generator  # noqa: unreachable

        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            mock_llm.return_value.astream = _error_astream
            result = _run_async(generate_answer(self._make_state()))

        assert "error" in result["final_answer"].lower()
        assert "conversation_history" in result

    def test_prompt_includes_context(self):
        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            captured = _patch_llm_capture_astream(mock_llm, "Test answer")
            _run_async(generate_answer(self._make_state()))

        all_text = " ".join(m.content for m in captured)
        assert "Context:" in all_text
        assert "Detailed parent information" in all_text
        assert "Question:" in all_text

    def test_prompt_includes_rag_grounding(self):
        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            captured = _patch_llm_capture_astream(mock_llm, "Answer")
            _run_async(generate_answer(self._make_state()))

        system_prompt = captured[0].content
        assert "context" in system_prompt.lower()
        assert "never invent" in system_prompt.lower()

    def test_with_conversation_history(self):
        history = [
            {"role": "user", "content": "What disease is this?"},
            {"role": "assistant", "content": "It looks like CMD."},
        ]

        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            captured = _patch_llm_capture_astream(mock_llm, "Follow-up answer")
            _run_async(generate_answer(self._make_state(
                history=history,
                message="How do I treat it?",
            )))

        all_text = " ".join(m.content for m in captured)
        assert "CMD" in all_text
        assert "Conversation history" in all_text
