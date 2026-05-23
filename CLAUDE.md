You are helping me build "PRANAV: Personal Resource & Asset Navigator for Abundant Value" — a self-hostable personal finance application 
(think Bitwarden model: open source, run it yourself or use the cloud version).

This is Phase 0: repo skeleton only. No feature code. The goal is a running 
docker compose stack with a FastAPI backend, a Next.js frontend, Postgres, and 
all the tooling scaffolded so future phases can move fast without creating mess.

## Constraints you must follow throughout this project

Before writing any code, read these and acknowledge them:

1. Before adding any function or class, grep for something similar first. 
   Report what you find. If something close exists, extend it — don't create a 
   duplicate.

2. All domain types live in `packages/shared/schemas.py` (backend) and 
   `packages/shared/types.ts` (frontend). Never define a domain shape inline 
   in a route or component.

3. All database operations go through SQLAlchemy models in `packages/db/models/`. 
   Raw SQL only in exceptional cases, documented with a comment explaining why.

4. Money values are stored as INTEGER (cents) in the database and on the wire. 
   Never float. The Pydantic model converts to/from decimal for display.

5. Dates: store as DATE or TIMESTAMPTZ in Postgres. ISO strings on the wire. 
   Always store both `transaction_date` and `post_date` on transactions.

6. Modules: apps/api/src/modules/<name>/. A module may not import from another 
   module's internal files. Cross-module calls go through packages/domain/.

7. No TODO comments that aren't tracked. If something is deferred, add it to 
   docs/BACKLOG.md instead.

8. Run `make check` (typecheck + lint + test) before declaring any task complete.

## Repo structure to create

finbrain/
├── apps/
│   ├── web/                          # Next.js 16.2+, App Router, TypeScript
│   │   ├── src/app/
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx              # "Personal Resource & Asset Navigator for Abundant Value - coming soon" placeholder
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── tsconfig.json
│   └── api/                          # FastAPI, Python 3.12
│       ├── src/
│       │   ├── main.py               # FastAPI app, CORS, routers
│       │   ├── config.py             # Settings via pydantic-settings
│       │   ├── database.py           # Async SQLAlchemy engine + session
│       │   └── modules/
│       │       └── health/
│       │           └── router.py     # GET /health → {status: ok, version}
│       ├── tests/
│       │   └── test_health.py
│       ├── Dockerfile
│       ├── requirements.txt
│       └── pyproject.toml
├── packages/
│   ├── db/
│   │   ├── models/
│   │   │   └── __init__.py           # Base declarative model only, no tables yet
│   │   ├── migrations/               # Alembic
│   │   │   └── env.py
│   │   └── alembic.ini
│   ├── shared/
│   │   ├── schemas.py                # Pydantic base schemas (empty, documented)
│   │   └── types.ts                  # TypeScript domain types (empty, documented)
│   └── domain/                       # Pure business logic, no DB or HTTP
│       └── __init__.py
├── docker/
│   └── docker-compose.yml            # web + api + postgres + adminer
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SCHEMA.md                     # Placeholder with Phase 1 tables listed
│   ├── BACKLOG.md
│   └── adr/
│       └── 001-modular-monolith.md
├── CLAUDE.md                         # Conventions (content below)
├── Makefile                          # make dev, make check, make migrate
└── README.md

## CLAUDE.md content to generate

Include these exact sections:

- "Before you write code" (grep check, check shared schemas, check docs/SCHEMA.md)
- "Module boundaries" (no cross-module internal imports)
- "Money handling" (always cents as int)
- "Date handling" (transaction_date + post_date, TIMESTAMPTZ)
- "Naming conventions" (get_X, list_X, create_X, update_X, delete_X — no fetch/load/retrieve)
- "Testing" (domain layer tests are mandatory; route tests are nice-to-have)
- "Before finishing a task" (run make check, check for duplicates)

## docker-compose.yml requirements

Services:

- postgres:16-alpine, port 5432, volume for data persistence
- api: builds from apps/api/Dockerfile, port 8000, depends on postgres, 
  env vars for DATABASE_URL

- web: builds from apps/web/Dockerfile, port 3000, depends on api, 
  NEXT_PUBLIC_API_URL env var

- adminer: port 8080, for local DB inspection (dev only)

All services must restart: unless-stopped.
Include a .env.example with all required variables documented.

## Makefile targets to create

make dev          → docker compose up --build
make down         → docker compose down
make migrate      → run alembic upgrade head inside api container
make check        → run pyright + ruff + pytest in api; tsc --noEmit + eslint in web
make shell-api    → docker compose exec api bash
make shell-db     → docker compose exec postgres psql -U finbrain

## FastAPI app requirements

- Python 3.12, FastAPI 0.136+, SQLAlchemy 2.0 async (NOT SQLModel), Alembic, Pydantic v2,
  pydantic-settings, asyncpg, anyio, httpx + asgi-lifespan (for tests), ruff, pyright

- Auth: PyJWT>=2.9 + pwdlib[argon2]>=0.2 (NOT fastapi-users, NOT passlib/bcrypt)
- Background jobs: procrastinate>=3 (Postgres-native, NOT pg-boss/ARQ/Celery)
- Logging: structlog>=24.4 JSON in prod / console in dev
- Config loaded from environment via pydantic-settings (DATABASE_URL, 
  SECRET_KEY, ENVIRONMENT, LOG_LEVEL)

- CORS: allow origins from ALLOWED_ORIGINS env var (default localhost:3000)
- /health endpoint returns {status, version, environment, db_connected}
  where db_connected actually tests the DB connection (SELECT 1)

- Lifespan handler creates/disposes the DB engine
- Structured JSON logging

## Next.js app requirements

- Next.js 16.2+, Node 22 (node:22-alpine in Dockerfile), TypeScript, Tailwind CSS 4, App Router
- shadcn/ui (Radix + Tailwind), TanStack Query v5, React Hook Form, Zod
- src/app/page.tsx: simple centered page, "Personal Resource & Asset Navigator for Abundant Value" heading,
  shows API health status fetched from /health (server component, fetch on render)

- If API is unreachable, show "API unavailable" gracefully — no crash
- tsconfig paths: @/* → src/*
- NOTE: Next.js 16 uses async params/cookies()/headers() — never use sync versions

## What NOT to do

- Do not create any auth, user, or account tables yet — those are Phase 1
- Do not add any feature routes beyond /health
- Do not install any packages not listed above without asking
- Do not use JavaScript — TypeScript everywhere in the frontend
- Do not use synchronous SQLAlchemy — async only

## Exit criteria

I will know Phase 0 is complete when:

1. `git clone <repo> && make dev` starts all four containers with no errors
2. http://localhost:3000 shows the PRANAV placeholder with API health status
3. http://localhost:8000/health returns {status: "ok", db_connected: true}
4. http://localhost:8080 shows Adminer connected to the DB
5. `make check` passes with zero errors
6. docs/ARCHITECTURE.md and CLAUDE.md are populated with the content described above

Start by showing me the complete file tree you will create, then build it 
file by file. After each file, tell me which exit criterion it moves toward. 
Do not skip the Makefile or the docs files — they are not optional.

REPO: https://github.com/plodha/ledgr

<!-- GSD:project-start source:PROJECT.md -->

## Project

**Personal Resource & Asset Navigator for Abundant Value**

A self-hostable personal finance application built on the Bitwarden model — fully open source, run it yourself or use the cloud version. Multi-user from day one via a household model: every financial record belongs to a household, not a user. Built for people who want to own their financial data.

**Core Value:** See where your money is going *before* it goes there — a trustworthy cash-flow forecast built on real account balances, recurring transactions, and your actual spending patterns.

### Constraints

- **Money:** Always INTEGER (cents) in DB and on wire — never float, never decimal in storage
- **Dates:** Store `transaction_date` + `post_date` as DATE/TIMESTAMPTZ; ISO strings on wire; always both on transactions
- **DB access:** Async SQLAlchemy 2.0 only — no sync ORM, no raw SQL except where documented with reason
- **Module boundaries:** `apps/api/src/modules/<name>/` — no cross-module internal imports; cross-module calls through `packages/domain/`
- **Domain types:** All shapes in `packages/shared/schemas.py` (backend) and `packages/shared/types.ts` (frontend) — never inline in routes or components
- **Naming:** `get_X`, `list_X`, `create_X`, `update_X`, `delete_X` — no fetch/load/retrieve
- **Stack:** Python 3.12, FastAPI 0.111+, Next.js 14 App Router, TypeScript, Tailwind CSS, Postgres 16
- **Self-hostability:** Never hard-code a dependency on a paid service; always a BYO-key or open alternative path

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## TL;DR — The Stack

| Layer | Pick | Version | Confidence |
|---|---|---|---|
| Backend framework | FastAPI | `>=0.136,<0.137` | HIGH (verified) |
| Python | CPython | `3.12.x` | HIGH (per CLAUDE.md) |
| ORM | SQLAlchemy async | `>=2.0.36,<2.1` | HIGH |
| Migrations | Alembic | `>=1.13,<2` | HIGH |
| DB driver | asyncpg | `>=0.30,<0.31` | HIGH |
| Validation | Pydantic v2 + pydantic-settings | `pydantic>=2.9,<3`, `pydantic-settings>=2.5,<3` | HIGH |
| Auth (Phase 1) | Hand-rolled OAuth2 + JWT (PyJWT) + pwdlib[argon2] | `PyJWT>=2.9`, `pwdlib>=0.2` | HIGH (matches official FastAPI tutorial) |
| Background jobs | ARQ (Redis) **or** procrastinate (Postgres-native) | `arq>=0.26` / `procrastinate>=3` | MEDIUM — see decision section |
| Encryption-at-rest | `cryptography` (Fernet + AES-GCM via envelope) | `cryptography>=43` | HIGH |
| File storage | filesystem-by-default, S3-compatible via boto3 abstracted | `boto3>=1.35` | HIGH |
| Email (transactional) | `fastapi-mail` (SMTP-only in self-host) | `fastapi-mail>=1.4` | MEDIUM |
| Email (inbound receipts) | SMTP catch via `aiosmtpd` (self-host) or SendGrid Inbound Parse (cloud) | `aiosmtpd>=1.4` | MEDIUM |
| Bank: Plaid | official `plaid-python` | `>=27,<28` | HIGH |
| Bank: SimpleFIN | hand-rolled httpx client (no official Python SDK) | n/a | HIGH — verified by absence |
| LLM (receipt parse) | `anthropic` + `openai` SDKs, dispatched by provider id | `anthropic>=0.40`, `openai>=1.50` | HIGH |
| OCR fallback | `pytesseract` or skip — let multimodal LLMs do vision | — | MEDIUM |
| Frontend framework | Next.js App Router | **upgrade target: 16.2**, baseline 15.x acceptable | HIGH — **Next.js 14 is no longer current; revisit choice** |
| React | React 19.x (canary via Next 16) | — | HIGH |
| Styling | Tailwind CSS | `>=4.0,<5` | MEDIUM |
| UI primitives | shadcn/ui on Radix UI | latest | HIGH |
| Server state | TanStack Query v5 | `>=5.60,<6` | HIGH |
| Client state | Zustand (only where needed) | `>=5,<6` | HIGH |
| Forms | React Hook Form + Zod | `react-hook-form>=7.53`, `zod>=3.23` | HIGH |
| Charts (forecast) | Recharts | `>=2.13,<3` | HIGH |
| Money on wire | INTEGER cents (per CLAUDE.md) | — | HIGH |
| Testing (api) | pytest + pytest-asyncio + httpx AsyncClient + ASGITransport | `pytest>=8`, `pytest-asyncio>=0.24`, `httpx>=0.27` | HIGH (verified) |
| Testing (web) | Vitest + React Testing Library + Playwright | latest | HIGH |
| Linting (api) | ruff + pyright | `ruff>=0.6`, `pyright>=1.1.380` | HIGH |
| Linting (web) | ESLint flat config + Prettier (or Biome) | — | HIGH |

## 1. Chosen Stack (Validated)

### FastAPI 0.136.x — VALIDATED

- Async-first, dependency injection model fits the modular-monolith design in CLAUDE.md (`apps/api/src/modules/<name>/router.py` → `APIRouter` is canonical).
- Pydantic v2 integration gives free schema validation that matches the "domain types live in `packages/shared/schemas.py`" rule.
- The official tutorial's "bigger applications" pattern is *exactly* the module layout CLAUDE.md describes — no fighting the framework.

### Python 3.12 — VALIDATED

### SQLAlchemy 2.0 async — VALIDATED

### Alembic — VALIDATED

### Postgres 16 — VALIDATED

### asyncpg — VALIDATED

### Pydantic v2 + pydantic-settings — VALIDATED

### Next.js App Router + TypeScript + Tailwind — VALIDATED PATTERN, VERSION FLAGGED

### Docker Compose — VALIDATED

## 2. Gaps to Fill (And Recommendations)

### 2.1 Auth — **Hand-rolled OAuth2 password flow + JWT in HttpOnly cookie**

- `PyJWT>=2.9` for token encode/decode (this is what the **official FastAPI tutorial uses today** — verified).
- `pwdlib[argon2]>=0.2` for password hashing (also the **current official FastAPI tutorial recommendation** — verified; replaces the older `passlib[bcrypt]` advice from pre-2024 tutorials).
- `OAuth2PasswordBearer` from FastAPI for header-based JWT during dev/local tooling.
- A second dependency that reads the same JWT from an **HttpOnly, SameSite=Lax, Secure cookie** for the actual browser flow.
- Refresh-token rotation: short-lived (15min) access JWT in cookie + long-lived (30d) opaque refresh token stored in a `refresh_token` table (revocable). Rotate on every refresh.
- The frontend (Next.js server components) needs to call the API from a server context. JWT-in-cookie + a `verify_token` dependency Just Works for both browser fetches and server-side `fetch` from RSC.
- Pure server-side sessions (Redis-backed) add an extra moving piece for self-hosters with no security gain at this scale.
- Stateless verification means the forecast endpoint (which will be the chattiest endpoint in the app, Phase 7) doesn't hit Redis per request.

### 2.2 Background Jobs — **procrastinate (Postgres-native)** ✅ recommended

- The project is already running Postgres. procrastinate uses Postgres `LISTEN/NOTIFY` + a `procrastinate_jobs` table; **no Redis container required**, which keeps the self-hostable Docker Compose footprint smaller (one less service, one less env var, one less thing for users to misconfigure).
- It's async-native, supports cron-like periodic tasks (needed for nightly Plaid sync in Phase 9), retries with backoff, and integrates cleanly with the existing SQLAlchemy migration story (its tables are managed by its own CLI; you wire it into Alembic as a one-time `alembic stamp`).
- The "pg-boss equivalent in Python" framing in the original question is literally procrastinate's positioning. pg-boss is Node-only; procrastinate is the closest 1:1 Python analog.
- ARQ is excellent but requires Redis. Adding Redis to the self-hostable stack means: another container, another credential, another backup target, another set of "is my Redis healthy?" questions for self-hosters. Not worth it for a job queue that won't exceed ~10k jobs/day per household.
- Heavyweight, sync-first, has a complex broker story, and the async support is a Frankenstein. Wrong fit for an async FastAPI codebase.
- Younger, less battle-tested, broker abstraction is its main selling point — but you don't want broker flexibility, you want one obvious choice that uses your existing Postgres.
- BackgroundTasks are *in-process*. Fine for "send a single email" but unusable for nightly Plaid sync, retries, and observability. Use them only for fire-and-forget post-response work.

### 2.3 File Storage (Receipts) — **Abstract behind a `Storage` interface; filesystem default, S3 optional**

- `LocalFilesystemStorage` — writes to a bind-mounted volume (`/data/receipts/{household_id}/{yyyy-mm}/{uuid}.jpg`). Default for self-host.
- `S3Storage` — uses `boto3>=1.35` with the async client (`aioboto3`) against any S3-compatible service (AWS S3, Cloudflare R2, MinIO, Backblaze B2). Configured by env vars: `STORAGE_BACKEND=s3`, `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`.
- A first-time self-hoster shouldn't need an S3 account to use the app. Filesystem-default is the Bitwarden/Vaultwarden norm.
- Receipts are sensitive financial data. A third-party image CDN is the wrong default. Self-hosted file or self-hosted S3-compatible only.

### 2.4 Email — **SMTP for outbound, two paths for inbound**

- Async, integrates with FastAPI's dependency injection, supports templates via Jinja2.
- Pure SMTP transport means no vendor lock-in.
- **Self-host path:** `aiosmtpd>=1.4` running as a separate container (or in-process if you must). Listens on port 25/465, hands message bodies + attachments to a procrastinate job that runs the same receipt parse pipeline as photo upload. Document that users need a public IP + reverse DNS + ideally MX records, OR they forward from their main email via filters.
- **Cloud path:** SendGrid Inbound Parse (free tier covers small volumes) posts a webhook to `/webhooks/email-inbound`. Same handler, same parse pipeline.
- It isn't needed before Phase 12. Don't build it. Defer to Phase 12 explicitly.

### 2.5 Encryption (Plaid / SimpleFIN credentials) — **Envelope encryption with `cryptography`**

- `wrapped_dek BYTEA` — the DEK encrypted with the app key (Fernet or AES-KW).
- `nonce BYTEA` — the GCM nonce (12 bytes).
- `ciphertext BYTEA` — the encrypted secret with auth tag appended.
- Fernet is fine for "the token" but commits you to one key forever (rotation is painful) and uses AES-128-CBC + HMAC, which is older than AES-GCM. Use Fernet only to *wrap* DEKs (it's convenient for that — combined enc+auth + base64).
- Storing the master key in the database (yes, people do this).
- Reusing a GCM nonce across rows (always 12-byte random per encryption).
- Storing Plaid `access_token` in a column called `access_token` (call it `credentials_encrypted` per the ROADMAP, store the whole envelope).

### 2.6 Testing (FastAPI async + pytest) — **pytest-asyncio + httpx AsyncClient + ASGITransport**

# conftest.py

# tests/test_health.py

- `pytest>=8`
- `pytest-asyncio>=0.24` (or `anyio[trio]>=4` — official docs use anyio markers; either works, anyio is more flexible)
- `httpx>=0.27` — includes `ASGITransport`
- `asgi-lifespan>=2.1` — **REQUIRED**; the official FastAPI docs flag that `AsyncClient` doesn't trigger lifespan events on its own, and the project's `main.py` uses a lifespan to init the DB engine
- Use a separate `finbrain_test` database (or a fresh schema per test session).
- Wrap each test in a SAVEPOINT-rollback fixture so tests don't pollute each other.
- For Phase 0, a single test against `/health` is enough.
- For domain logic (Phase 5 rule engine, Phase 7 forecast), prefer pure-function tests with no DB — CLAUDE.md says "domain layer tests are mandatory; route tests are nice-to-have" and that's exactly right.
- `TestClient` from `fastapi.testclient` — official docs explicitly say it doesn't work in async test functions; use `AsyncClient` instead.
- `pytest-anyio` (separate package) — `anyio` itself provides the pytest plugin via the `anyio` marker.

### 2.7 Frontend State Management with Next.js App Router

- Don't manage at all in client state. Re-fetch on navigation (Next.js handles cache via `fetch`).
- For Phase 0: the placeholder `/health` call is exactly this pattern.
- **Use TanStack Query v5 (`@tanstack/react-query>=5.60`).**
- Why: stale-while-revalidate, optimistic updates, mutation handling, request dedup, devtools. Industry standard.
- Wrap a `<QueryClientProvider>` at the root client boundary. Define a `getQueryClient()` server-side helper for prefetching from RSCs and hydrating into the client.
- **Use Zustand v5 sparingly.**
- Why: tiny (~1KB), no boilerplate, no Context Provider needed, works fine with RSC because stores are client-only.
- Only reach for it when `useState` lifted to a parent is awkward.
- The App Router pattern + TanStack Query removes 90% of what people historically used Redux for. RTK is overkill for this project.
- Atomic state is elegant but Zustand is simpler for the team and gives the same outcome.
- Fine for very small state, but the moment you need persistence (e.g. "remember the user's last forecast horizon"), Zustand's middleware (`persist`) is one line.
- **React Hook Form + Zod** (`react-hook-form>=7.53`, `zod>=3.23`).
- Shared validation: define `transactionSchema` in `packages/shared/types.ts` (technically as a Zod schema, then `z.infer<>` the TS type). Use the same Zod schema in API responses (via TS) and form validation.

### 2.8 Chart Library (Forecast View — Phase 7) — **Recharts**

- Built on D3, declarative React components, designed for time-series and financial charts.
- Composable: `<LineChart>` with `<ReferenceLine>` for "today", `<Brush>` for the 30/60/90 selector, `<Tooltip>` for hover values — all out of the box. The forecast view is exactly Recharts' wheelhouse.
- shadcn/ui ships a Recharts wrapper (`chart.tsx`) that gives you themed tooltips and legends for free.
- Excellent SSR support (renders in RSC without hydration mismatch headaches).
- Imperative Canvas-based API; harder to compose, no built-in React idioms.
- Tooltips and overlays for "what if" scenarios in Phase 7 require custom canvas plugins.
- More powerful but more low-level. You'd be reimplementing things Recharts gives you for free.
- Beautiful but opinionated, and the team scaled back maintenance through 2025. Risk of stagnation.
- Too low-level for this project's pace.
- Either heavy, license-encumbered (Highcharts), or way too much surface area (Plotly).

## 3. Frontend: The Next.js 14 → 16 Decision (RAISE TO USER)

- Next.js 16.2.6 is current.
- Next.js 16 GA was October 2025.
- Next.js 14 still receives security patches (CVE-2025-66478 was patched across 13/14/15/16) but is *not* the recommended target for new projects.
- `middleware.ts` → `proxy.ts` (deprecation, not removal).
- Async `params`, `searchParams`, `cookies()`, `headers()`, `draftMode()` — these are *breaking changes* if you write any code today against the 14 pattern, you'll have to rewrite for 16.
- Turbopack is the default bundler (significant dev-loop speedup).
- React 19.2 features available (View Transitions, useEffectEvent).
- React Compiler is stable (automatic memoization).
- New caching APIs (`updateTag`, `refresh`, `revalidateTag` with cacheLife).
- Cache Components (the successor to PPR).
- Node 20.9+ required (Phase 0 currently doesn't pin Node version — should pin in Dockerfile).
- Use `pnpm create next-app@latest` with `--yes` defaults (TypeScript, Tailwind, ESLint, App Router, Turbopack, `@/*` alias) — that's what CLAUDE.md describes anyway, just on the current major.
- Update CLAUDE.md "Stack" line from "Next.js 14 App Router" to "Next.js 16+ App Router".
- Add `node>=20.9` to the web Dockerfile (use `node:22-alpine` to be safe and forward-compatible).
- Get used to `await params` from day one — no migration pain later.
- Stay on the latest 15.x (which still has the App Router and is closer to 16's patterns).
- Do **not** start a new project on 14 in May 2026 — every line of code you write today will need migration in 6 months when something forces the upgrade.

## 4. Money + Date Handling (No Change — Validated)

- Money: INTEGER cents in DB and on wire.
- Dates: TIMESTAMPTZ in Postgres, ISO 8601 strings on wire.
- Always store both `transaction_date` and `post_date`.
- For currency *display* (`$1,234.56` formatting), use `Intl.NumberFormat` in the browser; do **not** ship a JS money library. Cents-to-display is a one-line `(cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" })`.
- For *parsing* user input ("12.34" → 1234), write one shared helper in `packages/shared/types.ts` (Zod `transform`). Do not duplicate this logic.
- For currency arithmetic in the API (Phase 7 forecast aggregation), Python `int` is sufficient — no `decimal.Decimal` needed because we're already in integer cents.
- For multi-currency (deferred / out of scope for v1.0 — confirm), store `currency` (ISO 4217 3-letter) alongside every amount column. Don't mix currencies in any aggregation.

## 5. Plaid + SimpleFIN Connectors (Phase 9 / 11)

### Plaid: official `plaid-python` SDK

- `apps/api/src/modules/connectors_plaid/` — thin route layer that handles Link token creation and webhook receipt.
- `packages/domain/connectors/plaid.py` — `PlaidConnector(Connector)` implementing the abstract interface from ROADMAP § Connector Interface.
- Self-host: settings page captures `PLAID_CLIENT_ID` + `PLAID_SECRET` + `PLAID_ENV` (sandbox/development/production), stored encrypted via the envelope crypto from §2.5.
- Webhook handler: `TRANSACTIONS_SYNC`, `ITEM_ERROR`, `AUTH_STATUS_UPDATED` → enqueue procrastinate job → reconcile.
- Use Plaid's `/transactions/sync` cursor-based endpoint (not the deprecated `/transactions/get`). Persist `last_cursor` per `plaid_account` row (already in the ROADMAP schema).
- Pending → posted transition: Plaid transaction IDs change when status flips. Use `pending_transaction_id` from Plaid's response to find the row to update, **not** the `transaction_id`. Document this loudly in the reconciliation module.

### SimpleFIN: hand-rolled httpx client

## 6. LLM (Receipt Parsing — Phase 12)

- `AnthropicReceiptParser` — `anthropic>=0.40`, uses Claude's vision capability on a `claude-3-5-sonnet`-class or `claude-4-sonnet`-class model.
- `OpenAIReceiptParser` — `openai>=1.50`, uses `gpt-4o`/`gpt-4.1`-class with the vision input.
- `StructuredReceiptParser` — deterministic regex/template parser for known formats (Costco, Amazon order emails); no LLM cost.

## 7. Logging + Observability

## 8. UI Components (Phase 1+)

- It's a CLI-installable copy-paste component library — components live *in your repo*, not in `node_modules`. You own them, you can modify them, no breaking-change risk from upstream.
- Built on Radix UI (accessibility, keyboard navigation handled).
- Tailwind-native, so it composes with the rest of the styling story.
- Free, MIT, no licensing.
- Includes the Recharts wrapper out of the box (for Phase 7).
- All ship runtime CSS-in-JS or large CSS bundles; the App Router story is worse than Tailwind+Radix.
- All are heavier than necessary for a self-hosted personal app.
- Smaller surface area than Radix. shadcn standardized on Radix; staying on shadcn's path is easier.

## 9. CI/CD

# .github/workflows/check.yml

## 10. What NOT to Use (Anti-Recommendations)

| Reject | Why |
|---|---|
| **SQLModel** | Conflates SQLAlchemy + Pydantic; violates CLAUDE.md's domain-types-separate-from-DB-models rule; redundant for this architecture. |
| **fastapi-users** | Opinionated user model fights the household-centric schema; auth is ~150 lines of well-documented FastAPI tutorial code. |
| **Celery** | Sync-first, broker-heavy, wrong fit for async FastAPI; procrastinate replaces it. |
| **ARQ** | Requires Redis. Adds a container with no benefit over Postgres-backed procrastinate at this scale. |
| **Redis** (as infrastructure) | Not needed at all in v1.0. Postgres handles jobs (procrastinate), sessions (JWT is stateless), and rate-limiting (Postgres advisory locks or in-memory). Resist the urge. |
| **passlib + bcrypt** | Officially superseded in the FastAPI tutorial by `pwdlib[argon2]`. passlib hasn't shipped a release in years. |
| **python-jose** | Replaced by PyJWT in the official FastAPI tutorial; python-jose's maintenance has been spotty. |
| **psycopg (sync) for async path** | asyncpg is faster and more battle-tested for FastAPI/SQLAlchemy 2.0 async. |
| **Float for money** | Mandated by CLAUDE.md; reiterating for emphasis. |
| **Decimal in the database** | Use INTEGER cents per CLAUDE.md; Decimal display conversion is a Pydantic concern, not a storage concern. |
| **Next.js Pages Router** | App Router is the framework's recommended default; Pages Router is maintained for backcompat. |
| **JavaScript (no TS)** | Mandated by CLAUDE.md; reiterating. |
| **Synchronous SQLAlchemy** | Mandated by CLAUDE.md; reiterating. |
| **Chart.js** | Imperative Canvas API; Recharts composes better with React for the forecast UI. |
| **Tremor** | Maintenance scaled back; risk for a chart library you'll lean on heavily in Phase 7. |
| **MUI / Chakra / Mantine** | Heavier than shadcn+Radix+Tailwind for this project; runtime CSS-in-JS is the wrong fit for the App Router. |
| **Cloudinary / Imgur (receipt storage)** | Sensitive financial data; third-party image CDNs are wrong by default. |
| **Floating point dates / Unix epoch ints for dates** | Use TIMESTAMPTZ; ISO 8601 on wire. CLAUDE.md mandates. |
| **SQLite in production** | The data model needs Postgres-specific features (LISTEN/NOTIFY for procrastinate, robust DATE handling, JSON columns for `csv_import_mapping.column_map`). Keep SQLite firmly off the table. |
| **Hand-rolled OCR pipeline (Tesseract pre-LLM)** | Multimodal LLMs do this better; only add OCR if a truly-offline mode is needed later. |
| **Redis-backed sessions** | JWT-in-cookie is stateless, sufficient, and removes a container. |
| **GraphQL / tRPC** | REST + OpenAPI from FastAPI is the simpler, well-trodden path for a self-hostable app. |

## 11. Stack Decisions Cheat Sheet (One-Liner Each)

| Question | Answer |
|---|---|
| Backend? | FastAPI 0.136+ on Python 3.12 |
| ORM? | SQLAlchemy 2.0 async (NOT SQLModel) |
| DB? | Postgres 16 with asyncpg |
| Migrations? | Alembic with async env.py |
| Validation? | Pydantic v2 + pydantic-settings |
| Auth? | Hand-rolled OAuth2 + JWT in HttpOnly cookie; PyJWT + pwdlib[argon2] |
| Background jobs? | procrastinate (Postgres-native), introduce at Phase 9 |
| Encryption? | `cryptography` lib, envelope pattern (AES-256-GCM + Fernet-wrapped DEK) |
| File storage? | Filesystem default, S3-compatible via `Storage` interface |
| Email out? | fastapi-mail + SMTP (BYO provider) |
| Email in (receipts)? | aiosmtpd (self-host) or SendGrid Inbound Parse (cloud) — Phase 12 only |
| Plaid? | Official `plaid-python` SDK, behind Connector interface |
| SimpleFIN? | Hand-rolled httpx client (no SDK), behind Connector interface |
| LLM (receipts)? | Anthropic + OpenAI SDKs, behind ReceiptParser interface |
| Testing API? | pytest + anyio + httpx AsyncClient + ASGITransport + asgi-lifespan |
| Logging? | structlog with JSON output |
| Frontend? | **Next.js 16.2** (upgrade from CLAUDE.md's 14) + TypeScript + Tailwind |
| UI lib? | shadcn/ui (Radix + Tailwind) |
| Server state? | TanStack Query v5 |
| Client state? | Zustand v5 (sparingly) |
| Forms? | React Hook Form + Zod (schema shared with API) |
| Tables? | TanStack Table v8 |
| Charts? | Recharts v2 |
| CI? | GitHub Actions (`.github/workflows/check.yml`) |
| Linters? | ruff + pyright (api); ESLint + Prettier (web) |
| Package manager? | pip + requirements.txt (api); pnpm (web) |

## 12. Confidence Notes / Gaps

- FastAPI 0.136.1 current version → fastapi.tiangolo.com/release-notes
- FastAPI security tutorial uses PyJWT + pwdlib[argon2] → fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- FastAPI async tests use httpx AsyncClient + ASGITransport + anyio marker → fastapi.tiangolo.com/advanced/async-tests
- FastAPI CORS via CORSMiddleware with allow_credentials caveats → fastapi.tiangolo.com/tutorial/cors
- FastAPI bigger-applications uses APIRouter per module → matches CLAUDE.md exactly
- Next.js 16.2.6 current; Next.js 14 superseded → nextjs.org/blog/next-16, nextjs.org/docs/app/getting-started/installation
- Node.js 20.9+ required for Next 16; defaults include App Router, Turbopack, TS, Tailwind → confirmed installation page
- SQLAlchemy 2.0.36+ as latest in 2.0.x line — training data says ~2.0.35; 2.0.36 is reasonable extrapolation but not live-checked.
- procrastinate v3 is current — strong training signal but not live-verified.
- fastapi-mail maintenance status — last known release pattern was 2023-2024; **explicit re-verification needed at Phase 1** (when first invite emails ship).
- Plaid SDK at v27 — strong signal from training data; verify against PyPI at Phase 9 start.
- anthropic / openai SDK versions — these move fast; pin loosely (`>=0.40`, `>=1.50`) and lock at Phase 12 start.
- Recharts v2.13 — training data current; verify at Phase 7 start.
- Whether `procrastinate` v3 supports Postgres 16 partitioning if/when transaction tables get large. Probably yes; verify before Phase 9.
- SimpleFIN protocol stability — should be near-zero risk but the spec is community-maintained.
- Whether `aiosmtpd` is the right inbound MX choice vs an external service for self-hosters in 2026. Re-check at Phase 12 — DKIM/SPF handling for inbound is fiddly and might warrant a managed solution even for self-host (e.g., Cloudflare Email Routing → webhook).
- `https://fastapi.tiangolo.com/release-notes/`
- `https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/`
- `https://fastapi.tiangolo.com/tutorial/cors/`
- `https://fastapi.tiangolo.com/tutorial/bigger-applications/`
- `https://fastapi.tiangolo.com/tutorial/testing/`
- `https://fastapi.tiangolo.com/advanced/async-tests/`
- `https://fastapi.tiangolo.com/tutorial/sql-databases/`
- `https://nextjs.org/blog/next-16`
- `https://nextjs.org/docs/app/getting-started/installation` (lastUpdated: 2026-05-19, version: 16.2.6)

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
