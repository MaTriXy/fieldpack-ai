"""Fixtures for E2E tests that drive a real running FieldPack stack over HTTP.

These tests do NOT load the knowledge pack in-process — they assume a backend
is already running (Docker or native) and talk to it via httpx.AsyncClient.
Opt in with `-m e2e`; default `pytest tests/` does not collect them.
"""

import os

import httpx
import pytest


@pytest.fixture
def e2e_base_url() -> str:
    """Base URL of the running backend under test."""
    return os.environ.get("FIELDPACK_E2E_URL", "http://localhost:8000")


@pytest.fixture
async def e2e_client(e2e_base_url):
    """httpx.AsyncClient with a long timeout to accommodate LLM calls.

    300s covers the worst case observed on CPU-only Gemma 4 E2B: classify (~17s)
    + vision / second-pass retrieval + generate (~50s each) can easily exceed
    the FastAPI 60s default or a naive 120s ceiling. On GPU this is overkill.
    """
    async with httpx.AsyncClient(base_url=e2e_base_url, timeout=300.0) as client:
        yield client
