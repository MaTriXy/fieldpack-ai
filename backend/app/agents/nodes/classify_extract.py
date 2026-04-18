"""Node 1: CLASSIFY + EXTRACT (LLM call #1).

Classifies the user's intent and extracts structured info:
intent, crop, disease_name, keywords, needs_image, confidence.

Uses structured output (Pydantic) with NL fallback parsing.
Includes image analysis when image_path is present.
"""

import json
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from app.agents.models import ClassifyExtractOutput, IntentType, extract_text
from app.agents.state import FieldAssistantState
from app.agents.history import history_to_nl
from app.logger import Step, pipeline_logger as log
from app.models.offline_llm import get_field_llm


# ============================================================
# Observation keyword heuristic (post-LLM intent correction)
# ============================================================

_OBSERVATION_PATTERNS = [
    re.compile(r"\bi\s+(saw|noticed|spotted|observed|found)\b", re.I),
    re.compile(r"\bi['\u2019]?m\s+(seeing|noticing|reporting)\b", re.I),
    re.compile(r"\b(today|yesterday|this morning|this week)\s+i\s+(saw|found|noticed)\b", re.I),
    re.compile(r"\bfield\s*?(report|log|observation|note)\b", re.I),
    re.compile(r"\brecord\s+(this|that|my)\b", re.I),
    re.compile(r"\b\d+\s+(plants?|trees?|fields?)\s+(affected|infected|showing)\b", re.I),
]

_OBSERVATION_OVERRIDE_INTENTS = frozenset({
    IntentType.DIAGNOSE_DISEASE,
    IntentType.GET_TREATMENT,
    IntentType.GENERAL_QUESTION,
})


def _should_override_to_observation(user_message: str, llm_intent: IntentType) -> bool:
    """Check if user message looks like an observation report that the LLM misclassified."""
    if llm_intent not in _OBSERVATION_OVERRIDE_INTENTS:
        return False
    return any(p.search(user_message) for p in _OBSERVATION_PATTERNS)


# ============================================================
# System prompt + few-shot examples
# ============================================================

CLASSIFY_SYSTEM_PROMPT = """Classify an agricultural field question. Output ONLY JSON:
- "intent": diagnose_disease|get_treatment|farming_advice|identify_image|log_observation|general_question|follow_up
- "crop": crop name or null
- "disease_name": disease name or null
- "keywords": 3-5 search terms
- "needs_image": true/false
- "confidence": 0.0-1.0
- "season": wet|dry|all or null
- "growth_stage": nursery|seedling|vegetative|flowering|grain_fill|harvest|post_harvest|planning or null
- "topic_subtype": planting|irrigation|soil|pest|harvest|post_harvest|fertilization|varieties or null"""

FEW_SHOT_EXAMPLES = [
    {
        "user": "My cassava leaves have yellow patches and they are curling",
        "output": {
            "intent": "diagnose_disease",
            "crop": "cassava",
            "disease_name": None,
            "keywords": ["cassava", "yellow", "patches", "curling", "leaves"],
            "needs_image": True,
            "confidence": 0.85,
        },
    },
    {
        "user": "How do I treat rice blast with local materials?",
        "output": {
            "intent": "get_treatment",
            "crop": "rice",
            "disease_name": "Rice Blast",
            "keywords": ["rice", "blast", "treatment", "local", "materials"],
            "needs_image": False,
            "confidence": 0.9,
        },
    },
]


def _build_classify_prompt(
    user_message: str,
    image_description: str | None,
    history: list[dict],
    summary: str = "",
) -> list:
    """Build the message list for the classify LLM call.

    Includes system prompt, few-shot examples, recent history,
    and the current user message with optional image description.
    """
    messages = [SystemMessage(content=CLASSIFY_SYSTEM_PROMPT)]

    # Few-shot examples
    for ex in FEW_SHOT_EXAMPLES:
        messages.append(HumanMessage(content=ex["user"]))
        messages.append(AIMessage(content=json.dumps(ex["output"])))

    # Build user message with optional history and image context
    user_parts = []

    if history:
        history_text = history_to_nl(history, summary=summary, max_recent=2)
        if history_text:
            user_parts.append(f"Recent conversation:\n{history_text}\n")

    user_parts.append(user_message)

    if image_description:
        user_parts.append(f"\n[Image analysis: {image_description}]")

    messages.append(HumanMessage(content="\n".join(user_parts)))

    return messages


def _parse_classify_response(response_text: str) -> ClassifyExtractOutput:
    """Parse LLM response into ClassifyExtractOutput.

    Fallback chain:
      1. Direct Pydantic parse from JSON
      2. Extract JSON from code block
      3. Regex JSON extraction
      4. Safe defaults (general_question, low confidence)
    """
    # Tier 1: Direct JSON parse
    try:
        data = json.loads(response_text.strip())
        return ClassifyExtractOutput.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        pass

    # Tier 2: JSON in code block
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            return ClassifyExtractOutput.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            pass

    # Tier 3: Regex JSON extraction
    json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return ClassifyExtractOutput.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            pass

    # Tier 4: Safe defaults
    log.log_step(Step.CLASSIFY, "parse_fallback", level="WARNING",
                 details={"response_preview": response_text[:200]})
    return ClassifyExtractOutput(
        intent=IntentType.GENERAL_QUESTION,
        confidence=0.2,
    )


def classify_and_extract(state: FieldAssistantState) -> dict:
    """Classify user intent and extract structured information.

    LLM call #1. Uses structured output with NL fallback.
    If image_path is present, runs image analysis first and
    includes the visual description in the classification prompt.

    Returns dict with: classify_result, tool_calls_log updates.
    """
    user_message = state.get("user_message", "")
    image_path = state.get("image_path")
    history = state.get("conversation_history", [])

    log.log_step(Step.CLASSIFY, "start", details={
        "message_preview": user_message[:200],
        "has_image": image_path is not None,
    })

    # Image analysis (if photo provided)
    image_description = None
    if image_path:
        try:
            from app.tools.image_analysis import analyze_plant_image
            analysis = analyze_plant_image(image_path, crop_hint=None)
            image_description = analysis.get("visual_description", "")
            # Enrich with symptoms for better classification
            symptoms = analysis.get("suspected_symptoms", [])
            if symptoms:
                image_description += f" Symptoms: {', '.join(symptoms)}"
            # Include crop identification if vision model detected one
            crop_guess = analysis.get("crop_guess", "unknown")
            if crop_guess and crop_guess.lower() != "unknown":
                image_description += f" Identified crop: {crop_guess}."
        except Exception as e:
            log.log_step(Step.CLASSIFY, "image_analysis_failed", level="WARNING",
                         details={"error": str(e)})

    # Build prompt and call LLM
    summary = state.get("conversation_summary", "")
    messages = _build_classify_prompt(user_message, image_description, history, summary=summary)

    with log.timed(Step.CLASSIFY, "llm_call") as t:
        try:
            llm = get_field_llm(temperature=0.1, num_predict=256, format="json")
            response = llm.invoke(messages)
            response_text = extract_text(response)
        except Exception as e:
            log.log_step(Step.CLASSIFY, "llm_error", level="ERROR",
                         details={"error": str(e)})
            # Return safe defaults on LLM failure
            return {
                "classify_result": ClassifyExtractOutput(
                    intent=IntentType.GENERAL_QUESTION,
                    confidence=0.1,
                ),
                "error": f"Classification failed: {e}",
            }

        result = _parse_classify_response(response_text)

        # Post-LLM observation heuristic: catch "I saw/noticed..." misclassified as disease
        if _should_override_to_observation(user_message, result.intent):
            log.log_step(Step.CLASSIFY, "observation_override", details={
                "original_intent": result.intent.value,
            })
            result.intent = IntentType.LOG_OBSERVATION

        t.set(details={
            "intent": result.intent.value,
            "crop": result.crop,
            "disease_name": result.disease_name,
            "keywords": result.keywords[:5],
            "confidence": result.confidence,
            "has_image_description": image_description is not None,
        })

    # Heuristic fallback: if LLM missed the crop but user said it, extract it
    if not result.crop:
        try:
            from app.knowledge_pack.loader import get_active_pack
            pack = get_active_pack()
            if pack and pack.manifest and pack.manifest.crops:
                msg_lower = user_message.lower()
                for crop_name in pack.manifest.crops:
                    if crop_name.lower() in msg_lower:
                        result.crop = crop_name
                        log.log_step(Step.CLASSIFY, "crop_heuristic_rescue",
                                     details={"crop": crop_name, "source": "user_message"})
                        break
        except Exception:
            pass

    # Ask-back: image present but crop unknown — ask the user
    if image_path and image_description and not result.crop:
        log.log_step(Step.CLASSIFY, "ask_crop", details={
            "reason": "Image provided but crop not identified"})
        from datetime import datetime, timezone
        from app.agents.state import trim_conversation_history
        ask_msg = (
            "I can see signs of disease in your photo, but I'm not sure which crop this is. "
            "Could you tell me the crop name? For example: cassava, rice, maize, groundnut, or tomato."
        )
        updated_history = list(history) + [
            {"role": "user", "content": user_message,
             "timestamp": datetime.now(timezone.utc).isoformat()},
            {"role": "assistant", "content": ask_msg,
             "timestamp": datetime.now(timezone.utc).isoformat()},
        ]
        return {
            "classify_result": result,
            "image_description": image_description,
            "final_answer": ask_msg,
            "needs_search": False,
            "conversation_history": trim_conversation_history(updated_history),
        }

    return {"classify_result": result, "image_description": image_description}
