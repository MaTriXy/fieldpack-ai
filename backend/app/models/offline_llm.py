import logging

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama

from app.config import settings

log = logging.getLogger(__name__)


def _ollama_reachable(base_url: str, token: str = "") -> bool:
    """Quick health check — returns True if Ollama responds at base_url."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = httpx.get(f"{base_url}/api/version", headers=headers, timeout=3)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def _make_ollama(
    base_url: str,
    temperature: float,
    token: str = "",
    num_predict: int | None = None,
    format: str | None = None,
) -> ChatOllama:
    kwargs = dict(
        model=settings.ollama_model,
        base_url=base_url,
        temperature=temperature,
        num_ctx=settings.ollama_num_ctx,
        keep_alive=settings.ollama_keep_alive,
    )
    if num_predict is not None:
        kwargs["num_predict"] = num_predict
    if format is not None:
        kwargs["format"] = format
    if token:
        kwargs["client_kwargs"] = {
            "headers": {"Authorization": f"Bearer {token}"}
        }
    return ChatOllama(**kwargs)


def _make_google(temperature: float) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.field_llm_google_model,
        google_api_key=settings.google_ai_studio_api_key,
        temperature=temperature,
        convert_system_message_to_human=True,
    )


def get_field_llm(
    temperature: float = 0.3,
    num_predict: int | None = None,
    format: str | None = None,
) -> BaseChatModel:
    """Field assistant LLM with automatic fallback.

    Resolution order:
      1. Tunnel Ollama (if OLLAMA_TUNNEL_TOKEN set and reachable)
      2. Local Ollama at OLLAMA_BASE_URL (if reachable)
      3. Google AI Studio API (if API key set)

    If field_llm_provider is explicitly "google", skips Ollama entirely.
    """
    if settings.field_llm_provider == "google":
        log.info("field_llm_provider=google, using Google AI Studio")
        return _make_google(temperature)

    # 1. Try tunnel Ollama
    if settings.ollama_tunnel_token:
        if _ollama_reachable(settings.ollama_base_url, settings.ollama_tunnel_token):
            log.info("Using tunnel Ollama at %s", settings.ollama_base_url)
            return _make_ollama(
                settings.ollama_base_url, temperature, settings.ollama_tunnel_token,
                num_predict=num_predict, format=format,
            )
        log.warning("Tunnel Ollama unreachable, falling back...")

    # 2. Try local Ollama
    local_url = "http://localhost:11434"
    if _ollama_reachable(local_url):
        log.info("Using local Ollama at %s", local_url)
        return _make_ollama(local_url, temperature, num_predict=num_predict, format=format)
    log.warning("Local Ollama unreachable at %s, falling back...", local_url)

    # 3. Fall back to Google API
    if settings.google_ai_studio_api_key:
        log.warning("Falling back to Google AI Studio API")
        return _make_google(temperature)

    raise RuntimeError(
        "No LLM available. Start Ollama, configure a tunnel, or set GOOGLE_AI_STUDIO_API_KEY."
    )
