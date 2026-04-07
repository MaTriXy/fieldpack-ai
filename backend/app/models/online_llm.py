"""Online LLM wrappers for Phase 1 (Google AI Studio).

Two model tiers:
  - Research (26B MoE): high throughput extraction, 4B active params
  - Planner (31B Dense): reasoning-heavy tasks (gap analysis, compilation)

Both use:
  - thinking_level='minimal' to cut thinking overhead (~2.6x speedup)
  - response_mime_type='application/json' for native JSON output

invoke_structured() replaces with_structured_output() which hangs on
Gemma 4. It calls ainvoke(), parses the JSON response, and validates
with the Pydantic model. On parse failure it retries once with the
error appended to the prompt.
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, ValidationError

from app.config import settings

T = TypeVar("T", bound=BaseModel)


def get_planner_llm(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    """Gemma 4 31B — used for mission planning and knowledge compilation."""
    return ChatGoogleGenerativeAI(
        model=settings.online_model_large,
        google_api_key=settings.google_ai_studio_api_key,
        temperature=temperature,
        thinking_level="minimal",
        response_mime_type="application/json",
    )


def get_research_llm() -> ChatGoogleGenerativeAI:
    """Gemma 4 26B MoE — used for parallel research agents."""
    return ChatGoogleGenerativeAI(
        model=settings.online_model_research,
        google_api_key=settings.google_ai_studio_api_key,
        temperature=0.4,
        thinking_level="minimal",
        response_mime_type="application/json",
    )


# ------------------------------------------------------------------
# JSON extraction from LLM response
# ------------------------------------------------------------------

# Matches ```json ... ``` or ``` ... ``` code fences
_CODE_FENCE_RE = re.compile(
    r"```(?:json)?\s*\n?(.*?)```",
    re.DOTALL,
)


def _extract_json_text(content) -> str:
    """Extract the JSON string from an LLM response content.

    Handles:
      - Plain string responses
      - List[dict] with thinking + text blocks (Gemma 4 format)
      - Code-fence-wrapped JSON
    """
    # If content is a list of blocks (Gemma 4 thinking format)
    if isinstance(content, list):
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block["text"])
            elif isinstance(block, str):
                text_parts.append(block)
        raw = "\n".join(text_parts)
    else:
        raw = str(content)

    raw = raw.strip()

    # Strip code fences if present — use last match (first may be thinking noise)
    fence_matches = _CODE_FENCE_RE.findall(raw)
    if fence_matches:
        return fence_matches[-1].strip()

    return raw


async def invoke_structured(
    llm: ChatGoogleGenerativeAI,
    prompt: str,
    model_class: type[T],
    *,
    max_retries: int = 1,
) -> T:
    """Call the LLM and parse the response into a Pydantic model.

    Replaces llm.with_structured_output(Model).ainvoke(prompt) which
    hangs on Gemma 4. Uses response_mime_type='application/json' (set
    on the LLM instance) for native JSON output, then validates with
    Pydantic.

    On JSON parse or validation failure, retries once with the error
    message appended to the prompt so the LLM can self-correct.

    Args:
        llm: ChatGoogleGenerativeAI instance (with response_mime_type set).
        prompt: The full prompt text.
        model_class: Pydantic BaseModel subclass to validate against.
        max_retries: Number of retry attempts on parse/validation failure.

    Returns:
        Validated Pydantic model instance.

    Raises:
        ValueError: If all attempts fail to produce valid output.
    """
    last_error = ""

    for attempt in range(1, max_retries + 2):  # +2 because range is exclusive
        current_prompt = prompt
        if last_error:
            current_prompt += (
                f"\n\n--- PREVIOUS ATTEMPT FAILED ---\n"
                f"Your response could not be parsed. Fix these errors:\n"
                f"{last_error}\n"
                f"--- END ERRORS ---\n"
                f"Return ONLY valid JSON matching the required schema."
            )

        # Append JSON schema on first attempt so the LLM sees field
        # descriptions, valid enum values, and types — replicating what
        # with_structured_output() did automatically.
        if attempt == 1 and not last_error:
            schema = json.dumps(model_class.model_json_schema(), indent=2)
            current_prompt += (
                f"\n\nRespond with JSON matching this schema:\n{schema}"
            )

        result = await llm.ainvoke(current_prompt)
        json_text = _extract_json_text(result.content)

        # Try to parse JSON
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            last_error = f"Invalid JSON: {exc}. Response started with: {json_text[:200]}"
            if attempt <= max_retries:
                continue
            raise ValueError(
                f"Failed to parse JSON after {attempt} attempts. "
                f"Last error: {last_error}"
            )

        # Auto-wrap bare arrays: if the LLM returned [...] but the model
        # expects {"field": [...]}, wrap it into the single list field.
        # Gemma 4 frequently drops the wrapper object.
        if isinstance(parsed, list):
            list_fields = [
                name for name, info in model_class.model_fields.items()
                if hasattr(info.annotation, "__origin__")
                and info.annotation.__origin__ is list
            ]
            if len(list_fields) == 1:
                parsed = {list_fields[0]: parsed}

        # Validate with Pydantic
        try:
            return model_class.model_validate(parsed)
        except ValidationError as exc:
            last_error = str(exc)[:800]
            if attempt <= max_retries:
                continue
            raise ValueError(
                f"Pydantic validation failed after {attempt} attempts. "
                f"Last error: {last_error}"
            )

    # Should not reach here, but just in case
    raise ValueError(f"invoke_structured exhausted all attempts. Last error: {last_error}")
