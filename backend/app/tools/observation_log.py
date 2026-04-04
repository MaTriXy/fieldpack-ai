"""Observation logging tool.

Records field observations to SQLite for later sync when connectivity
returns. Observations track disease sightings, crop conditions,
treatments applied, and general notes.

No limit on details text — field workers need to record everything.
"""

from datetime import datetime, timezone

from langchain_core.tools import tool

from app.knowledge_pack.loader import get_active_pack
from app.logger import Step, pipeline_logger as log


# Valid observation types
VALID_OBS_TYPES = {"disease_sighting", "crop_condition", "treatment_applied", "note"}


def log_observation(
    obs_type: str,
    details: str,
    location: str | None = None,
    image_path: str | None = None,
) -> dict:
    """Log a field observation to the Knowledge Pack's SQLite database.

    Observations are stored with synced=0, ready for later upload
    when connectivity is available.

    Args:
        obs_type: One of: disease_sighting, crop_condition, treatment_applied, note.
        details: Full observation text (no length limit).
        location: Optional location description (field name, GPS, etc.).
        image_path: Optional path to an associated photo.

    Returns:
        Dict with status, observation_id, and timestamp.
    """
    pack = get_active_pack()
    if pack is None:
        log.log_step(Step.OBSERVATION, "log_no_pack", level="ERROR",
                     details={"error": "No active pack loaded"})
        raise RuntimeError("No active Knowledge Pack loaded")

    if obs_type not in VALID_OBS_TYPES:
        raise ValueError(
            f"Invalid observation type: {obs_type}. "
            f"Must be one of: {sorted(VALID_OBS_TYPES)}"
        )

    if not details or not details.strip():
        raise ValueError("Observation details cannot be empty")

    timestamp = datetime.now(timezone.utc).isoformat()

    with log.timed(Step.OBSERVATION, "log_observation") as t:
        # The loader opens sqlite_conn as read-only — we need a writable connection
        # for field_observations. Use a separate connection for writes.
        import sqlite3
        db_path = pack.path / "knowledge.db"
        conn = sqlite3.connect(str(db_path))

        try:
            cursor = conn.execute(
                "INSERT INTO field_observations (timestamp, type, location, details, image_path, synced) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                (timestamp, obs_type, location, details, image_path),
            )
            conn.commit()
            observation_id = cursor.lastrowid
        finally:
            conn.close()

        t.set(details={
            "observation_id": observation_id,
            "type": obs_type,
            "location": location,
            "details_length": len(details),
            "has_image": image_path is not None,
        })

    log.log_step(Step.OBSERVATION, "logged", details={
        "id": observation_id,
        "type": obs_type,
    })

    return {
        "status": "saved",
        "observation_id": observation_id,
        "timestamp": timestamp,
    }


def get_observations(
    obs_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Retrieve field observations, optionally filtered by type.

    Args:
        obs_type: Filter by type, or None for all.
        limit: Max observations to return (default 20).

    Returns:
        List of observation dicts.
    """
    pack = get_active_pack()
    if pack is None:
        log.log_step(Step.OBSERVATION, "get_no_pack", level="ERROR",
                     details={"error": "No active pack loaded"})
        return []

    import sqlite3
    db_path = pack.path / "knowledge.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        if obs_type:
            if obs_type not in VALID_OBS_TYPES:
                return []
            cursor = conn.execute(
                "SELECT * FROM field_observations WHERE type = ? ORDER BY timestamp DESC LIMIT ?",
                (obs_type, limit),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM field_observations ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )

        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_unsynced_observations() -> list[dict]:
    """Retrieve all observations that haven't been synced yet.

    Returns observations with synced=0, ready for upload.
    """
    pack = get_active_pack()
    if pack is None:
        log.log_step(Step.OBSERVATION, "get_unsynced_no_pack", level="ERROR",
                     details={"error": "No active pack loaded"})
        return []

    import sqlite3
    db_path = pack.path / "knowledge.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute(
            "SELECT * FROM field_observations WHERE synced = 0 ORDER BY timestamp ASC",
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# ============================================================
# @tool wrappers for LangGraph
# ============================================================

@tool
def log_observation_tool(
    obs_type: str,
    details: str,
    location: str = "",
    image_path: str = "",
) -> str:
    """Save a field observation for later sync.

    Record what you see in the field: disease sightings, crop conditions,
    treatments applied, or general notes. These are stored locally and
    synced when internet is available.

    Args:
        obs_type: Type of observation. One of:
            disease_sighting, crop_condition, treatment_applied, note.
        details: What you observed (be as detailed as needed).
        location: Where you made the observation (field name, GPS, etc.).
        image_path: Path to a photo, if you took one.
    """
    loc = location if location and location.strip() else None
    img = image_path if image_path and image_path.strip() else None

    try:
        result = log_observation(obs_type, details, loc, img)
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"

    return (
        f"Observation saved (ID: {result['observation_id']}, "
        f"type: {obs_type}, time: {result['timestamp']})"
    )


@tool
def get_observations_tool(
    obs_type: str = "",
    limit: int = 20,
) -> str:
    """Retrieve saved field observations.

    View previously recorded observations. Optionally filter by type.

    Args:
        obs_type: Filter by type (disease_sighting, crop_condition,
            treatment_applied, note). Leave empty for all.
        limit: Maximum observations to return (default 20).
    """
    ot = obs_type if obs_type and obs_type.strip() else None
    observations = get_observations(ot, limit)

    if not observations:
        return "No observations found."

    parts = []
    for i, obs in enumerate(observations, 1):
        line = f"[{i}] ({obs.get('type', '?')}) {obs.get('details', '')[:200]}"
        if obs.get("location"):
            line += f" | Location: {obs['location']}"
        parts.append(line)

    return "\n\n".join(parts)
