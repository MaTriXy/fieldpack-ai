from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/mission", tags=["mission"])


class MissionRequest(BaseModel):
    description: str
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
