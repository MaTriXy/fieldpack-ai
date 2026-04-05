"""LangGraph pipeline state for the field assistant.

The FieldAssistantState flows through the entire 6-step retrieval graph.
Each node reads from and writes to this state.
"""

from typing import TypedDict

from app.agents.models import (
    ClassifyExtractOutput,
    CraftedQuery,
    ScoredResult,
    SearchResult,
    SearchRoute,
)


class FieldAssistantState(TypedDict, total=False):
    # Input
    user_message: str
    image_path: str | None
    conversation_history: list[dict]
    conversation_summary: str

    # Step 1: Classify + Extract
    classify_result: ClassifyExtractOutput | None

    # Step 2: Route
    route: SearchRoute | None

    # Step 2.5: Needs Search (hybrid gate)
    needs_search: bool

    # Step 3: Craft Search Query
    crafted_query: CraftedQuery | None
    crafted_queries: list[CraftedQuery]

    # Step 4: Execute Searches
    search_results: list[SearchResult]

    # Step 5: Re-Rank
    ranked_results: list[ScoredResult]
    is_sufficient: bool
    retrieval_attempts: int

    # Step 6: Generate Answer
    final_answer: str

    # Observation logging
    observation_stats: dict | None

    # Observability
    tool_calls_log: list[dict]
    error: str | None


def trim_conversation_history(
    history: list[dict],
    max_messages: int = 10,
) -> list[dict]:
    """Keep only the most recent messages (sliding window)."""
    if max_messages <= 0:
        return []
    if len(history) <= max_messages:
        return list(history)
    return list(history[-max_messages:])
