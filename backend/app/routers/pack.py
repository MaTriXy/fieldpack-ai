import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.knowledge_pack.loader import get_active_pack, load_pack as loader_load_pack, unload_pack
from app.logger import Step, pipeline_logger as log

router = APIRouter(prefix="/packs", tags=["packs"])


class PackInfo(BaseModel):
    pack_id: str
    name: str
    region: str
    crops: list[str]
    diseases_count: int
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
            packs.append(PackInfo(
                pack_id=pack_dir.name,
                name=data.get("name", pack_dir.name),
                region=data.get("region", {}).get("name", "Unknown"),
                crops=data.get("crops", []),
                diseases_count=data.get("statistics", {}).get("diseases_count", 0),
                loaded=pack_dir.resolve() == active_path,
            ))
    return packs


@router.post("/load/{pack_id}", response_model=PackLoadResponse)
async def load_pack_endpoint(pack_id: str):
    """Load a Knowledge Pack for offline use."""
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
        region=manifest.region.name if manifest.region else "Unknown",
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
