"""Tests for Step 5.6: GENERATE ANSWER node (LLM call #4)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.models import ScoredResult
from app.agents.nodes.generate_answer import (
    _assemble_context,
    _format_conversation,
    generate_answer,
)


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
        mock_response = MagicMock()
        mock_response.content = (
            "Based on the symptoms you describe, your cassava may have Cassava Mosaic Disease. "
            "Here are recommended treatment steps:\n"
            "- Remove and burn infected plants\n"
            "- Use resistant varieties like TME 419"
        )

        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = generate_answer(self._make_state())

        assert "final_answer" in result
        assert len(result["final_answer"]) > 0
        assert "cassava" in result["final_answer"].lower()

    def test_conversation_history_updated(self):
        mock_response = MagicMock()
        mock_response.content = "Test answer"

        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = generate_answer(self._make_state())

        history = result["conversation_history"]
        assert len(history) >= 2
        # Last two entries should be user + assistant
        assert history[-2]["role"] == "user"
        assert history[-1]["role"] == "assistant"
        assert history[-1]["content"] == "Test answer"

    def test_history_trimmed_to_max(self):
        existing = [{"role": "user", "content": f"msg {i}"} for i in range(9)]
        mock_response = MagicMock()
        mock_response.content = "Answer"

        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = generate_answer(self._make_state(history=existing))

        # 9 existing + 2 new = 11, trimmed to 5 (default max_messages)
        assert len(result["conversation_history"]) <= 5

    def test_empty_results_honest_answer(self):
        result = generate_answer(self._make_state(results=[]))
        assert "don't have enough information" in result["final_answer"]

    def test_llm_error_fallback(self):
        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = Exception("Ollama down")
            result = generate_answer(self._make_state())

        assert "error" in result["final_answer"].lower()
        assert "conversation_history" in result

    def test_prompt_includes_context(self):
        captured_messages = []

        def capture_invoke(messages):
            captured_messages.extend(messages)
            mock_resp = MagicMock()
            mock_resp.content = "Test answer"
            return mock_resp

        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = capture_invoke
            generate_answer(self._make_state())

        all_text = " ".join(m.content for m in captured_messages)
        assert "Context:" in all_text
        assert "Detailed parent information" in all_text
        assert "Question:" in all_text

    def test_prompt_includes_rag_grounding(self):
        captured_messages = []

        def capture_invoke(messages):
            captured_messages.extend(messages)
            mock_resp = MagicMock()
            mock_resp.content = "Answer"
            return mock_resp

        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = capture_invoke
            generate_answer(self._make_state())

        system_prompt = captured_messages[0].content
        assert "context" in system_prompt.lower()
        assert "don't have" in system_prompt.lower() or "not sure" in system_prompt.lower()
        assert "Do NOT invent" in system_prompt

    def test_with_conversation_history(self):
        captured_messages = []

        def capture_invoke(messages):
            captured_messages.extend(messages)
            mock_resp = MagicMock()
            mock_resp.content = "Follow-up answer"
            return mock_resp

        history = [
            {"role": "user", "content": "What disease is this?"},
            {"role": "assistant", "content": "It looks like CMD."},
        ]

        with patch("app.agents.nodes.generate_answer.get_field_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = capture_invoke
            generate_answer(self._make_state(
                history=history,
                message="How do I treat it?",
            ))

        all_text = " ".join(m.content for m in captured_messages)
        assert "CMD" in all_text
        assert "Conversation history" in all_text
