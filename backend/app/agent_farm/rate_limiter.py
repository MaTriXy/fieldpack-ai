"""Adaptive rate limiter for Google AI Studio API calls.

Separate sliding windows per model (26B research vs 31B planner) since
they have independent rate limits. Exponential backoff on 429 responses:
start 2s, double each retry, cap at 60s, reset on success.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class _ModelWindow:
    """Sliding window state for a single model."""

    rpm: int  # max requests per minute
    timestamps: deque[float] = field(default_factory=deque)
    backoff_seconds: float = 0.0  # current backoff (0 = no backoff active)


class AdaptiveRateLimiter:
    """Per-model adaptive rate limiter with exponential backoff.

    Usage:
        limiter = AdaptiveRateLimiter()
        await limiter.wait("gemma-4-26b-a4b-it")   # before each API call
        limiter.on_success("gemma-4-26b-a4b-it")    # after successful call
        limiter.on_rate_limit("gemma-4-26b-a4b-it") # after 429 response
    """

    INITIAL_BACKOFF = 2.0
    MAX_BACKOFF = 60.0

    def __init__(self, default_rpm: int = 25) -> None:
        self._default_rpm = default_rpm
        self._windows: dict[str, _ModelWindow] = {}
        self._lock = asyncio.Lock()

    def _get_window(self, model: str) -> _ModelWindow:
        if model not in self._windows:
            self._windows[model] = _ModelWindow(rpm=self._default_rpm)
        return self._windows[model]

    async def wait(self, model: str) -> None:
        """Wait until it's safe to make a request for this model."""
        # Phase 1: check if backoff is active (lock briefly, then release to sleep)
        async with self._lock:
            window = self._get_window(model)
            backoff = window.backoff_seconds

        if backoff > 0:
            await asyncio.sleep(backoff)

        # Phase 2: sliding window check (may need to sleep at capacity)
        while True:
            async with self._lock:
                window = self._get_window(model)

                # Slide the window: remove timestamps older than 60s
                now = time.monotonic()
                while window.timestamps and (now - window.timestamps[0]) > 60.0:
                    window.timestamps.popleft()

                # If under capacity, record timestamp and proceed
                if len(window.timestamps) < window.rpm:
                    window.timestamps.append(time.monotonic())
                    return

                # At capacity — calculate wait time, release lock, then sleep
                wait_time = 60.0 - (now - window.timestamps[0]) + 0.1

            await asyncio.sleep(max(wait_time, 0.1))

    def on_success(self, model: str) -> None:
        """Reset backoff on successful API call."""
        window = self._get_window(model)
        window.backoff_seconds = 0.0

    def on_rate_limit(self, model: str) -> None:
        """Increase backoff on 429 response."""
        window = self._get_window(model)
        if window.backoff_seconds == 0.0:
            window.backoff_seconds = self.INITIAL_BACKOFF
        else:
            window.backoff_seconds = min(window.backoff_seconds * 2, self.MAX_BACKOFF)


# Singleton — shared across all agent farm operations
rate_limiter = AdaptiveRateLimiter()
