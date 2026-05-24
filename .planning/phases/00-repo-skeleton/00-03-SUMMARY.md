---
phase: 00-repo-skeleton
plan: 03
subsystem: database
tags: [alembic, sqlalchemy, asyncpg, postgres, rls, migrations, pydantic]

# Dependency graph
requires:
  - phase: 00-repo-skeleton
    provides: "Plan 01 baseline tests (apps/api/tests/test_health.py::test_baseline_migration_applied) — encodes the SELECT note FROM _phase0_marker contract this plan satisfies"
  - phase: 00-repo-skeleton
    provides: "Plan 02 FastAPI app (apps/api/src/database.py, apps/api/src/config.py) — Alembic's env.py reads the same DATABASE_URL the api uses"
provides:
  - "packages/db/ scaffold (alembic.ini, async env.py, Base DeclarativeBase, baseline migration)"
  - "packages/db/migrations/versions/0001_phase0_baseline.py — creates _phase0_marker singleton and reserves app.current_household_id GUC via COMMENT ON DATABASE"
  - "packages/shared/{__init__.py, schemas.py} — documented Pydantic schema home (Phase 0: empty, Phase 1+ populates)"
  - "packages/domain/__init__.py — documented pure business logic package (no DB / no FastAPI imports)"
  - "Foundation for INFRA-04 (make migrate runs Alembic) and INFRA-09 (RLS GUC convention reserved)"
affects:
  - "00-04 Next.js scaffold (creates packages/shared/types.ts alongside the existing schemas.py)"
  - "00-05 Makefile + docker-compose (wires `make migrate` to `cd packages/db && alembic upgrade head` inside the api container)"
  - "01-foundation (Phase 1 rewrites target_metadata = Base.metadata, adds User/Household models, enables RLS per table, attaches policies referencing current_setting('app.current_household_id', true))"

# Tech tracking
tech-stack:
  added:
    - "Alembic 1.13+ async env (async_engine_from_config + pool.NullPool + connection.run_sync)"
  patterns:
    - "DATABASE_URL env var wins over alembic.ini's sqlalchemy.url at runtime (RESEARCH.md Pitfall 1)"
    - "Custom Postgres GUC convention reserved via COMMENT ON DATABASE — documentation contract for Phase 1 RLS policies"
    - "current_setting('app.current_household_id', true) with explicit missing_ok flag (RESEARCH.md Pitfall 9 — non-negotiable)"
    - "Singleton sentinel table pattern (SMALLINT PK DEFAULT 1 + CHECK id=1) for migration smoke proof"
    - "Migrations use op.execute(raw SQL) only — no SQLAlchemy ORM bulk operations (async-safe + Alembic 1.13 sync-context safe)"

key-files:
  created:
    - "packages/db/__init__.py"
    - "packages/db/alembic.ini"
    - "packages/db/models/__init__.py"
    - "packages/db/migrations/env.py"
    - "packages/db/migrations/script.py.mako"
    - "packages/db/migrations/versions/.gitkeep"
    - "packages/db/migrations/versions/0001_phase0_baseline.py"
    - "packages/shared/__init__.py"
    - "packages/shared/schemas.py"
    - "packages/domain/__init__.py"
  modified: []

key-decisions:
  - "Reserve RLS GUC convention via COMMENT ON DATABASE only; do NOT enable RLS on any table in Phase 0 (RESEARCH.md Open Question 1 recommendation (a) — Postgres RLS is per-table; Phase 1 owns per-table ALTER TABLE ENABLE ROW LEVEL SECURITY as domain tables are created)"
  - "Marker note default text starts exactly with 'Phase 0 migration succeeded' to satisfy the Plan 01 test contract (note.startswith assertion)"
  - "downgrade() drops _phase0_marker but does NOT undo COMMENT ON DATABASE (comment is documentation of the convention, not migration state)"
  - "Offline Alembic mode raises NotImplementedError in Phase 0 — single online target, no current need for SQL emission mode"
  - "packages/db/models/__init__.py exports ONLY Base (no User/Household/Account/Transaction — those are Phase 1+ per CLAUDE.md 'Do not create any auth, user, or account tables yet')"

patterns-established:
  - "Async Alembic env.py shape: os.getenv DATABASE_URL → config.set_main_option → async_engine_from_config(NullPool) → connection.run_sync(do_run_migrations)"
  - "Migration file naming: NNNN_short_slug.py with revision identifier matching (Alembic chains by revision string, not filename, but matching is the convention here)"
  - "_current_db() helper for safely quoting the connected database name in COMMENT ON DATABASE statements"

requirements-completed: [INFRA-04, INFRA-09]

# Metrics
duration: 3min
completed: 2026-05-24
---

# Phase 00 Plan 03: Alembic Async Baseline + Packages Scaffold Summary

**Async Alembic env.py with DATABASE_URL override, Phase 0 baseline migration that seeds `_phase0_marker` and reserves the `app.current_household_id` RLS GUC convention via `COMMENT ON DATABASE`, plus documented packages/shared and packages/domain namespaces ready for Phase 1+ to populate.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-24T02:30:32Z
- **Completed:** 2026-05-24T02:33:35Z
- **Tasks:** 3
- **Files created:** 10

## Accomplishments

- Stood up `packages/db/` with Alembic async env.py (`async_engine_from_config` + `pool.NullPool` + `connection.run_sync`) that reads `DATABASE_URL` from the environment at runtime — `alembic.ini`'s `sqlalchemy.url` is now a developer-laptop fallback only (RESEARCH.md Pitfall 1 mitigated).
- Shipped the Phase 0 baseline migration `0001_phase0_baseline.py`: creates `_phase0_marker` (singleton via SMALLINT PK + CHECK id=1) with the exact default note text Plan 01's `test_baseline_migration_applied` asserts on, and issues a `COMMENT ON DATABASE` that embeds `current_setting('app.current_household_id', true)` with the non-negotiable `missing_ok` flag (Pitfall 9 mitigated).
- Created `packages/shared/schemas.py` (empty Pydantic schemas module with multi-line docstring encoding CLAUDE.md constraint #2 — domain types live here) and `packages/domain/__init__.py` (empty pure-business-logic package documenting CLAUDE.md constraint #6 — cross-module calls go through here; no SQLAlchemy / no FastAPI imports). `packages/db/models/__init__.py` exports only `Base = DeclarativeBase` — no domain tables yet, per CLAUDE.md.
- Foundation for INFRA-04 (Alembic tooling ready for `make migrate` to invoke in Wave 4) and INFRA-09 (RLS GUC convention reserved as documentation; per-table activation deferred to Phase 1).

## Task Commits

Each task was committed atomically:

1. **Task 1: packages/db scaffold — alembic.ini, env.py, script.py.mako, models/__init__.py** — `d1c2622` (feat)
2. **Task 2: Phase 0 baseline migration (0001_phase0_baseline.py)** — `8d16f04` (feat)
3. **Task 3: packages/shared + packages/domain scaffold** — `119c213` (feat)

_Plan metadata commit (SUMMARY) follows after this file lands._

## Files Created/Modified

- `packages/db/__init__.py` — package marker with one-line docstring
- `packages/db/alembic.ini` — Alembic config (`script_location=migrations`, `prepend_sys_path=../..`, `postgresql+asyncpg://` fallback URL, full logger config so `fileConfig` works)
- `packages/db/models/__init__.py` — exports only `class Base(DeclarativeBase): pass`; Phase 1+ adds domain models that inherit Base
- `packages/db/migrations/env.py` — async env: reads `os.getenv("DATABASE_URL")`, overrides `sqlalchemy.url`, uses `async_engine_from_config(..., poolclass=pool.NullPool)`, `connection.run_sync(do_run_migrations)`, raises `NotImplementedError` in offline mode
- `packages/db/migrations/script.py.mako` — Alembic 1.18 default mako template for `alembic revision`
- `packages/db/migrations/versions/.gitkeep` — keeps the empty versions/ dir tracked
- `packages/db/migrations/versions/0001_phase0_baseline.py` — creates `_phase0_marker` (SMALLINT PK DEFAULT 1, applied_at TIMESTAMPTZ, note TEXT DEFAULT 'Phase 0 migration succeeded. RLS scaffolded; policies wired in Phase 1.', `CONSTRAINT _phase0_marker_singleton CHECK (id = 1)`), inserts id=1, then runs `COMMENT ON DATABASE` that documents the `app.current_household_id` GUC convention with the `current_setting(..., true)` missing_ok flag. `downgrade()` drops the marker but leaves the COMMENT (it is documentation, not state).
- `packages/shared/__init__.py` — one-line docstring describing the shared-types role across api (Pydantic) and web (Zod via future types.ts)
- `packages/shared/schemas.py` — empty module with multi-line docstring documenting CLAUDE.md constraint #2: Pydantic v2 BaseModel, read/write schema separation, INTEGER cents, TIMESTAMPTZ / ISO 8601
- `packages/domain/__init__.py` — empty package with multi-line docstring documenting CLAUDE.md constraint #6: pure business logic only, no SQLAlchemy / no FastAPI imports, planned subpackages (money, dates, categorization, transactions, forecast, connectors)

## Decisions Made

- **RLS interpretation:** Per RESEARCH.md Open Question 1 (lines 1198-1205) — recommendation (a) — Phase 0 reserves the `app.current_household_id` GUC convention via a `COMMENT ON DATABASE` and a marker table only. **No `ENABLE ROW LEVEL SECURITY` or `CREATE POLICY` statements appear anywhere in Phase 0.** Postgres has no cluster-level RLS enable; activation is per-table and is Phase 1's responsibility as domain tables come online.
- **Migration contract:** The default `note` text on `_phase0_marker` is exactly `'Phase 0 migration succeeded. RLS scaffolded; policies wired in Phase 1.'` so that Plan 01's `note.startswith("Phase 0 migration succeeded")` assertion is satisfied and so the trailing clause re-documents the deferral.
- **`current_setting(..., true)` discipline:** The COMMENT ON DATABASE body embeds the literal call `current_setting('app.current_household_id', true)` with the `missing_ok=true` flag. RESEARCH.md Pitfall 9 (lines 1132-1138) flags this as non-negotiable: without it an unset GUC raises `unrecognized configuration parameter` instead of returning NULL, which would surface as opaque errors in Phase 1 RLS policies.
- **NullPool for Alembic engine:** RESEARCH.md Pattern 4 — Alembic is a one-shot CLI tool; a pooled connection would leak state across invocations.
- **Offline mode disabled:** Single online Postgres target; no current SQL emission use case. `raise NotImplementedError` is the safer fail-fast.
- **Models export ONLY `Base`:** CLAUDE.md "Do not create any auth, user, or account tables yet — those are Phase 1" is honored exactly.
- **packages/shared/types.ts NOT in this plan:** Deferred to Plan 04 (Next.js scaffold), which owns the TypeScript toolchain that will resolve the file.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1–4 deviations applied. The plan's `<verify>` automated gates and acceptance criteria pass verbatim; no auto-fixes were needed.

## Issues Encountered

None.

## Threat-Model Mitigations Honored

- **T-00-11 (SQL injection via `_current_db()`):** `_current_db()` reads the database name from the active engine's URL (env-controlled, not user input), escapes embedded double-quotes, and wraps the name in standard SQL identifier double-quoting. No untrusted input reaches the SQL string.
- **T-00-12 (RLS GUC unset → opaque error):** The COMMENT ON DATABASE text and the migration's docstring both teach the `current_setting('app.current_household_id', true)` form; the missing_ok flag is present in the comment body.
- **T-00-13 (Phase 1 forgets `ENABLE ROW LEVEL SECURITY` on a new table):** Out of scope for Phase 0 (the plan acknowledges this as Phase 1's responsibility). Phase 0's contribution is the marker that proves migration tooling works + the COMMENT-anchored convention reminder.
- **T-00-14 (migration lock contention):** N/A in Phase 0 — empty database. Discipline documentation deferred to Plan 06 (docs/MIGRATIONS.md).

## User Setup Required

None — Phase 0 migration scaffold is fully wired. Once Wave 4 lands `make migrate` and docker-compose stands up Postgres, `cd packages/db && alembic upgrade head` will materialize `_phase0_marker` and the COMMENT ON DATABASE in one shot.

## Next Phase Readiness

- **Plan 04 (Next.js scaffold):** Will create `packages/shared/types.ts` alongside the existing `packages/shared/schemas.py` and import-resolve `@/shared/types` from the web app's tsconfig.
- **Plan 05 (Makefile + docker-compose):** Will add `make migrate` → `docker compose exec api sh -c 'cd /app/packages/db && alembic upgrade head'`. The env.py reads `DATABASE_URL` from the container's environment via `os.getenv`.
- **Phase 1 (foundation):** Will rewrite `packages/db/migrations/env.py` line `target_metadata = None` to `from packages.db.models import Base; target_metadata = Base.metadata`, add User/Household/Account/Transaction models under `packages/db/models/`, ENABLE ROW LEVEL SECURITY per domain table, attach policies using `current_setting('app.current_household_id', true)::uuid`, and have `apps/api/src/database.py::get_session` issue `SET LOCAL app.current_household_id = '<uuid>'` after auth resolves.

## Self-Check

Verified before publishing:

```
packages/db/__init__.py                                FOUND
packages/db/alembic.ini                                FOUND
packages/db/models/__init__.py                         FOUND
packages/db/migrations/env.py                          FOUND
packages/db/migrations/script.py.mako                  FOUND
packages/db/migrations/versions/.gitkeep               FOUND
packages/db/migrations/versions/0001_phase0_baseline.py FOUND
packages/shared/__init__.py                            FOUND
packages/shared/schemas.py                             FOUND
packages/domain/__init__.py                            FOUND

d1c2622 (Task 1)  FOUND in git log
8d16f04 (Task 2)  FOUND in git log
119c213 (Task 3)  FOUND in git log
```

## Self-Check: PASSED

---

*Phase: 00-repo-skeleton*
*Completed: 2026-05-24*
