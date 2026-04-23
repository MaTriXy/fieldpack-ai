"""Background internet reachability probe for the laptop.

Periodically checks whether the laptop itself has internet access and caches
the result so /health can return it without blocking. The phone uses this to
distinguish "laptop offline" (amber) from "laptop on, no internet"
(green, Field Mode) from "laptop on, with internet" (green, Online).

Primary probe: HEAD https://www.gstatic.com/generate_204 (standard Android
captive-portal check, 204 No Content, tiny).

Fallback: TCP connect to 1.1.1.1:443 — guards against environments where
gstatic is blocked but general internet works.

Probe cadence: every 30s, with a 3s timeout. Never raises; a failure just
flips the cached flag to False and logs a warning.

Staleness note: the phone's "laptop has internet" indicator can lag reality
by up to 30s (one probe interval). Fine for a field-worker UX where internet
state changes slowly; do NOT rely on this for real-time captive-portal checks.
"""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.logger import Step, pipeline_logger as log


PROBE_INTERVAL_SECONDS = 30.0
PROBE_TIMEOUT_SECONDS = 3.0
PROBE_URL = "https://www.gstatic.com/generate_204"
FALLBACK_HOST = "1.1.1.1"
FALLBACK_PORT = 443


@dataclass
class InternetStatus:
    online: bool
    checked_at: str  # ISO-8601 UTC; "never" before first probe completes


_status = InternetStatus(online=False, checked_at="never")
_task: asyncio.Task | None = None


def get_status() -> dict:
    """Return the current cached internet status for /health."""
    return {"online": _status.online, "checked_at": _status.checked_at}


async def _http_probe() -> bool:
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            resp = await client.head(PROBE_URL)
            return resp.status_code == 204
    except httpx.HTTPError:
        return False


async def _tcp_probe() -> bool:
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: socket.create_connection(
                    (FALLBACK_HOST, FALLBACK_PORT), timeout=PROBE_TIMEOUT_SECONDS
                ).close(),
            ),
            timeout=PROBE_TIMEOUT_SECONDS + 0.5,
        )
        return True
    except (OSError, asyncio.TimeoutError):
        return False


async def check_once() -> InternetStatus:
    """Run one probe cycle and update the cached status. Exposed for tests."""
    global _status
    online = await _http_probe()
    if not online:
        online = await _tcp_probe()
    _status = InternetStatus(
        online=online,
        checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    return _status


async def _probe_loop() -> None:
    while True:
        try:
            await check_once()
        except Exception as exc:
            log.log_step(
                Step.PACK_LOAD,
                "internet_probe_error",
                level="WARNING",
                details={"error": str(exc)},
            )
        await asyncio.sleep(PROBE_INTERVAL_SECONDS)


def start_probe() -> None:
    """Launch the background probe task. Safe to call multiple times."""
    global _task
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(_probe_loop(), name="internet_probe")


async def stop_probe() -> None:
    """Cancel the background probe task. Safe to call if not running."""
    global _task
    if _task is None:
        return
    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass
    _task = None
