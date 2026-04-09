import logging

from fastapi import APIRouter, HTTPException
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


class MissionCard(BaseModel):
    region: str = Field(description="Geographic region, e.g. 'Casamance, Senegal'")
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
- Infer season from the region if not stated (e.g., Casamance → "Rainy (Jul–Oct)").
- Infer reasonable focus_areas if not stated (default to ["Disease ID", "Treatment Protocols", "Farming Calendar"]).
- Once you have at least region + 1 crop, set ready=true and fill the mission_card.
- Estimate scale_estimate based on crop count (roughly 30 records per crop from 4 sources).
- Keep replies short and friendly (1-3 sentences).
- Do NOT invent information the user didn't provide or that can't be reasonably inferred.\
"""


def _build_mission_chat_prompt(message: str, history: list[MissionChatMessage]) -> str:
    parts = [_MISSION_CHAT_SYSTEM, ""]
    for msg in history:
        role_label = "User" if msg.role == "user" else "Assistant"
        parts.append(f"{role_label}: {msg.content}")
    parts.append(f"User: {message}")
    return "\n".join(parts)


@router.post("/chat", response_model=MissionChatResponse)
async def mission_chat(req: MissionChatRequest):
    """Parse a mission description via Gemma 4 31B and extract structured fields."""
    from app.models.online_llm import get_planner_llm, invoke_structured

    llm = get_planner_llm(temperature=0.3)
    prompt = _build_mission_chat_prompt(req.message, req.conversation_history)

    try:
        result = await invoke_structured(llm, prompt, _MissionChatLLMOutput)
    except ValueError as exc:
        logger.warning("Mission chat LLM parsing failed: %s", exc)
        raise HTTPException(status_code=502, detail="Mission planner could not process the request")

    return MissionChatResponse(
        reply=result.reply,
        mission_card=result.mission_card if result.ready else None,
    )
