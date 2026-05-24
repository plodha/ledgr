"""Wave 0 failing-by-design test for the structlog request-context contract.

Encodes INFRA-07: Wave 1 must export ``configure_logging`` and
``RequestContextMiddleware`` from ``src.logging_config`` such that the
middleware reads the ``x-request-id`` header off an ASGI scope and binds it as
a ``request_id`` structlog contextvar visible inside the request task.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from structlog.contextvars import get_contextvars

from src.logging_config import RequestContextMiddleware, configure_logging


def test_request_id_bound_via_middleware() -> None:
    """Calling ``RequestContextMiddleware.__call__`` with an ASGI HTTP scope
    that carries ``x-request-id: test-correlation-id`` must bind
    ``request_id`` into the structlog contextvars for the duration of the
    inner app's invocation.
    """
    # Configure logging once so contextvars machinery is wired up; the actual
    # output (JSON in prod / console in dev) does not matter for this test.
    configure_logging(environment="dev", level="INFO")

    captured: dict[str, object] = {}

    async def passthrough(scope: object, receive: object, send: object) -> None:
        # Snapshot the contextvars at the moment the inner app is invoked.
        captured.update(get_contextvars())

    middleware = RequestContextMiddleware(passthrough)

    scope: dict[str, object] = {
        "type": "http",
        "headers": [(b"x-request-id", b"test-correlation-id")],
    }
    receive: AsyncMock = AsyncMock()
    send: AsyncMock = AsyncMock()

    asyncio.run(middleware(scope, receive, send))

    assert captured.get("request_id") == "test-correlation-id"
