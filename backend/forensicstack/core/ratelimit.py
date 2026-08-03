"""
Rate limiting for abuse-prone endpoints.

Why this exists
---------------
Login and register had no throttle: an attacker could brute-force credentials or
enumerate usernames as fast as the server answered, and a script could exhaust
storage by hammering the upload endpoints. This adds a per-client fixed-window
limiter applied as a FastAPI dependency, so protecting an endpoint is one line
and never changes its signature.

Backend note
------------
The default backend is in-process (per-worker) - correct and dependency-free for
a single-process or small deployment. For a horizontally-scaled deployment the
same interface should be backed by Redis (already a platform dependency) so the
window is shared across workers; ``FixedWindowLimiter`` is deliberately small
and swappable to make that change local.

Testability
-----------
Disabled when ``RATELIMIT_ENABLED`` is false (the test suite sets this so the
existing auth tests, which hit /login and /register repeatedly, are unaffected).
The limiter logic is unit-tested directly, and one integration test enables it
explicitly on a throwaway app.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable

from fastapi import HTTPException, Request, status


def _enabled_default() -> bool:
    return os.getenv("RATELIMIT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


class FixedWindowLimiter:
    """Thread-safe fixed-window counter. Not distributed (see module docstring)."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = int(limit)
        self.window = float(window_seconds)
        self._hits: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, *, now: float | None = None) -> tuple[bool, int]:
        """Register a hit for ``key``. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic() if now is None else now
        with self._lock:
            window_start, count = self._hits.get(key, (now, 0))
            if now - window_start >= self.window:
                window_start, count = now, 0  # window rolled over
            count += 1
            self._hits[key] = (window_start, count)
            if count <= self.limit:
                return True, 0
            retry_after = int(self.window - (now - window_start)) + 1
            return False, max(retry_after, 1)


def client_key(request: Request) -> str:
    """Best-effort client identity. Honours the first X-Forwarded-For hop when
    the app runs behind a trusted proxy, else the socket peer."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(
    scope: str,
    limit: int,
    window_seconds: float,
    *,
    enabled: bool | None = None,
) -> Callable:
    """Build a FastAPI dependency that throttles ``scope`` per client.

    Each call creates one persistent limiter (kept alive by the returned
    closure), so declare it once at import time in the route's ``dependencies=``.
    """
    limiter = FixedWindowLimiter(limit, window_seconds)
    is_on = _enabled_default() if enabled is None else enabled

    async def _dependency(request: Request) -> None:
        if not is_on:
            return
        key = f"{scope}:{client_key(request)}"
        allowed, retry_after = limiter.check(key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many '{scope}' requests. Retry in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dependency


__all__ = ["FixedWindowLimiter", "rate_limit", "client_key"]
