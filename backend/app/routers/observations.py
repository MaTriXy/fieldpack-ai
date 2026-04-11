"""Field observations REST router.

Exposes CRUD for field_observations stored in the active Knowledge Pack's
SQLite database.  Reuses functions from app.tools.observation_log.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.knowledge_pack.loader import get_active_pack
from app.tools.observation_log import (
    count_observations,
    get_observation_by_id,
    get_observation_stats,
    get_observations,
    log_observation,
)

router = APIRouter(prefix="/observations", tags=["observations"])


# ── Pydantic models ──────────────────────────────────────────

class ObservationCreate(BaseModel):
    type: str
    details: str
    location: str | None = None
    image_path: str | None = None


class ObservationOut(BaseModel):
    id: int
    timestamp: str
    type: str
    location: str | None
    details: str
    image_path: str | None
    synced: int
    crop_id: int | None = None
    severity_observed: str | None = None


class ObservationListResponse(BaseModel):
    observations: list[ObservationOut]
    total: int
    unsynced_count: int


class ObservationStatsResponse(BaseModel):
    total: int
    unsynced: int
    by_type: dict[str, int]
    recent: list[dict]


# ── Endpoints ────────────────────────────────────────────────

@router.get("/", response_model=ObservationListResponse)
def list_observations(type: str | None = None, limit: int = Query(default=50, ge=1, le=500)):
    """List observations, optionally filtered by type."""
    observations = get_observations(obs_type=type, limit=limit)
    total = count_observations(obs_type=type)
    stats = get_observation_stats()
    return ObservationListResponse(
        observations=[ObservationOut(**o) for o in observations],
        total=total,
        unsynced_count=stats["unsynced"],
    )


@router.get("/stats", response_model=ObservationStatsResponse)
def observation_stats():
    """Get observation summary statistics."""
    stats = get_observation_stats()
    return ObservationStatsResponse(
        total=stats["total_observations"],
        unsynced=stats["unsynced"],
        by_type=stats["by_type"],
        recent=stats["recent"],
    )


@router.post("/")
def create_observation(body: ObservationCreate):
    """Create a new observation directly (no LLM parsing)."""
    pack = get_active_pack()
    if pack is None:
        raise HTTPException(503, "No Knowledge Pack loaded")

    try:
        result = log_observation(
            obs_type=body.type,
            details=body.details,
            location=body.location,
            image_path=body.image_path,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    return {
        "status": "saved",
        "observation_id": result["observation_id"],
        "timestamp": result["timestamp"],
    }


class SummaryResponse(BaseModel):
    summary: str
    observation_count: int


@router.post("/summary", response_model=SummaryResponse)
def summarize_observations(limit: int = Query(default=20, ge=1, le=100)):
    """Generate AI summary of recent observations."""
    pack = get_active_pack()
    if pack is None:
        raise HTTPException(503, "No Knowledge Pack loaded")

    observations = get_observations(limit=limit)
    if not observations:
        raise HTTPException(404, "No observations to summarize")

    from langchain_core.messages import HumanMessage, SystemMessage
    from app.agents.models import extract_text
    from app.models.offline_llm import get_field_llm

    obs_text = "\n".join(
        f"- [{o['type']}] {o['timestamp'][:10]}: {o['details']}"
        + (f" (location: {o['location']})" if o.get("location") else "")
        + (f" (severity: {o['severity_observed']})" if o.get("severity_observed") else "")
        for o in observations
    )

    try:
        llm = get_field_llm(temperature=0.3, num_predict=512)
        response = llm.invoke([
            SystemMessage(content=(
                "You are a field agriculture analyst. Summarize these field observations "
                "into a concise actionable intelligence brief for a humanitarian field worker. "
                "Highlight: (1) key patterns or trends, (2) areas needing urgent attention, "
                "(3) recommended next steps. Be specific and practical. "
                "Use bullet points. Keep under 300 words."
            )),
            HumanMessage(content=f"Here are the {len(observations)} most recent field observations:\n\n{obs_text}"),
        ])
        summary = extract_text(response)
    except Exception as e:
        raise HTTPException(503, "AI unavailable — check that Ollama is running")

    return SummaryResponse(summary=summary, observation_count=len(observations))


@router.get("/{obs_id}", response_model=ObservationOut)
def get_observation(obs_id: int):
    """Get a single observation by ID."""
    obs = get_observation_by_id(obs_id)
    if obs is None:
        raise HTTPException(404, "Observation not found")
    return ObservationOut(**obs)
