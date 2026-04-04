from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/packs", tags=["packs"])


class PackInfo(BaseModel):
    pack_id: str
    name: str
    region: str
    crops: list[str]
    diseases_count: int
    loaded: bool = False


@router.get("/", response_model=list[PackInfo])
async def list_packs():
    """List all available Knowledge Packs."""
    packs = []
    packs_dir = settings.packs_path
    for pack_dir in packs_dir.iterdir():
        manifest = pack_dir / "manifest.json"
        if pack_dir.is_dir() and manifest.exists():
            import json

            data = json.loads(manifest.read_text())
            packs.append(PackInfo(
                pack_id=pack_dir.name,
                name=data.get("name", pack_dir.name),
                region=data.get("region", {}).get("name", "Unknown"),
                crops=data.get("crops", []),
                diseases_count=data.get("statistics", {}).get("diseases_count", 0),
            ))
    return packs


@router.post("/load/{pack_id}")
async def load_pack(pack_id: str):
    """Load a Knowledge Pack for offline use."""
    pack_path = settings.packs_path / pack_id
    if not pack_path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")
    # TODO: initialize ChromaDB client + SQLite connection from pack
    return {"status": "loaded", "pack_id": pack_id}
