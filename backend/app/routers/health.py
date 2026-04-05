import httpx
from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Check system health including Ollama connectivity."""
    ollama_status = "unknown"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.ollama_base_url}/api/tags",
                timeout=3.0,
            )
            ollama_status = "ok" if resp.status_code == 200 else "error"
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
        ollama_status = "unreachable"

    status = "ok" if ollama_status == "ok" else "degraded"
    return {"status": status, "ollama": ollama_status}
