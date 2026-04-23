"""Tests for /health endpoint and internet probe.

Covers the new internet reachability field: cached status returned without
blocking, DEMO_MODE shortcut, and the probe module's cache behavior.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import internet_probe
from app.config import settings


# ---------------------------------------------------------------
# internet_probe unit tests
# ---------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_probe_cache():
    """Reset the probe's cached status between tests."""
    original = internet_probe._status
    yield
    internet_probe._status = original


def test_get_status_returns_cached_shape():
    internet_probe._status = internet_probe.InternetStatus(
        online=True, checked_at="2026-04-23T12:00:00+00:00"
    )
    s = internet_probe.get_status()
    assert s == {"online": True, "checked_at": "2026-04-23T12:00:00+00:00"}


def test_get_status_default_before_first_probe():
    internet_probe._status = internet_probe.InternetStatus(
        online=False, checked_at="never"
    )
    s = internet_probe.get_status()
    assert s["online"] is False
    assert s["checked_at"] == "never"


@pytest.mark.asyncio
async def test_check_once_offline_when_both_probes_fail(monkeypatch):
    async def fail_http():
        return False

    async def fail_tcp():
        return False

    monkeypatch.setattr(internet_probe, "_http_probe", fail_http)
    monkeypatch.setattr(internet_probe, "_tcp_probe", fail_tcp)

    status = await internet_probe.check_once()
    assert status.online is False
    assert status.checked_at != "never"


@pytest.mark.asyncio
async def test_check_once_online_when_http_succeeds(monkeypatch):
    async def ok_http():
        return True

    async def fail_tcp():
        return False

    monkeypatch.setattr(internet_probe, "_http_probe", ok_http)
    monkeypatch.setattr(internet_probe, "_tcp_probe", fail_tcp)

    status = await internet_probe.check_once()
    assert status.online is True


@pytest.mark.asyncio
async def test_check_once_falls_back_to_tcp(monkeypatch):
    async def fail_http():
        return False

    async def ok_tcp():
        return True

    monkeypatch.setattr(internet_probe, "_http_probe", fail_http)
    monkeypatch.setattr(internet_probe, "_tcp_probe", ok_tcp)

    status = await internet_probe.check_once()
    assert status.online is True


# ---------------------------------------------------------------
# /health endpoint integration
# ---------------------------------------------------------------

def test_health_demo_mode_includes_internet_online(monkeypatch):
    """DEMO_MODE short-circuits to a canned response with internet online."""
    monkeypatch.setattr(settings, "demo_mode", True)
    from app.main import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "internet" in body
    assert body["internet"]["online"] is True


def test_health_live_mode_includes_internet_from_cache(monkeypatch):
    """Live mode reads internet status from the cached probe result."""
    monkeypatch.setattr(settings, "demo_mode", False)
    internet_probe._status = internet_probe.InternetStatus(
        online=True, checked_at="2026-04-23T14:00:00+00:00"
    )
    from app.main import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["internet"] == {
        "online": True,
        "checked_at": "2026-04-23T14:00:00+00:00",
    }


def test_health_internet_field_offline(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    internet_probe._status = internet_probe.InternetStatus(
        online=False, checked_at="2026-04-23T14:05:00+00:00"
    )
    from app.main import app
    client = TestClient(app)
    resp = client.get("/health")
    body = resp.json()
    assert body["internet"]["online"] is False
