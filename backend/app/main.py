from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logger import Step, pipeline_logger as log
from app.routers import chat, conversations, health, mission, observations, pack, upload


def _auto_load_first_pack() -> None:
    """Load the first available Knowledge Pack on startup.

    Iterates packs_path for directories that contain a manifest.json and
    knowledge.db, and loads the first one found.  Failures are logged but
    never raise — the server must start even if no pack exists yet.
    """
    from app.knowledge_pack.loader import get_active_pack, load_pack

    if get_active_pack() is not None:
        return  # already loaded (e.g. re-entrant lifespan in tests)

    packs_dir = settings.packs_path
    for pack_dir in sorted(packs_dir.iterdir()):
        if not pack_dir.is_dir():
            continue
        if not (pack_dir / "manifest.json").exists():
            continue
        if not (pack_dir / "knowledge.db").exists():
            continue
        try:
            load_pack(pack_dir)
            log.log_step(Step.PACK_LOAD, "auto_loaded", details={"pack": pack_dir.name})
            return
        except Exception as exc:
            log.log_step(Step.PACK_LOAD, "auto_load_failed", level="WARNING",
                         details={"pack": pack_dir.name, "error": str(exc)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure directories exist, then auto-load first available pack
    settings.packs_path
    settings.uploads_path
    if settings.demo_mode:
        log.log_step(Step.PACK_LOAD, "demo_mode", details={"demo": True})
    else:
        _auto_load_first_pack()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="FieldPack AI",
    description="Offline AI field assistant powered by Gemma 4 Knowledge Packs",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: FieldPack runs on a closed LAN (laptop hotspot + phone).
# Origins are restricted to localhost dev + Capacitor APK.
# No wildcard "*" — only known client origins are allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost",
        "capacitor://localhost",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Upgrade", "Connection"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(mission.router)
app.include_router(pack.router)
app.include_router(upload.router)
app.include_router(observations.router)
