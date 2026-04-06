"""Node: LOG OBSERVATION (LLM parse + DB write + stats).

Handles the LOG_OBSERVATION intent path. Parses the user's natural
language message into structured observation fields using LLM +
classify hints, saves to SQLite, queries stats, and returns a
confirmation with observation statistics.

This node short-circuits the search loop entirely.
"""

import json
import re
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.models import IntentType, extract_text
from app.agents.state import FieldAssistantState, trim_conversation_history
from app.logger import Step, pipeline_logger as log
from app.models.offline_llm import get_field_llm
from app.tools.observation_log import VALID_OBS_TYPES, log_observation


PARSE_OBSERVATION_PROMPT = """You are a field observation parser for an agricultural assistant in Casamance, Senegal.

Extract structured fields from the farmer's message:

- "obs_type": one of: disease_sighting, crop_condition, treatment_applied, note
- "details": the full observation text, cleaned up but preserving all information
- "location": where the observation was made (field name, area, GPS), or null if not mentioned
- "summary": a one-sentence summary for display

Output ONLY valid JSON. Example:
{
  "obs_type": "disease_sighting",
  "details": "Brown spots on cassava leaves in the lower canopy, affecting about 30% of plants",
  "location": "Field 3, near the river",
  "summary": "Brown spot disease sighting on cassava in Field 3"
}"""


def _infer_obs_type(classify_result: object | None) -> str:
    """Infer observation type from classify output as a hint."""
    if classify_result is None:
        return "note"

    disease = getattr(classify_result, "disease_name", None)
    keywords = getattr(classify_result, "keywords", [])
    keywords_lower = [k.lower() for k in keywords]

    if disease:
        return "disease_sighting"

    treatment_words = {"treatment", "treated", "applied", "sprayed", "used"}
    if treatment_words & set(keywords_lower):
        return "treatment_applied"

    condition_words = {"condition", "growth", "healthy", "wilting", "growing"}
    if condition_words & set(keywords_lower):
        return "crop_condition"

    return "note"


def _parse_observation_response(
    response_text: str,
    fallback_type: str,
    user_message: str,
) -> dict:
    """Parse LLM response into observation fields.

    Fallback chain: JSON → code block → regex → defaults.
    """
    # Tier 1: Direct JSON
    try:
        data = json.loads(response_text.strip())
        if isinstance(data, dict) and "details" in data:
            obs_type = data.get("obs_type", fallback_type)
            if obs_type not in VALID_OBS_TYPES:
                obs_type = fallback_type
            return {
                "obs_type": obs_type,
                "details": data["details"],
                "location": data.get("location"),
                "summary": data.get("summary", ""),
            }
    except (json.JSONDecodeError, Exception):
        pass

    # Tier 2: JSON in code block
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            if isinstance(data, dict) and "details" in data:
                obs_type = data.get("obs_type", fallback_type)
                if obs_type not in VALID_OBS_TYPES:
                    obs_type = fallback_type
                return {
                    "obs_type": obs_type,
                    "details": data["details"],
                    "location": data.get("location"),
                    "summary": data.get("summary", ""),
                }
        except (json.JSONDecodeError, Exception):
            pass

    # Tier 3: Regex extraction
    json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            if isinstance(data, dict) and "details" in data:
                obs_type = data.get("obs_type", fallback_type)
                if obs_type not in VALID_OBS_TYPES:
                    obs_type = fallback_type
                return {
                    "obs_type": obs_type,
                    "details": data["details"],
                    "location": data.get("location"),
                    "summary": data.get("summary", ""),
                }
        except (json.JSONDecodeError, Exception):
            pass

    # Tier 4: Safe defaults
    log.log_step(Step.OBSERVATION, "parse_fallback", level="WARNING",
                 details={"response_preview": response_text[:200]})
    return {
        "obs_type": fallback_type,
        "details": user_message,
        "location": None,
        "summary": "",
    }


def _query_observation_stats(pack) -> dict:
    """Query observation statistics from the database."""
    import sqlite3
    db_path = pack.path / "knowledge.db"
    conn = None

    try:
        conn = sqlite3.connect(str(db_path))

        # Total by type
        cursor = conn.execute(
            "SELECT type, COUNT(*) as count FROM field_observations GROUP BY type"
        )
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # Total count
        total = sum(by_type.values())

        # Most recent 3
        cursor = conn.execute(
            "SELECT type, details, timestamp FROM field_observations "
            "ORDER BY timestamp DESC LIMIT 3"
        )
        recent = [
            {"type": row[0], "details": row[1][:100], "timestamp": row[2]}
            for row in cursor.fetchall()
        ]

        return {
            "total_observations": total,
            "by_type": by_type,
            "recent": recent,
        }
    except Exception as e:
        log.log_step(Step.OBSERVATION, "stats_error", level="WARNING",
                     details={"error": str(e)})
        return {"total_observations": 0, "by_type": {}, "recent": []}
    finally:
        if conn:
            conn.close()


def log_observation_node(state: FieldAssistantState) -> dict:
    """Parse, save, and report a field observation.

    LLM call to extract structured fields, then writes to SQLite
    and returns confirmation with stats.

    Returns dict with: final_answer, observation_stats, conversation_history.
    """
    user_message = state.get("user_message", "")
    classify_result = state.get("classify_result")
    image_path = state.get("image_path")
    history = state.get("conversation_history", [])

    log.log_step(Step.OBSERVATION, "start", details={
        "message_preview": user_message[:200],
        "has_image": image_path is not None,
    })

    # Infer obs_type hint from classify output
    fallback_type = _infer_obs_type(classify_result)

    # LLM call to parse structured fields
    hint_text = ""
    if classify_result:
        if classify_result.crop:
            hint_text += f" Crop: {classify_result.crop}."
        if classify_result.disease_name:
            hint_text += f" Disease: {classify_result.disease_name}."

    messages = [
        SystemMessage(content=PARSE_OBSERVATION_PROMPT),
        HumanMessage(content=f"{user_message}{hint_text}"),
    ]

    with log.timed(Step.OBSERVATION, "llm_call") as t:
        try:
            llm = get_field_llm(temperature=0.2, num_predict=256, format="json")
            response = llm.invoke(messages)
            response_text = extract_text(response)
            parsed = _parse_observation_response(response_text, fallback_type, user_message)
        except Exception as e:
            log.log_step(Step.OBSERVATION, "llm_error", level="ERROR",
                         details={"error": str(e)})
            parsed = {
                "obs_type": fallback_type,
                "details": user_message,
                "location": None,
                "summary": "",
            }

        t.set(details={
            "obs_type": parsed["obs_type"],
            "has_location": parsed["location"] is not None,
            "details_length": len(parsed["details"]),
        })

    # Save to database
    from app.knowledge_pack.loader import get_active_pack
    pack = get_active_pack()

    if pack is None:
        log.log_step(Step.OBSERVATION, "no_pack", level="ERROR",
                     details={"error": "No active pack loaded"})
        answer = (
            "I couldn't save your observation because no Knowledge Pack is loaded. "
            "Please load a pack first."
        )
        updated_history = list(history) + [
            {"role": "user", "content": user_message,
             "timestamp": datetime.now(timezone.utc).isoformat()},
            {"role": "assistant", "content": answer,
             "timestamp": datetime.now(timezone.utc).isoformat()},
        ]
        return {
            "final_answer": answer,
            "observation_stats": {},
            "conversation_history": trim_conversation_history(updated_history),
        }

    try:
        result = log_observation(
            obs_type=parsed["obs_type"],
            details=parsed["details"],
            location=parsed["location"],
            image_path=image_path,
        )
    except Exception as e:
        log.log_step(Step.OBSERVATION, "save_error", level="ERROR",
                     details={"error": str(e), "error_type": type(e).__name__})
        answer = f"I couldn't save the observation: {e}"
        updated_history = list(history) + [
            {"role": "user", "content": user_message,
             "timestamp": datetime.now(timezone.utc).isoformat()},
            {"role": "assistant", "content": answer,
             "timestamp": datetime.now(timezone.utc).isoformat()},
        ]
        return {
            "final_answer": answer,
            "observation_stats": {},
            "conversation_history": trim_conversation_history(updated_history),
        }

    # Query stats
    with log.timed(Step.OBSERVATION, "stats") as t:
        stats = _query_observation_stats(pack)
        t.set(details={"total": stats["total_observations"]})

    # Build confirmation
    summary_text = parsed["summary"] or parsed["details"][:80]
    type_label = parsed["obs_type"].replace("_", " ")

    answer_parts = [
        f"Observation saved ({type_label}).",
        f"Summary: {summary_text}",
    ]
    if parsed["location"]:
        answer_parts.append(f"Location: {parsed['location']}")

    answer_parts.append(
        f"\nYou now have {stats['total_observations']} observation(s) recorded. "
        "They will sync when you're back online."
    )

    if stats["by_type"]:
        breakdown = ", ".join(
            f"{t.replace('_', ' ')}: {c}" for t, c in stats["by_type"].items()
        )
        answer_parts.append(f"Breakdown: {breakdown}")

    answer = "\n".join(answer_parts)

    log.log_step(Step.OBSERVATION, "complete", details={
        "observation_id": result["observation_id"],
        "obs_type": parsed["obs_type"],
        "total_observations": stats["total_observations"],
    })

    updated_history = list(history) + [
        {"role": "user", "content": user_message,
         "timestamp": datetime.now(timezone.utc).isoformat()},
        {"role": "assistant", "content": answer,
         "timestamp": datetime.now(timezone.utc).isoformat()},
    ]

    return {
        "final_answer": answer,
        "observation_stats": stats,
        "conversation_history": trim_conversation_history(updated_history),
    }
