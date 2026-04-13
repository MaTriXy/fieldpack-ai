import json
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mission", tags=["mission"])


class MissionRequest(BaseModel):
    description: str = ""
    region: str | None = None
    crops: list[str] = []


class MissionStatus(BaseModel):
    mission_id: str
    status: str  # "planning" | "researching" | "compiling" | "complete" | "error"
    progress: float  # 0.0 - 1.0
    current_step: str
    pack_id: str | None = None


@router.post("/start", response_model=MissionStatus)
async def start_mission(req: MissionRequest):
    """Phase 1: Start a knowledge-gathering mission."""
    # TODO: wire to mission_planner → research_agents → knowledge_compiler
    return MissionStatus(
        mission_id="stub-mission-001",
        status="planning",
        progress=0.0,
        current_step="Mission planner analyzing request...",
    )


@router.get("/status/{mission_id}", response_model=MissionStatus)
async def get_mission_status(mission_id: str):
    """Poll the status of a running mission."""
    # TODO: read from mission state store
    return MissionStatus(
        mission_id=mission_id,
        status="planning",
        progress=0.0,
        current_step="Awaiting implementation",
    )


# ------------------------------------------------------------------
# /mission/chat — conversational mission planner
# ------------------------------------------------------------------


class MissionChatMessage(BaseModel):
    role: str
    content: str


class MissionChatRequest(BaseModel):
    message: str = Field(max_length=2000)
    conversation_history: list[MissionChatMessage] = Field(default_factory=list)
    language: str | None = None


class MissionCard(BaseModel):
    region: str = Field(description="Geographic region, e.g. 'Eastern Kenya'")
    crops: list[str] = Field(description="List of crop names, e.g. ['Cassava', 'Rice']")
    season: str = Field(description="Growing season, e.g. 'Rainy (Jul-Oct)'")
    focus_areas: list[str] = Field(description="Research focus areas, e.g. ['Disease ID', 'Treatment Protocols']")
    scale_estimate: str | None = Field(None, description="Estimated scale, e.g. '~150 records from 4 sources'")


class _MissionChatLLMOutput(BaseModel):
    """Schema the LLM must produce."""
    reply: str = Field(description="Conversational response to the user. If you need more info, ask here.")
    ready: bool = Field(description="True if enough info to build a mission card, False if still gathering info")
    mission_card: MissionCard | None = Field(None, description="Set ONLY when ready=True and you have region, crops, season, and focus_areas")


class MissionChatResponse(BaseModel):
    reply: str
    mission_card: MissionCard | None = None


_MISSION_CHAT_SYSTEM = """\
You are FieldPack AI's mission planner. You help humanitarian field workers \
plan a Knowledge Pack for their deployment.

Gather these 4 pieces of information:
1. **Region** — where they are going (country + sub-region if possible)
2. **Crops** — which crops they will work with (at least 1)
3. **Season** — the growing season or time of year
4. **Focus areas** — what they need help with (e.g., Disease ID, Treatment Protocols, \
Farming Calendar, Pest Management, Soil Health, Seed Varieties, Post-Harvest Storage)

Rules:
- If the user provides partial info, acknowledge what you understood and ask for the rest.
- Infer season from the region if not stated.
- Infer reasonable focus_areas if not stated (default to ["Disease ID", "Treatment Protocols", "Farming Calendar"]).
- Once you have at least region + 1 crop, set ready=true and fill the mission_card.
- Estimate scale_estimate based on crop count (roughly 30 records per crop from 4 sources).
- Keep replies short and friendly (1-3 sentences).
- Do NOT invent information the user didn't provide or that can't be reasonably inferred.\
"""


_MISSION_LANGUAGE_INSTRUCTIONS = {
    "fr": "IMPORTANT: Respond entirely in French (Francais).",
    "wo": "IMPORTANT: Respond entirely in Wolof.",
    "pt": "IMPORTANT: Respond entirely in Portuguese (Portugues).",
}


def _build_mission_chat_prompt(
    message: str,
    history: list[MissionChatMessage],
    language: str | None = None,
) -> str:
    lang_instruction = (
        _MISSION_LANGUAGE_INSTRUCTIONS.get(language)
        if language and language != "en"
        else None
    )
    system = (
        lang_instruction + "\n\n" + _MISSION_CHAT_SYSTEM
        if lang_instruction
        else _MISSION_CHAT_SYSTEM
    )
    parts = [system, ""]
    for msg in history:
        role_label = "User" if msg.role == "user" else "Assistant"
        parts.append(f"{role_label}: {msg.content}")
    parts.append(f"User: {message}")
    return "\n".join(parts)


@router.post("/chat", response_model=MissionChatResponse)
async def mission_chat(req: MissionChatRequest):
    """Parse a mission description via LLM (Google AI Studio with Ollama fallback)."""
    prompt = _build_mission_chat_prompt(req.message, req.conversation_history, req.language)

    # Try Google AI Studio first (online planner)
    result = await _try_google_planner(prompt)

    # Fallback to Ollama (tunnel or local) if Google fails
    if result is None:
        result = await _try_ollama_planner(prompt)

    if result is None:
        raise HTTPException(status_code=502, detail="Mission planner unavailable. No LLM reachable.")

    return MissionChatResponse(
        reply=result.reply,
        mission_card=result.mission_card if result.ready else None,
    )


async def _try_google_planner(prompt: str) -> _MissionChatLLMOutput | None:
    try:
        from app.models.online_llm import get_planner_llm, invoke_structured
        llm = get_planner_llm(temperature=0.3)
        return await invoke_structured(llm, prompt, _MissionChatLLMOutput)
    except Exception as exc:
        logger.warning("Google AI Studio planner failed, trying Ollama: %s", exc)
        return None


async def _try_ollama_planner(prompt: str) -> _MissionChatLLMOutput | None:
    import json as _json  # shadow module-level json to avoid name collision
    try:
        from app.models.offline_llm import get_field_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        schema = _json.dumps(_MissionChatLLMOutput.model_json_schema(), indent=2)
        llm = get_field_llm(temperature=0.3, format="json")
        messages = [
            SystemMessage(content=f"Respond with JSON matching this schema:\n{schema}"),
            HumanMessage(content=prompt),
        ]
        response = await llm.ainvoke(messages)
        text = response.content if isinstance(response.content, str) else str(response.content)
        parsed = _json.loads(text)
        return _MissionChatLLMOutput.model_validate(parsed)
    except Exception as exc:
        logger.warning("Ollama planner fallback also failed: %s", exc)
        return None


# ------------------------------------------------------------------
# /mission/ws — streaming agent farm pipeline
# ------------------------------------------------------------------


@router.websocket("/ws")
async def mission_ws(websocket: WebSocket):
    from app.agent_farm.graph import run_agent_farm_stream

    await websocket.accept()
    try:
        data = await websocket.receive_text()
        try:
            msg = json.loads(data)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "message": "Invalid JSON"})
            await websocket.close(code=1003)
            return

        crops: list[str] = msg.get("crops", [])
        region: str = msg.get("region", "")
        description: str = msg.get("description", "")

        if not region or not crops:
            await websocket.send_json({"type": "error", "message": "region and at least one crop are required"})
            await websocket.close(code=1003)
            return

        logger.info(
            "mission_ws: starting pipeline region=%r crops=%r", region, crops
        )

        try:
            async for event in run_agent_farm_stream(
                crops=crops,
                region=region,
                mission_description=description,
            ):
                await websocket.send_json(event)
        except WebSocketDisconnect:
            raise
        except Exception as exc:
            logger.exception("mission_ws: pipeline error — %s", exc)
            await websocket.send_json({"type": "error", "message": "Pipeline error. Check server logs."})

    except WebSocketDisconnect:
        pass


# ------------------------------------------------------------------
# /mission/chat/ws — streaming mission chat via WebSocket
# ------------------------------------------------------------------


@router.websocket("/chat/ws")
async def mission_chat_stream_ws(websocket: WebSocket):
    """Stream mission chat responses via WebSocket."""
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        try:
            msg = json.loads(data)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "message": "Invalid JSON"})
            await websocket.close(code=1003)
            return

        message = msg.get("message", "")
        history = [
            MissionChatMessage(role=m["role"], content=m["content"])
            for m in msg.get("conversation_history", [])
        ]
        language = msg.get("language")

        prompt = _build_mission_chat_prompt(message, history, language)

        # Emit planning status
        await websocket.send_json({"type": "status", "step": "planning"})

        # Try Google AI Studio first
        result = await _try_google_planner(prompt)

        if result is None:
            # Fallback to Ollama
            await websocket.send_json({"type": "status", "step": "fallback"})
            result = await _try_ollama_planner(prompt)

        if result is None:
            await websocket.send_json({
                "type": "error",
                "message": "Mission planner unavailable. No LLM reachable.",
            })
        else:
            await websocket.send_json({
                "type": "done",
                "reply": result.reply,
                "mission_card": result.mission_card.model_dump() if result.ready and result.mission_card else None,
            })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("mission_chat_stream_ws error: %s", exc)
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
