"""
Observability: structured logging + per-request correlation.

Why this exists
---------------
A DFIR platform whose own actions cannot be reconstructed is indefensible: if
an investigator disputes what the system did to a piece of evidence, "check the
logs" must produce an answer. Until now the app logged with bare ``print()`` and
no request correlation, so two concurrent uploads interleaved into an unreadable
stream with no way to tell which line belonged to which call.

This module provides:

* ``configure_logging()`` - one structured formatter for the whole process, so
  every line is machine-parseable (logfmt by default, JSON on request) and
  carries the correlation id.
* ``RequestContextMiddleware`` - a *pure ASGI* middleware (deliberately NOT
  Starlette's ``BaseHTTPMiddleware``, which buffers the request body and would
  break the multi-GB evidence uploads) that assigns/propagates an
  ``X-Request-ID``, binds it to a context variable for the duration of the
  request, echoes it back on the response, and emits one access-log line.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar

# The correlation id in scope for the current task. Every log record emitted
# while a request is being handled carries this, so lines from concurrent
# requests can be separated after the fact.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_ACCESS = logging.getLogger("forensicstack.access")


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        record.request_id = request_id_ctx.get()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str | None = None) -> None:
    """Install a single structured handler on the root logger.

    Idempotent: replaces prior handlers so re-invocation (uvicorn reload, tests)
    does not stack duplicates. ``LOG_FORMAT=json`` switches to JSON lines;
    default is logfmt, which stays greppable by eye.
    """
    level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIdFilter())

    if os.getenv("LOG_FORMAT", "logfmt").lower() == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "ts=%(asctime)s level=%(levelname)s logger=%(name)s "
                "req=%(request_id)s msg=%(message)s"
            )
        )

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


class RequestContextMiddleware:
    """Pure-ASGI correlation + access logging. Body streams are never touched."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        incoming = headers.get(b"x-request-id")
        # Accept a caller-supplied id (so a request can be traced across the
        # frontend, the API and a worker), but cap its length so it cannot be
        # used to smuggle huge/garbage values into the logs.
        rid = incoming.decode("latin-1")[:64] if incoming else uuid.uuid4().hex[:16]

        token = request_id_ctx.set(rid)
        started = time.monotonic()
        status_holder = {"code": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
                message.setdefault("headers", [])
                message["headers"].append((b"x-request-id", rid.encode("latin-1")))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.monotonic() - started) * 1000.0
            client = scope.get("client")
            _ACCESS.info(
                "method=%s path=%s status=%s dur_ms=%.1f client=%s",
                scope.get("method"),
                scope.get("path"),
                status_holder["code"],
                duration_ms,
                client[0] if client else "-",
            )
            request_id_ctx.reset(token)


__all__ = ["configure_logging", "RequestContextMiddleware", "request_id_ctx"]
