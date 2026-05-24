"""Wave 0 failing-by-design tests for the /health endpoint and the Phase 0
baseline migration.

These encode the INFRA-02, INFRA-04, and INFRA-09 contracts. Wave 1 (FastAPI
app) and Wave 2 (Alembic baseline) must satisfy these tests to be considered
complete.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from src.database import AsyncSessionLocal


@pytest.mark.anyio
async def test_health_ok(client: AsyncClient) -> None:
    """``GET /health`` returns the INFRA-02 contract envelope."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db_connected"] is True
    assert body["environment"] in {"dev", "production", "test"}
    assert "version" in body


@pytest.mark.anyio
async def test_baseline_migration_applied(client: AsyncClient) -> None:
    """The Phase 0 baseline migration creates the ``_phase0_marker`` table and
    seeds row ``id=1`` with a note that begins with ``"Phase 0 migration
    succeeded"``. This is the load-bearing proof for INFRA-04 + INFRA-09 — if
    the marker row is missing, the Alembic baseline did not run.
    """
    # ``client`` is yielded so the app's lifespan has fully bound the DB
    # engine before we open our own session.
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT note FROM _phase0_marker WHERE id = 1")
        )
        row = result.first()

    assert row is not None, "_phase0_marker row id=1 was not seeded"
    note = row[0]
    assert isinstance(note, str)
    assert note.startswith("Phase 0 migration succeeded"), (
        f"unexpected marker note: {note!r}"
    )
