# PRANAV — Migration Discipline

> **Schema changes must not lock production tables for more than a few hundred
> milliseconds.** This document is the rule book. Every Phase 1+ Alembic
> migration follows these rules; deviations require a comment in the migration
> file explaining why.

This document satisfies INFRA-08 ("MIGRATIONS.md documents nullable-first +
CREATE INDEX CONCURRENTLY discipline AND the `app.current_household_id` GUC
convention with the `missing_ok` flag") and is the single source of truth for
migration practice in the repo.

## Goal

In a multi-tenant system with self-hosted deployments, the worst kind of
migration is one that takes an `AccessExclusiveLock` on a populated table for
multiple seconds — every other query queues behind it, the web app times out,
and self-hosters with no DBA experience blame the application. Every rule
below exists to keep lock duration to the millisecond range, even on tables
with millions of rows.

## Rule 1 — Nullable-first column adds

**Never** `ADD COLUMN ... NOT NULL DEFAULT 'x'` on a populated table. That
syntax rewrites every existing row to insert the default, holding an
`AccessExclusiveLock` for the duration of the rewrite.

Always split the change into three migrations:

1. `ALTER TABLE <name> ADD COLUMN <col> <type> NULL;` — instant, no row rewrite.
2. `UPDATE <name> SET <col> = <value> WHERE <col> IS NULL;` — backfill in
   batches if the table is large (see the batched-update example in the
   Phase 4 worker code, once it lands).
3. `ALTER TABLE <name> ALTER COLUMN <col> SET NOT NULL;` — fast metadata-only
   operation, no row rewrite (Postgres 11+).

If the column has a default that should apply to **new** rows but not require
a backfill, use `ALTER TABLE ... ADD COLUMN <col> <type> DEFAULT 'x'` without
`NOT NULL` in step 1 — Postgres 11+ stores the default in the catalog and
does not rewrite rows.

## Rule 2 — `CREATE INDEX CONCURRENTLY`

Adding an index to a populated table with `CREATE INDEX` (no `CONCURRENTLY`)
takes a `ShareLock` that blocks writes for the duration of the index build —
several minutes on a multi-million-row table.

Always use:

```sql
CREATE INDEX CONCURRENTLY idx_<table>_<columns>
  ON <table> (<columns>);
```

Caveats for Alembic:

- `CREATE INDEX CONCURRENTLY` **cannot run inside a transaction**. Alembic
  wraps every migration in a transaction by default.
- The migration must declare `transactional_ddl = False` at the top OR use
  `op.execute(...)` with explicit transaction handling that closes the
  surrounding transaction first.
- Phase 1 lands the first canonical example of this pattern (when
  `transaction.household_id` gets its index); refer back to that migration
  when adding concurrent indexes in Phase 2+.

For tables that are still empty (a brand-new table, just created in the
same migration), plain `CREATE INDEX` is fine — there are no rows to lock.

## Rule 3 — Constraints as `NOT VALID` then `VALIDATE`

Adding a `CHECK` or `FOREIGN KEY` constraint to a populated table with the
default syntax scans the entire table to verify existing rows satisfy the
constraint — `AccessExclusiveLock` for the scan duration.

Split it:

```sql
-- Migration N: add the constraint as NOT VALID (skips the full-table check).
ALTER TABLE <name>
  ADD CONSTRAINT <name>_<col>_check
  CHECK (<col> > 0) NOT VALID;

-- Migration N+1 (or same migration, separate statement after a sleep):
ALTER TABLE <name>
  VALIDATE CONSTRAINT <name>_<col>_check;
```

`NOT VALID` only enforces the constraint on **new and updated** rows.
`VALIDATE CONSTRAINT` does the existing-row check but holds only a
`ShareUpdateExclusiveLock` — concurrent reads and writes continue.

Same pattern for foreign keys:

```sql
ALTER TABLE child
  ADD CONSTRAINT child_parent_id_fkey
  FOREIGN KEY (parent_id) REFERENCES parent(id) NOT VALID;
ALTER TABLE child
  VALIDATE CONSTRAINT child_parent_id_fkey;
```

## Rule 4 — Drop columns are two-phase

A `DROP COLUMN` migration is fast (metadata-only), but it cannot be rolled
back without restoring from backup if the application still references the
column.

Always:

1. **Phase N migration:** Ship a code change that removes all references to
   the column. Deploy. Verify nothing breaks.
2. **Phase N+1 migration:** `ALTER TABLE <name> DROP COLUMN <col>;` — only
   after the column has been unused for at least one deploy cycle.

This means a rollback during phase N (revert the deploy) does not break
anything; a rollback during phase N+1 just re-deploys the old code which
still doesn't read the column. The migration history stays linear, and the
column can be dropped without coordinating a code revert.

## Rule 5 — Foreign-key adds use `ON DELETE` carefully

- **`household_id` FKs use `ON DELETE CASCADE`.** Deleting a household
  cleans up every row owned by that household. Required for tenant deletion
  flows (Phase 1+).
- **Intra-domain FKs default to `ON DELETE RESTRICT`.** Prevents accidental
  cascade-deletes (e.g., deleting a category should not silently delete all
  transactions in that category — it should fail and force the user to
  reassign or explicitly drop).
- **Where `ON DELETE SET NULL` is the right semantic** (e.g.,
  `intent_category_id` becomes nullable on category deletion), document the
  choice in the migration comment.

The migration writer must consciously pick the right behavior — there is no
universal default.

## Rule 6 — Long-running data backfills go through procrastinate

If a backfill touches more than ~10k rows, do not run it inline in the
migration. Instead:

1. Migration N: add the column nullable (Rule 1), and enqueue a procrastinate
   job that does the batched backfill.
2. The worker (Phase 4+) runs the backfill in batches with checkpoints.
3. A follow-up migration (after the worker reports complete) flips the
   column to NOT NULL.

This keeps `make migrate` fast even on production-sized data and lets the
backfill resume cleanly if it crashes mid-run.

## RLS convention (Phase 0 reservation; Phase 1 activation)

Every domain table from Phase 1 onward must:

1. Carry a `household_id UUID NOT NULL REFERENCES household(id) ON DELETE CASCADE` column.
2. Have RLS enabled:

   ```sql
   ALTER TABLE <name> ENABLE ROW LEVEL SECURITY;
   ```

3. Carry a per-table household-isolation policy:

   ```sql
   CREATE POLICY <name>_household_isolation ON <name>
     USING (
       household_id = current_setting('app.current_household_id', true)::uuid
     );
   ```

### The `, true` second argument is non-negotiable

`current_setting('app.current_household_id')` (one argument) is **strict**:
when the GUC is unset, Postgres raises
`unrecognized configuration parameter "app.current_household_id"` and the
query fails.

`current_setting('app.current_household_id', true)` (two arguments, where
`true` is the `missing_ok` flag) is **lenient**: when the GUC is unset, it
returns `NULL`, and the policy's `USING` clause then evaluates to
`household_id = NULL::uuid` — which is always `NULL` (effectively `false`) —
so no rows match and the unauthenticated session sees an empty result.

**Every RLS policy in this codebase uses the two-argument form.** A Phase 1+
migration that omits the `, true` is a bug. Code review must catch it.

Source: Phase 0 research register Pitfall 9 (`.planning/phases/00-repo-skeleton/00-RESEARCH.md`,
lines 1132-1138).

### GUC binding from the api

Phase 1's `get_session()` will be extended to issue:

```python
await session.execute(
    text("SET LOCAL app.current_household_id = :hid").bindparams(hid=str(household_id))
)
```

immediately after the session is yielded, using the household_id resolved
from the authenticated user's JWT. `SET LOCAL` scopes the GUC to the current
transaction — when the transaction commits or rolls back, the GUC goes away
with it. This means a connection returned to the pool never carries
household_id state across requests.

### Phase 0 reservation mechanism

Phase 0 does not create any domain tables and does not enable RLS on any
table. It only **reserves the convention** via a `COMMENT ON DATABASE`
statement in the baseline migration:

```sql
COMMENT ON DATABASE <db_name> IS
  'PRANAV. Multi-tenancy via Postgres RLS. Per-table policies activated in
   Phase 1+ filter by current_setting(''app.current_household_id'', true)::uuid.';
```

The comment is documentation — it doesn't enforce anything at the SQL layer.
Enforcement is per-table from Phase 1 onward.

## Migration naming

`packages/db/migrations/versions/NNNN_short_description.py`, where:

- `NNNN` is a zero-padded 4-digit sequence (0001, 0002, …, 0042, …).
- `short_description` is snake_case, describing the migration's purpose
  (e.g., `0002_phase1_household`, `0003_phase1_user_refresh_token`).
- The `revision` identifier inside the file (top of the docstring block)
  matches the filename prefix: `revision: str = "0001_phase0_baseline"`.

Alembic chains migrations by the `down_revision` string in each file, not by
filename. Filename and revision identifier matching is convention only — but
it makes the migration history grep-able and reviewable.

## Running migrations

The developer interface is the Makefile target:

```bash
make migrate
```

This expands to:

```bash
docker compose -f docker/docker-compose.yml --env-file .env exec api \
  alembic -c packages/db/alembic.ini upgrade head
```

The api container has `alembic` installed (it's in `requirements-dev.txt`
which is pip-installed during the api image build). `packages/db/` is
bind-mounted into the container at `/app/packages` so migrations under
`packages/db/migrations/versions/` are visible.

The Alembic `env.py` reads `DATABASE_URL` from the environment at runtime,
overriding the `alembic.ini` fallback URL. The api container inherits
`DATABASE_URL` from docker-compose (interpolated from `POSTGRES_*` env vars
in `.env`), so `make migrate` Just Works without extra config.

To roll back the latest migration:

```bash
docker compose -f docker/docker-compose.yml --env-file .env exec api \
  alembic -c packages/db/alembic.ini downgrade -1
```

(There is no Makefile target for downgrade — it's intentionally manual.)

To inspect current revision:

```bash
docker compose -f docker/docker-compose.yml --env-file .env exec api \
  alembic -c packages/db/alembic.ini current
```

## Quick checklist for every new migration

Before merging a migration PR, the author confirms:

- [ ] No `ADD COLUMN ... NOT NULL DEFAULT 'x'` on a populated table (Rule 1).
- [ ] Index adds on populated tables use `CREATE INDEX CONCURRENTLY` (Rule 2).
- [ ] Constraint adds on populated tables use `NOT VALID` + `VALIDATE`
      (Rule 3).
- [ ] Column drops follow the two-phase pattern (Rule 4).
- [ ] FK `ON DELETE` behavior chosen consciously (Rule 5).
- [ ] Domain tables include `household_id` + RLS + the two-argument
      `current_setting('app.current_household_id', true)` policy (RLS
      Convention).
- [ ] Filename matches `NNNN_short_description.py` and the `revision`
      string inside matches.
- [ ] A `downgrade()` is implemented (even if it's a no-op with a comment
      explaining why).

---

*Phase 0 establishes the convention. Phase 1 lands the first migration that
applies these rules to real domain tables.*
