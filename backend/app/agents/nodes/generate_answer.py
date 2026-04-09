"""Node 6: GENERATE ANSWER (LLM call #4).

Synthesizes the final answer from re-ranked context chunks,
conversation history, and the user's question. Uses parent content
only (not child chunks) for clean, detailed context.

RAG-grounded persona: answers ONLY from provided context.
Explicitly told it's OK not to know. Never hallucinate.

Token streaming is handled by LangGraph's astream_events in
field_assistant.py — this node returns the full answer synchronously.
"""

from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.models import ScoredResult, extract_text
from app.agents.state import FieldAssistantState, trim_conversation_history
from app.agents.history import history_to_nl
from app.logger import Step, pipeline_logger as log
from app.models.offline_llm import get_field_llm


MAX_CONTEXT_WORDS = 2000

GENERATE_SYSTEM_PROMPT = """Agricultural field assistant. Answer using ONLY the provided context.
- Be concise: 3-8 sentences for simple questions, longer for treatment plans
- Be specific and actionable, reference locally available materials
- Use bullet points for treatment steps
- Include safety precautions for treatments
- If context has nothing relevant, say: "I don't have information on this topic in the knowledge pack."
- Never invent disease names, treatments, or statistics not in context."""


def _assemble_context(
    ranked_results: list[ScoredResult],
    max_total_words: int = MAX_CONTEXT_WORDS,
) -> str:
    """Assemble context from ranked results with score-proportional space.

    Higher-scored results get more of the word budget.
    Uses parent_content (full detail) not child content.
    """
    if not ranked_results:
        return ""

    # Calculate score-proportional word allocation
    total_score = sum(r.relevance_score for r in ranked_results)
    if total_score <= 0:
        total_score = len(ranked_results)  # Equal allocation fallback

    context_parts = []
    for i, result in enumerate(ranked_results):
        # Word budget proportional to score
        proportion = result.relevance_score / total_score
        word_budget = max(50, int(proportion * max_total_words))

        # Use parent_content (the whole point of parent/child chunking)
        text = result.parent_content or result.content
        words = text.split()
        if len(words) > word_budget:
            text = " ".join(words[:word_budget]) + "..."

        context_parts.append(f"[Source {i + 1}]\n{text}")

    return "\n\n---\n\n".join(context_parts)


def _format_conversation(
    history: list[dict],
    summary: str = "",
    max_messages: int = 5,
) -> str:
    """Format conversation history as natural language for the LLM."""
    return history_to_nl(history, summary=summary, max_recent=max_messages)


def generate_answer(state: FieldAssistantState) -> dict:
    """Generate the final answer from ranked context + conversation history.

    LLM call #4. Assembles context with score-proportional space allocation,
    formats conversation history, and generates a grounded answer.

    Returns dict with: final_answer, conversation_history updates.
    """
    user_message = state.get("user_message", "")
    ranked_results = state.get("ranked_results", [])
    history = state.get("conversation_history", [])

    # Assemble context
    context_text = _assemble_context(ranked_results)

    if not context_text:
        no_context_answer = (
            "I don't have enough information in the knowledge pack to answer this question. "
            "Try asking about specific crops (cassava, rice, maize, groundnut, tomato) "
            "or diseases that affect them in your region."
        )
        log.log_step(Step.GENERATE, "no_context",
                     details={"message": user_message[:200]})

        # Update conversation history
        updated_history = list(history) + [
            {"role": "user", "content": user_message,
             "timestamp": datetime.now(timezone.utc).isoformat()},
            {"role": "assistant", "content": no_context_answer,
             "timestamp": datetime.now(timezone.utc).isoformat()},
        ]
        return {
            "final_answer": no_context_answer,
            "conversation_history": trim_conversation_history(updated_history),
        }

    # Format conversation history as natural language
    summary = state.get("conversation_summary", "")
    history_text = _format_conversation(history, summary=summary)

    # Build prompt
    messages = [SystemMessage(content=GENERATE_SYSTEM_PROMPT)]

    user_prompt_parts = [f"Context:\n{context_text}"]

    image_description = state.get("image_description")
    if image_description:
        user_prompt_parts.append(
            f"\nImage analysis of the farmer's photo: {image_description}"
            "\nIMPORTANT: Compare the visual symptoms above against ALL diseases in the context. "
            "Choose the disease whose symptoms best match what was observed in the photo, "
            "even if it is not the top-ranked source. State your diagnosis confidently, then provide treatment steps."
        )

    if history_text:
        user_prompt_parts.append(f"\nConversation history:\n{history_text}")

    user_prompt_parts.append(f"\nQuestion: {user_message}")

    messages.append(HumanMessage(content="\n".join(user_prompt_parts)))

    with log.timed(Step.GENERATE, "llm_call") as t:
        try:
            llm = get_field_llm(temperature=0.4, num_predict=512)
            response = llm.invoke(messages)
            answer = extract_text(response)
        except Exception as e:
            log.log_step(Step.GENERATE, "llm_error", level="ERROR",
                         details={"error": str(e)})
            t.set(level="ERROR")
            answer = (
                "I encountered an error generating an answer. "
                "Please try again or rephrase your question."
            )

        t.set(details={
            "context_sources": len(ranked_results),
            "context_words": len(context_text.split()),
            "history_messages": len(history),
            "answer_length": len(answer),
        })

    # Update conversation history with this exchange
    updated_history = list(history) + [
        {"role": "user", "content": user_message,
         "timestamp": datetime.now(timezone.utc).isoformat()},
        {"role": "assistant", "content": answer,
         "timestamp": datetime.now(timezone.utc).isoformat()},
    ]

    return {
        "final_answer": answer,
        "conversation_history": trim_conversation_history(updated_history),
    }
