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

from app.agents.models import ClassifyExtractOutput, IntentType
from app.agents.state import FieldAssistantState
from app.agents.history import history_to_nl
from app.logger import Step, pipeline_logger as log
from app.models.offline_llm import get_field_llm


# ============================================================
# System prompt + few-shot examples
# ============================================================

CLASSIFY_SYSTEM_PROMPT = """You are a classification system for an agricultural field assistant in Casamance, Senegal.

Analyze the user's message and output JSON with these fields:
- "intent": one of: diagnose_disease, get_treatment, farming_advice, identify_image, log_observation, general_question, follow_up
- "crop": the crop mentioned (cassava, rice, maize, groundnut, tomato) or null
- "disease_name": specific disease name if mentioned, or null
- "keywords": list of 3-5 important search terms from the message
- "needs_image": true if the user is describing visual symptoms that would benefit from a photo
- "confidence": 0.0 to 1.0, how confident you are in the classification
- "season": "wet", "dry", or "all" if the question relates to a specific season, or null
- "growth_stage": one of: nursery, seedling, vegetative, flowering, grain_fill, harvest, post_harvest, planning — or null if not applicable
- "topic_subtype": one of: planting, irrigation, soil, pest, harvest, post_harvest, fertilization, varieties — or null if not a farming question

If this is a follow-up to a previous conversation, determine what the user is actually asking about and classify as that intent (not as follow_up).

Output ONLY valid JSON. No explanation."""

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
            "season": None,
            "growth_stage": None,
            "topic_subtype": None,
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
            "season": None,
            "growth_stage": None,
            "topic_subtype": None,
        },
    },
    {
        "user": "When should I plant rice in Casamance?",
        "output": {
            "intent": "farming_advice",
            "crop": "rice",
            "disease_name": None,
            "keywords": ["rice", "planting", "timing", "Casamance", "season"],
            "needs_image": False,
            "confidence": 0.9,
            "season": "wet",
            "growth_stage": "planning",
            "topic_subtype": "planting",
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
            response_text = response.content if hasattr(response, "content") else str(response)
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
        t.set(details={
            "intent": result.intent.value,
            "crop": result.crop,
            "disease_name": result.disease_name,
            "keywords": result.keywords[:5],
            "confidence": result.confidence,
            "has_image_description": image_description is not None,
        })

    return {"classify_result": result}
