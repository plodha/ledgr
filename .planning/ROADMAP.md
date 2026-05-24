# Roadmap: PRANAV — Personal Resource & Asset Navigator for Abundant Value

## Overview

PRANAV is a self-hostable personal finance application (Bitwarden-style: open source, run it yourself or use the cloud version). The core value is a **trustworthy cash-flow forecast** — see where your money is going *before* it goes there. Every prior phase exists to make that forecast trustworthy: real account balances, well-categorized transactions, recurring schedules, and budget guardrails.

This roadmap uses **horizontal-layer structuring** (foundation → auth → data → import → automation → projection → views). Each phase delivers one cohesive technical layer with observable user behavior. v1.0 ships after Phase 11 (Onboarding). Phases 0-11 reach a usable v1.0 ship point; v2 phases (Plaid, Price Tracking, SimpleFIN, Receipts, Multi-User UI, Investments) live in `.planning/PROJECT.md` Active list.

**Granularity:** fine (12 phases)
**Mode:** interactive
**Coverage:** 73/73 v1 requirements mapped (REQUIREMENTS.md states "71 total" but enumerates 73 distinct REQ-IDs — coverage is exhaustive).

## Phases

**Phase Numbering:** Integer phases (0-11) only; no decimal insertions at this stage. The original PROJECT.md "Phase 6.5 / 7.5 / 8.5" labels have been promoted to integer phases (7, 9, 11) so they're treated as first-class roadmap milestones.

- [ ] **Phase 0: Repo Skeleton** - Running Docker stack (FastAPI + Next.js + Postgres + Adminer) with RLS scaffolding, logging, and migration discipline in place
- [ ] **Phase 1: Auth + Household + RLS Activation** - Register/login/logout, household auto-created, 2FA, password reset, Postgres RLS policies enforced
- [ ] **Phase 2: Accounts + Net Worth History** - Model financial accounts; dashboard net worth widget + history chart from daily balance snapshots
- [ ] **Phase 3: Categories + Manual Transactions + Tags + Transfers** - Manually log spending; merchant_category vs intent_category_id distinct; pending excluded from totals; transfers without double-counting
- [ ] **Phase 4: CSV Import + Background Worker** - Upload statements; column mapping memory per institution; duplicate detection; procrastinate worker container introduced
- [ ] **Phase 5: Rules Engine** - Pure-domain rule evaluator; auto-apply on import; re-apply to history; rule suggestions from manual overrides
- [ ] **Phase 6: Recurring Transactions** - RFC 5545 rrule-based scheduled income/expenses; generator produces expected list without writing transactions
- [ ] **Phase 7: Budget View** - Monthly per-category allocations; allocated vs actual; over-budget flagging; rollover behavior configurable
- [ ] **Phase 8: Forecast View** - Daily projected balance per account 30/60/90d with p25/p75 bands, "what if" sliders, accuracy tracking, staleness caveat
- [ ] **Phase 9: Reports** - Spending by category, monthly income/expense/net, year-over-year, transaction_date vs post_date toggle
- [ ] **Phase 10: Bill Pay Tracking** - "Action needed" dashboard widget for non-autopay cards within 7 days of due date; mark-as-paid logs transaction
- [ ] **Phase 11: Onboarding Wizard** - Guided first-run flow (account → transactions → categories → recurring); empty states across views; **v1.0 ship point**

## Phase Details

### Phase 0: Repo Skeleton

**Goal:** A developer can `git clone && make dev` and get a running four-container Docker stack with FastAPI, Next.js, Postgres, and Adminer, plus all the tooling scaffolded — including Postgres Row-Level Security infrastructure ready for Phase 1 to wire policies into.
**Depends on:** Nothing (first phase)
**Requirements:** INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07, INFRA-08, INFRA-09
**Success Criteria** (what must be TRUE):

  1. `git clone && make dev` starts all four containers (web, api, postgres, adminer) with zero errors
  2. `http://localhost:8000/health` returns `{status: "ok", db_connected: true, version, environment}` with a real `SELECT 1` against Postgres
  3. `make check` passes with zero errors (pyright + ruff + pytest on api; tsc --noEmit + eslint on web)
  4. `make migrate` runs Alembic upgrade-head inside the api container; `MIGRATIONS.md` documents nullable-first + `CREATE INDEX CONCURRENTLY` discipline
  5. Postgres RLS is enabled at the cluster level and `app.current_household_id` session variable is reserved (policies still inactive — Phase 1 activates them); structured JSON logging via `structlog` is wired with request_id and sensitive-field redaction**Plans:** 1/6 plans executed

**Wave 1**

  - [x] 00-01-PLAN.md — Wave 0: Repo guards (.gitignore, .env.example) + apps/api test infrastructure (pyproject.toml, conftest, failing-by-design test suite)
  - [ ] 00-02-PLAN.md — Wave 1: FastAPI core (config.py, database.py, logging_config.py, main.py, health/router.py)

**Wave 2** *(blocked on Wave 1 completion)*

  - [ ] 00-03-PLAN.md — Wave 2: Alembic async env.py + Phase 0 baseline migration (_phase0_marker + RLS GUC convention reservation)

**Wave 3** *(blocked on Wave 2 completion)*

  - [ ] 00-04-PLAN.md — Wave 3: Next.js 16.2 scaffold + placeholder page (Server Component fetching /health) + web Dockerfile

**Wave 4** *(blocked on Wave 3 completion)*

  - [ ] 00-05-PLAN.md — Wave 4: API Dockerfile + docker-compose.yml (4 services) + Makefile (dev/down/migrate/check/shell-*)

**Wave 5** *(blocked on Wave 4 completion)*

  - [ ] 00-06-PLAN.md — Wave 5: docs/ (ARCHITECTURE, SCHEMA, BACKLOG, MIGRATIONS, ADR-001) + README + .github/workflows/check.yml + end-of-phase human-verify checkpoint

### Phase 1: Auth + Household + RLS Activation

**Goal:** Users can register, log in (with optional TOTP 2FA), reset passwords, and log out. A household is auto-created on signup. Every database query is scoped to the calling user's household via Postgres Row-Level Security policies — cross-household data is invisible (returns 404, never 403).
**Depends on:** Phase 0
**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09
**Success Criteria** (what must be TRUE):

  1. Register with email+password → auto-login → empty dashboard appears; household_membership row exists with role=owner; session persists across browser refresh
  2. Log out from any page; log back in; 2FA TOTP enrollment + verification works end-to-end via an authenticator app
  3. Password reset request emits an email link; clicking it lets the user set a new password and invalidates prior sessions
  4. Two-household pytest fixture proves cross-household isolation: User B requesting User A's resource gets 404 (not 403); unauthenticated requests to protected routes return 401
  5. `CurrentContext` + `get_current_context` FastAPI dependency are the sole entry point for household scoping; RLS policies are active on every domain table; basic shell layout with navigation renders post-login

**Plans:** TBD
**UI hint:** yes

### Phase 2: Accounts + Net Worth History

**Goal:** Users can model every financial account they own (checking, savings, credit card, cash, money market, CD, loan, other) with name, type, institution, balance, currency, and bill-pay fields. The dashboard displays current net worth and a multi-period history chart fed by daily balance snapshots.
**Depends on:** Phase 1
**Requirements:** ACCT-01, ACCT-02, ACCT-03, ACCT-04, ACCT-05, ACCT-06
**Success Criteria** (what must be TRUE):

  1. User creates accounts of every supported type; edits an account; archives an account (archived accounts are hidden from totals but retained for history)
  2. Dashboard net worth widget equals `sum(asset balances) - sum(liability balances)` in cents and matches the user's mental model of their finances
  3. `account_balance_snapshot` rows are written daily (procrastinate-ready hook, even if worker arrives in Phase 4) and the dashboard history chart renders multi-period (1M/3M/1Y) line chart from snapshots
  4. Account fields `is_autopay_enabled`, `statement_close_day`, `payment_due_day` are stored and editable (consumed by Phase 10's bill-pay widget)

**Plans:** TBD
**UI hint:** yes

### Phase 3: Categories + Manual Transactions + Tags + Transfers

**Goal:** Users can manually log transactions with full taxonomy: hierarchical categories, tags, and transfers between own accounts. The architectural invariants — `merchant_category` immutable, `intent_category_id` editable, `transaction_date` as DATE, pending excluded from totals — are encoded in domain helpers (`packages/domain/money/`, `packages/domain/dates/`, `list_transactions_for_totals()`).
**Depends on:** Phase 2
**Requirements:** TXN-01, TXN-02, TXN-03, TXN-04, TXN-05, TXN-06, TXN-07, TXN-08, TXN-09, TXN-10
**Success Criteria** (what must be TRUE):

  1. User logs a week of real spending manually: each transaction has account, amount (integer cents), `transaction_date` (DATE), optional `post_date`, merchant, intent category, notes; edit and delete own transactions works
  2. Transaction list filters by account, category, date range, and status; pending transactions render with visual distinction (e.g., italic + badge) and are demonstrably excluded from category totals until `status='posted'`
  3. `merchant_category` (populated from seeded MCC reference table) and `intent_category_id` are always separate columns; a property test asserts `merchant_category` is immutable after insert
  4. User creates parent/child categories; tags a transaction as tax-deductible/reimbursable/custom; records a transfer between two own accounts that appears as exactly one transfer row (not double-counted as income+expense)
  5. Canonical `list_transactions_for_totals()` in `packages/domain/transactions/totals.py` is the *only* aggregator that touches transaction sums — enforced by import-linter

**Plans:** TBD
**UI hint:** yes

### Phase 4: CSV Import + Background Worker

**Goal:** Users can upload bank/card CSVs with a column-mapping wizard that remembers each institution's layout, preview the first 10 rows with duplicate flags, and commit the import. The procrastinate background worker container (`apps/worker/`) is introduced as the first job consumer, and the `packages/domain/reconciliation/dedupe` module is born (reused by future Plaid/SimpleFIN connectors).
**Depends on:** Phase 3
**Requirements:** CSV-01, CSV-02, CSV-03, CSV-04, CSV-05, CSV-06, CSV-07
**Success Criteria** (what must be TRUE):

  1. User uploads a CSV, selects date format from a dropdown (preview shows parsed date with day-of-week), maps columns to date/amount/merchant/description/type; mapping is saved per `institution_name` and pre-populated on next upload
  2. Preview shows first 10 rows with flagged potential duplicates (hash of `account_id + transaction_date + amount_cents + merchant_name`); user can override "actually different" per row before commit
  3. Re-importing the same CSV produces zero duplicate transactions; an `import_batch` row records filename, row_count, imported_at, and status for auditability
  4. `apps/worker/` container runs procrastinate workers against Postgres `LISTEN/NOTIFY` (no Redis); CSV parsing dispatched as a job; `make dev` brings up the worker alongside api/web

**Plans:** TBD
**UI hint:** yes

### Phase 5: Rules Engine

**Goal:** Users can author categorization rules that auto-apply on every CSV import. The rule evaluator is pure domain logic — no DB calls inside the evaluator — so it can run in batch (re-apply to history) and on streaming imports identically. When a user manually re-categorizes a transaction, the app offers to extract a rule.
**Depends on:** Phase 4
**Requirements:** RULE-01, RULE-02, RULE-03, RULE-04, RULE-05, RULE-06
**Success Criteria** (what must be TRUE):

  1. User creates a rule with multiple conditions (field, operator, value) joined by AND logic; rule fires on the next CSV import and assigns `intent_category_id` automatically
  2. Rule evaluator is a pure function in `packages/domain/categorization/` — unit tests prove it has zero DB dependencies; import-linter blocks SQLAlchemy imports from that path
  3. "Re-apply rules to history" endpoint re-categorizes only transactions where `intent_category_id` was not manually overridden; manual overrides survive
  4. User reorders rules by priority via drag-and-drop and enables/disables individual rules; the editor reflects priority on next evaluation
  5. After a manual category change in the UI, app prompts "create a rule for this?" with pre-filled conditions; clicking yes saves the rule

**Plans:** TBD
**UI hint:** yes

### Phase 6: Recurring Transactions

**Goal:** Users can declare scheduled income and expenses with weekly/biweekly/monthly/yearly cadences. The generator produces an expected-transactions list for any date range without ever writing to the `transaction` table — that separation is required for the Phase 8 forecast to remain trustworthy.
**Depends on:** Phase 5
**Requirements:** RECUR-01, RECUR-02, RECUR-03, RECUR-04, RECUR-05
**Success Criteria** (what must be TRUE):

  1. User creates a biweekly paycheck and a monthly rent payment; dates are computed via `python-dateutil`'s `rrule` (RFC 5545) — not hand-rolled — and survive month-end, leap year, and DST property tests over 24 months
  2. Dashboard "Upcoming this week" widget lists scheduled occurrences with correct dates pulled from the generator
  3. Creating or editing a recurring item shows a live preview of the next 3 occurrences before save
  4. Generator returns expected transactions for a given date range as DTOs; a code-review check confirms zero writes to the `transaction` table from the generator path

**Plans:** TBD
**UI hint:** yes

### Phase 7: Budget View

**Goal:** Users can set monthly per-category budget allocations and see allocated vs. actual spend at a glance. Categories over budget are visually flagged. Rollover behavior (start fresh each month vs. roll unused) is configurable per category.
**Depends on:** Phase 6
**Requirements:** BUDG-01, BUDG-02, BUDG-03, BUDG-04
**Success Criteria** (what must be TRUE):

  1. User sets a monthly budget for "Groceries" of $600; the budget view shows allocated $600 vs. actual (summed from posted transactions in the current month) with a progress bar
  2. Categories where actual > allocated are visually flagged (red bar + over-amount badge); under-budget categories render in green/neutral
  3. User toggles a category's rollover behavior between "start fresh" and "roll unused"; the next month's allocation reflects the choice
  4. Actual spend in the budget view uses `list_transactions_for_totals()` (canonical aggregator) — pending transactions are excluded from "actual"

**Plans:** TBD
**UI hint:** yes

### Phase 8: Forecast View

**Goal:** The headline differentiator. Users see daily projected balance per account (and total) for the next 30/60/90 days, with p25/p75 uncertainty bands, "what if" scenario sliders, accuracy tracking against prior forecasts, and a staleness caveat when data is >3 days old. Inputs are current balances + scheduled transactions (Phase 6) + rolling-90d avg spend by category + known one-offs — forecast trustworthiness depends on prior phases.
**Depends on:** Phase 7 (and Phase 6 recurring schedules)
**Requirements:** FORE-01, FORE-02, FORE-03, FORE-04, FORE-05, FORE-06, FORE-07
**Success Criteria** (what must be TRUE):

  1. `GET /forecast?days=90&account_id=all` returns daily projected balance per account and aggregate, each with median + p25 + p75 bands; the chart renders 30/60/90d toggle with uncertainty fill
  2. Forecast inputs are all four sources (current balances, scheduled transactions, rolling-90d avg-spend-by-category, known one-offs); a unit test asserts removing any input changes the output
  3. "What if" sliders adjust category spend percentages (e.g., Groceries -20%) and the forecast line updates in real time without a page reload
  4. Accuracy tracking compares last month's saved forecast snapshot to actuals and shows MAE per account; a staleness caveat banner renders when most-recent sync (or manual entry) is older than 3 days
  5. User makes a real financial decision based on the forecast (delay a purchase, confirm bill coverage) — qualitative trust check before v1.0

**Plans:** TBD
**UI hint:** yes

### Phase 9: Reports

**Goal:** Users can answer "where did my money go" with three reports: spending by category for any date range, monthly income vs. expenses vs. net, and year-over-year spending comparison by category. A user-level setting toggles whether reports group by `transaction_date` (default) or `post_date`.
**Depends on:** Phase 8
**Requirements:** REPT-01, REPT-02, REPT-03, REPT-04
**Success Criteria** (what must be TRUE):

  1. User picks an arbitrary date range and sees spending grouped by intent category, sorted by amount, with per-category totals matching `list_transactions_for_totals()` to the cent
  2. Monthly summary report shows income, expenses, and net for each month of the selected year as a stacked or paired bar chart
  3. Year-over-year report compares current year vs. prior year by category (Δ amount + Δ %); empty categories for the prior year render gracefully
  4. User toggles "Group reports by post_date" in settings; all three reports recompute using `post_date` and the change persists across sessions

**Plans:** TBD
**UI hint:** yes

### Phase 10: Bill Pay Tracking

**Goal:** Users never miss a credit-card payment. The "Action needed" dashboard widget surfaces credit-card accounts where `is_autopay_enabled=false` and the computed due date (from `statement_close_day` + `payment_due_day`) is within 7 days. Marking a bill as paid logs a transaction and clears the entry.
**Depends on:** Phase 9
**Requirements:** BILL-01, BILL-02, BILL-03
**Success Criteria** (what must be TRUE):

  1. A credit-card account with `is_autopay_enabled=false` and due date 5 days out appears in the "Action needed" widget with days-remaining badge; an autopay-enabled card with the same due date does NOT appear
  2. User clicks "Mark as paid" → modal asks for amount + source account → confirming creates a posted transaction in `transaction` table and removes the bill from the widget
  3. The widget query uses only the three account fields (`is_autopay_enabled`, `statement_close_day`, `payment_due_day`) — no separate bill-tracking table required

**Plans:** TBD
**UI hint:** yes

### Phase 11: Onboarding Wizard

**Goal:** A first-time user is guided through the four steps that produce a usable system: add first account → import or manually log a transaction → set up categories → add a recurring item. The wizard is dismissible and resumable; once completed it never reappears. Every major view shows contextual empty states for users who skipped or are early in onboarding. **This phase concludes v1.0 — ship and dogfood for 30 days.**
**Depends on:** Phase 10
**Requirements:** ONBRD-01, ONBRD-02, ONBRD-03
**Success Criteria** (what must be TRUE):

  1. Fresh signup (no data) lands on Step 1 of the wizard ("Add your first account"); each step links to the relevant create form and the wizard tracks completion in a household-scoped row
  2. User dismisses the wizard; on next login it offers "Resume onboarding" with progress preserved; completing the final step sets a flag that suppresses the wizard forever
  3. Major views (Transactions, Budget, Forecast, Reports) render context-appropriate empty states with a "get started" CTA pointing to the relevant onboarding step
  4. End-to-end test: a brand-new user completes all four onboarding steps via the wizard and lands on a dashboard with non-empty net worth, at least one transaction, and at least one recurring item

**Plans:** TBD
**UI hint:** yes

## Progress

**Execution Order:**
Phases execute in numeric order: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Repo Skeleton | 1/6 | In Progress|  |
| 1. Auth + Household + RLS Activation | 0/TBD | Not started | - |
| 2. Accounts + Net Worth History | 0/TBD | Not started | - |
| 3. Categories + Manual Transactions + Tags + Transfers | 0/TBD | Not started | - |
| 4. CSV Import + Background Worker | 0/TBD | Not started | - |
| 5. Rules Engine | 0/TBD | Not started | - |
| 6. Recurring Transactions | 0/TBD | Not started | - |
| 7. Budget View | 0/TBD | Not started | - |
| 8. Forecast View | 0/TBD | Not started | - |
| 9. Reports | 0/TBD | Not started | - |
| 10. Bill Pay Tracking | 0/TBD | Not started | - |
| 11. Onboarding Wizard | 0/TBD | Not started | - |

## Traceability — Coverage Validation

| Phase | Requirements | Count |
|-------|--------------|-------|
| 0  | INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07, INFRA-08, INFRA-09 | 9 |
| 1  | AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09 | 9 |
| 2  | ACCT-01, ACCT-02, ACCT-03, ACCT-04, ACCT-05, ACCT-06 | 6 |
| 3  | TXN-01, TXN-02, TXN-03, TXN-04, TXN-05, TXN-06, TXN-07, TXN-08, TXN-09, TXN-10 | 10 |
| 4  | CSV-01, CSV-02, CSV-03, CSV-04, CSV-05, CSV-06, CSV-07 | 7 |
| 5  | RULE-01, RULE-02, RULE-03, RULE-04, RULE-05, RULE-06 | 6 |
| 6  | RECUR-01, RECUR-02, RECUR-03, RECUR-04, RECUR-05 | 5 |
| 7  | BUDG-01, BUDG-02, BUDG-03, BUDG-04 | 4 |
| 8  | FORE-01, FORE-02, FORE-03, FORE-04, FORE-05, FORE-06, FORE-07 | 7 |
| 9  | REPT-01, REPT-02, REPT-03, REPT-04 | 4 |
| 10 | BILL-01, BILL-02, BILL-03 | 3 |
| 11 | ONBRD-01, ONBRD-02, ONBRD-03 | 3 |
| **Total** | | **73** |

**Coverage:** 73/73 mapped, 0 orphaned, 0 duplicates.

**Note on count discrepancy:** REQUIREMENTS.md states "v1 requirements: 71 total" but enumerates 73 distinct REQ-IDs (INFRA: 9, AUTH: 9, ACCT: 6, TXN: 10, CSV: 7, RULE: 6, RECUR: 5, BUDG: 4, FORE: 7, REPT: 4, BILL: 3, ONBRD: 3 = 73). All 73 enumerated requirements are mapped. Recommend correcting the "71 total" tally during the next REQUIREMENTS.md update.

---
*Roadmap created: 2026-05-23*
