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


@router.get("/{obs_id}", response_model=ObservationOut)
def get_observation(obs_id: int):
    """Get a single observation by ID."""
    obs = get_observation_by_id(obs_id)
    if obs is None:
        raise HTTPException(404, "Observation not found")
    return ObservationOut(**obs)
