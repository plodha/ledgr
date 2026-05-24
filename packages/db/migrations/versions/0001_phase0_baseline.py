"""Phase 0 baseline migration.

This migration exists for two reasons:

1. **Create ``_phase0_marker``** — a single-row sentinel table proving that
   ``make migrate`` (and therefore the Alembic env.py, the asyncpg driver, and
   the DATABASE_URL plumbing) actually ran end-to-end against a live Postgres
   instance. Plan 01's ``test_baseline_migration_applied`` queries this row;
   Phase 1 will drop this table once real domain tables provide a stronger
   signal.

2. **Reserve the ``app.current_household_id`` session GUC convention** via
   ``COMMENT ON DATABASE``. Postgres custom GUCs whose names are dotted
   (``app.*``) need no registration since Postgres 9.2; the SQL comment is the
   documentation contract for future contributors. Phase 1 will then:

   (a) ``ALTER TABLE ... ENABLE ROW LEVEL SECURITY`` on each domain table as
       it is created (RLS is per-table — there is no cluster-level "enable" in
       Postgres).
   (b) Attach policies of the form::

           CREATE POLICY ... USING (
               household_id = current_setting('app.current_household_id', true)::uuid
           )

       The second argument ``true`` (``missing_ok``) is **non-negotiable** per
       RESEARCH.md Pitfall 9 — without it, an unset GUC raises
       ``unrecognized configuration parameter`` instead of returning ``NULL``.
   (c) Have ``get_session`` issue ``SET LOCAL app.current_household_id =
       '<uuid>'`` after auth resolves the active household.

Per RESEARCH.md Open Question 1 (recommendation (a)), this Phase 0 baseline
DOES NOT enable RLS or create policies anywhere. The convention is reserved,
not activated. Phase 1 owns activation.
"""

from __future__ import annotations

from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "0001_phase0_baseline"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def _current_db() -> str:
    """Return the connected database name as a quoted SQL identifier.

    Reads the database name from the active engine's URL (which the env.py
    populated from ``DATABASE_URL``). Wraps the name in double-quotes with
    standard double-quote escaping so the resulting ``COMMENT ON DATABASE
    <name>`` SQL is safe against unusual but legal characters in the database
    name. The source is environment-controlled config, not user input — this
    quoting is defensive, not load-bearing for security (T-00-11 disposition).
    """
    bind = context.get_bind()
    db_name = bind.engine.url.database
    if db_name is None:
        raise RuntimeError("No database name available on the Alembic engine URL")
    # Escape any embedded double-quotes per SQL identifier rules.
    escaped = db_name.replace('"', '""')
    return f'"{escaped}"'


def upgrade() -> None:
    # Singleton marker table. The CHECK constraint prevents accidental
    # multi-row inserts; the DEFAULT note text is what
    # ``test_baseline_migration_applied`` asserts ``startswith``.
    op.execute(
        """
        CREATE TABLE _phase0_marker (
            id SMALLINT PRIMARY KEY DEFAULT 1,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            note TEXT NOT NULL DEFAULT 'Phase 0 migration succeeded. RLS scaffolded; policies wired in Phase 1.',
            CONSTRAINT _phase0_marker_singleton CHECK (id = 1)
        );
        """
    )
    op.execute("INSERT INTO _phase0_marker (id) VALUES (1);")

    # Reserve the RLS GUC convention via a database comment. Note the literal
    # ``, true`` inside ``current_setting`` — Pitfall 9 (non-negotiable).
    comment = (
        f"COMMENT ON DATABASE {_current_db()} IS "
        "'PRANAV: RLS GUC convention = app.current_household_id "
        "(set via SET LOCAL per session; read via "
        "current_setting(''app.current_household_id'', true)). "
        "Policies attached in Phase 1.';"
    )
    op.execute(comment)


def downgrade() -> None:
    # Drop the marker table. We intentionally do NOT undo the COMMENT ON
    # DATABASE: it is documentation, not state, and clearing it would lose
    # the convention reservation that Phase 1 depends on (RESEARCH.md
    # Pattern 4 line 702).
    op.execute("DROP TABLE IF EXISTS _phase0_marker")
