from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, health, mission, pack


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure directories exist
    settings.packs_path
    settings.uploads_path
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="FieldPack AI",
    description="Offline AI field assistant powered by Gemma 4 Knowledge Packs",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Upgrade", "Connection"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(mission.router)
app.include_router(pack.router)
