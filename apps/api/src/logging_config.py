"""Structured logging configuration + pure-ASGI request-context middleware.

This module establishes the INFRA-07 contract for the application:

1. ``configure_logging(environment, level)`` wires structlog with a processor
   pipeline that timestamps, level-tags, redacts secrets, and renders either
   colored console output (dev/test) or JSON (production).

2. ``_redact_processor`` walks ``event_dict`` recursively (dicts + lists) and
   replaces values whose keys (lowercased) appear in ``SENSITIVE_KEYS`` with
   the literal string ``"***"``. The match is case-insensitive and applies at
   *any* nesting depth — so a log call like
   ``logger.info("auth", payload={"User": {"password": "x"}})`` redacts the
   nested password regardless of the outer wrapper.

3. ``RequestContextMiddleware`` is a **pure ASGI** middleware (NOT a
   starlette ``BaseHTTP`` middleware subclass). Per RESEARCH.md Anti-Pattern
   (line 1030) and Pitfall 3 (lines 1090-1095), the high-level HTTP-style
   middleware creates a fresh asyncio context copy, breaking
   ``structlog.contextvars`` propagation across awaits within the same
   request. The pure-ASGI form runs in the same context as the downstream
   handler so vars bound here are visible everywhere in the request scope.

The middleware reads the ``x-request-id`` header (if present) and falls back
to ``uuid.uuid4().hex`` otherwise, then ``bind_contextvars(request_id=...)``
so every subsequent structlog call within the request automatically carries
the field via the ``merge_contextvars`` processor.
"""

from __future__ import annotations

import logging
import sys
import uuid
from typing import Any, cast

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from starlette.types import ASGIApp, Receive, Scope, Send

SENSITIVE_KEYS = {
    "password",
    "token",
    "secret",
    "authorization",
    "access_token",
    "refresh_token",
    "api_key",
    "secret_key",
}


def _redact_processor(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Recursively replace SENSITIVE_KEYS values with ``"***"`` at any depth.

    Walks the entire ``event_dict``: nested dicts inherit the same rule,
    lists are walked element-wise. Non-container leaf values are returned
    unchanged. Key match is case-insensitive (``"Authorization"`` and
    ``"AUTHORIZATION"`` both redact).
    """

    def scrub(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: ("***" if isinstance(k, str) and k.lower() in SENSITIVE_KEYS else scrub(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [scrub(x) for x in obj]
        return obj

    # ``scrub`` is typed ``Any -> Any`` because it recurses across dicts,
    # lists, and leaf values; the top-level input is always a dict, so the
    # top-level output is always a dict — the cast restores that invariant
    # for the caller's type expectations without changing runtime behavior.
    return cast("dict[str, Any]", scrub(event_dict))


def configure_logging(environment: str, level: str) -> None:
    """Configure structlog for the current process.

    Idempotent — calling twice is safe (structlog.configure replaces prior
    state). Called once at module import in ``main.py``.

    ``environment == "production"`` => JSON renderer (machine-parseable).
    Otherwise => colored console renderer (developer-friendly).
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        timestamper,
        _redact_processor,
    ]

    renderer: Any
    if environment == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


class RequestContextMiddleware:
    """Pure ASGI middleware — binds ``request_id`` to structlog contextvars.

    Why pure ASGI and not the high-level HTTP-style middleware base: the
    high-level base creates a separate asyncio context copy, so contextvars
    bound in a downstream handler are not visible to log lines emitted at
    the middleware's "after" boundary. Pure ASGI runs in the same context —
    vars bound anywhere in the request lifecycle are visible everywhere.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        clear_contextvars()
        request_id = next(
            (v.decode() for k, v in scope.get("headers", []) if k == b"x-request-id"),
            uuid.uuid4().hex,
        )
        bind_contextvars(request_id=request_id)
        await self.app(scope, receive, send)
