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
    reasoning: bool | None = None,
) -> ChatOllama:
    kwargs = dict(
        model=settings.ollama_model,
        base_url=base_url,
        temperature=temperature,
        num_ctx=settings.ollama_num_ctx,
        keep_alive=settings.ollama_keep_alive,
        num_keep=256,  # Pin system prompt tokens — never evicted from context
    )
    if num_predict is not None:
        kwargs["num_predict"] = num_predict
    if format is not None:
        kwargs["format"] = format
    # E2B is a thinking model — always disable reasoning to avoid
    # wasting tokens on internal chain-of-thought
    kwargs["reasoning"] = reasoning if reasoning is not None else False
    # GPU layer offloading: -1 = auto, 0 = CPU-only.
    # Intel iGPUs cause garbage output with partial offload (75% CPU / 25% GPU
    # splits layers across precision boundaries). Force CPU-only for local.
    # Only apply to local Ollama — tunnel GPU manages its own offloading.
    if not token and settings.ollama_num_gpu >= 0:
        kwargs["num_gpu"] = settings.ollama_num_gpu
    client_kwargs = {"timeout": settings.ollama_timeout}
    if token:
        client_kwargs["headers"] = {"Authorization": f"Bearer {token}"}
    kwargs["client_kwargs"] = client_kwargs
    return ChatOllama(**kwargs)


def _make_google(
    temperature: float,
    max_output_tokens: int | None = None,
) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    kwargs = dict(
        model=settings.field_llm_google_model,
        google_api_key=settings.google_ai_studio_api_key,
        temperature=temperature,
    )
    if max_output_tokens is not None:
        kwargs["max_output_tokens"] = max_output_tokens
    return ChatGoogleGenerativeAI(**kwargs)


# Cache resolved provider so we only probe once per process
_resolved_provider: str | None = None
_resolved_at: float = 0.0
_RESOLVE_TTL: float = 30.0  # Re-probe every 30 seconds


def get_field_llm(
    temperature: float = 0.3,
    num_predict: int | None = None,
    format: str | None = None,
    reasoning: bool | None = None,
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
        return _make_google(temperature, max_output_tokens=num_predict)
    if settings.field_llm_provider == "ollama-local":
        log.info("field_llm_provider=ollama-local, using local Ollama")
        return _make_ollama(
            "http://localhost:11434", temperature,
            num_predict=num_predict, format=format, reasoning=reasoning,
        )
    if settings.field_llm_provider == "ollama":
        # "ollama" = use tunnel if available, else local — skip Google fallback
        if settings.ollama_tunnel_token and _ollama_reachable(
            settings.ollama_base_url, settings.ollama_tunnel_token
        ):
            log.info("field_llm_provider=ollama, using tunnel Ollama at %s", settings.ollama_base_url)
            return _make_ollama(
                settings.ollama_base_url, temperature, settings.ollama_tunnel_token,
                num_predict=num_predict, format=format, reasoning=reasoning,
            )
        if _ollama_reachable("http://localhost:11434"):
            log.info("field_llm_provider=ollama, using local Ollama")
            return _make_ollama(
                "http://localhost:11434", temperature,
                num_predict=num_predict, format=format, reasoning=reasoning,
            )
        raise RuntimeError(
            "field_llm_provider=ollama but no Ollama reachable (tunnel or local). "
            "Start Ollama or change FIELD_LLM_PROVIDER."
        )

    # Auto-resolve: probe once, cache with TTL
    import time as _time
    if _resolved_provider is None or (_time.monotonic() - _resolved_at) > _RESOLVE_TTL:
        _resolve_provider()

    if _resolved_provider == "tunnel":
        return _make_ollama(
            settings.ollama_base_url, temperature, settings.ollama_tunnel_token,
            num_predict=num_predict, format=format, reasoning=reasoning,
        )
    if _resolved_provider == "google":
        return _make_google(temperature, max_output_tokens=num_predict)
    if _resolved_provider == "local":
        return _make_ollama(
            "http://localhost:11434", temperature,
            num_predict=num_predict, format=format, reasoning=reasoning,
        )

    raise RuntimeError(
        "No LLM available. Start Ollama, configure a tunnel, or set GOOGLE_AI_STUDIO_API_KEY."
    )


def get_resolved_provider() -> str:
    """Return the currently resolved provider name.

    Respects explicit settings before falling back to auto-resolve.
    Possible values: "tunnel", "google", "local", "none".
    """
    if settings.field_llm_provider == "google":
        return "google"
    if settings.field_llm_provider == "ollama-local":
        return "local"
    if settings.field_llm_provider == "ollama":
        if settings.ollama_tunnel_token and _ollama_reachable(
            settings.ollama_base_url, settings.ollama_tunnel_token
        ):
            return "tunnel"
        if _ollama_reachable("http://localhost:11434"):
            return "local"
        return "none"
    import time as _time
    if _resolved_provider is None or (_time.monotonic() - _resolved_at) > _RESOLVE_TTL:
        _resolve_provider()
    return _resolved_provider or "none"


def _resolve_provider():
    """Probe available providers and cache the result with TTL."""
    global _resolved_provider, _resolved_at
    import time as _time

    # 1. Tunnel Ollama
    if settings.ollama_tunnel_token:
        if _ollama_reachable(settings.ollama_base_url, settings.ollama_tunnel_token):
            log.info("Resolved LLM: tunnel Ollama at %s", settings.ollama_base_url)
            _resolved_provider = "tunnel"
            _resolved_at = _time.monotonic()
            return
        log.warning("Tunnel Ollama unreachable")

    # 2. Google AI Studio API
    if settings.google_ai_studio_api_key:
        log.info("Resolved LLM: Google AI Studio API")
        _resolved_provider = "google"
        _resolved_at = _time.monotonic()
        return

    # 3. Local Ollama
    if _ollama_reachable("http://localhost:11434"):
        log.info("Resolved LLM: local Ollama at localhost:11434")
        _resolved_provider = "local"
        _resolved_at = _time.monotonic()
        return

    _resolved_provider = "none"
    _resolved_at = _time.monotonic()
    log.error("No LLM provider available")
