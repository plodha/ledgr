"""Base declarative model. No domain tables in Phase 0. Phase 1 adds User, Household, etc.

This module deliberately exports ONLY ``Base``. Per CLAUDE.md "Do not create any
auth, user, or account tables yet — those are Phase 1", Phase 0 ships the
SQLAlchemy 2.0 ``DeclarativeBase`` foundation and nothing else. Phase 1+ adds
domain models (``User``, ``Household``, ``Account``, ``Transaction``, …) by
subclassing this ``Base``; Alembic's autogenerate will then diff against
``Base.metadata`` once the env.py is rewired to import it.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base — single source of metadata for Alembic.

    Phase 0: no subclasses. Phase 1+: every domain table inherits from this.
    """

    pass
