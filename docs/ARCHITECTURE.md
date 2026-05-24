# PRANAV — Architecture

> **Phase 0 architecture reference.** This document describes the running shape
> of the repo at the end of Phase 0. Future phases extend it; the conventions
> declared here are load-bearing for everything that comes after.

## 1. Overview

PRANAV ("Personal Resource & Asset Navigator for Abundant Value") is a
self-hostable personal finance application following the Bitwarden model: open
source, run it yourself or use the cloud version. Phase 0 ships the repo
skeleton — there is no feature code, only the substrate on which Phases 1-11
will build.

The Phase 0 deployable surface is a **4-container Docker Compose stack**:

| Container | Image | Port | Role |
|-----------|-------|------|------|
| `postgres` | `postgres:16-alpine` | 5432 | Source of truth: transactions, accounts, RLS-scoped tenancy, procrastinate jobs (Phase 4+) |
| `api`      | built from `apps/api/Dockerfile` (`python:3.12-slim`) | 8000 | FastAPI app: `/health` in Phase 0, all REST endpoints in later phases |
| `web`      | built from `apps/web/Dockerfile` (`node:22-alpine`) | 3000 | Next.js 16.2 App Router; server-rendered placeholder in Phase 0 |
| `adminer`  | `adminer:latest` | 8080 | Dev-only DB inspector (login pre-fills `Server: postgres`) |

The api and web apps are a **modular monolith** rather than a microservice
fleet — single deploy unit, hard import boundaries enforced by convention
(Phase 0) and `import-linter` (Phase 1+). See
[`adr/001-modular-monolith.md`](adr/001-modular-monolith.md) for the full
decision record and tradeoffs.

The whole stack starts with one command:

```bash
cp .env.example .env
make dev
```

After Postgres reports healthy, `make migrate` applies the Phase 0 Alembic
baseline. `http://localhost:3000` renders the placeholder page;
`http://localhost:8000/health` returns `{"status":"ok","db_connected":true,…}`;
`http://localhost:8080` opens Adminer.

## 2. Directory Layout

This is the on-disk shape at the end of Phase 0. Every file here exists; nothing
listed below is aspirational.

```
ledgr/                                     # repo root
├── apps/
│   ├── web/                               # Next.js 16.2 web app
│   │   ├── src/
│   │   │   └── app/
│   │   │       ├── layout.tsx             # root layout (PRANAV metadata)
│   │   │       ├── page.tsx               # async RSC; fetches /health
│   │   │       └── globals.css            # Tailwind 4 + shadcn variables
│   │   ├── public/                        # default Next.js folder
│   │   ├── components.json                # shadcn config (Tailwind 4 compatible)
│   │   ├── eslint.config.mjs              # ESLint flat config
│   │   ├── next.config.ts                 # Next.js config
│   │   ├── package.json                   # next, react, tailwind, RHF, Zod, TanStack Query
│   │   ├── pnpm-lock.yaml
│   │   ├── postcss.config.mjs             # Tailwind 4 via PostCSS
│   │   ├── tsconfig.json                  # paths: @/* → ./src/*
│   │   ├── Dockerfile                     # multi-stage: deps → builder → runner
│   │   ├── .dockerignore
│   │   ├── .nvmrc                         # 22
│   │   └── .gitignore                     # Next.js default
│   └── api/                               # FastAPI app
│       ├── src/
│       │   ├── __init__.py
│       │   ├── main.py                    # app + lifespan + middleware + router include
│       │   ├── config.py                  # Settings (pydantic-settings)
│       │   ├── database.py                # async engine + AsyncSessionLocal + get_session
│       │   ├── logging_config.py          # structlog + redactor + RequestContextMiddleware
│       │   └── modules/
│       │       ├── __init__.py
│       │       └── health/
│       │           ├── __init__.py
│       │           └── router.py          # GET /health
│       ├── tests/
│       │   ├── __init__.py
│       │   ├── conftest.py                # async client + LifespanManager fixture
│       │   ├── test_health.py
│       │   ├── test_logging.py
│       │   └── test_env_example.py
│       ├── Dockerfile                     # multi-stage: builder → runtime (python:3.12-slim)
│       ├── .dockerignore
│       ├── .python-version                # 3.12
│       ├── requirements.txt               # runtime deps (pinned floor + ceiling)
│       ├── requirements-dev.txt           # dev/test deps (-r requirements.txt + 7)
│       └── pyproject.toml                 # ruff + pyright + pytest config ONLY
├── packages/
│   ├── db/
│   │   ├── __init__.py
│   │   ├── alembic.ini                    # script_location=migrations, asyncpg fallback URL
│   │   ├── models/
│   │   │   └── __init__.py                # Base = DeclarativeBase only
│   │   └── migrations/
│   │       ├── env.py                     # async env.py (NullPool + run_sync)
│   │       ├── script.py.mako
│   │       └── versions/
│   │           └── 0001_phase0_baseline.py # _phase0_marker + COMMENT ON DATABASE
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── schemas.py                     # Pydantic domain types (empty in Phase 0)
│   │   └── types.ts                       # TS domain types (empty in Phase 0)
│   └── domain/
│       └── __init__.py                    # Pure business logic (no DB / no HTTP)
├── docker/
│   └── docker-compose.yml                 # 4-service stack
├── docs/
│   ├── ARCHITECTURE.md                    # this file
│   ├── SCHEMA.md                          # Phase 1+ table reservations
│   ├── BACKLOG.md                         # tracked deferrals (CLAUDE.md #7)
│   ├── MIGRATIONS.md                      # migration discipline (INFRA-08)
│   └── adr/
│       └── 001-modular-monolith.md
├── .github/
│   └── workflows/
│       └── check.yml                      # api + web CI on push + PR
├── .env.example                           # 8 env vars + commented native-dev DATABASE_URL
├── .gitignore
├── .gitattributes                         # text=auto eol=lf
├── CLAUDE.md                              # repo-wide conventions
├── Makefile                               # dev | down | migrate | check | shell-{api,db}
└── README.md                              # quickstart
```

## 3. Backend (FastAPI)

The api is a Python 3.12 application built on:

- **FastAPI** `>=0.136,<0.137` — async HTTP framework; APIRouter per module
- **SQLAlchemy** `>=2.0.36,<2.1` (`[asyncio]`) — async ORM; NOT SQLModel
- **asyncpg** `>=0.30,<0.32` — async Postgres driver
- **Alembic** `>=1.18,<2` — schema migrations (async env.py)
- **Pydantic v2** + **pydantic-settings** — validation + env-loaded config
- **structlog** `>=25.1,<26` — JSON-in-prod, console-in-dev logging
- **PyJWT** `>=2.9` + **pwdlib[argon2]** `>=0.3` — auth substrate (Phase 1+)
- **uvicorn[standard]** `>=0.36,<1` — ASGI server; `--reload` in dev compose

### Module layout

Every api module lives under `apps/api/src/modules/<name>/` and exposes a
`router = APIRouter()` at module level. Phase 0 ships one module:

- `apps/api/src/modules/health/router.py` — `GET /health` returning the
  `{status, version, environment, db_connected}` envelope

`main.py` imports the router with a relative path and includes it with a prefix:

```python
from .modules.health.router import router as health_router
app.include_router(health_router, prefix="/health", tags=["health"])
```

**Cross-module imports are forbidden.** If module `A` needs logic from module
`B`, that logic moves to `packages/domain/`. Phase 0 has only one module, so
the constraint is dormant; Phase 1+ enforces it via `import-linter` (tracked in
`BACKLOG.md`).

### Async DB engine + session lifecycle

`apps/api/src/database.py` creates the async engine and sessionmaker at module
import:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.ENVIRONMENT == "dev",
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

`expire_on_commit=False` is **non-negotiable** for async sessions —
`expire_on_commit=True` triggers surprising re-loads after commit and
breaks under async I/O patterns. (See
[PITFALLS / Anti-Patterns](#anti-patterns-tracked-in-research) below.)

The `get_session()` dependency is the canonical FastAPI dependency every route
uses:

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

Engine setup is at module import; the FastAPI `lifespan` context manager only
disposes the engine on shutdown. There is no startup-side engine init in the
lifespan — that would race with module imports during test collection.

### `/health` endpoint contract

`GET /health` returns a 4-key JSON envelope:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "dev",
  "db_connected": true
}
```

`db_connected` reflects an actual `SELECT 1` against the injected
`AsyncSession`. On DB outage, the handler returns **HTTP 200** with
`status="degraded"` and `db_connected=false` — NOT HTTP 500. This is the
Kubernetes liveness convention: liveness ≠ readiness, and the api process is
still alive even when the DB is unreachable. Readiness probes belong on a
separate `/ready` endpoint (Phase 12+ deployment work).

The envelope is exactly four keys — no DB URL, no secret hashes, no internal
paths, no auth state. Information disclosure is the threat being mitigated
(T-00-07 in the Phase 0 research register).

## 4. Frontend (Next.js)

The web app is a Next.js 16.2 application built on:

- **Next.js** `^16.2.6` — App Router; Turbopack default; async params/cookies/headers
- **React** `^19.2` — bundled with Next 16; Server Components first
- **TypeScript** `^5.9` — strict mode
- **Tailwind CSS** `^4.3` — CSS-first config (no `tailwind.config.ts`)
- **shadcn/ui** — Radix UI + Tailwind copy-paste components (init in Phase 0; no components yet)
- **TanStack Query v5**, **Zustand v5**, **React Hook Form v7**, **Zod v4**,
  **@hookform/resolvers v5** — version-locked for Phase 1+ use, not wired yet

The Phase 0 placeholder is an async **Server Component** at `src/app/page.tsx`.
It fetches `/health` server-side and renders the result. URL resolution order:

```
process.env.API_URL_INTERNAL          # Docker network (http://api:8000)
  → process.env.NEXT_PUBLIC_API_URL   # Browser/dev (http://localhost:8000)
  → "http://localhost:8000"           # Last-resort default
```

When the API is unreachable, the page renders `"API unavailable"` instead of
crashing. The fetch uses `cache: 'no-store'` so dev iteration surfaces API
state immediately.

> **Next.js 16 idiom note:** `params`, `searchParams`, `cookies()`, `headers()`,
> and `draftMode()` are async — always `await` them. The legacy synchronous
> pattern from Next.js 14 will not compile under Next 16's stricter typing.

## 5. Database (Postgres 16)

The database is Postgres 16 in an `alpine` container with a `pg_isready`
healthcheck wired into Compose. The api container's `depends_on.postgres`
uses `condition: service_healthy` — `make migrate` will not race the DB on
first boot.

Schema migrations live in `packages/db/migrations/versions/` and are managed
by **Alembic with an async env.py**. The env.py reads `DATABASE_URL` from
the environment at runtime, overriding the `alembic.ini` fallback URL:

```python
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
connectable = async_engine_from_config(
    config.get_section(config.config_ini_section),
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
)
async with connectable.connect() as connection:
    await connection.run_sync(do_run_migrations)
```

`NullPool` is intentional — migrations are short-lived and the engine should
not hold connections after the upgrade completes.

### Phase 0 baseline migration

`0001_phase0_baseline.py` does two things:

1. **Creates `_phase0_marker`** — a singleton table proving migrations ran.
   Schema: `id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id=1)`,
   `applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`,
   `note TEXT NOT NULL DEFAULT 'Phase 0 migration succeeded'`.
2. **Reserves the `app.current_household_id` RLS GUC** via
   `COMMENT ON DATABASE` — a documentation contract, no policies yet.

The `test_baseline_migration_applied` test (apps/api/tests/test_health.py)
asserts the singleton row exists with the expected default note, proving the
migration ran in CI and locally.

### Row-Level Security (Phase 0 reservation; Phase 1 activation)

PRANAV uses Postgres Row-Level Security for **household-scoped multi-tenancy**.
Every domain table (Phase 1+) carries
`household_id UUID NOT NULL REFERENCES household(id) ON DELETE CASCADE` and is
guarded by a per-table policy:

```sql
ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;
CREATE POLICY <table_name>_household_isolation ON <table_name>
  USING (
    household_id = current_setting('app.current_household_id', true)::uuid
  );
```

The **`, true` second argument** to `current_setting()` is non-negotiable.
Without it, Postgres raises `unrecognized configuration parameter` when the
GUC is unset (e.g., during migrations, in admin sessions, in misconfigured
worker contexts). See [`MIGRATIONS.md`](MIGRATIONS.md) §RLS Convention for
the full rule.

Phase 1's `get_session()` will issue
`SET LOCAL app.current_household_id = '<uuid>'` after auth resolves the
household. Phase 0 only documents the convention via `COMMENT ON DATABASE`;
no policies fire and no domain tables exist yet.

## 6. Logging (structlog)

Logging is structured-first. `apps/api/src/logging_config.py` configures
structlog with three knobs that vary by environment:

- **Renderer:** `JSONRenderer()` in `ENVIRONMENT=production`; `ConsoleRenderer()`
  otherwise. Logs to stdout in both cases — Docker captures them.
- **Redactor:** `_redact_processor` walks the `event_dict` recursively (dicts
  + lists at any nesting depth) and replaces values whose keys (lowercased)
  match `SENSITIVE_KEYS` with `"***"`. The 8 keys covered: `password`, `token`,
  `secret`, `authorization`, `access_token`, `refresh_token`, `api_key`,
  `secret_key`.
- **Context propagation:** `structlog.contextvars.merge_contextvars` adds any
  bound contextvars to every log line. `RequestContextMiddleware` binds
  `request_id` (from the `x-request-id` header, or `uuid.uuid4().hex` if absent)
  at the start of every request.

### `RequestContextMiddleware` — pure ASGI, not BaseHTTPMiddleware

The middleware is a **pure ASGI class**, not a subclass of the high-level
HTTP-style middleware base. The high-level base creates a separate asyncio
context copy and breaks structlog contextvar propagation across awaits — the
`request_id` binding would not survive the trip from middleware to handler.

Shape:

```python
class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            clear_contextvars()
            request_id = _extract_request_id(scope) or uuid.uuid4().hex
            bind_contextvars(request_id=request_id)
        await self.app(scope, receive, send)
```

The middleware is added **after** `CORSMiddleware` in `main.py` so the
`request_id` is bound for CORS preflight (OPTIONS) responses too.

Every future module that needs to bind request-scoped contextvars (user_id,
household_id, the RLS GUC) follows this same pure-ASGI pattern. See
[`adr/001-modular-monolith.md`](adr/001-modular-monolith.md) for the
rationale.

## 7. CORS

`main.py` adds `CORSMiddleware` with origins from the `ALLOWED_ORIGINS` env
var (comma-separated; default `http://localhost:3000`). The CORS config sets
`allow_credentials=True` for the JWT-in-cookie auth flow (Phase 1+).

`allow_credentials=True` combined with `allow_origins=["*"]` is **forbidden by
the CORS spec** — FastAPI raises at startup if you try. The default origin
list is explicit, and `Settings.allowed_origins_list` parses
`ALLOWED_ORIGINS=https://a.example,https://b.example` into a typed list.

## 8. What lives where (Architectural Responsibility Map)

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTTP routing + JSON request/response | API / Backend (FastAPI) | — | All `/health`, all future routes — FastAPI is the canonical HTTP layer. |
| Async DB engine + session management | API / Backend (`packages/db`) | — | Phase 0 owns the engine lifespan; workers will reuse the same `packages/db` in Phase 4. |
| Schema migrations | API / Backend (Alembic, in api container) | — | `make migrate` runs `docker compose exec api alembic upgrade head`. Alembic lives in `packages/db/migrations`. |
| RLS GUC reservation (no policies yet) | Database / Storage | API / Backend (sets GUC per session in Phase 1+) | Phase 0 reserves the convention via SQL comment + a no-op migration; Phase 1's `get_session` will issue `SET LOCAL app.current_household_id = ?`. |
| Structured logging | API / Backend (apps/api) | — | structlog binds request context (request_id) per request via ASGI middleware. Web app uses Next.js default logger (out of scope for this phase). |
| Server-rendered placeholder page | Frontend Server (Next.js App Router RSC) | API / Backend (provides `/health`) | RSC `fetch(API_URL + "/health")` in `app/page.tsx`; result rendered server-side. No client-side state needed. |
| Container orchestration | CDN / Static (Docker Compose dev) | — | Compose is the dev-time orchestration layer; production hosting is out of scope for Phase 0. |
| Linting + typechecking | Build/CI (`.github/workflows/check.yml` + `make check`) | — | ruff + pyright on Python; tsc + eslint on TS. Run in CI on every push. |
| Secrets handling | Build/CI + Self-host deployer | — | `.env` is in `.gitignore`; `.env.example` is committed. Secrets never logged (verified by structlog redactor pattern). |

## 9. Conventions

These are repo-wide rules. CLAUDE.md is the source of truth; this section
summarizes for the architecture reader.

### Naming

Function and method names follow a strict verb prefix discipline:

- `get_X` — fetch one record by id/key (raises or returns None)
- `list_X` — fetch many records (filtered, sorted, paged)
- `create_X` — insert a new record
- `update_X` — modify an existing record
- `delete_X` — remove a record

Forbidden synonyms: `fetch_X`, `load_X`, `retrieve_X`, `find_X`, `pull_X`,
`grab_X`. The verb prefix is grep-able and reviewable.

### Money

**All monetary values are stored as INTEGER cents** — both in the database
and on the wire. Never float, never `Decimal` in storage.

- DB columns: `amount_cents INTEGER NOT NULL`
- Pydantic models: `amount_cents: int`
- Display formatting (browser only): `(cents / 100).toLocaleString("en-US",
  { style: "currency", currency: "USD" })`

Currency arithmetic in the API uses Python `int` directly — no `decimal.Decimal`
is needed because we're already in integer cents.

### Dates

- **Business dates** (when a transaction occurred): `DATE` in Postgres.
- **Timestamps** (when a row was created, when a transaction posted): `TIMESTAMPTZ`.
- **On the wire:** ISO 8601 strings (e.g., `"2026-05-23"`, `"2026-05-23T14:30:00Z"`).
- **Transactions always store BOTH `transaction_date` (DATE — purchase date) and `post_date` (TIMESTAMPTZ — bank settlement timestamp).** The difference matters for reconciliation, forecasting, and reports.

### Module boundaries

`apps/api/src/modules/<name>/` is the module unit.

- A module **may not** import from another module's internal files.
- Cross-module logic **must** live in `packages/domain/` and be imported
  from both sides.
- `packages/domain/` contains pure business logic — no DB imports, no FastAPI
  imports, no HTTP framework imports. It is testable as a pure function tree.

`packages/db/` owns SQLAlchemy models, the async engine, and migrations.
`packages/shared/` owns Pydantic schemas (`schemas.py`) and TypeScript types
(`types.ts`) — the shapes that cross the wire.

### Anti-patterns (tracked in research)

The Phase 0 research captured these explicit anti-patterns; the architecture
reader should internalize them:

- `@app.middleware("http")` (BaseHTTPMiddleware) for contextvar binding — breaks
  structlog across awaits. Use pure ASGI middleware.
- `TestClient` from `fastapi.testclient` in async tests — official FastAPI
  docs say it doesn't work. Use `httpx.AsyncClient` + `ASGITransport` +
  `LifespanManager`.
- `SQLModel` — fuses Pydantic with SQLAlchemy; violates the
  `packages/shared/schemas.py` ↔ `packages/db/models/` separation.
- `expire_on_commit=True` on async sessionmaker — already covered above.
- Sync `psycopg2` in the application path — fine as a transitive tooling dep
  in rare Alembic edge cases; the application engine must be
  `postgresql+asyncpg://`.
- Lazy relationships (`lazy="select"`) in async sessions — silent failures or
  I/O outside the session scope. Use `selectinload`/`joinedload` explicitly.
- Static `version: "3.8"` in docker-compose.yml — deprecated in Compose v2.
- `tailwind.config.ts` in a Tailwind v4 project — v4 is CSS-config-first.

## 10. Phase 0 status

Phase 0 ships the foundation. What's in place:

- 4-container Docker Compose stack (postgres + api + web + adminer)
- FastAPI `/health` endpoint with real `SELECT 1` DB probe and k8s-conventional
  degraded mode
- Alembic async env.py and baseline migration that creates `_phase0_marker`
  and reserves the `app.current_household_id` RLS GUC convention
- structlog JSON-in-prod / console-in-dev with recursive sensitive-key
  redaction and a pure-ASGI `RequestContextMiddleware`
- Next.js 16.2 App Router placeholder page with graceful API-unavailable
  degradation
- `make dev` / `make migrate` / `make check` / `make shell-{api,db}` developer
  interface
- GitHub Actions CI workflow (`.github/workflows/check.yml`) running api +
  web jobs on push + PR
- Documentation set (this file, [`SCHEMA.md`](SCHEMA.md),
  [`MIGRATIONS.md`](MIGRATIONS.md), [`BACKLOG.md`](BACKLOG.md), and
  [`adr/001-modular-monolith.md`](adr/001-modular-monolith.md))

What's **NOT** in place (all Phase 1+):

- Any user-facing routes beyond `/health` (no auth, no households, no
  accounts, no transactions)
- Any domain tables (`household`, `user`, `account`, `transaction`, etc.)
- Active RLS policies (the GUC is reserved; per-table activation is Phase 1)
- The procrastinate worker container (Phase 4)
- Plaid / SimpleFIN / receipt-parse connectors (Phase 9, 11, 12)
- The forecast view (Phase 8 — the differentiator)
- All authentication and authorization (Phase 1)

The full phase map lives in [`.planning/ROADMAP.md`](../.planning/ROADMAP.md).

---

*Phase 0 architecture as of 2026-05-24. Future phases will append to this
document rather than rewrite it; the modular-monolith decision is recorded
permanently in [`adr/001-modular-monolith.md`](adr/001-modular-monolith.md).*
