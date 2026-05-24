"""Alembic async env.py for the PRANAV migrations tree.

Reproduces RESEARCH.md Pattern 4 (lines 605-652):

* Read ``DATABASE_URL`` from the process environment and override the
  ``sqlalchemy.url`` value from ``alembic.ini`` at runtime. The .ini fallback is
  a developer-laptop convenience for direct ``alembic`` invocation outside the
  container; in normal use (``make migrate`` inside the api container), the env
  var supplied by docker-compose wins. This addresses RESEARCH.md Pitfall 1
  ("hard-coded sqlalchemy.url leaks across environments").
* Use ``async_engine_from_config`` with ``pool.NullPool`` — Alembic runs
  one-shot from the CLI and should not keep a pool warm (RESEARCH.md Pattern 4
  line 640; Pitfall 2).
* Drive ``context.run_migrations`` from the sync side via
  ``connection.run_sync(do_run_migrations)`` because Alembic's migration API is
  sync-only and we are inside an async engine.

Phase 0 has no SQLAlchemy models to autogenerate against, so
``target_metadata = None``. Phase 1 will rewrite this line to
``from packages.db.models import Base; target_metadata = Base.metadata``.

Offline mode is intentionally not supported in Phase 0: the project has a
single online DB target (Postgres via asyncpg), and offline SQL emission would
need separate plumbing that has no current use case.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

# RESEARCH.md Pattern 4 lines 619-622 / Pitfall 1: env var wins over alembic.ini.
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Phase 0: no models, no autogenerate. Phase 1 replaces this with
# ``from packages.db.models import Base; target_metadata = Base.metadata``.
target_metadata = None


def do_run_migrations(connection: Connection) -> None:
    """Run the migration batch inside a sync ``Connection``.

    Alembic's migration API is synchronous; we call this via
    ``connection.run_sync`` from the async engine context.
    """
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Open an async engine, run migrations, dispose the engine.

    ``NullPool`` is required: Alembic is a one-shot CLI tool and must not leave
    a connection pool resident across invocations.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Synchronous entry point Alembic invokes — dispatches into asyncio."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    raise NotImplementedError("Offline mode not supported in Phase 0; use online mode")
else:
    run_migrations_online()
