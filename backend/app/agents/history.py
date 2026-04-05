"""Conversation history utilities.

Converts JSON conversation history to natural language for LLM
consumption, and builds heuristic conversation summaries.

LLMs should never see raw JSON history — this module ensures
all history is presented as clean natural language.
"""


MAX_CONTENT_CHARS = 400


def history_to_nl(
    history: list[dict],
    summary: str = "",
    max_recent: int = 10,
) -> str:
    """Convert conversation history to natural language.

    Prepends conversation summary (if any) then formats the last
    N messages as a readable dialogue. Truncates individual messages
    to avoid overflowing the LLM context window.

    Args:
        history: List of message dicts with role/content keys.
        summary: Optional conversation summary from prior turns.
        max_recent: Number of recent messages to include.

    Returns:
        Natural language string ready for LLM prompt injection.
    """
    if not history and not summary:
        return ""

    parts = []

    if summary and summary.strip():
        parts.append(f"Previous conversation context: {summary.strip()}")

    if history:
        recent = history[-max_recent:] if len(history) > max_recent else history
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if not content:
                continue
            if len(content) > MAX_CONTENT_CHARS:
                content = content[:MAX_CONTENT_CHARS] + "..."
            speaker = "Farmer" if role == "user" else "Assistant"
            parts.append(f"{speaker}: {content}")

    return "\n".join(parts)


def build_conversation_summary(
    classify_result: object | None,
    final_answer: str = "",
    previous_summary: str = "",
) -> str:
    """Build a heuristic conversation summary.

    Combines classify output (crop, disease, intent) with the
    first sentence of the answer. No LLM call — pure Python.

    Args:
        classify_result: ClassifyExtractOutput or None.
        final_answer: The generated answer text.
        previous_summary: Summary from the prior turn (rolled forward).

    Returns:
        Human-readable summary string.
    """
    parts = []

    if classify_result is not None:
        crop = getattr(classify_result, "crop", None)
        disease = getattr(classify_result, "disease_name", None)
        intent = getattr(classify_result, "intent", None)

        if crop:
            parts.append(f"discussing {crop}")
        if disease:
            parts.append(f"regarding {disease}")
        if intent and not crop and not disease:
            intent_label = (intent.value if hasattr(intent, "value") else str(intent)).replace("_", " ")
            parts.append(f"topic: {intent_label}")

    if final_answer:
        first_sentence = final_answer.split(". ")[0]
        if len(first_sentence) > 150:
            first_sentence = first_sentence[:147] + "..."
        parts.append(f"Last response covered: {first_sentence}.")

    if not parts and previous_summary:
        return previous_summary

    summary = " ".join(parts) if parts else ""

    if previous_summary and summary:
        combined = f"{previous_summary} | {summary}"
        # Cap summary length to avoid inflating every LLM prompt
        if len(combined) > 500:
            combined = "..." + combined[-497:]
        return combined

    return summary
