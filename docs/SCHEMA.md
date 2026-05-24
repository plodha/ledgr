# PRANAV — Database Schema

> **Phase 0 placeholder.** This document lists the schema PRANAV will grow
> into across Phases 1-11. Phase 0 ships only the `_phase0_marker` singleton
> table — every domain table named below is a reservation, not a created
> object. As each phase lands, this document gets the actual column list and
> constraint syntax in place of the prose description.

## Phase 0 status (what exists today)

The Phase 0 baseline migration (`packages/db/migrations/versions/0001_phase0_baseline.py`)
creates exactly **one table**:

| Table | Purpose | Columns |
|-------|---------|---------|
| `_phase0_marker` | Singleton sentinel proving the baseline migration ran | `id SMALLINT PK DEFAULT 1 CHECK (id=1)`, `applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `note TEXT NOT NULL DEFAULT 'Phase 0 migration succeeded'` |

Plus Alembic's own bookkeeping table (`alembic_version`).

No domain tables exist yet. The `_phase0_marker` row is the proof-of-life signal
that `apps/api/tests/test_health.py::test_baseline_migration_applied` queries
against.

In addition, the Phase 0 migration issues a `COMMENT ON DATABASE` reserving
the **`app.current_household_id` Postgres GUC** convention for Phase 1+ RLS
policies. Per [`MIGRATIONS.md`](MIGRATIONS.md) §RLS Convention, the GUC is
read via `current_setting('app.current_household_id', true)::uuid` — the
**`, true` second argument is non-negotiable** (without it, an unset GUC
raises `unrecognized configuration parameter`).

## Phase 1 will add (Auth + Household + RLS Activation)

The four tables that anchor multi-tenant identity:

| Table | Purpose |
|-------|---------|
| `household` | The unit of data isolation. Every domain row carries `household_id`. Created automatically on signup. |
| `household_membership` | Many-to-many between `user` and `household` with a role column (`owner`, `member`). One user can belong to multiple households (Phase 1+ invitation flow). |
| `user` | Authenticated principal: email, hashed password (pwdlib + argon2), optional TOTP secret for 2FA, timestamps. |
| `refresh_token` | Long-lived revocable tokens for refresh-token rotation. Short-lived access JWT lives in an HttpOnly cookie; the refresh token is opaque and stored encrypted. |

Phase 1 also activates **per-table RLS policies** on all four tables using the
GUC reserved in Phase 0. The auth-resolved `household_id` is written to the
session via `SET LOCAL app.current_household_id = '<uuid>'` inside
`get_session()`.

## Phase 2 will add (Accounts + Net Worth)

| Table | Purpose |
|-------|---------|
| `account` | Every financial account the user models: checking, savings, credit card, cash, money market, CD, loan, other. Includes `is_autopay_enabled`, `statement_close_day`, `payment_due_day` (consumed by Phase 10's bill-pay widget), `archived_at` (archived accounts are hidden from totals but retained). |
| `account_balance_snapshot` | Daily snapshots of account balances. Written by a procrastinate-ready hook (worker arrives Phase 4). Drives the multi-period net-worth history chart on the dashboard. |

## Phase 3 will add (Categories + Transactions + Tags + Transfers)

| Table | Purpose |
|-------|---------|
| `transaction` | The central domain row. **`transaction_date DATE`** (when the user made the purchase), **`post_date TIMESTAMPTZ NULL`** (when the bank settled it), `amount_cents INTEGER NOT NULL`, `account_id FK`, **`merchant_category VARCHAR` (immutable after insert)**, **`intent_category_id UUID NULL` (user-editable)**, `status` enum (`pending`, `posted`), `notes TEXT NULL`, `merchant_name`. Pending transactions are excluded from category totals. |
| `category` | Hierarchical (parent_id self-FK). User-managed; seeded with a default tree. `intent_category_id` on `transaction` references this. |
| `tag` | User-defined tags: tax-deductible, reimbursable, custom. |
| `transaction_tag` | Many-to-many between `transaction` and `tag`. |
| `transfer` | Represents one transfer between two own accounts as a single row (NOT two transactions). Phase 3 invariant: transfers are not double-counted as income+expense. |

> **Architectural invariants** (encoded in `packages/domain/money/` and
> `packages/domain/dates/`):
> - `merchant_category` is immutable after insert (property test in Phase 3).
> - `intent_category_id` is user-editable.
> - `list_transactions_for_totals()` is the **canonical aggregator** —
>   pending transactions are filtered out here, never at the SQL layer of
>   individual queries.

## Phase 4 will add (CSV Import + Background Worker)

| Table | Purpose |
|-------|---------|
| `import_batch` | One row per CSV upload: filename, row_count, imported_at, status. Auditability for "where did this transaction come from". |
| `csv_import_mapping` | Saved per-institution column mapping. JSON `column_map` field maps source columns to date/amount/merchant/description/type. Pre-populated on next upload for the same `institution_name`. |
| `procrastinate_jobs` (+ siblings) | procrastinate's own tables. Managed by procrastinate's CLI; wired into Alembic as a one-time `alembic stamp` so the migration history stays linear. |

## Phase 5 will add (Rules Engine)

| Table | Purpose |
|-------|---------|
| `rule` | User-authored categorization rule: name, priority, enabled, conditions (JSON array of `{field, operator, value}`), target `intent_category_id`. Fires on every CSV import. The evaluator is pure domain logic in `packages/domain/categorization/` — zero DB calls (import-linter blocks SQLAlchemy imports from that path). |

## Phase 6 will add (Recurring Transactions)

| Table | Purpose |
|-------|---------|
| `recurring_transaction` | Scheduled income/expense with RFC 5545 rrule string, account_id, amount_cents, merchant, default category. The generator produces an expected-transactions DTO list for any date range — it **never writes** to the `transaction` table (separation required for Phase 8 forecast trustworthiness). |

## Phase 7 will add (Budget View)

| Table | Purpose |
|-------|---------|
| `budget_allocation` | Per-category monthly allocation in cents. Includes a `rollover_behavior` column (`start_fresh` or `roll_unused`). Actuals come from `list_transactions_for_totals()` — pending excluded. |

## Phase 8 will add (Forecast View — the differentiator)

| Table | Purpose |
|-------|---------|
| `forecast_snapshot` | Persisted forecast for accuracy tracking. Stores the median + p25 + p75 projected balance per account per day at snapshot time, so next month's actuals can be compared back. Drives the MAE-per-account widget. |

## Phase 9 will add (Reports)

| Table | Purpose |
|-------|---------|
| `report_preference` | User-level setting: group reports by `transaction_date` (default) or `post_date`. Persists across sessions. |

## Phase 10 will add (Bill Pay Tracking)

(Uses existing `account.is_autopay_enabled`, `account.statement_close_day`,
`account.payment_due_day` from Phase 2 — no new tables.)

## Phase 11 will add (Onboarding Wizard)

| Table | Purpose |
|-------|---------|
| `onboarding_progress` | Per-user step tracking for the first-run wizard. Includes JSON `completed_steps` field and the current `step_index`. |

## Conventions (mandatory for every domain table)

These rules apply to **every** domain table added from Phase 1 onward. They are
not negotiable for individual table designs.

### Multi-tenancy (RLS)

Every domain table:

```sql
ALTER TABLE <name>
  ADD COLUMN household_id UUID NOT NULL
  REFERENCES household(id) ON DELETE CASCADE;

ALTER TABLE <name> ENABLE ROW LEVEL SECURITY;

CREATE POLICY <name>_household_isolation ON <name>
  USING (
    household_id = current_setting('app.current_household_id', true)::uuid
  );
```

The `, true` second argument to `current_setting` is **non-negotiable** — see
[`MIGRATIONS.md`](MIGRATIONS.md) §RLS Convention and the Phase 0 research
register Pitfall 9.

### Money

Money values are stored as **`amount_cents INTEGER NOT NULL`** — never
`NUMERIC`, never `FLOAT`, never `DECIMAL` at the storage layer. Display
conversion to formatted dollars happens in the browser via `Intl.NumberFormat`.

### Dates

- **Business dates:** `DATE` (e.g., `transaction_date DATE NOT NULL`).
- **Timestamps:** `TIMESTAMPTZ NOT NULL DEFAULT NOW()`.
- **Wire format:** ISO 8601 strings (`"2026-05-23"`, `"2026-05-23T14:30:00Z"`).
- **Transactions** always carry **both** `transaction_date DATE` (purchase
  date) and `post_date TIMESTAMPTZ NULL` (bank settlement timestamp).

### Timestamps on every row

Every domain table has:

```sql
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

Plus a trigger to bump `updated_at` on row update (a single shared trigger
function created in the Phase 1 migration).

### Primary keys

Every domain table uses UUID primary keys generated server-side:

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

The `gen_random_uuid()` function comes from Postgres 16's built-in pgcrypto
support — Phase 1 enables the `pgcrypto` extension in its first migration.
UUIDs (not bigserials) so household_id-scoped data can be moved between
environments without ID collisions.

### Indexes

- Every `household_id` column gets a B-tree index (every RLS-policied query
  filters by it).
- Every foreign key gets an index (Postgres does not auto-create them).
- Time-range queries (e.g., transactions in a month) get composite indexes:
  `(household_id, transaction_date DESC)`.

Index additions on populated tables MUST use `CREATE INDEX CONCURRENTLY` per
[`MIGRATIONS.md`](MIGRATIONS.md) Rule 2.

---

*Schema as of Phase 0. Updated by each phase that adds tables.*
