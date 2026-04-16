import httpx
from fastapi import APIRouter

from app.config import settings
from app.knowledge_pack.loader import get_active_pack

router = APIRouter(tags=["health"])


def _ollama_headers() -> dict:
    """Build auth headers for Ollama requests."""
    if settings.ollama_tunnel_token:
        return {"Authorization": f"Bearer {settings.ollama_tunnel_token}"}
    return {}


@router.get("/health")
async def health_check():
    """Check system health including Ollama connectivity and model metadata.

    Returns Ollama version, whether the configured model exists and is loaded,
    and model details (parameter count, quantization, family, memory usage).
    """
    if settings.demo_mode:
        from app.demo_replay import get_demo_pack_info
        return {
            "service": "fieldpack-ai",
            "status": "ok",
            "demo_mode": True,
            "ollama": "demo",
            "ollama_version": "demo",
            "model": {
                "name": "fieldpack-assistant-lite",
                "exists": True,
                "loaded": True,
                "parameters": "5.1B",
                "quantization": "Q4_K_M",
                "family": "gemma4",
                "memory_mb": 7322,
            },
            "pack": {"loaded": True, **get_demo_pack_info()},
        }

    base = settings.ollama_base_url
    headers = _ollama_headers()
    result = {
        "service": "fieldpack-ai",
        "status": "unknown",
        "ollama": "unknown",
        "ollama_version": None,
        "model": {
            "name": settings.ollama_model,
            "exists": False,
            "loaded": False,
            "parameters": None,
            "quantization": None,
            "family": None,
            "memory_mb": None,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 1. Ollama version
            try:
                ver_resp = await client.get(f"{base}/api/version", headers=headers)
                if ver_resp.status_code == 200:
                    result["ollama_version"] = ver_resp.json().get("version")
            except httpx.HTTPError:
                pass

            # 2. Check model exists via /api/tags
            try:
                tags_resp = await client.get(f"{base}/api/tags", headers=headers)
                if tags_resp.status_code == 200:
                    result["ollama"] = "ok"
                    models = tags_resp.json().get("models", [])
                    for m in models:
                        if m.get("name", "") == settings.ollama_model or m.get("model", "") == settings.ollama_model:
                            result["model"]["exists"] = True
                            details = m.get("details", {})
                            result["model"]["parameters"] = details.get("parameter_size")
                            result["model"]["quantization"] = details.get("quantization_level")
                            result["model"]["family"] = details.get("family")
                            break
                else:
                    result["ollama"] = "error"
            except httpx.HTTPError:
                result["ollama"] = "unreachable"

            # 3. Check if model is loaded via /api/ps
            try:
                ps_resp = await client.get(f"{base}/api/ps", headers=headers)
                if ps_resp.status_code == 200:
                    running = ps_resp.json().get("models", [])
                    for m in running:
                        if m.get("name", "") == settings.ollama_model or m.get("model", "") == settings.ollama_model:
                            result["model"]["loaded"] = True
                            size_bytes = m.get("size", 0)
                            if size_bytes:
                                result["model"]["memory_mb"] = round(size_bytes / (1024 * 1024))
                            break
            except httpx.HTTPError:
                pass

    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
        result["ollama"] = "unreachable"

    # Pack status
    pack = get_active_pack()
    if pack is not None:
        try:
            pack_info = pack.health_check()
            pack_info["loaded"] = True
            result["pack"] = pack_info
        except Exception:
            result["pack"] = {"loaded": True, "error": "health_check failed"}
    else:
        result["pack"] = {"loaded": False}

    result["status"] = "ok" if result["ollama"] == "ok" else "degraded"
    return result
