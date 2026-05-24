"""Pytest fixtures for the apps/api test suite.

Encodes the async-client contract Wave 1 (src.main) must satisfy. httpx's
``AsyncClient`` does NOT trigger ASGI lifespan events on its own, so the DB
engine that ``src.main`` initializes in its lifespan never wires up unless we
wrap the app in ``LifespanManager`` — see RESEARCH.md Pitfall 5 and the
official FastAPI advanced/async-tests page.

This file imports ``app`` from ``src.main`` which does not exist until Wave 1
lands. Import-time failure is the intentional Wave 0 red signal.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
def anyio_backend() -> str:
    """Force the anyio backend to asyncio.

    The FastAPI tests use the ``@pytest.mark.anyio`` marker. anyio's default
    backend list is ``["asyncio", "trio"]``; we only support asyncio because
    SQLAlchemy 2.0's async dialect targets asyncio, not trio.
    """
    return "asyncio"


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Yield an httpx ``AsyncClient`` wired to the live ASGI app.

    ``LifespanManager(app)`` is non-optional: without it ``app.state`` (which
    holds the SQLAlchemy engine / sessionmaker) is never populated and any
    handler that touches the DB raises ``AttributeError`` at request time.
    """
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
