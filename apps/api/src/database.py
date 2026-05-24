"""Async SQLAlchemy 2.0 engine + sessionmaker + ``get_session`` dependency.

The engine is created at module import (settings come from ``get_settings()``)
and disposed in the FastAPI lifespan in ``main.py``. The sessionmaker uses
``expire_on_commit=False`` per RESEARCH.md Anti-Pattern at line 1033 — the
default ``True`` causes surprising async re-loads of ORM attributes after
``await session.commit()``, which fails outside a session scope.

``get_session`` is the FastAPI dependency injected into every route that
needs DB access. It commits on clean exit and rolls back on any exception
raised inside the handler, then closes the session via ``async with``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` with commit-on-success / rollback-on-error.

    The session is closed by the surrounding ``async with`` block regardless
    of which branch runs. Re-raising the exception preserves the original
    traceback for FastAPI's exception handlers / our structlog pipeline.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
