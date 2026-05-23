# Requirements: PRANAV Personal Finance App

**Defined:** 2026-05-23
**Core Value:** See where your money is going before it goes there — a trustworthy cash-flow forecast built on real account balances, recurring transactions, and actual spending patterns.

---

## v1 Requirements

### Infrastructure (Phase 0)

- [ ] **INFRA-01**: Developer can `git clone && make dev` to start all four containers with no errors
- [ ] **INFRA-02**: `/health` endpoint returns `{status: "ok", db_connected: true}` with real DB connection test
- [ ] **INFRA-03**: `make check` passes (pyright + ruff + pytest; tsc + eslint) with zero errors
- [ ] **INFRA-04**: `make migrate` runs Alembic migrations inside the API container
- [ ] **INFRA-05**: Adminer accessible at localhost:8080 connected to the DB
- [ ] **INFRA-06**: `.env.example` documents all required variables
- [ ] **INFRA-07**: Structured JSON logging in place with `structlog` (request_id, redaction of sensitive fields)
- [ ] **INFRA-08**: MIGRATIONS.md documents non-locking migration discipline (nullable-first, `CREATE INDEX CONCURRENTLY`)
- [ ] **INFRA-09**: Postgres RLS infrastructure scaffolded in Phase 0 (enabled, `app.current_household_id` session variable, policies wired in Phase 1)

### Authentication + Household (Phase 1)

- [ ] **AUTH-01**: User can register with email and password
- [ ] **AUTH-02**: User is auto-logged in after registration and a household is created for them
- [ ] **AUTH-03**: User can log in with email and password; session persists across browser refresh
- [ ] **AUTH-04**: User can log out from any page
- [ ] **AUTH-05**: User can request password reset via email link and set a new password
- [ ] **AUTH-06**: User can enable 2FA via TOTP authenticator app
- [ ] **AUTH-07**: All protected routes require authentication; unauthenticated requests return 401
- [ ] **AUTH-08**: Household ID is enforced on all data queries via Postgres RLS; cross-household data is invisible (returns 404, not 403)
- [ ] **AUTH-09**: Basic shell layout with navigation renders after login

### Accounts (Phase 2)

- [ ] **ACCT-01**: User can create a financial account (name, type, institution, balance, currency)
- [ ] **ACCT-02**: Account types: checking, savings, credit_card, cash, money_market, cd, loan, other
- [ ] **ACCT-03**: User can edit and archive accounts
- [ ] **ACCT-04**: Dashboard shows current net worth (`sum(assets) - sum(liabilities)`)
- [ ] **ACCT-05**: Dashboard shows net worth history chart (multi-period line chart)
- [ ] **ACCT-06**: `account_balance_snapshot` records daily balance per account for history chart

### Categories + Transactions (Phase 3)

- [ ] **TXN-01**: User can manually log a transaction (account, amount, date, merchant, category, notes)
- [ ] **TXN-02**: Transaction list is filterable by account, category, date range, and status
- [ ] **TXN-03**: Pending transactions are displayed with visual distinction and excluded from category totals until posted
- [ ] **TXN-04**: `transaction_date` and `post_date` are always stored separately; `transaction_date` is type `DATE` (not TIMESTAMPTZ)
- [ ] **TXN-05**: `merchant_category` (bank-assigned, immutable) and `intent_category_id` (user-editable FK) are always distinct fields
- [ ] **TXN-06**: User can create and manage categories with parent/child hierarchy
- [ ] **TXN-07**: User can tag transactions (tax-deductible, reimbursable, vacation, custom)
- [ ] **TXN-08**: User can record transfers between own accounts without double-counting as income + expense
- [ ] **TXN-09**: MCC codes seeded as reference table; `merchant_category` populated from MCC lookup on import
- [ ] **TXN-10**: User can edit and delete own transactions

### CSV Import (Phase 4)

- [ ] **CSV-01**: User can upload a CSV file and map its columns to date, amount, merchant, description, type
- [ ] **CSV-02**: Column mapping is saved per institution and reused on next upload
- [ ] **CSV-03**: User must explicitly select date format from a dropdown; parsed date previewed with day-of-week
- [ ] **CSV-04**: Preview shows first 10 rows with flagged potential duplicates before commit
- [ ] **CSV-05**: Duplicate detection uses hash(account + transaction_date + amount_cents + merchant); user can override "actually different"
- [ ] **CSV-06**: Import batch record created for auditability (filename, row count, imported_at, status)
- [ ] **CSV-07**: Re-importing same file adds zero duplicate transactions

### Rules Engine (Phase 5)

- [ ] **RULE-01**: User can create categorization rules with conditions (field, operator, value) and AND logic
- [ ] **RULE-02**: Rules are evaluated as pure domain logic (no DB calls in rule evaluator)
- [ ] **RULE-03**: Rules are applied automatically on every CSV import
- [ ] **RULE-04**: User can trigger "re-apply rules to history" for transactions not manually overridden
- [ ] **RULE-05**: User can reorder rules by priority (drag-and-drop) and enable/disable individual rules
- [ ] **RULE-06**: When user manually changes a category, app offers "create a rule for this?"

### Recurring Transactions (Phase 6)

- [ ] **RECUR-01**: User can create scheduled transactions (label, account, category, amount, cadence, start date)
- [ ] **RECUR-02**: Cadences: weekly, biweekly, monthly, yearly; dates computed via RFC 5545 rrule (not hand-rolled math)
- [ ] **RECUR-03**: Generator produces expected transaction list for a date range without writing to transaction table
- [ ] **RECUR-04**: Dashboard shows "Upcoming this week" widget from recurring generator
- [ ] **RECUR-05**: User sees preview of next 3 occurrences when creating/editing a recurring item

### Budget View (Phase 7)

- [ ] **BUDG-01**: User can set a monthly budget allocation per category
- [ ] **BUDG-02**: Dashboard / budget view shows allocated vs actual spend per category for current month
- [ ] **BUDG-03**: Categories over budget are visually flagged
- [ ] **BUDG-04**: Budget rollover behavior is configurable (start fresh vs roll unused amount)

### Forecast View (Phase 8)

- [ ] **FORE-01**: Forecast shows daily projected balance per account for 30/60/90 days
- [ ] **FORE-02**: Forecast inputs: current balances, scheduled transactions, avg spend by category (rolling 90-day), known one-offs
- [ ] **FORE-03**: Forecast displays uncertainty bands (p25/p75), not a single line
- [ ] **FORE-04**: "What if" scenario sliders adjust category spend % and show updated forecast in real time
- [ ] **FORE-05**: Forecast accuracy tracking compares last month's forecast to actuals
- [ ] **FORE-06**: Forecast view shows staleness caveat when last sync is >3 days old
- [ ] **FORE-07**: `GET /forecast?days=90&account_id=all` API endpoint

### Reports (Phase 9)

- [ ] **REPT-01**: User can view spending by category for any date range
- [ ] **REPT-02**: User can view monthly summary (income vs expenses vs net)
- [ ] **REPT-03**: User can view year-over-year spending comparison by category
- [ ] **REPT-04**: Reports default to `transaction_date`; user can switch to `post_date` in settings

### Bill Pay Tracking (Phase 10)

- [ ] **BILL-01**: Dashboard "Action needed" widget lists credit card accounts where autopay is off and due date is within 7 days
- [ ] **BILL-02**: User can mark a bill as paid (logs a transaction, clears from widget)
- [ ] **BILL-03**: Account fields `is_autopay_enabled`, `statement_close_day`, `payment_due_day` drive the widget

### Onboarding (Phase 11)

- [ ] **ONBRD-01**: First-time user is guided through: add first account → import or manual transaction → set categories → add a recurring item
- [ ] **ONBRD-02**: Onboarding wizard can be dismissed and resumed; not shown again once completed
- [ ] **ONBRD-03**: Empty states on all major views show contextual "get started" prompts

---

## v2 Requirements

### Data Portability

- **PORT-01**: User can export full household data as CSV (all transactions, accounts, categories)
- **PORT-02**: User can export full household data as JSON
- **PORT-03**: `make backup` wraps pg_dump with documented restore procedure

### Plaid Connector (Phase 12)

- **PLAID-01**: User can connect a bank account via Plaid Link (BYO `PLAID_CLIENT_ID` + `PLAID_SECRET`)
- **PLAID-02**: Nightly sync pulls new transactions via Plaid Transactions Sync cursor
- **PLAID-03**: Plaid transactions are deduplicated against existing manual/CSV entries
- **PLAID-04**: Pending→posted transition updates in place; user notes and tags preserved
- **PLAID-05**: `ITEM_LOGIN_REQUIRED` surfaces as dashboard banner; connector status shown
- **PLAID-06**: Plaid webhooks (`TRANSACTIONS_SYNC`, `ITEM_ERROR`, `AUTH_STATUS_UPDATED`) handled idempotently

### Price Tracking (Phase 13)

- **PRICE-01**: User can create a tracked item (name, unit, optional barcode)
- **PRICE-02**: User can log a price observation (store, price, date)
- **PRICE-03**: Per-item chart shows price history over time annotated with store
- **PRICE-04**: Dashboard widget shows items with biggest price change in last 30 days
- **PRICE-05**: Auto-link fires when a receipt line item matches a tracked item name (fuzzy)

### SimpleFIN Connector (Phase 14)

- **SIMFIN-01**: User can connect accounts via SimpleFIN bridge token
- **SIMFIN-02**: Sync reuses all reconciliation logic from Plaid connector with zero code changes

### Receipt Parsing (Phase 15)

- **RCPT-01**: User can photograph/upload a receipt; app parses it via LLM (BYO API key)
- **RCPT-02**: Parsed line items are shown for user confirmation before saving
- **RCPT-03**: Confirmed line items attach to an existing transaction or create a new one
- **RCPT-04**: Line items auto-trigger price observations for tracked items
- **RCPT-05**: Per-household rate limit (50/day configurable) and cost preview before parsing
- **RCPT-06**: User can forward receipt emails to a configured inbox for auto-parsing

### Multi-User UI (Phase 16)

- **MULTI-01**: Household owner can invite a member by email
- **MULTI-02**: Invitee receives email link, accepts, joins household
- **MULTI-03**: Role enforcement: owner can invite/remove; member can read/write; viewer is read-only
- **MULTI-04**: Transactions can be attributed to a specific household member (cardholder_id)
- **MULTI-05**: Dashboard and reports show per-member spend breakdown
- **MULTI-06**: Member can leave household; owner can transfer ownership

### Investment Accounts (Phase 17)

- **INVEST-01**: User can create an investment account (brokerage, IRA, 401k, Roth IRA, HSA)
- **INVEST-02**: User can manually enter portfolio positions (symbol, quantity, cost basis)
- **INVEST-03**: Price snapshots fetched from free-tier source (Yahoo Finance / Alpha Vantage)
- **INVEST-04**: Portfolio value shown on net worth dashboard and history chart

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| OAuth login (Google, GitHub) | Email/password + 2FA sufficient for v1; household model complicates OAuth mapping |
| Phone bill / utility integrations | Per-vendor effort, low ROI |
| Stock buy/sell recommendations | Regulatory risk, different product |
| Crypto tracking | Different data model, v3+ |
| Tax optimization / filing | Requires CPA-level domain knowledge |
| Bill negotiation / rate shopping | Third-party dependency, scope creep |
| "Family" plan with child accounts | Design when a real user needs it |
| Receipt auto-capture via bank partnerships | Requires enterprise Plaid agreement |
| AI chatbot for finances | Hallucination risk, regulatory exposure |
| Credit score monitoring | Vendor dependency, different product |
| Ad-supported tier | Not a self-hostable product concept |
| Gamified goals / streaks | Distraction from core value |
| Multi-currency (v1) | US-only / single-currency-per-household for v1.0; add in future milestone |

---

## Traceability

*Populated by roadmapper — see ROADMAP.md for full phase details and success criteria.*

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 through INFRA-09 | Phase 0 — Repo Skeleton | Pending |
| AUTH-01 through AUTH-09 | Phase 1 — Auth + Household + RLS Activation | Pending |
| ACCT-01 through ACCT-06 | Phase 2 — Accounts + Net Worth History | Pending |
| TXN-01 through TXN-10 | Phase 3 — Categories + Manual Transactions + Tags + Transfers | Pending |
| CSV-01 through CSV-07 | Phase 4 — CSV Import + Background Worker | Pending |
| RULE-01 through RULE-06 | Phase 5 — Rules Engine | Pending |
| RECUR-01 through RECUR-05 | Phase 6 — Recurring Transactions | Pending |
| BUDG-01 through BUDG-04 | Phase 7 — Budget View | Pending |
| FORE-01 through FORE-07 | Phase 8 — Forecast View | Pending |
| REPT-01 through REPT-04 | Phase 9 — Reports | Pending |
| BILL-01 through BILL-03 | Phase 10 — Bill Pay Tracking | Pending |
| ONBRD-01 through ONBRD-03 | Phase 11 — Onboarding Wizard | Pending |

**Coverage:**
- v1 requirements enumerated: 73 total (INFRA 9 + AUTH 9 + ACCT 6 + TXN 10 + CSV 7 + RULE 6 + RECUR 5 + BUDG 4 + FORE 7 + REPT 4 + BILL 3 + ONBRD 3)
- Mapped to phases: 73
- Unmapped: 0 ✓

*Note: prior "71 total" tally corrected on 2026-05-23 during roadmap creation — all REQ-IDs were already enumerated; only the summary count was off.*

---
*Requirements defined: 2026-05-23*
*Last updated: 2026-05-23 — traceability populated, phase numbers promoted (6.5→7, 7.5→9, 8.5→11), count tally corrected*
