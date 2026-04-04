"""Tests for Step 1.2: LangGraph pipeline state."""

from app.agents.models import (
    ClassifyExtractOutput,
    CraftedQuery,
    IntentType,
    SearchRoute,
)
from app.agents.state import (
    ConversationMessage,
    FieldAssistantState,
    trim_conversation_history,
)


# --- FieldAssistantState ---

def test_state_all_fields():
    state: FieldAssistantState = {
        "user_message": "My cassava has brown spots",
        "image_path": None,
        "conversation_history": [],
        "classify_result": ClassifyExtractOutput(intent=IntentType.DIAGNOSE_DISEASE),
        "route": SearchRoute(),
        "crafted_query": CraftedQuery(),
        "search_results": [],
        "ranked_results": [],
        "is_sufficient": False,
        "retrieval_attempts": 0,
        "final_answer": "",
        "tool_calls_log": [],
        "error": None,
    }
    assert state["user_message"] == "My cassava has brown spots"
    assert state["retrieval_attempts"] == 0
    assert state["error"] is None


def test_state_partial():
    """FieldAssistantState uses total=False, so partial dicts are valid."""
    state: FieldAssistantState = {
        "user_message": "Hello",
    }
    assert state["user_message"] == "Hello"


def test_state_with_image():
    state: FieldAssistantState = {
        "user_message": "What is wrong with this plant?",
        "image_path": "/uploads/plant_photo.jpg",
    }
    assert state["image_path"] == "/uploads/plant_photo.jpg"


# --- ConversationMessage ---

def test_conversation_message():
    msg: ConversationMessage = {
        "role": "user",
        "content": "What diseases affect cassava?",
        "timestamp": "2026-04-04T10:00:00Z",
    }
    assert msg["role"] == "user"
    assert "cassava" in msg["content"]


# --- trim_conversation_history ---

def test_trim_under_limit():
    history = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
    trimmed = trim_conversation_history(history, max_messages=10)
    assert len(trimmed) == 5


def test_trim_at_limit():
    history = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
    trimmed = trim_conversation_history(history, max_messages=10)
    assert len(trimmed) == 10


def test_trim_over_limit():
    history = [{"role": "user", "content": f"msg {i}"} for i in range(15)]
    trimmed = trim_conversation_history(history, max_messages=10)
    assert len(trimmed) == 10
    # Should keep the LAST 10, not the first 10
    assert trimmed[0]["content"] == "msg 5"
    assert trimmed[-1]["content"] == "msg 14"


def test_trim_empty():
    trimmed = trim_conversation_history([], max_messages=10)
    assert trimmed == []


def test_trim_does_not_mutate_original():
    history = [{"role": "user", "content": f"msg {i}"} for i in range(15)]
    original_len = len(history)
    trim_conversation_history(history, max_messages=10)
    assert len(history) == original_len


def test_trim_custom_limit():
    history = [{"role": "user", "content": f"msg {i}"} for i in range(8)]
    trimmed = trim_conversation_history(history, max_messages=3)
    assert len(trimmed) == 3
    assert trimmed[0]["content"] == "msg 5"
