# Personal Resource & Asset Navigator for Abundant Value

## What This Is

A self-hostable personal finance application built on the Bitwarden model — fully open source, run it yourself or use the cloud version. Multi-user from day one via a household model: every financial record belongs to a household, not a user. Built for people who want to own their financial data.

## Core Value

See where your money is going *before* it goes there — a trustworthy cash-flow forecast built on real account balances, recurring transactions, and your actual spending patterns.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **Phase 0:** Running Docker stack — FastAPI + Next.js + Postgres + Adminer, `make dev` starts all four containers, `/health` returns `db_connected: true`, `make check` passes
- [ ] **Phase 1:** Auth + Household — register, login, logout; household auto-created on signup; every future row scoped to a household
- [ ] **Phase 2:** Accounts — model every financial account; net worth widget on dashboard
- [ ] **Phase 3:** Categories + Manual Transactions — log spending manually; merchant_category (bank-immutable) vs intent_category_id (user-editable) always distinct; pending transactions shown but excluded from totals until posted
- [ ] **Phase 4:** CSV Import — upload bank statements; column mapping wizard with per-institution memory; duplicate detection; preview before commit
- [ ] **Phase 5:** Rules Engine — auto-categorization; rule evaluator is pure domain logic (no DB calls); re-apply to history endpoint
- [ ] **Phase 6:** Recurring Income + Expenses — scheduled transactions; generator produces expected list without writing to transaction table
- [ ] **Phase 7:** Forecast View — daily projected balance per account for 30/60/90 days; "what if" scenario sliders; accuracy tracking vs actuals
- [ ] **Phase 8:** Bill Pay Tracking — "Action needed" widget; mark-as-paid logs a transaction
- [ ] **Phase 9:** Plaid Connector — BYO keys for self-hosters; abstract Connector interface; pending→posted remap; nightly pg-boss sync
- [ ] **Phase 10:** Price Tracking ("Strawberries Over Time") — track recurring purchase prices over time; inflation made visible
- [ ] **Phase 11:** SimpleFIN Connector — reuses all reconciliation logic from Phase 9
- [ ] **Phase 12:** Receipt Parsing — OCR + LLM pipeline; BYO API key; line items attach to transactions; email intake; auto-trigger price observations
- [ ] **Phase 13:** Multi-User UI — invite by email; role enforcement (owner/member/viewer); per-member spend breakdown
- [ ] **Phase 14:** Investment Accounts — manual position entry; price lookup; portfolio value on net worth

### Out of Scope

- Phone bill / utility integrations — per-vendor effort, low ROI
- Stock buy/sell recommendations — regulatory risk, different product
- Crypto tracking — different data model, v3+
- Tax optimization — requires CPA-level domain knowledge
- Bill negotiation / rate shopping — third-party dependency, scope creep
- "Family" plan with child accounts — design when a real user needs it
- Receipt auto-capture via bank partnerships — requires enterprise Plaid agreement

## Context

- Self-hostable model: users bring their own Plaid/SimpleFIN/LLM API keys; cloud version abstracts behind same interfaces
- Household model designed from Phase 1: `household_id` on every domain table; `household_membership` with owner/member/viewer roles; Phase 13 is just UI + enforcement on top of already-correct schema
- Forecast (Phase 7) is the headline differentiator — everything before it is infrastructure for the forecast to be trustworthy
- `transaction_date` + `post_date` always stored; pending transactions always shown, visually distinguished, excluded from category totals until posted
- MCC codes seeded once as reference table; `merchant_category` (bank label, immutable) and `intent_category_id` (user intent, editable) never merged
- Connector interface (`link`, `sync`, `get_transactions`, `get_balances`) is abstract; Plaid, SimpleFIN, CSV are implementations — reconciliation never talks to a specific connector
- v1.0 ship point after Phase 8; use daily for 30 days, fix what hurts, then continue

## Constraints

- **Money:** Always INTEGER (cents) in DB and on wire — never float, never decimal in storage
- **Dates:** Store `transaction_date` + `post_date` as DATE/TIMESTAMPTZ; ISO strings on wire; always both on transactions
- **DB access:** Async SQLAlchemy 2.0 only — no sync ORM, no raw SQL except where documented with reason
- **Module boundaries:** `apps/api/src/modules/<name>/` — no cross-module internal imports; cross-module calls through `packages/domain/`
- **Domain types:** All shapes in `packages/shared/schemas.py` (backend) and `packages/shared/types.ts` (frontend) — never inline in routes or components
- **Naming:** `get_X`, `list_X`, `create_X`, `update_X`, `delete_X` — no fetch/load/retrieve
- **Stack:** Python 3.12, FastAPI 0.111+, Next.js 14 App Router, TypeScript, Tailwind CSS, Postgres 16
- **Self-hostability:** Never hard-code a dependency on a paid service; always a BYO-key or open alternative path

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Monorepo (apps + packages) | Single deployable with shared types; no microservices until real bottleneck | — Pending |
| Household model from day 1 | Multi-user built into schema; no migration pain later when adding second person | — Pending |
| `merchant_category` vs `intent_category_id` never merged | Bank data is immutable fact; user intent is separate truth; merging destroys auditability | — Pending |
| Connector abstract interface before any implementation | All reconciliation/rules logic stays provider-agnostic; swap Plaid for SimpleFIN with zero logic changes | — Pending |
| BYO API keys for self-hosted LLM/Plaid/SimpleFIN | No vendor lock-in; self-hosters stay in control; cloud version uses same interface | — Pending |
| Forecast as headline feature (Phase 7) | Everything before it (accounts, transactions, recurring) is infrastructure; forecast is the reason to keep using the app | — Pending |
| Next.js 16.2+ (upgraded from 14) | 14 is 2 majors behind; async params/cookies()/headers() are breaking changes; Node 22 required | ✓ Good |
| SQLAlchemy 2.0 async over SQLModel | FastAPI tutorial recommends SQLModel but it fuses ORM+schema layers, violating CLAUDE.md separation | ✓ Good |
| procrastinate over pg-boss/ARQ | pg-boss is Node-only; procrastinate is Postgres-native, keeps Redis out of docker-compose | ✓ Good |
| Hand-rolled auth over fastapi-users | fastapi-users is user-centric, fights household schema; ~150 lines with PyJWT + pwdlib[argon2] | ✓ Good |
| Postgres RLS in Phase 1 (not Phase 13) | Retrofitting multi-tenancy isolation across 14 tables is expensive; enforce from day one | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-23 after initialization*
