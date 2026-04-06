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


# Cache resolved provider so we only probe once per process
_resolved_provider: str | None = None


def get_field_llm(
    temperature: float = 0.3,
    num_predict: int | None = None,
    format: str | None = None,
) -> BaseChatModel:
    """Field assistant LLM with automatic fallback.

    Resolution order:
      1. Tunnel Ollama (if OLLAMA_TUNNEL_TOKEN set and reachable)
      2. Google AI Studio API (if API key set)
      3. Local Ollama at localhost:11434 (if reachable)

    Result is cached — health checks only run once per process.
    If field_llm_provider is explicitly set, skips fallback entirely.
    """
    global _resolved_provider

    if settings.field_llm_provider == "google":
        log.info("field_llm_provider=google, using Google AI Studio")
        return _make_google(temperature)
    if settings.field_llm_provider == "ollama-local":
        log.info("field_llm_provider=ollama-local, using local Ollama")
        return _make_ollama(
            "http://localhost:11434", temperature,
            num_predict=num_predict, format=format,
        )

    # Auto-resolve: probe once, cache result
    if _resolved_provider is None:
        _resolve_provider()

    if _resolved_provider == "tunnel":
        return _make_ollama(
            settings.ollama_base_url, temperature, settings.ollama_tunnel_token,
            num_predict=num_predict, format=format,
        )
    if _resolved_provider == "google":
        return _make_google(temperature)
    if _resolved_provider == "local":
        return _make_ollama(
            "http://localhost:11434", temperature,
            num_predict=num_predict, format=format,
        )

    raise RuntimeError(
        "No LLM available. Start Ollama, configure a tunnel, or set GOOGLE_AI_STUDIO_API_KEY."
    )


def _resolve_provider():
    """Probe available providers once and cache the result."""
    global _resolved_provider

    # 1. Tunnel Ollama
    if settings.ollama_tunnel_token:
        if _ollama_reachable(settings.ollama_base_url, settings.ollama_tunnel_token):
            log.info("Resolved LLM: tunnel Ollama at %s", settings.ollama_base_url)
            _resolved_provider = "tunnel"
            return
        log.warning("Tunnel Ollama unreachable")

    # 2. Google AI Studio API
    if settings.google_ai_studio_api_key:
        log.info("Resolved LLM: Google AI Studio API")
        _resolved_provider = "google"
        return

    # 3. Local Ollama
    if _ollama_reachable("http://localhost:11434"):
        log.info("Resolved LLM: local Ollama at localhost:11434")
        _resolved_provider = "local"
        return

    _resolved_provider = "none"
    log.error("No LLM provider available")
