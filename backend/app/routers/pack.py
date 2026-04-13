import json

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.demo_replay import get_demo_pack_info
from app.knowledge_pack.loader import get_active_pack, load_pack as loader_load_pack, unload_pack
from app.logger import Step, pipeline_logger as log
from app.tools.fts_search import fts_search
from app.tools.sqlite_query import structured_query
from app.tools.chroma_search import chroma_search

router = APIRouter(prefix="/packs", tags=["packs"])


class PackInfo(BaseModel):
    pack_id: str
    name: str
    region: str
    crops: list[str]
    diseases_count: int
    knowledge_entries: int = 0
    sources: list[str] = []
    loaded: bool = False


class PackLoadResponse(BaseModel):
    status: str
    pack_id: str
    name: str
    region: str
    crops: list[str]
    diseases_count: int


@router.get("/", response_model=list[PackInfo])
async def list_packs():
    """List all available Knowledge Packs."""
    if settings.demo_mode:
        info = get_demo_pack_info()
        return [PackInfo(
            pack_id=info["pack_id"],
            name=info["name"],
            region=info["region"],
            crops=info["crops"],
            diseases_count=15,
            knowledge_entries=info["knowledge_entries"],
            sources=info["sources"],
            loaded=True,
        )]

    packs = []
    packs_dir = settings.packs_path
    active = get_active_pack()
    active_path = active.path.resolve() if active else None

    for pack_dir in packs_dir.iterdir():
        manifest = pack_dir / "manifest.json"
        if pack_dir.is_dir() and manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            stats = data.get("statistics", {})
            packs.append(PackInfo(
                pack_id=pack_dir.name,
                name=data.get("name", pack_dir.name),
                region=", ".join(filter(None, [
                    data.get("region", {}).get("name"),
                    data.get("region", {}).get("country"),
                ])) or "Unknown",
                crops=data.get("crops", []),
                diseases_count=stats.get("diseases_count", 0),
                knowledge_entries=stats.get("text_chunks", 0),
                sources=data.get("sources", []),
                loaded=pack_dir.resolve() == active_path,
            ))
    return packs


@router.post("/load/{pack_id}", response_model=PackLoadResponse)
async def load_pack_endpoint(pack_id: str):
    """Load a Knowledge Pack for offline use."""
    if settings.demo_mode:
        info = get_demo_pack_info()
        return PackLoadResponse(
            status="loaded",
            pack_id=info["pack_id"],
            name=info["name"],
            region=info["region"],
            crops=info["crops"],
            diseases_count=15,
        )

    pack_path = (settings.packs_path / pack_id).resolve()
    packs_root = settings.packs_path.resolve()
    if not pack_path.is_relative_to(packs_root):
        raise HTTPException(status_code=400, detail="Invalid pack ID")
    if not pack_path.exists():
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    manifest_path = pack_path / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=400, detail=f"Pack '{pack_id}' has no manifest.json")

    log.log_step(Step.PACK_LOAD, "loading", details={"pack_id": pack_id})

    try:
        pack = loader_load_pack(pack_path)
    except Exception as e:
        log.log_step(Step.PACK_LOAD, "load_error", level="ERROR",
                     details={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to load pack. Check server logs.")

    # Use already-validated manifest from the loaded pack (no second disk read)
    manifest = pack.manifest

    log.log_step(Step.PACK_LOAD, "loaded", details={
        "pack_id": pack_id,
        "name": manifest.name,
    })

    return PackLoadResponse(
        status="loaded",
        pack_id=pack_id,
        name=manifest.name,
        region=", ".join(filter(None, [
            manifest.region.name if manifest.region else None,
            manifest.region.country if manifest.region else None,
        ])) or "Unknown",
        crops=manifest.crops,
        diseases_count=manifest.statistics.diseases_count if manifest.statistics else 0,
    )


@router.post("/unload")
async def unload_pack_endpoint():
    """Unload the currently active Knowledge Pack."""
    active = get_active_pack()
    if active is None:
        return {"status": "no_pack_loaded"}

    unload_pack()
    log.log_step(Step.PACK_LOAD, "unloaded")
    return {"status": "unloaded"}


# ============================================================
# Badge color constants
# ============================================================

_COLOR_PRIMARY = "bg-primary/10 text-primary"
_COLOR_SECONDARY = "bg-secondary/10 text-secondary"
_COLOR_TERTIARY = "bg-tertiary/10 text-tertiary"
_COLOR_MUTED = "bg-text-muted/10 text-text-muted"

# Map severity values -> badge color
_SEVERITY_COLORS = {
    "critical": _COLOR_PRIMARY,
    "high": _COLOR_PRIMARY,
    "medium": _COLOR_TERTIARY,
    "low": _COLOR_MUTED,
}

# Map difficulty values -> badge color
_DIFFICULTY_COLORS = {
    "easy": _COLOR_SECONDARY,
    "medium": _COLOR_TERTIARY,
    "hard": _COLOR_PRIMARY,
}


def _severity_badge(severity: str) -> dict:
    color = _SEVERITY_COLORS.get(severity.lower(), _COLOR_MUTED)
    return {"label": severity, "color": color}


def _difficulty_badge(difficulty: str) -> dict:
    color = _DIFFICULTY_COLORS.get(difficulty.lower(), _COLOR_MUTED)
    return {"label": difficulty, "color": color}


def _label_badge(label: str, color: str = _COLOR_SECONDARY) -> dict:
    return {"label": label, "color": color}


# ============================================================
# Per-category result builders
# ============================================================

def _build_disease_item(result) -> dict:
    m = result.metadata
    badges = []
    crop = m.get("crop") or m.get("crops")
    if crop:
        badges.append(_label_badge(crop, _COLOR_SECONDARY))
    severity = m.get("severity_scale") or m.get("severity")
    if severity:
        badges.append(_severity_badge(severity))
    pathogen = m.get("type")
    if pathogen:
        badges.append(_label_badge(pathogen, _COLOR_MUTED))

    details = []
    if m.get("visual_markers"):
        details.append(m["visual_markers"])
    if m.get("spread_mechanism"):
        details.append(m["spread_mechanism"])
    if m.get("affected_growth_stage"):
        details.append(m["affected_growth_stage"])

    return {
        "id": m.get("id", result.source),
        "type": "disease",
        "title": m.get("name", "Unknown Disease"),
        "description": m.get("symptoms_text", ""),
        "badges": badges,
        "details": details,
    }


def _build_treatment_item(result) -> dict:
    m = result.metadata
    badges = []
    difficulty = m.get("difficulty")
    if difficulty:
        badges.append(_difficulty_badge(difficulty))
    method_type = m.get("treatment_type")
    if method_type:
        badges.append(_label_badge(method_type, _COLOR_TERTIARY))
    if m.get("is_organic") in ("1", "True", "true"):
        badges.append(_label_badge("organic", _COLOR_SECONDARY))

    details = []
    if m.get("materials_needed"):
        details.append(m["materials_needed"])
    if m.get("local_availability"):
        details.append(m["local_availability"])
    if m.get("application_timing"):
        details.append(m["application_timing"])

    return {
        "id": m.get("id", result.source),
        "type": "treatment",
        "title": m.get("method", m.get("name", "Unknown Treatment")),
        "description": m.get("description", ""),
        "badges": badges,
        "details": details,
    }


def _build_pest_item(result) -> dict:
    m = result.metadata
    badges = []
    crop = m.get("crop") or m.get("crops")
    if crop:
        badges.append(_label_badge(crop, _COLOR_SECONDARY))
    pest_type = m.get("type")
    if pest_type:
        badges.append(_label_badge(pest_type, _COLOR_MUTED))
    season = m.get("season_peak")
    if season:
        badges.append(_label_badge(season, _COLOR_TERTIARY))

    details = []
    if m.get("identification_notes"):
        details.append(m["identification_notes"])
    if m.get("control_organic"):
        details.append(m["control_organic"])
    if m.get("prevention_notes"):
        details.append(m["prevention_notes"])

    return {
        "id": m.get("id", result.source),
        "type": "pest",
        "title": m.get("name", "Unknown Pest"),
        "description": m.get("damage_description", m.get("description", "")),
        "badges": badges,
        "details": details,
    }


def _build_practice_item(result) -> dict:
    m = result.metadata
    badges = []
    crop = m.get("crop")
    if crop:
        badges.append(_label_badge(crop, _COLOR_SECONDARY))
    practice_type = m.get("practice_type")
    if practice_type:
        badges.append(_label_badge(practice_type, _COLOR_TERTIARY))
    season = m.get("season")
    if season:
        badges.append(_label_badge(season, _COLOR_MUTED))

    # Chroma results carry document text in content / parent_content
    description = result.parent_content or result.content or ""

    details = []
    growth_stage = m.get("growth_stage")
    if growth_stage:
        details.append(growth_stage)
    topic = m.get("topic")
    if topic:
        details.append(topic)

    return {
        "id": m.get("topic_id", result.source),
        "type": "practice",
        "title": m.get("title", "Practice"),
        "description": description,
        "badges": badges,
        "details": details,
    }


def _build_climate_item(result) -> dict:
    m = result.metadata
    badges = []
    region = m.get("region")
    if region:
        badges.append(_label_badge(region, _COLOR_SECONDARY))
    drought_risk = m.get("drought_risk")
    if drought_risk:
        badges.append(_severity_badge(drought_risk))
    month = m.get("month")
    if month:
        badges.append(_label_badge(f"Month {month}", _COLOR_MUTED))

    details = []
    if m.get("rainfall_mm"):
        details.append(f"Rainfall: {m['rainfall_mm']} mm")
    if m.get("temperature_avg_c"):
        details.append(f"Avg temp: {m['temperature_avg_c']} C")
    if m.get("notes"):
        details.append(m["notes"])

    return {
        "id": m.get("id", result.source),
        "type": "climate",
        "title": f"{m.get('region', 'Region')} - Month {m.get('month', '?')}",
        "description": m.get("notes", ""),
        "badges": badges,
        "details": details,
    }


# ============================================================
# Category fetch helpers  (search path vs. browse path)
# ============================================================

_CATEGORY_FTS_TABLE = {
    "disease":   "diseases_fts",
    "treatment": "treatments_fts",
    "pest":      "pests_fts",
}

_CATEGORY_STRUCT_TABLE = {
    "disease":   "diseases",
    "treatment": "treatments",
    "pest":      "pests",
    "climate":   "climate",
}

_CATEGORY_BUILDER = {
    "disease":   _build_disease_item,
    "treatment": _build_treatment_item,
    "pest":      _build_pest_item,
    "practice":  _build_practice_item,
    "climate":   _build_climate_item,
}

_PRACTICE_CHROMA_COLLECTION = "farming_practices"
# Sentinel query used when browsing practices without a search term
_PRACTICE_BROWSE_QUERY = "farming practices planting soil crop management"


def _fetch_category(category: str, search: str, limit: int) -> list[dict]:
    """Fetch and build browse items for a single category.

    Returns an empty list (rather than raising) if the underlying query fails,
    so a broken table/collection never breaks the whole response.
    """
    builder = _CATEGORY_BUILDER.get(category)
    if builder is None:
        return []

    try:
        if category == "practice":
            # Practices live in ChromaDB — use semantic search regardless of
            # whether the user supplied a search term.
            query = search if search else _PRACTICE_BROWSE_QUERY
            results = chroma_search(query, _PRACTICE_CHROMA_COLLECTION, top_k=limit)
            # Deduplicate by topic_id so parent/child duplicates are collapsed
            seen: set[str] = set()
            items = []
            for r in results:
                key = r.metadata.get("topic_id") or r.source
                if key not in seen:
                    seen.add(key)
                    items.append(builder(r))
            return items[:limit]

        if search:
            fts_table = _CATEGORY_FTS_TABLE.get(category)
            if fts_table is None:
                # climate has no FTS table — fall through to structured
                results = structured_query(
                    _CATEGORY_STRUCT_TABLE[category], limit=limit,
                )
            else:
                results = fts_search(search, fts_table, top_k=limit)
                if not results:
                    # FTS found nothing — fall back to structured browse
                    results = structured_query(
                        _CATEGORY_STRUCT_TABLE[category], limit=limit,
                    )
        else:
            results = structured_query(
                _CATEGORY_STRUCT_TABLE[category], limit=limit,
            )

        return [builder(r) for r in results]

    except Exception as e:
        log.log_step(Step.SEARCH, "browse_category_error", level="WARNING",
                     details={"category": category, "error": str(e)})
        return []


# ============================================================
# Endpoint
# ============================================================

_ALL_CATEGORIES = ["disease", "treatment", "pest", "practice", "climate"]
_VALID_TYPES = set(_ALL_CATEGORIES) | {"all"}


@router.get("/browse")
async def browse_pack(
    category_filter: str = Query(default="all", alias="type", description="Category filter: all, disease, treatment, pest, practice, climate"),
    search: str = Query(default="", description="Optional keyword search term"),
    limit: int = Query(default=50, ge=1, le=200, description="Max items per category"),
):
    """Browse Knowledge Pack contents with optional filtering and search.

    Returns structured items across diseases, treatments, pests, farming
    practices, and climate data.  When a search term is supplied, FTS5 (or
    Chroma for practices) is used; otherwise a plain structured browse is
    returned.
    """
    if not settings.demo_mode and get_active_pack() is None:
        raise HTTPException(status_code=503, detail="No Knowledge Pack is loaded. Load a pack first.")

    if settings.demo_mode:
        return {"count": 0, "items": []}

    type_lower = category_filter.lower()
    if type_lower not in _VALID_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type '{category_filter}'. Must be one of: {sorted(_VALID_TYPES)}",
        )

    categories = _ALL_CATEGORIES if type_lower == "all" else [type_lower]

    items: list[dict] = []
    for category in categories:
        category_items = _fetch_category(category, search.strip(), limit)
        items.extend(category_items)

    log.log_step(Step.SEARCH, "browse_pack", details={
        "type": type_lower,
        "search": search[:100] if search else "",
        "limit": limit,
        "result_count": len(items),
    })

    return {"count": len(items), "items": items}
