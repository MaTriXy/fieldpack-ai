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
from app.knowledge_pack.loader import get_active_pack
from app.logger import Step, pipeline_logger as log
from app.models.offline_llm import get_field_llm


MAX_CONTEXT_WORDS = 2000

LANGUAGE_INSTRUCTIONS = {
    "fr": "IMPORTANT: Respond entirely in French (Francais).",
    "wo": "IMPORTANT: Respond entirely in Wolof.",
    "pt": "IMPORTANT: Respond entirely in Portuguese (Portugues).",
}

GENERATE_SYSTEM_PROMPT = """Agricultural field assistant. Answer using ONLY the provided context.
- Be concise: 3-8 sentences for simple questions, longer for treatment plans
- Be specific and actionable, reference locally available materials
- Use bullet points for treatment steps
- Include safety precautions for treatments
- Answer from whatever relevant information is in the context, even if it only partially addresses the question
- Only say "I don't have information on this topic" if NONE of the sources relate to the question at all
- Never invent disease names, treatments, or statistics not in context."""

CONVERSATIONAL_SYSTEM_PROMPT = "You are FieldPack AI, an agricultural field assistant{region_suffix}. You help farmers with crop diseases, treatments, and farming. Reply briefly and helpfully."

SEARCH_EXHAUSTED_CONTEXT = "[No relevant information was found in the knowledge base for this question.]"

SEARCH_EXHAUSTED_SYSTEM_PROMPT = """You are FieldPack AI, an agricultural field assistant. The knowledge base was searched but no relevant information was found for this question.
- Honestly tell the farmer you don't have information on this specific topic
- Suggest they rephrase their question or ask about a different crop or topic
- Be brief (2-3 sentences)
- Never invent disease names, treatments, or statistics."""


def _get_pack_region() -> str:
    """Get the loaded pack's region name, or empty string if no pack."""
    try:
        pack = get_active_pack()
        if pack and pack.manifest and pack.manifest.region:
            return pack.manifest.region.name
    except Exception:
        pass
    return ""


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


async def generate_answer(state: FieldAssistantState) -> dict:
    """Generate the final answer from ranked context + conversation history.

    LLM call #4. Assembles context with score-proportional space allocation,
    formats conversation history, and generates a grounded answer.
    Async so LangGraph can capture streaming tokens via astream_events.

    Returns dict with: final_answer, conversation_history updates.
    """
    user_message = state.get("user_message", "")
    ranked_results = state.get("ranked_results", [])
    history = state.get("conversation_history", [])
    language = state.get("language")

    lang_instruction = LANGUAGE_INSTRUCTIONS.get(language) if language and language != "en" else None

    # Assemble context
    context_text = _assemble_context(ranked_results)

    # Distinguish "user is chatting" from "search failed after retries"
    retrieval_attempts = state.get("retrieval_attempts", 0)
    needs_search = state.get("needs_search", True)
    search_exhausted = needs_search and not context_text and retrieval_attempts >= 1

    is_conversational = not context_text and not search_exhausted

    # Inject sentinel so the model sees an explicit "no results" rather than
    # an empty context block with instructions to "answer from context"
    if search_exhausted:
        context_text = SEARCH_EXHAUSTED_CONTEXT

    # Pick system prompt: RAG when we have context, conversational for chat,
    # and a knowledge-aware fallback when search was attempted but found nothing
    if is_conversational:
        region = _get_pack_region()
        region_suffix = f" for {region}" if region else ""
        base_prompt = CONVERSATIONAL_SYSTEM_PROMPT.format(region_suffix=region_suffix)
    elif search_exhausted:
        base_prompt = SEARCH_EXHAUSTED_SYSTEM_PROMPT
    else:
        base_prompt = GENERATE_SYSTEM_PROMPT
    system_prompt = (
        lang_instruction + "\n\n" + base_prompt
        if lang_instruction
        else base_prompt
    )

    if search_exhausted:
        log.log_step(Step.GENERATE, "search_exhausted",
                     details={"message": user_message[:200],
                              "retrieval_attempts": retrieval_attempts})
    elif is_conversational:
        log.log_step(Step.GENERATE, "no_context",
                     details={"message": user_message[:200]})

    # Format conversation history as natural language
    summary = state.get("conversation_summary", "")
    history_text = _format_conversation(history, summary=summary)

    # Build prompt
    messages = [SystemMessage(content=system_prompt)]

    if is_conversational:
        # Structured document with labeled fields — anchors the model in English
        # and gives it enough structure to pattern-match against instruction tuning
        user_prompt_parts = []
        if history_text:
            user_prompt_parts.append(f"Conversation history:\n{history_text}")
        user_prompt_parts.append(f"Farmer message: {user_message}")
        user_prompt_parts.append("Task: Reply to the farmer. Be brief and helpful.")
        messages.append(HumanMessage(content="\n".join(user_prompt_parts)))
    else:
        # RAG path — context-grounded prompt
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

        user_prompt_parts.append(f"Question: {user_message}")
        messages.append(HumanMessage(content="\n".join(user_prompt_parts)))

    temperature = 0.1 if is_conversational else 0.4
    # 256 for search_exhausted: deliberate cap to limit hallucination length
    # when the model has no real context to ground on
    max_tokens = 128 if is_conversational else 256 if search_exhausted else 512
    fmt = None

    with log.timed(Step.GENERATE, "llm_call") as t:
        try:
            llm = get_field_llm(temperature=temperature, num_predict=max_tokens, format=fmt)
            # Use astream() so LangGraph's astream_events can capture
            # individual tokens and forward them to the frontend
            chunks = []
            async for chunk in llm.astream(messages):
                chunks.append(chunk)
            answer = "".join(extract_text(c) for c in chunks).lstrip("?!.,;: \n")
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("generate_answer LLM call failed")
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
