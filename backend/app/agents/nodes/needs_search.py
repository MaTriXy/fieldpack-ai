"""Node 2.5: NEEDS SEARCH (hybrid gate).

Decides whether the pipeline should search the knowledge base or
skip directly to answer generation / observation logging.

Hybrid approach:
  1. Heuristic catches obvious cases (no engines, follow-up with
     existing results, observation logging)
  2. LLM decides ambiguous cases (general questions that may or
     may not need search)

This node sits between route_intent and craft_search_query.
"""

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.models import IntentType, extract_text
from app.agents.state import FieldAssistantState
from app.logger import Step, pipeline_logger as log
from app.models.offline_llm import get_field_llm


NEEDS_SEARCH_SYSTEM_PROMPT = """You are a decision system for an agricultural field assistant.

Given the user's message and conversation context, decide if we need to search the knowledge base for NEW information.

Answer YES if:
- The user asks a NEW question not covered by prior conversation
- The user asks about a different crop or disease
- The user needs specific data (treatments, symptoms, farming advice)

Answer NO if:
- The user is asking about information already provided in the conversation
- The user says thank you, goodbye, or other conversational messages
- The user asks to clarify or elaborate on something already discussed
- The user is making small talk

Output ONLY "YES" or "NO" followed by a brief reason.
Example: "NO - user is asking for clarification on previously provided treatment steps"
Example: "YES - user asks about a new disease not discussed before"
"""


_CONVERSATIONAL_PATTERNS = [
    re.compile(r"^(hi|hello|hey|yo|bonjour|salut|bonsoir)\b", re.I),
    re.compile(r"^(good\s+(morning|afternoon|evening|day))\b", re.I),
    re.compile(r"^(thanks?|thank\s*you|merci|ndeysaan)\b", re.I),
    re.compile(r"^(bye|goodbye|see\s+you|au\s*revoir)\b", re.I),
    re.compile(r"^(ok|okay|got\s+it|understood|alright|sure)\s*[.!?]*$", re.I),
    re.compile(r"^(how\s+are\s+you|what'?s\s+up|how'?s\s+it\s+going)\b", re.I),
    re.compile(r"^(yes|no|yeah|nah|yep|nope)\s*[.!?]*$", re.I),
    re.compile(r"^(who\s+are\s+you|what\s+can\s+you\s+do|what\s+are\s+you)\b", re.I),
]


def _is_conversational(message: str) -> bool:
    """Detect greetings, thanks, and small talk via fast regex."""
    text = message.strip()
    if len(text) > 80:
        return False
    return any(p.search(text) for p in _CONVERSATIONAL_PATTERNS)


def _heuristic_check(state: FieldAssistantState) -> bool | None:
    """Fast heuristic check. Returns True/False if certain, None if ambiguous.

    Catches obvious cases without an LLM call.
    """
    route = state.get("route")
    classify_result = state.get("classify_result")
    ranked_results = state.get("ranked_results", [])
    user_message = state.get("user_message", "")

    # No engines → definitely no search (observation, etc.)
    if route and not route.engines:
        return False

    # LOG_OBSERVATION intent → skip search
    if classify_result and classify_result.intent == IntentType.LOG_OBSERVATION:
        return False

    # Conversational messages (hi, thanks, bye, etc.) → skip search
    if _is_conversational(user_message):
        return False

    # FOLLOW_UP with conversation history → skip search (LLM has enough
    # context from prior turns to answer without re-searching)
    if classify_result and classify_result.intent == IntentType.FOLLOW_UP:
        history = state.get("conversation_history", [])
        if history:
            new_crop = (classify_result.crop or "").lower()
            new_disease = (classify_result.disease_name or "").lower()
            if not new_crop and not new_disease:
                return False
            # Topic changed to something new → need search
            return True

    # No classify result → play it safe, search
    if classify_result is None:
        return True

    # High confidence knowledge-seeking intent → definitely search
    if classify_result.intent in (
        IntentType.DIAGNOSE_DISEASE,
        IntentType.GET_TREATMENT,
        IntentType.IDENTIFY_IMAGE,
        IntentType.FARMING_ADVICE,
    ) and classify_result.confidence >= 0.5:
        return True

    # Default: search. Searching when uncertain is cheap (~0.2s DB)
    # vs. an LLM call to decide (~3-4s). Reranker filters noise.
    return True


def _parse_needs_search_response(response_text: str) -> bool:
    """Parse YES/NO from LLM response. Defaults to YES (safe fallback)."""
    text = response_text.strip().upper()

    if text.startswith("NO"):
        return False
    if text.startswith("YES"):
        return True

    # Look for yes/no anywhere (check YES first — safer to search than not)
    if re.search(r"\bYES\b", text):
        return True
    if re.search(r"\bNO\b", text):
        return False

    # Default: search (safe)
    log.log_step(Step.NEEDS_SEARCH, "parse_fallback", level="WARNING",
                 details={"response_preview": response_text[:200]})
    return True


def needs_search_node(state: FieldAssistantState) -> dict:
    """Decide whether the pipeline needs to search the knowledge base.

    Hybrid approach: heuristic first, LLM for ambiguous cases.

    Returns dict with: needs_search.
    """
    user_message = state.get("user_message", "")
    classify_result = state.get("classify_result")
    history = state.get("conversation_history", [])

    log.log_step(Step.NEEDS_SEARCH, "start", details={
        "intent": classify_result.intent.value if classify_result else "unknown",
        "has_ranked_results": bool(state.get("ranked_results")),
        "history_length": len(history),
    })

    # Step 1: Heuristic check
    heuristic_result = _heuristic_check(state)

    if heuristic_result is not None:
        log.log_step(Step.NEEDS_SEARCH, "decision", details={
            "needs_search": heuristic_result,
            "method": "heuristic",
            "intent": classify_result.intent.value if classify_result else "unknown",
        })
        return {"needs_search": heuristic_result}

    # Step 2: LLM decides ambiguous cases
    context_parts = [f"User message: {user_message}"]

    if history:
        recent = history[-4:]
        history_text = "\n".join(
            f"{'Farmer' if m.get('role') == 'user' else 'Assistant'}: {m.get('content', '')}"
            for m in recent
        )
        context_parts.append(f"\nRecent conversation:\n{history_text}")

    if classify_result:
        context_parts.append(
            f"\nDetected intent: {classify_result.intent.value}, "
            f"confidence: {classify_result.confidence}"
        )

    messages = [
        SystemMessage(content=NEEDS_SEARCH_SYSTEM_PROMPT),
        HumanMessage(content="\n".join(context_parts)),
    ]

    with log.timed(Step.NEEDS_SEARCH, "llm_call") as t:
        try:
            llm = get_field_llm(temperature=0.1, num_predict=64)
            response = llm.invoke(messages)
            response_text = extract_text(response)
            result = _parse_needs_search_response(response_text)
        except Exception as e:
            log.log_step(Step.NEEDS_SEARCH, "llm_error", level="ERROR",
                         details={"error": str(e)})
            result = True  # Safe fallback: search

        t.set(details={
            "needs_search": result,
            "method": "llm",
        })

    log.log_step(Step.NEEDS_SEARCH, "decision", details={
        "needs_search": result,
        "method": "llm",
        "intent": classify_result.intent.value if classify_result else "unknown",
    })

    return {"needs_search": result}
