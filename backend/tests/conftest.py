"""Shared fixtures for FieldPack AI test suite.

Provides:
  - requires_ollama: skip tests when Ollama isn't running
  - ollama_model: parametrize across Ollama models
  - google_api_model: use Google AI Studio API for live tests
  - live_llm: default for live tests — tries Ollama E2B first, falls back to Google API
  - live_pack: module-scoped real Knowledge Pack for live tests
"""

from pathlib import Path

import httpx
import pytest

from app.config import settings
from app.logger import pipeline_logger


# ============================================================
# Clean logger state between tests to prevent counter leaks
# ============================================================

@pytest.fixture(autouse=True)
def _clean_logger():
    """Reset PipelineLogger counters after each test.

    Pack lifecycle is managed by each test module's own fixtures.
    We only reset the logger here to prevent buffer/counter accumulation.
    """
    yield
    pipeline_logger._buffer.clear()
    pipeline_logger._session_id = None
    pipeline_logger._pipeline_start = None
    pipeline_logger._total_llm_calls = 0
    pipeline_logger._total_tokens_in = 0
    pipeline_logger._total_tokens_out = 0


# ============================================================
# Auto-deselect @pytest.mark.live tests unless -m live is given
# ============================================================

def pytest_collection_modifyitems(config, items):
    """Deselect live-marked tests unless explicitly requested via -m."""
    marker_expr = config.getoption("-m", default="")
    if "live" not in marker_expr:
        live_items = [item for item in items if item.get_closest_marker("live")]
        for item in live_items:
            items.remove(item)
        if live_items:
            config.hook.pytest_deselected(items=live_items)


# ============================================================
# Ollama availability check
# ============================================================

_OLLAMA_MODELS = [
    "gemma4:e2b-it-q4_K_M",
    # "gemma4:e4b-it-q4_K_M",  # Disabled: E2B is primary target (phone deployment)
]

_DEFAULT_OLLAMA_MODEL = "gemma4:e2b-it-q4_K_M"


def _ollama_tags() -> list[dict] | None:
    """Fetch Ollama model list. Returns None if unreachable."""
    headers = {}
    if settings.ollama_tunnel_token:
        headers["Authorization"] = f"Bearer {settings.ollama_tunnel_token}"
    try:
        r = httpx.get(
            f"{settings.ollama_base_url}/api/tags",
            timeout=5.0,
            headers=headers,
        )
        if r.status_code != 200:
            return None
        return r.json().get("models", [])
    except httpx.HTTPError:
        return None


def _ollama_is_running() -> bool:
    """Check if Ollama is reachable (local or remote via tunnel)."""
    return _ollama_tags() is not None


def _ollama_has_model(model_name: str) -> bool:
    """Check if a specific model is pulled in Ollama."""
    tags = _ollama_tags()
    if tags is None:
        return False
    return any(m.get("name", "").startswith(model_name) for m in tags)


@pytest.fixture
def requires_ollama():
    """Skip test if Ollama is not running."""
    if not _ollama_is_running():
        pytest.skip("Ollama is not running at " + settings.ollama_base_url)


# ============================================================
# Model parametrization for live tests
# ============================================================

def _model_id(model_name: str) -> str:
    """Short ID for pytest parametrize display."""
    if "e2b" in model_name:
        return "E2B"
    if "e4b" in model_name:
        return "E4B"
    return model_name


@pytest.fixture(params=_OLLAMA_MODELS, ids=[_model_id(m) for m in _OLLAMA_MODELS])
def ollama_model(request, requires_ollama, monkeypatch):
    """Parametrized fixture: runs each test once per Ollama model.

    Patches settings so get_field_llm() uses Ollama with the correct model.
    Skips if the model isn't pulled.
    """
    model_name = request.param
    if not _ollama_has_model(model_name):
        pytest.skip(f"Model {model_name} not pulled in Ollama")
    monkeypatch.setattr(settings, "field_llm_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_model", model_name)
    return model_name


# ============================================================
# Google AI Studio API model fixture for live tests
# ============================================================

def _google_api_available() -> bool:
    """Check if Google AI Studio API key is configured."""
    return bool(settings.google_ai_studio_api_key
                and settings.google_ai_studio_api_key != "your_api_key_here")


@pytest.fixture
def google_api_model(monkeypatch):
    """Use Google AI Studio API (Gemma 3 27B) for live tests.

    Patches settings so get_field_llm() returns ChatGoogleGenerativeAI.
    Skips if no API key is configured.
    """
    if not _google_api_available():
        pytest.skip("GOOGLE_AI_STUDIO_API_KEY not set")
    monkeypatch.setattr(settings, "field_llm_provider", "google")
    monkeypatch.setattr(settings, "field_llm_google_model", "gemma-3-27b-it")
    return "gemma-3-27b-it"


# ============================================================
# live_llm: default fixture — Ollama E2B first, Google API fallback
# ============================================================

@pytest.fixture
def live_llm(monkeypatch):
    """Default LLM for live tests. Tries Ollama E2B first, falls back to Google API.

    This is Gemma 4 E2B Q4_K_M on Ollama (local or Colab tunnel) by default.
    Falls back to Google AI Studio only if Ollama is unavailable.
    Returns a tuple: (model_name: str, provider: str).
    """
    # Try Ollama first (local or remote tunnel) — single HTTP call
    tags = _ollama_tags()
    if tags is not None and any(
        m.get("name", "").startswith(_DEFAULT_OLLAMA_MODEL) for m in tags
    ):
        monkeypatch.setattr(settings, "field_llm_provider", "ollama")
        monkeypatch.setattr(settings, "ollama_model", _DEFAULT_OLLAMA_MODEL)
        return (_DEFAULT_OLLAMA_MODEL, "ollama")

    # Fall back to Google API
    if _google_api_available():
        monkeypatch.setattr(settings, "field_llm_provider", "google")
        monkeypatch.setattr(settings, "field_llm_google_model", "gemma-3-27b-it")
        return ("gemma-3-27b-it", "google")

    pytest.skip("No LLM available: Ollama not running and no Google API key")


# ============================================================
# Test image path
# ============================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def test_image_path() -> Path:
    """Path to the cassava mosaic test image."""
    path = FIXTURES_DIR / "cassava_mosaic_test.jpg"
    assert path.exists(), f"Test image not found at {path}"
    return path
