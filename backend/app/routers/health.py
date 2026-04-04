from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "ollama_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "online_model": settings.online_model_large,
    }
