# Research Summary — PRANAV Personal Finance App

**Project:** PRANAV (Personal Resource & Asset Navigator for Abundant Value) / ledgr
**Synthesized:** 2026-05-23
**Overall confidence:** HIGH on architecture and stack; MEDIUM on feature/competitive claims.

---

## Stack (Validated + Key Changes)

- **VALIDATED — Backend:** FastAPI 0.136+ on Python 3.12, SQLAlchemy 2.0 async (`AsyncEngine` + `async_sessionmaker`, `expire_on_commit=False`), Alembic with async `env.py`, asyncpg driver, Pydantic v2 + pydantic-settings, Postgres 16. **Do NOT adopt SQLModel** — it fuses ORM and schema layers, violating CLAUDE.md's "domain types in `packages/shared/schemas.py`, DB models in `packages/db/models/`" separation.
- **CHANGE — Frontend:** **Upgrade CLAUDE.md from "Next.js 14" to "Next.js 16.2+"** before any frontend code is written. Verified live: Next.js 16.2.6 is current (2026-05-19). Async `params`, `cookies()`, `headers()` are breaking changes from 14. Pin Node 22 in Dockerfile. Stack: Next 16.2 + TypeScript + Tailwind 4 + shadcn/ui + TanStack Query v5 + Zustand v5 + React Hook Form + Zod + Recharts 2 + TanStack Table v8.
- **CHANGE — Background jobs:** **Replace "pg-boss" in ROADMAP Phase 9 with `procrastinate>=3`** (pg-boss is Node-only; procrastinate is Postgres-native via `LISTEN/NOTIFY`). Keeps Redis out of docker-compose entirely. Introduce at Phase 4 (CSV imports are first consumer), not Phase 9.
- **DECIDED — Auth:** Hand-rolled OAuth2 + JWT in HttpOnly SameSite=Lax cookies, using `PyJWT>=2.9` + `pwdlib[argon2]>=0.2` (current official FastAPI tutorial). Skip `fastapi-users` — its user-centric model fights the household schema. Hand-roll is ~150 lines.
- **DECIDED — Crypto/storage/LLM:** `cryptography>=43` envelope encryption (Fernet-wrapped DEK + AES-256-GCM per row, `encryption_key_version` column). `ObjectStorage` interface with `LocalFSStorage` default / `S3Storage` for cloud. `anthropic` + `openai` SDKs behind `ReceiptParser` interface; skip Tesseract.
- **Testing:** pytest + anyio + `httpx.AsyncClient` with `ASGITransport` + `asgi-lifespan`. Do NOT use `TestClient` in async tests.
- **Logging:** `structlog>=24.4` JSON in prod / console in dev; bind `request_id`, `household_id`, `user_id` via contextvars middleware.

---

## Table Stakes Features

**Already covered by ROADMAP:** account aggregation, manual transactions, CSV import, category hierarchy, auto-categorization rules, recurring transactions, bill reminders, account archive, pending vs posted, multi-user household, notes.

**Missing — must close before v1.0:**

| Gap | Priority | Where to add |
|---|---|---|
| Budget view (allocated $/month per category vs actual) | HIGH | New Phase 6.5 or extend Phase 6 |
| Net-worth history chart | HIGH | Extend Phase 2 — `account_balance_snapshot` + nightly job |
| Reports phase (spending by category, YoY, monthly) | HIGH | New phase or expand Phase 3 |
| Password reset / forgot password | HIGH | Phase 1 |
| 2FA / TOTP | HIGH | Phase 1 or v1.0 hardening |
| Data export (CSV/JSON dump) | MEDIUM-HIGH | Phase 1 or 3 |
| Backup/restore (`make backup` + docs) | MEDIUM-HIGH | Phase 0 stub |
| Onboarding wizard | MEDIUM | Pre-v1.0; biggest weakness of Firefly III / Actual |
| Transfers between own accounts | MEDIUM | Phase 3 extension |
| Tags (tax-deductible, reimbursable) | MEDIUM | Phase 3 |

**Anti-features (do not build):** AI chatbot, stock recommendations, credit score, ad-supported tier, bill negotiation, crypto, tax filing, child accounts.

---

## Architecture Decisions

- **Modular monolith with hexagonal layering.** Modules in `apps/api/src/modules/<name>/` each with `router.py` (HTTP), `service.py` (orchestration), `deps.py` (FastAPI deps). No cross-module internal imports. Cross-module logic in `packages/domain/` (pure functions, no DB/HTTP/I/O). Enforce with import-linter CI rule.
- **Session:** One session per request via `Depends(get_session)`. `expire_on_commit=False`. `lazy="raise"` + explicit `selectinload()`/`joinedload()`. Repository functions accept session, never create one.
- **Multi-tenancy: 5-layer defense.** (1) `household_id NOT NULL` on every domain table. (2) Repository functions take `household_id` as required arg. (3) Services load household from session context, never request body. (4) Single `get_current_context` FastAPI dependency at parent router. (5) **Postgres Row-Level Security — Phase 1, not Phase 13.**
- **Background jobs from Phase 4.** procrastinate, Postgres-backed. New `apps/worker/` container. Every job idempotent on deterministic key.
- **Connector pattern (Phase 9+).** Abstract `Connector` ABC returns `RawTransaction` + `RawBalance` frozen-dataclass DTOs. Connectors never write to `transaction` table — `packages/domain/reconciliation/` owns the merge. HTTP client injected.
- **Forecast (Phase 7).** Ship uncached. Show p25/p75 bands, exponential decay, staleness caveat if `last_synced_at > 3 days`.
- **Encryption (Phase 9+).** Envelope: app key wraps per-row DEK; DEK encrypts with AES-256-GCM. Three columns per secret: `wrapped_dek`, `nonce`, `ciphertext`. `encryption_key_version` for rotation.

**Architectural prerequisites by phase:**
- Phase 0: structured logging + redaction, `make backup` stub, MIGRATIONS.md / UPGRADE.md skeletons
- Phase 1: `CurrentContext` + `get_current_context` + `household_id` mixin + **Postgres RLS**
- Phase 3: `packages/domain/money` + `dates` helpers, `list_transactions_for_totals()`, initial indexes
- Phase 4: procrastinate + `apps/worker/` container, `reconciliation/dedupe` domain module
- Phase 9: `Connector` ABC + DTOs, credential encryption with key versioning
- Phase 12: `ObjectStorage`, `ReceiptParser` interface, BYO-key LLM with cost preview

---

## Top Pitfalls to Avoid

1. **(P3+) Money as float anywhere.** INTEGER cents in DB and on wire. Pydantic validator rejects non-integer. Property test: `sum(transactions.amount_cents) == category_total_cents`.
2. **(P1+) Missing `household_id` on a query.** Enable Postgres RLS in Phase 1. CI lint flags missing scopes. Two-household pytest fixture asserts 404 (not 403) on every list/get.
3. **(P3) `transaction_date` as TIMESTAMPTZ.** Timezone drift turns April 1 Eastern into April 2 Pacific. Use `DATE` for `transaction_date` and `post_date`. `TIMESTAMPTZ` only for `created_at`/`synced_at`.
4. **(P3) `merchant_category` and `intent_category_id` merged.** Lock with ADR. `merchant_category` + `mcc` immutable post-insert via domain guard. Without this you lose bank truth and can't retrain rules.
5. **(P3+) Bank/provider IDs as primary keys.** Plaid changes `transaction_id` on pending→posted. Your UUID is always PK. `external_id` columns nullable, indexed, unique-per-provider.
6. **(P3, P7) Pending transactions summed into totals.** Only `list_transactions_for_totals()` in `packages/domain/transactions/totals.py` may aggregate — enforces `status='posted'` filter.
7. **(P4) CSV date format guessing.** Force user to pick format from dropdown; preview parsed date with day-of-week; remember per institution.
8. **(P6) Hand-rolled recurring-date math.** Use `python-dateutil`'s `rrule` (RFC 5545). Store cadence as rrule fields, not bare enum. Test 24-month generation against month-end, leap year, DST.
9. **(P9) Plaid `ITEM_LOGIN_REQUIRED` swallowed silently.** `connector.status` enum; dashboard banner; forecast staleness caveat.
10. **(P9) Webhook idempotency.** Dedup on `(item_id, webhook_code, provider_webhook_id)`. Row-level advisory lock per connector during sync.
11. **(P12) LLM receipt parsing without guardrails.** Hard per-household rate limit. Cost preview before parsing. Structured-output mode only. Sum-of-line-items must equal receipt total ±$0.05. Human confirmation mandatory.

---

## Roadmap Gaps (Pre-v1.0)

Current v1.0 ship point is after Phase 8. Missing table-stakes:

| # | Gap | Recommended placement |
|---|---|---|
| 1 | Budget view | New Phase 6.5 or extend Phase 6 |
| 2 | Net-worth history chart | Extend Phase 2 |
| 3 | Reports | New phase after Phase 7 |
| 4 | Password reset | Phase 1 checklist |
| 5 | 2FA / TOTP | Phase 1 |
| 6 | Data export | Phase 1 or 3 |
| 7 | Backup/restore | Phase 0 stub |
| 8 | Onboarding wizard | Pre-v1.0 |
| 9 | Transfers between own accounts | Phase 3 extension |
| 10 | Tags | Phase 3 |

---

## Key Open Questions

Decisions needed before Phase 0 or Phase 1:

1. **Confirm Next.js 16.2 upgrade** in CLAUDE.md before any frontend code. Strongest single recommendation. **→ Upgrade.**
2. **Confirm procrastinate over ARQ/pg-boss.** Keeps Redis out forever. **→ procrastinate.**
3. **Confirm hand-rolled auth over fastapi-users.** ~150 lines now vs. ongoing friction. **→ Hand-roll.**
4. **Confirm SQLAlchemy 2.0 async over SQLModel.** Official FastAPI tutorial recommends SQLModel; CLAUDE.md's separation requires raw SQLAlchemy. Document in ADR. **→ Keep SQLAlchemy.**
5. **Confirm Phase 1 enables Postgres RLS** (not Phase 13). Retrofitting with 14 tables is expensive. **→ Phase 1.**
6. **Confirm session strategy:** JWT-in-HttpOnly-cookie with refresh-token rotation. **→ ADR-001.**
7. **Confirm v1.0 scope:** extend by ~2 weeks to absorb budget/reports/password-reset/2FA/export, OR commit to v1.1 fast-follow. **→ Extend scope.**
8. **Multi-currency for v1.0:** US-only / single-currency-per-household recommended. Decide explicitly.
9. **Receipt deletion policy:** allow user to delete original image while keeping line items? **→ Yes, explicit user action.**
10. **Phase 12 email-intake:** `aiosmtpd` local SMTP catch vs. IMAP polling. IMAP polling dramatically simpler. Defer to Phase 12.

---

## Re-verification Triggers

- **Phase 0 close:** procrastinate v3 current, fastapi-mail maintenance, FastAPI minor pin
- **Phase 1 start:** PyJWT + pwdlib[argon2] still official FastAPI tutorial choice
- **Phase 4 start:** ADR-002 with current SQLAlchemy 2.0 + procrastinate compatibility
- **Phase 9 start:** Plaid SDK, Transactions Sync cursor, current error taxonomy, webhook formats
- **Phase 11 start:** SimpleFIN protocol stability
- **Phase 12 start:** Anthropic + OpenAI SDK versions, structured-output API shape

---

## Sources

**Live-verified (2026-05-23):** fastapi.tiangolo.com (FastAPI 0.136.1), nextjs.org/blog/next-16 (Next.js 16.2.6)

**Training-data (re-verify at consuming phase):** SQLAlchemy 2.0 async, procrastinate/ARQ, Plaid SDK v27, SimpleFIN protocol, competitor feature surfaces (Monarch/Copilot/Firefly/Actual through Jan 2026)
