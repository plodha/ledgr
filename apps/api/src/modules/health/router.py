"""Health-check endpoint (INFRA-02).

Exposes ``GET /health`` (the prefix is supplied by ``main.py`` when including
this router) returning the four-key envelope mandated by CLAUDE.md and the
``test_health_ok`` Wave 0 test:

  {
    "status":        "ok" | "degraded",
    "version":       Settings.APP_VERSION,
    "environment":   "dev" | "production" | "test",
    "db_connected":  bool
  }

When the DB is unreachable the endpoint still returns HTTP 200 with
``status="degraded"`` and ``db_connected=False`` — matching the Kubernetes
liveness convention (RESEARCH.md Don't Hand-Roll, line 1057) so that an
unhealthy DB does not cause the entire pod to fail liveness checks.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_settings
from ...database import get_session

router = APIRouter()
settings = get_settings()


@router.get("")
async def get_health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str | bool]:
    """Return INFRA-02 health envelope after a literal ``SELECT 1`` probe.

    Wraps the probe in try/except so a DB outage degrades the response
    rather than raising a 500 — see module docstring for the rationale.
    """
    try:
        result = await session.execute(text("SELECT 1"))
        db_connected = result.scalar_one() == 1
    except Exception:
        db_connected = False
    return {
        "status": "ok" if db_connected else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "db_connected": db_connected,
    }
