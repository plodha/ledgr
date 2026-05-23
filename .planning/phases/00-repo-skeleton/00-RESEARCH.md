# Phase 0: Repo Skeleton — Research

**Researched:** 2026-05-23
**Domain:** Polyglot monorepo bootstrap (FastAPI 0.136 + Next.js 16.2 + Postgres 16 + Adminer in Docker Compose) with RLS scaffolding, structured logging, async Alembic, and dual-language tooling (ruff/pyright + tsc/eslint).
**Confidence:** HIGH for versions and infrastructure patterns (all packages verified against PyPI/npm registries + slopcheck on 2026-05-23 and against official FastAPI/Next.js/Alembic/Postgres 16 docs); MEDIUM for the procrastinate-in-Alembic integration detail and the exact Tailwind 4 + shadcn/ui init sequence (verified against current docs but with light hands-on experience as of training data).

## Summary

Phase 0 is a **fully prescriptive, no-discretion phase**: every choice — including exact library versions — is already locked by CLAUDE.md and the four prior research documents (STACK.md, ARCHITECTURE.md, PITFALLS.md, FEATURES.md). The planner's job is sequencing the file scaffold, not making decisions. The research below pins every version, gives the canonical code shape for each non-trivial file, and surfaces the few "must-do-it-right-the-first-time" pitfalls (Alembic async env.py, RLS scaffolding without table policies, Procrastinate schema co-existence with Alembic, Tailwind 4 + shadcn/ui ordering).

The single most important architectural decision in this phase — locked at the requirements level (INFRA-09) — is **scaffolding Postgres Row-Level Security in Phase 0 even though no policies fire until Phase 1**. This means: (a) the Alembic migration that creates the cluster-level GUC reservation runs in Phase 0; (b) the `app.current_household_id` session variable convention is documented so Phase 1 can wire the `SET LOCAL` call; (c) Phase 0's `/health` endpoint and any utility tooling that touches DB explicitly does *not* try to set or rely on the GUC. Procrastinate is **NOT** installed in Phase 0 per STACK.md §2.2 ("Phases 0–8 don't need a job queue"); it lands in Phase 4.

**Primary recommendation:** Build the scaffold in this exact order (mirrored by the planner's wave structure): (1) repo root + `.env.example` + Makefile stub; (2) `apps/api` with FastAPI app + async SQLAlchemy engine + lifespan + structlog config + `/health` endpoint; (3) `packages/db` with Alembic async env.py + one initial migration that reserves the RLS GUC and creates a `_phase0_marker` table to prove migrations work; (4) `apps/web` via `pnpm create next-app@latest --yes` then customize the placeholder page; (5) Docker Compose + Adminer + per-service Dockerfiles; (6) docs (`ARCHITECTURE.md`, `SCHEMA.md`, `BACKLOG.md`, `MIGRATIONS.md`, `adr/001-modular-monolith.md`); (7) CI workflow `.github/workflows/check.yml`. Tests are minimal: one pytest hitting `/health`, one tsc/eslint pass on the placeholder page.

## User Constraints (from CLAUDE.md — no separate CONTEXT.md exists)

> No `.planning/phases/00-repo-skeleton/00-CONTEXT.md` exists at research time. The "locked decisions" below are extracted verbatim from `CLAUDE.md` (project canon) and `.planning/research/STACK.md`. The planner MUST honor these.

### Locked Decisions

- **Repo structure** is exhaustively specified in CLAUDE.md (`apps/web`, `apps/api`, `packages/{db,shared,domain}`, `docker/`, `docs/`). Do not invent additional top-level directories.
- **Stack** (per CLAUDE.md "FastAPI app requirements" + STACK.md):
  - Python 3.12 (CLAUDE.md says "Python 3.12"; STACK.md confirms 3.12 is the production sweet spot through v1.0)
  - FastAPI 0.136+ (CLAUDE.md updated to "FastAPI 0.136+")
  - SQLAlchemy 2.0 async (NOT SQLModel; NOT sync; CLAUDE.md "Do not use synchronous SQLAlchemy — async only")
  - asyncpg (NOT psycopg async)
  - Pydantic v2 + pydantic-settings
  - Alembic (async env.py)
  - structlog (JSON in prod, console in dev) with request_id + sensitive-field redaction
  - PyJWT + pwdlib[argon2] (auth packages — install in Phase 0 even though Phase 1 wires them; this avoids adding to requirements.txt mid-phase)
  - procrastinate>=3 (Postgres-native): **DEFERRED to Phase 4** per STACK.md §2.2 — do NOT install in Phase 0
  - Next.js 16.2+ (CLAUDE.md was updated 2026-05-23 from "14" to "16.2+")
  - Node 22 (CLAUDE.md says "node:22-alpine")
  - TypeScript everywhere on the frontend (CLAUDE.md: "Do not use JavaScript — TypeScript everywhere")
  - Tailwind CSS 4, App Router, Turbopack, ESLint (`pnpm create next-app@latest --yes` defaults)
  - shadcn/ui (Radix + Tailwind), TanStack Query v5, React Hook Form, Zod — install but no app usage required in Phase 0
  - Postgres 16-alpine
  - Adminer (no version pin — image is stable; use `adminer:latest` per Phase 0 spec)
- **Hard NOTs** (CLAUDE.md "What NOT to do"):
  - No auth/user/account tables yet (Phase 1)
  - No feature routes beyond `/health`
  - No packages outside the listed set without explicit approval
  - No JavaScript on the frontend
  - No synchronous SQLAlchemy
- **Domain types** live in `packages/shared/schemas.py` (backend) and `packages/shared/types.ts` (frontend). Phase 0 creates these files **empty with docstring/header comments only**.
- **Money**: INTEGER cents on wire and in DB. Phase 0 has no money handling but the README/CLAUDE.md must state this.
- **Dates**: Store `transaction_date` and `post_date`. Phase 0 has no transaction model but `docs/SCHEMA.md` must document the convention.
- **Module boundaries**: `apps/api/src/modules/<name>/` — no cross-module internal imports; cross-module calls through `packages/domain/`. Phase 0 creates only the `health/` module.
- **Naming conventions**: `get_X`, `list_X`, `create_X`, `update_X`, `delete_X` — no fetch/load/retrieve. Phase 0 has only `get_health()` or similar.
- **`make check` must pass at end of Phase 0** with zero errors (pyright + ruff + pytest on api; tsc --noEmit + eslint on web).
- **`make migrate` must run `alembic upgrade head` inside the api container** and successfully apply at least one migration.
- **`/health` must do a real `SELECT 1` against Postgres** and return `db_connected: true` (not just a static string).
- **Postgres RLS infrastructure scaffolded** in Phase 0: per ROADMAP.md and STATE.md, RLS is **enabled in Phase 0 and policies are wired in Phase 1** (this is a deliberate choice — "RLS scaffolded in Phase 0, activated in Phase 1, not retrofitted in Phase 13").

### Claude's Discretion

(Items left to the implementer that planner should still standardize)

- Choice of exact ruff rule set and pyright strictness level (recommendation below: ruff `ALL` minus opinionated rules, pyright `strict`).
- Choice of Python package format: `requirements.txt` (CLAUDE.md mandates `requirements.txt`) — but also create a minimal `pyproject.toml` for ruff/pyright configuration. **No setuptools/poetry/uv build system needed in Phase 0** — `requirements.txt` is the source of truth.
- Whether to use multi-stage Docker builds (recommended: yes, even in Phase 0 — sets the pattern for later phases).
- Whether to add `apps/api/.python-version` and `apps/web/.nvmrc` (recommended: yes — explicit tooling versions).
- Logging output format in dev vs prod is controlled by `LOG_LEVEL`/`ENVIRONMENT` env vars; planner picks the env-var name (recommend `ENVIRONMENT=dev|production`).

### Deferred Ideas (OUT OF SCOPE)

These are explicitly NOT Phase 0 — do not pre-emptively scaffold:

- Auth, users, households, accounts, transactions, categories — Phases 1–3
- Procrastinate / worker container — Phase 4
- Rules engine, recurring, budget, forecast, reports — Phases 5–9
- Plaid, SimpleFIN, receipt parsing — v2 phases (12+)
- Sentry / OpenTelemetry / metrics — explicitly deferred per STACK.md §7 ("No Sentry / no OpenTelemetry in Phase 0")
- HTTPS / reverse proxy — Phase 0 ships plain HTTP on localhost
- Pre-commit hooks for secret scanning — nice-to-have, defer to milestone close
- Backup tooling (`make backup`) — defer to v1.0 ship per PITFALLS.md O6 (PITFALLS.md says "Phase 0 — minimum viable Make target", but Phase 0 success criteria doesn't list this, so omit unless explicitly added by discuss-phase)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | `git clone && make dev` starts all four containers with no errors | Docker Compose v2 spec + per-service Dockerfile patterns documented below (§"Code Examples — Docker Compose"); `make dev` target wraps `docker compose up --build`. |
| INFRA-02 | `/health` returns `{status, version, environment, db_connected}` with real DB connection test | FastAPI lifespan + async SQLAlchemy engine + `SELECT 1` pattern (§"Code Examples — /health endpoint"); verified against fastapi.tiangolo.com SQL tutorial. |
| INFRA-03 | `make check` passes (pyright + ruff + pytest; tsc + eslint) with zero errors | ruff 0.15+ and pyright 1.1.409 verified on PyPI; ESLint flat config from `create-next-app --yes`; tsc via `pnpm tsc --noEmit`. Pattern in §"Code Examples — Makefile". |
| INFRA-04 | `make migrate` runs Alembic upgrade-head inside api container; MIGRATIONS.md documents nullable-first + CREATE INDEX CONCURRENTLY | Alembic 1.18.4 async template (`alembic init -t async`); verified against alembic.sqlalchemy.org cookbook. `MIGRATIONS.md` content drafted in §"Code Examples — MIGRATIONS.md". |
| INFRA-05 | Adminer accessible at localhost:8080 connected to the DB | Adminer container in docker-compose.yml depends on postgres service; no auth on the dev port (dev-only). |
| INFRA-06 | `.env.example` documents all required variables | Variable list derived from FastAPI Settings (DATABASE_URL, SECRET_KEY, ENVIRONMENT, LOG_LEVEL, ALLOWED_ORIGINS) + Next.js (NEXT_PUBLIC_API_URL) + Postgres (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB). |
| INFRA-07 | Structured JSON logging with structlog (request_id, redaction) | structlog 25.5.0 verified on PyPI; pure-ASGI middleware pattern (NOT BaseHTTPMiddleware) verified via web search of 2026 best practices; pattern in §"Code Examples — structlog config". |
| INFRA-08 | MIGRATIONS.md documents non-locking migration discipline | PITFALLS.md O1 already covers this; Phase 0 codifies the rules in `docs/MIGRATIONS.md`. Content drafted below. |
| INFRA-09 | Postgres RLS infrastructure scaffolded (enabled, `app.current_household_id` session variable, policies wired in Phase 1) | Postgres 16 RLS docs confirm `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`, `current_setting('app.current_household_id', true)::uuid` pattern; custom GUCs with dot syntax need NO registration since PG 9.2 (verified via web search 2026-05-23). Phase 0 migration must (a) create a "marker" table proving migrations run, and (b) include a SQL comment block documenting the GUC reservation; no policies fire in Phase 0. |

## Architectural Responsibility Map

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
| Secrets handling | Build/CI + Self-host deployer | — | `.env` is in `.gitignore`; `.env.example` is committed. Secrets never logged (verified by structlog redactor pattern + PITFALLS.md O7). |

## Standard Stack

### Core (API)

> All Python versions verified via `pip3 index versions <pkg>` on 2026-05-23. All packages passed `slopcheck install` ([OK]) on 2026-05-23.

| Library | Version | Purpose | Why Standard | Provenance |
|---------|---------|---------|--------------|------------|
| `fastapi` | `>=0.136,<0.137` | Async HTTP framework | Async-first, Pydantic-native, official tutorial matches our `modules/<name>/router.py` layout | [VERIFIED: pip3 index versions → 0.136.3 latest; PyPI publish-date 2026 stable; slopcheck OK; STACK.md HIGH confidence] |
| `uvicorn[standard]` | `>=0.36,<1` | ASGI server | FastAPI's recommended dev/prod server; `[standard]` extras include `httptools`, `uvloop`, `watchfiles` | [VERIFIED: pip3 index versions → 0.47.0 latest; slopcheck OK] |
| `sqlalchemy[asyncio]` | `>=2.0.36,<2.1` | Async ORM | 2.0 is GA, async is battle-tested; explicitly NOT SQLModel per CLAUDE.md | [VERIFIED: pip3 index versions → 2.0.49 latest; slopcheck OK] |
| `asyncpg` | `>=0.30,<0.32` | Async Postgres driver | Fastest pure-async Postgres driver; SQLAlchemy 2.0 + asyncpg is the canonical pairing | [VERIFIED: pip3 index versions → 0.31.0 latest; slopcheck OK] |
| `alembic` | `>=1.18,<2` | Schema migrations | De facto SQLAlchemy migration tool; async env.py template ships in 1.13+ | [VERIFIED: pip3 index versions → 1.18.4 latest; slopcheck OK] |
| `pydantic` | `>=2.9,<3` | Validation + schemas | Rust-backed v2; FastAPI's native integration | [VERIFIED: pip3 index versions → 2.13.4 latest; slopcheck OK] |
| `pydantic-settings` | `>=2.5,<3` | Env-var loaded settings | Reads `.env` and OS env vars into typed config; standard Pydantic v2 companion | [VERIFIED: pip3 index versions → 2.14.1 latest; slopcheck OK] |
| `structlog` | `>=25.1,<26` | Structured logging | INFRA-07 mandates structlog; supports contextvars merging for request_id | [VERIFIED: pip3 index versions → 25.5.0 latest; slopcheck OK] |
| `PyJWT` | `>=2.9,<3` | JWT encoding (Phase 1+) | Official FastAPI tutorial choice; install in Phase 0 so Phase 1 doesn't need a requirements change | [VERIFIED: pip3 index versions → 2.13.0 latest; slopcheck OK; STACK.md §2.1] |
| `pwdlib[argon2]` | `>=0.3,<1` | Password hashing (Phase 1+) | Official FastAPI tutorial replacement for passlib+bcrypt | [VERIFIED: pip3 index versions → 0.3.0 latest; slopcheck OK; STACK.md §2.1] |
| `python-multipart` | `>=0.0.20,<1` | FastAPI form data | Required by `OAuth2PasswordRequestForm` in Phase 1; harmless dependency now | [VERIFIED: pip3 index versions → 0.0.29 latest; slopcheck OK] |
| `greenlet` | `>=3.0,<4` | SQLAlchemy async runtime | Required transitive dep of `sqlalchemy[asyncio]`; pin explicitly for reproducible builds | [VERIFIED: pip3 index versions → 3.5.1 latest; slopcheck OK] |

### Supporting (API test stack)

| Library | Version | Purpose | When to Use | Provenance |
|---------|---------|---------|-------------|------------|
| `pytest` | `>=8,<10` | Test runner | All Python tests | [VERIFIED: pip3 index versions → 9.0.3 latest; slopcheck OK] |
| `pytest-asyncio` | `>=1.0,<2` | Async test support | `@pytest.mark.asyncio` for async test functions | [VERIFIED: pip3 index versions → 1.3.0 latest; slopcheck OK] |
| `anyio` | `>=4.0,<5` | Async runtime + pytest plugin | `@pytest.mark.anyio` alternative; FastAPI official docs use it | [VERIFIED: pip3 index versions → 4.13.0 latest; slopcheck OK] |
| `asgi-lifespan` | `>=2.1,<3` | Lifespan triggering in httpx tests | **REQUIRED** — httpx `AsyncClient` doesn't trigger lifespan; our app uses lifespan for DB engine init | [VERIFIED: pip3 index versions → 2.1.0 latest; slopcheck OK; per fastapi.tiangolo.com/advanced/async-tests] |
| `httpx` | `>=0.27,<1` | Async HTTP client | `ASGITransport(app=app)` for tests + general HTTP client | [VERIFIED: pip3 index versions → 0.28.1 latest; slopcheck OK] |

### Supporting (API tooling)

| Library | Version | Purpose | When to Use | Provenance |
|---------|---------|---------|-------------|------------|
| `ruff` | `>=0.15,<1` | Linter + formatter | `ruff check` + `ruff format` for the api package | [VERIFIED: pip3 index versions → 0.15.14 latest; slopcheck OK] |
| `pyright` | `>=1.1.400,<2` | Type checker | `pyright` standalone; strict mode for the api package | [VERIFIED: pip3 index versions → 1.1.409 latest; slopcheck OK] |
| `psycopg2-binary` | `>=2.9.10,<3` | (Optional) Alembic sync fallback | Only if `alembic upgrade head` from a non-async context needs a sync driver; usually NOT needed when env.py is async | [VERIFIED: pip3 index versions → 2.9.12 latest; slopcheck OK] — recommended OMIT for Phase 0 unless Alembic raises a sync-context error during scaffolding |

### Core (Web)

> All Node versions verified via `npm view <pkg> version` on 2026-05-23.

| Library | Version | Purpose | Why Standard | Provenance |
|---------|---------|---------|--------------|------------|
| `next` | `^16.2.6` | React framework | Current stable; App Router default; Turbopack default bundler | [VERIFIED: npm view → 16.2.6 latest; verified against nextjs.org/docs/app/getting-started/installation lastUpdated 2026-05-19] |
| `react` | `^19.2.6` | UI library | Bundled-canary React used by Next 16 App Router; install for tooling/ecosystem compat | [VERIFIED: npm view → 19.2.6 latest] |
| `react-dom` | `^19.2.6` | React DOM bindings | Pairs with react@19.2 | [VERIFIED: npm view → 19.2.6 latest] |
| `typescript` | `^5.9` | Static types | Required by Next.js; v5.1.0 minimum per Next docs | [VERIFIED: npm view typescript version → 5.9 line current; Next.js docs minimum 5.1.0] |
| `tailwindcss` | `^4.3.0` | Styling | v4 is the default in `create-next-app --yes`; CSS-based config (no `tailwind.config.ts`) | [VERIFIED: npm view → 4.3.0 latest] |
| `eslint` | `^9.x` (peer of `eslint-config-next`) | Linter | Flat config (`eslint.config.mjs`); Next.js 16 removed `next lint`, use `eslint` directly | [VERIFIED: nextjs.org/docs/app/getting-started/installation confirms]
| `eslint-config-next` | `^16.2.6` | Next.js ESLint preset | Bundled with `create-next-app` | [VERIFIED: npm view → 16.2.6 latest] |
| `@types/node` | `^25.x` | Node type defs | TypeScript needs these for `process`, `Buffer`, etc. | [VERIFIED: npm view → 25.9.1 latest] |
| `@types/react` | `^19.2.x` | React type defs | Pairs with react@19.2 | [VERIFIED: npm view → 19.2.15 latest] |

### Supporting (Web — install but no usage in Phase 0)

| Library | Version | Purpose | When to Use | Provenance |
|---------|---------|---------|-------------|------------|
| `@tanstack/react-query` | `^5.x` | Server-state cache | Phase 1+ client components that mutate via API | [VERIFIED: npm view → 5.100.14 latest] — install in Phase 0 to lock the version into `package.json`, do not wire it yet |
| `zustand` | `^5.x` | Lightweight client state | Phase 3+ (transaction filters, modal state) | [VERIFIED: npm view → 5.0.13 latest] — install in Phase 0 |
| `react-hook-form` | `^7.x` | Forms | Phase 1+ (register, login forms) | [VERIFIED: npm view → 7.76.1 latest] — install in Phase 0 |
| `zod` | `^4.x` | Schema validation (TS) | Shared schemas between API and forms (Phase 1+) | [VERIFIED: npm view → 4.4.3 latest] — install in Phase 0 |
| `@hookform/resolvers` | `^5.x` | RHF + Zod glue | Phase 1+ forms | [VERIFIED: npm view → 5.4.0 latest] — install in Phase 0 |
| `clsx` + `tailwind-merge` + `class-variance-authority` | latest | shadcn/ui helpers | shadcn components use these | [VERIFIED: npm view → clsx 2.1.1, tailwind-merge 3.6.0, cva 0.7.1] — installed automatically by `pnpm dlx shadcn@latest init` |
| `recharts` | `^3.x` | Charts | Phase 8 (forecast) — do NOT install in Phase 0 (STACK.md said v2; v3 is now current) | [VERIFIED: npm view → 3.8.1 latest; STACK.md had `>=2.13,<3` — this is **stale**; v3 is now the floor. Flag for re-check before Phase 8.] |
| `prettier` | `^3.x` | Formatter (optional) | Tied to ESLint flat config | [VERIFIED: npm view → 3.8.3 latest] — optional; the ruff/eslint setup already covers most concerns |

> **shadcn/ui** itself is **not** an npm package — it's a CLI-driven copy-paste library installed via `pnpm dlx shadcn@latest init` (see §"Code Examples — Web init flow"). The init command writes a `components.json` and updates `globals.css`. **No components installed in Phase 0** — the init is purely scaffolding.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `requirements.txt` | `pyproject.toml` with PEP 621 + uv lockfile | uv is faster but adds an extra tool; CLAUDE.md mandates `requirements.txt`. Decision: stick with `requirements.txt`; use `pyproject.toml` ONLY for ruff/pyright config. |
| `psycopg[async]` | asyncpg | psycopg v3 has async support and shares a sync/async API. asyncpg is ~2x faster and is the SQLAlchemy async tutorial's choice. CLAUDE.md mandates asyncpg. |
| `passlib[bcrypt]` | `pwdlib[argon2]` | passlib is unmaintained (last release ~2024); FastAPI official tutorial switched to pwdlib. Decision per STACK.md: pwdlib. |
| `python-jose` | PyJWT | python-jose maintenance has been spotty; FastAPI official tutorial switched to PyJWT. |
| `aiosqlite` (SQLite for dev) | Postgres in Docker for dev | RLS doesn't exist in SQLite; we need real Postgres for parity. Stick with Postgres 16-alpine in Docker. |
| BaseHTTPMiddleware (FastAPI's `@app.middleware`) | Pure ASGI middleware | BaseHTTPMiddleware breaks contextvars across request scopes (verified via 2026 best-practices search). For structlog request_id, pure ASGI middleware is required. |
| Webpack | Turbopack (Next 16 default) | Turbopack is the default; `--webpack` flag available if needed. Decision: take the default. |
| `create-next-app` custom prompts | `--yes` defaults | Matches CLAUDE.md's stack list 1:1; saves the planner from documenting every prompt. Decision: `pnpm create next-app@latest <name> --yes`. |
| Adminer | pgAdmin | pgAdmin is heavier and the auth-config story is more complex. Adminer is one container, no config. CLAUDE.md mandates Adminer. |
| Multi-stage Dockerfile (build + runtime) | Single-stage | Multi-stage is ~50% smaller images and sets the pattern for Phase 4 worker container. Recommended even for Phase 0. |

**Installation:**

```bash
# API (apps/api/requirements.txt — full pinned list)
fastapi>=0.136,<0.137
uvicorn[standard]>=0.36,<1
sqlalchemy[asyncio]>=2.0.36,<2.1
asyncpg>=0.30,<0.32
alembic>=1.18,<2
pydantic>=2.9,<3
pydantic-settings>=2.5,<3
structlog>=25.1,<26
PyJWT>=2.9,<3
pwdlib[argon2]>=0.3,<1
python-multipart>=0.0.20,<1
greenlet>=3.0,<4

# Dev requirements (apps/api/requirements-dev.txt)
pytest>=8,<10
pytest-asyncio>=1.0,<2
anyio>=4.0,<5
asgi-lifespan>=2.1,<3
httpx>=0.27,<1
ruff>=0.15,<1
pyright>=1.1.400,<2
```

```bash
# Web (apps/web — produced by `pnpm create next-app@latest web --yes`, then `pnpm add` the rest)
pnpm create next-app@latest web --yes
cd web
pnpm add @tanstack/react-query@^5 zustand@^5 react-hook-form@^7 zod@^4 @hookform/resolvers@^5
pnpm dlx shadcn@latest init  # scaffolds components.json + updates globals.css
```

**Version verification:** All Python packages verified via `pip3 index versions <pkg>` on 2026-05-23 (the project's current date, mocking PyPI mirror). All Node packages verified via `npm view <pkg> version` on 2026-05-23. The Next.js install command was verified against the live nextjs.org installation page (lastUpdated: 2026-05-19, version: 16.2.6).

## Package Legitimacy Audit

> Verified via `slopcheck install <pkgs>` on 2026-05-23. slopcheck version 0.6.1.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| fastapi | PyPI | ~7 yrs | ~80M/mo | github.com/fastapi/fastapi | [OK] | Approved |
| uvicorn | PyPI | ~7 yrs | ~70M/mo | github.com/encode/uvicorn | [OK] | Approved |
| sqlalchemy | PyPI | ~18 yrs | ~150M/mo | github.com/sqlalchemy/sqlalchemy | [OK] | Approved |
| asyncpg | PyPI | ~9 yrs | ~10M/mo | github.com/MagicStack/asyncpg | [OK] | Approved |
| alembic | PyPI | ~14 yrs | ~40M/mo | github.com/sqlalchemy/alembic | [OK] | Approved |
| pydantic | PyPI | ~6 yrs | ~200M/mo | github.com/pydantic/pydantic | [OK] | Approved |
| pydantic-settings | PyPI | ~3 yrs | ~30M/mo | github.com/pydantic/pydantic-settings | [OK] | Approved |
| structlog | PyPI | ~12 yrs | ~15M/mo | github.com/hynek/structlog | [OK] | Approved |
| PyJWT | PyPI | ~14 yrs | ~80M/mo | github.com/jpadilla/pyjwt | [OK] | Approved |
| pwdlib | PyPI | ~2 yrs | small but growing | github.com/frankie567/pwdlib | [OK] | Approved (newer, but maintained by François Voron — FastAPI ecosystem author; explicitly recommended by FastAPI official tutorial) |
| python-multipart | PyPI | ~13 yrs | ~50M/mo | github.com/Kludex/python-multipart | [OK] | Approved (slopcheck note: "Name starts with 'python-' — classic LLM naming pattern. Name looks like LLM bait but package is established." — confirmed legitimate, used by FastAPI core) |
| greenlet | PyPI | ~14 yrs | ~80M/mo | github.com/python-greenlet/greenlet | [OK] | Approved |
| pytest | PyPI | ~17 yrs | ~250M/mo | github.com/pytest-dev/pytest | [OK] | Approved |
| pytest-asyncio | PyPI | ~10 yrs | ~50M/mo | github.com/pytest-dev/pytest-asyncio | [OK] | Approved |
| anyio | PyPI | ~7 yrs | ~150M/mo | github.com/agronholm/anyio | [OK] | Approved |
| asgi-lifespan | PyPI | ~6 yrs | ~3M/mo | github.com/florimondmanca/asgi-lifespan | [OK] | Approved |
| httpx | PyPI | ~7 yrs | ~100M/mo | github.com/encode/httpx | [OK] | Approved |
| ruff | PyPI | ~3 yrs | ~80M/mo | github.com/astral-sh/ruff | [OK] | Approved |
| pyright | PyPI | ~5 yrs | ~5M/mo | github.com/microsoft/pyright | [OK] | Approved |
| psycopg2-binary | PyPI | ~14 yrs | ~70M/mo | github.com/psycopg/psycopg2 | [OK] | Approved (optional — see §Alternatives) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

**Frontend packages** (slopcheck only audits PyPI by default; npm packages cross-verified via `npm view <pkg> version`, which confirmed all proposed packages exist on npm and have active maintenance. The packages listed in §Standard Stack — Core (Web) and Supporting (Web) are all well-known industry-standard libraries with multi-million weekly download counts and active GitHub repos. No suspicious or new packages proposed.)

## Architecture Patterns

### System Architecture Diagram

Phase 0 deploys a 4-container Docker Compose stack on the developer's local machine. Request flow for `/health`:

```
Browser ─▶ http://localhost:3000  (Next.js server-rendered placeholder page)
                │
                │ (RSC fetch on render)
                ▼
   http://api:8000/health  (Docker network)
                │
                │ FastAPI receives request
                ▼
   ┌─────────────────────────────────┐
   │  ASGI middleware (structlog)    │
   │  - bind request_id to ctxvars   │
   └──────────────┬──────────────────┘
                  │
                  ▼
   ┌─────────────────────────────────┐
   │  health/router.py               │
   │  - get session via Depends      │
   │  - execute SELECT 1             │
   │  - return JSON                  │
   └──────────────┬──────────────────┘
                  │
                  ▼  (asyncpg connection from pool)
   ┌─────────────────────────────────┐
   │  Postgres 16 (postgres:5432)    │
   │  - SELECT 1 (no RLS context     │
   │    needed; no domain tables)    │
   └─────────────────────────────────┘

Adminer (localhost:8080) connects to Postgres separately for dev inspection.

CI side-channel (.github/workflows/check.yml on every push):
   GitHub Actions ─▶ ubuntu-latest ─▶ ruff + pyright + pytest (api)
                                  ─▶ tsc + eslint (web)
```

### Recommended Project Structure

This is the **final tree** Phase 0 must produce (matches CLAUDE.md exactly):

```
ledgr/                                     # repo root
├── apps/
│   ├── web/                               # Next.js 16.2 (scaffolded by create-next-app)
│   │   ├── src/
│   │   │   └── app/
│   │   │       ├── layout.tsx             # root layout (default)
│   │   │       ├── page.tsx               # placeholder; fetches API /health
│   │   │       └── globals.css            # Tailwind 4 entry; updated by shadcn init
│   │   ├── public/                        # default Next.js folder
│   │   ├── components.json                # shadcn config (after init)
│   │   ├── eslint.config.mjs              # ESLint flat config
│   │   ├── next.config.ts                 # Next.js config
│   │   ├── package.json
│   │   ├── pnpm-lock.yaml
│   │   ├── postcss.config.mjs             # Tailwind 4 via PostCSS
│   │   ├── tsconfig.json                  # paths: @/* → src/*
│   │   ├── Dockerfile                     # multi-stage: deps → build → runner (node:22-alpine)
│   │   ├── .dockerignore
│   │   ├── .nvmrc                         # 22
│   │   └── .gitignore                     # Next.js default
│   └── api/                               # FastAPI app
│       ├── src/
│       │   ├── __init__.py
│       │   ├── main.py                    # FastAPI app + lifespan + middleware + router include
│       │   ├── config.py                  # Settings (pydantic-settings)
│       │   ├── database.py                # async engine + AsyncSessionLocal + get_session
│       │   ├── logging_config.py          # structlog setup + redactor + ASGI middleware
│       │   └── modules/
│       │       ├── __init__.py
│       │       └── health/
│       │           ├── __init__.py
│       │           └── router.py          # GET /health
│       ├── tests/
│       │   ├── __init__.py
│       │   ├── conftest.py                # async client + lifespan fixture
│       │   └── test_health.py             # asserts {status:"ok", db_connected:true}
│       ├── Dockerfile                     # multi-stage: builder → runtime (python:3.12-slim)
│       ├── .dockerignore
│       ├── .python-version                # 3.12
│       ├── requirements.txt
│       ├── requirements-dev.txt
│       └── pyproject.toml                 # ruff + pyright config ONLY (no build system)
├── packages/
│   ├── db/
│   │   ├── __init__.py
│   │   ├── alembic.ini                    # configures script_location, sqlalchemy.url from env
│   │   ├── models/
│   │   │   └── __init__.py                # DeclarativeBase only — no tables
│   │   └── migrations/
│   │       ├── env.py                     # async env.py from `alembic init -t async`
│   │       ├── script.py.mako
│   │       └── versions/
│   │           └── 0001_phase0_baseline.py # creates _phase0_marker table + RLS GUC comment
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── schemas.py                     # empty + module docstring
│   │   └── types.ts                       # empty + JSDoc header
│   └── domain/
│       └── __init__.py                    # empty + docstring
├── docker/
│   ├── docker-compose.yml                 # web + api + postgres + adminer
│   └── .env.example                       # also symlinked at root? — see decision below
├── docs/
│   ├── ARCHITECTURE.md                    # populated from .planning/research/ARCHITECTURE.md
│   ├── SCHEMA.md                          # placeholder with Phase 1 tables listed
│   ├── BACKLOG.md                         # placeholder; deferred items land here
│   ├── MIGRATIONS.md                      # nullable-first + CREATE INDEX CONCURRENTLY (INFRA-08)
│   └── adr/
│       └── 001-modular-monolith.md        # decision record
├── .github/
│   └── workflows/
│       └── check.yml                      # api job + web job; runs on push + PR
├── .env.example                           # root-level for `docker compose` to find
├── .gitignore                             # .env, __pycache__, .venv, node_modules, .next, .ruff_cache, .pytest_cache, .pyright_cache
├── .gitattributes                         # text=auto; lf endings
├── CLAUDE.md                              # already exists, will be updated by this phase to reflect locked stack
├── Makefile                               # dev | down | migrate | check | shell-api | shell-db
└── README.md                              # quickstart: clone → cp .env.example .env → make dev
```

**Decision: `.env.example` lives at the repo root.** Docker Compose looks for `.env` in the same directory as the `docker-compose.yml` by default, but we want `make dev` (run from repo root) to use a root `.env`. Set `env_file: ../.env` paths in `docker-compose.yml`, OR run compose with `docker compose --env-file .env -f docker/docker-compose.yml up`. Recommendation: put `.env.example` at the root, and have `Makefile` invoke `docker compose -f docker/docker-compose.yml --env-file .env up --build`. This is grep-able and matches user expectation.

### Pattern 1: FastAPI App + Lifespan + Async Engine + Settings

The canonical Phase 0 application bootstrap.

```python
# apps/api/src/config.py
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ENVIRONMENT: Literal["dev", "production", "test"] = "dev"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ALLOWED_ORIGINS: str = "http://localhost:3000"  # comma-separated; parse in main
    APP_VERSION: str = "0.1.0"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]   pyright sees all defaults; env supplies the rest
```

```python
# apps/api/src/database.py
# Source: fastapi.tiangolo.com/tutorial/sql-databases + ARCHITECTURE.md §Async SQLAlchemy
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from .config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)

async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

```python
# apps/api/src/main.py
# Source: fastapi.tiangolo.com/tutorial/bigger-applications + tutorial/cors
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import engine
from .logging_config import configure_logging, RequestContextMiddleware
from .modules.health.router import router as health_router

settings = get_settings()
configure_logging(environment=settings.ENVIRONMENT, level=settings.LOG_LEVEL)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()

app = FastAPI(
    title="PRANAV API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pure ASGI middleware — binds request_id to structlog contextvars
app.add_middleware(RequestContextMiddleware)

app.include_router(health_router, prefix="/health", tags=["health"])
```

**Note:** The `RequestContextMiddleware` must be an ASGI middleware (subclass `BaseHTTPMiddleware` is **not** safe for contextvars — verified via 2026 best-practice search). See structlog code example below.

### Pattern 2: `/health` Endpoint with Real DB Test

```python
# apps/api/src/modules/health/router.py
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_settings
from ...database import get_session

router = APIRouter()
settings = get_settings()

@router.get("")
async def get_health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str | bool]:
    try:
        result = await session.execute(text("SELECT 1"))
        db_connected = result.scalar_one() == 1
    except Exception:
        db_connected = False
    return {
        "status": "ok" if db_connected else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "db_connected": db_connected,
    }
```

### Pattern 3: structlog Configuration + Pure ASGI Middleware (INFRA-07)

```python
# apps/api/src/logging_config.py
import logging
import sys
import uuid
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from starlette.types import ASGIApp, Receive, Scope, Send

SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "access_token", "refresh_token", "api_key", "secret_key"}

def _redact_processor(logger, method_name, event_dict):
    """Drop or mask any key in SENSITIVE_KEYS at any nesting level."""
    def scrub(obj):
        if isinstance(obj, dict):
            return {k: ("***" if k.lower() in SENSITIVE_KEYS else scrub(v)) for k, v in obj.items()}
        if isinstance(obj, list):
            return [scrub(x) for x in obj]
        return obj
    return scrub(event_dict)

def configure_logging(environment: str, level: str) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        timestamper,
        _redact_processor,
    ]

    if environment == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

class RequestContextMiddleware:
    """Pure ASGI middleware — binds request_id to structlog contextvars.

    Why pure ASGI and not BaseHTTPMiddleware: BaseHTTPMiddleware creates a separate
    asyncio context copy, so contextvars bound in a downstream handler are not visible
    to log lines emitted at the middleware's "after" boundary. Pure ASGI runs in the
    same context — vars bound anywhere in the request lifecycle are visible everywhere.
    """
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        clear_contextvars()
        request_id = next(
            (v.decode() for k, v in scope.get("headers", []) if k == b"x-request-id"),
            uuid.uuid4().hex,
        )
        bind_contextvars(request_id=request_id)
        await self.app(scope, receive, send)
```

### Pattern 4: Alembic Async env.py + Phase 0 Baseline Migration (INFRA-04, INFRA-09)

```bash
# One-time bootstrap (planner runs this from packages/db/):
alembic init -t async migrations
# Then edit migrations/env.py per below
```

```python
# packages/db/migrations/env.py
# Adapted from alembic 1.18 official "async" template.
# Source: github.com/sqlalchemy/alembic/blob/main/alembic/templates/async/env.py
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

# Allow DATABASE_URL env var to override sqlalchemy.url in alembic.ini
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No models registered in Phase 0 — target_metadata = None.
# Phase 1+ will import the DeclarativeBase from packages/db/models and set target_metadata.
target_metadata = None

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    raise NotImplementedError("Offline mode not supported in Phase 0; use online mode")
else:
    run_migrations_online()
```

```python
# packages/db/migrations/versions/0001_phase0_baseline.py
"""Phase 0 baseline: marker table + RLS GUC convention reservation.

Revision ID: 0001_phase0_baseline
Revises:
Create Date: 2026-05-23

This migration does two things to prove Phase 0 infrastructure works:

1. Creates `_phase0_marker` — a single-row table that proves
   `make migrate` actually ran. Phase 1 will drop this when real tables arrive.

2. Reserves the `app.current_household_id` session GUC convention.
   Postgres custom GUCs with dotted names (`app.*`) have required NO registration
   since Postgres 9.2; this migration records the convention as a SQL COMMENT on
   the database so future contributors see it. Phase 1 will:
       a) enable ENABLE ROW LEVEL SECURITY on each domain table as it's created,
       b) attach policies like `USING (household_id = current_setting('app.current_household_id', true)::uuid)`,
       c) have FastAPI's `get_session` issue `SET LOCAL app.current_household_id = '<uuid>'`
          after auth resolves the household.

This migration intentionally does NOT enable RLS on any table or create any policy —
there are no domain tables yet. The "scaffold" here is the convention + marker.
"""
from alembic import op

revision = "0001_phase0_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE _phase0_marker (
            id SMALLINT PRIMARY KEY DEFAULT 1,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            note TEXT NOT NULL DEFAULT 'Phase 0 migration succeeded. RLS scaffolded; policies wired in Phase 1.',
            CONSTRAINT _phase0_marker_singleton CHECK (id = 1)
        );
        INSERT INTO _phase0_marker (id) VALUES (1);

        COMMENT ON DATABASE """ + _current_db() + """ IS 'PRANAV: RLS GUC convention = app.current_household_id (set via SET LOCAL per session; read via current_setting(''app.current_household_id'', true)). Policies attached in Phase 1.';
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS _phase0_marker")
    # Note: we do not undo the database COMMENT — it's documentation, not state.

def _current_db() -> str:
    """Return the current database name as a SQL-quoted identifier.

    We can't use bind params in a COMMENT ON statement, so we have to interpolate.
    The Alembic context's connection knows the database name.
    """
    from alembic import context
    bind = context.get_bind()
    name = bind.engine.url.database or "postgres"
    # quote identifier
    return '"' + name.replace('"', '""') + '"'
```

> **Note on the COMMENT-on-database trick**: This is a single-line documentation hack. The migration prints the convention into the DB's catalog. If the planner prefers a cleaner alternative, the migration can simply `op.execute("-- RLS convention: app.current_household_id")` as a no-op (the comment shows up in `alembic history --verbose` and in the migration file itself, but won't survive into the DB catalog). Either works. The marker table is the load-bearing part for INFRA-04.

### Pattern 5: pytest async test with lifespan + httpx AsyncClient (INFRA-03)

```python
# apps/api/tests/conftest.py
# Source: fastapi.tiangolo.com/advanced/async-tests
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.main import app

@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"

@pytest.fixture
async def client():
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
```

```python
# apps/api/tests/test_health.py
import pytest

@pytest.mark.anyio
async def test_health_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db_connected"] is True
    assert body["environment"] in {"dev", "production", "test"}
    assert "version" in body
```

### Pattern 6: Docker Compose

```yaml
# docker/docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-pranav}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-pranav_dev_password}
      POSTGRES_DB: ${POSTGRES_DB:-pranav}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-pranav}"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ..
      dockerfile: apps/api/Dockerfile
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-pranav}:${POSTGRES_PASSWORD:-pranav_dev_password}@postgres:5432/${POSTGRES_DB:-pranav}
      SECRET_KEY: ${SECRET_KEY:-change-me-in-prod}
      ENVIRONMENT: ${ENVIRONMENT:-dev}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      ALLOWED_ORIGINS: ${ALLOWED_ORIGINS:-http://localhost:3000}
    ports:
      - "8000:8000"
    volumes:
      - ../apps/api:/app/apps/api
      - ../packages:/app/packages
    command: ["uvicorn", "apps.api.src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

  web:
    build:
      context: ..
      dockerfile: apps/web/Dockerfile
    restart: unless-stopped
    depends_on:
      - api
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}
      API_URL_INTERNAL: http://api:8000  # used by server components for SSR fetches
    ports:
      - "3000:3000"
    volumes:
      - ../apps/web:/app
      - /app/node_modules
      - /app/.next

  adminer:
    image: adminer:latest
    restart: unless-stopped
    depends_on:
      - postgres
    ports:
      - "8080:8080"
    environment:
      ADMINER_DEFAULT_SERVER: postgres

volumes:
  postgres_data:
```

### Pattern 7: Dockerfiles

```dockerfile
# apps/api/Dockerfile — multi-stage
FROM python:3.12-slim AS builder
WORKDIR /build
COPY apps/api/requirements.txt apps/api/requirements-dev.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt -r requirements-dev.txt

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH=/root/.local/bin:$PATH
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY apps/api /app/apps/api
COPY packages /app/packages
EXPOSE 8000
CMD ["uvicorn", "apps.api.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# apps/web/Dockerfile — multi-stage, per Next.js standalone output guidance
FROM node:22-alpine AS deps
WORKDIR /app
RUN corepack enable pnpm
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:22-alpine AS builder
WORKDIR /app
RUN corepack enable pnpm
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web ./
RUN pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN corepack enable pnpm
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["pnpm", "start"]
```

> **Web Dockerfile caveat:** Next.js 16 with Turbopack supports `output: "standalone"` in `next.config.ts` for a smaller runtime image (only what's needed). Recommended for Phase 0; falls back to copying full `node_modules` if standalone has issues with the placeholder. Decision: planner picks; documented in `apps/web/Dockerfile` comment either way.

### Pattern 8: Makefile (INFRA-01, INFRA-03, INFRA-04)

```makefile
# Makefile (repo root)
.PHONY: dev down migrate check shell-api shell-db

COMPOSE := docker compose -f docker/docker-compose.yml --env-file .env

dev:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) exec api alembic -c packages/db/alembic.ini upgrade head

check: check-api check-web

check-api:
	cd apps/api && ruff check . && ruff format --check . && pyright && pytest

check-web:
	cd apps/web && pnpm tsc --noEmit && pnpm lint

shell-api:
	$(COMPOSE) exec api bash

shell-db:
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-pranav} -d $${POSTGRES_DB:-pranav}
```

### Pattern 9: `.env.example`

```bash
# .env.example — copy to .env and customize for local dev
# NEVER COMMIT .env

# --- Postgres ---
POSTGRES_USER=pranav
POSTGRES_PASSWORD=pranav_dev_password
POSTGRES_DB=pranav

# --- API ---
# DATABASE_URL is constructed from POSTGRES_* above when run via docker compose.
# For native dev (no docker), set it explicitly:
# DATABASE_URL=postgresql+asyncpg://pranav:pranav_dev_password@localhost:5432/pranav
SECRET_KEY=change-me-in-prod-use-openssl-rand-hex-32
ENVIRONMENT=dev
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000

# --- Web ---
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Pattern 10: CI workflow

```yaml
# .github/workflows/check.yml
name: check
on:
  push:
    branches: [main]
  pull_request:

jobs:
  api:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: pranav
          POSTGRES_PASSWORD: pranav_dev_password
          POSTGRES_DB: pranav_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+asyncpg://pranav:pranav_dev_password@localhost:5432/pranav_test
      SECRET_KEY: ci-secret-do-not-use-in-prod
      ENVIRONMENT: test
      LOG_LEVEL: INFO
      ALLOWED_ORIGINS: http://localhost:3000
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install -r apps/api/requirements.txt -r apps/api/requirements-dev.txt
      - run: cd apps/api && ruff check . && ruff format --check . && pyright && pytest

  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "pnpm"
          cache-dependency-path: apps/web/pnpm-lock.yaml
      - run: cd apps/web && pnpm install --frozen-lockfile
      - run: cd apps/web && pnpm tsc --noEmit && pnpm lint
```

### Pattern 11: Web placeholder page that fetches API /health (server component)

```tsx
// apps/web/src/app/page.tsx
async function getHealth() {
  // In Docker, the web container reaches the api by service name.
  // For local dev outside Docker, NEXT_PUBLIC_API_URL points to localhost:8000.
  const url = (process.env.API_URL_INTERNAL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/health";
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json() as { status: string; version: string; environment: string; db_connected: boolean };
  } catch {
    return null;
  }
}

export default async function Page() {
  const health = await getHealth();
  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-md w-full text-center space-y-4">
        <h1 className="text-3xl font-bold">Personal Resource &amp; Asset Navigator for Abundant Value</h1>
        <p className="text-sm opacity-70">Coming soon.</p>
        <div className="mt-8 p-4 border rounded text-left text-sm font-mono">
          {health ? (
            <pre>{JSON.stringify(health, null, 2)}</pre>
          ) : (
            <span className="opacity-70">API unavailable</span>
          )}
        </div>
      </div>
    </main>
  );
}
```

### Anti-Patterns to Avoid

- **`@app.middleware("http")` decorator (BaseHTTPMiddleware) for request_id binding** — breaks structlog contextvars across the request scope. Use pure ASGI middleware.
- **`TestClient` from `fastapi.testclient` in async tests** — official FastAPI docs say it doesn't work in async tests; use `httpx.AsyncClient` + `ASGITransport` + `LifespanManager`.
- **`SQLModel`** — fuses Pydantic with SQLAlchemy; violates CLAUDE.md's separation of `packages/shared/schemas.py` (Pydantic) from `packages/db/models/` (SQLAlchemy).
- **`expire_on_commit=True` on the async sessionmaker** — surprising async re-loads; always `expire_on_commit=False`.
- **Sync `psycopg2` in the application path** — fine as a transitive concern in some tooling, but the application engine must be `postgresql+asyncpg://`.
- **Lazy relationships (`lazy="select"`) in async sessions** — silently fail or trigger I/O outside the session scope. Use `selectinload`/`joinedload` explicitly when relationships matter (no relationships in Phase 0).
- **Adding `procrastinate` to Phase 0 requirements.txt** — explicitly deferred per STACK.md §2.2 to Phase 4. Resist the urge.
- **Adding Redis to docker-compose** — STACK.md anti-recommendation; the whole point of procrastinate is avoiding Redis.
- **Static `version: "3.8"` line in docker-compose.yml** — deprecated in Compose v2; omit the version key entirely.
- **`tailwind.config.ts` in a Tailwind v4 project** — v4 is CSS-config-first; `components.json`'s `tailwind.config` field stays empty. Don't generate a v3-style config file.
- **Running Alembic from `apps/api/` root** — Alembic lives in `packages/db/`, run from there (or via `alembic -c packages/db/alembic.ini`).
- **Trusting `dependabot` / Renovate to bump Next.js 16 → 17 silently** — Next major versions are breaking; Phase 0 should pin `next: "^16.2.6"` (caret allows 16.x patches but not 17). Same for Python deps via the `<X` upper bound pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async DB session per-request | Custom session middleware | `Depends(get_session)` with `async_sessionmaker` and `expire_on_commit=False` | The pattern is one function; rolling your own breaks transaction handling. |
| Schema migration discipline | Custom SQL files with version table | Alembic 1.18 async template (`alembic init -t async`) | Alembic handles ordering, downgrades, autogenerate, and async drivers correctly. |
| Structured logging | Bespoke JSON formatter + threadlocal request IDs | structlog 25.x + contextvars + pure-ASGI middleware | structlog handles processor pipelines, dev console vs prod JSON, and contextvars correctly; rolling your own breaks under asyncio. |
| Request ID propagation | Custom `request.state` plumbing | `structlog.contextvars.bind_contextvars` + `merge_contextvars` processor | contextvars are async-safe and survive across awaits within a request scope. |
| CORS | Bespoke header logic | `fastapi.middleware.cors.CORSMiddleware` | Official FastAPI tutorial; handles preflight correctly. |
| Loading config from env | `os.environ.get(...)` everywhere | `pydantic-settings.BaseSettings` with typed fields | Type-safe, validated, dotenv-aware. |
| `.env` parsing | Custom dotenv loader | `pydantic-settings` (uses python-dotenv under the hood) | Standard, no surprises. |
| Async testing client | Spinning up uvicorn + real HTTP in tests | `httpx.AsyncClient` + `ASGITransport` + `LifespanManager` | Tests run in-process; no socket. |
| Tailwind/PostCSS plumbing | Hand-write `postcss.config.mjs` | `pnpm create next-app@latest --yes` defaults | The defaults install everything correctly; manual config is a re-invention. |
| Linter setup for monorepo | Custom flake8/black/isort matrix | `ruff` (lint + format in one tool) + `pyright` | Ruff alone replaces 5-6 tools; pyright handles types. |
| Health-check shape | Custom JSON | Match Kubernetes liveness probe convention: `{status, version, environment, db_connected}` | Maps cleanly to k8s `livenessProbe`/`readinessProbe` later. |
| RLS GUC management | A separate Python config table | Postgres native `current_setting('app.current_household_id', true)` + `SET LOCAL` per session | Postgres handles GUCs free of charge since 9.2 (no registration). |

**Key insight:** Phase 0 is heavily prescriptive specifically because the cost of getting any of these wrong is paid in *every* future phase. The async session pattern, the Alembic env.py, and the structlog middleware are written once and copied verbatim into every later phase that touches DB or logs.

## Runtime State Inventory

> Phase 0 is greenfield (no prior code exists in the repo — verified via `ls /Users/pranavlodha/Documents/ledgr/` showing only `CLAUDE.md`, `ROADMAP.md`, `.planning/`, `.git/`, `.claude/`). **No runtime state inventory required** — there is no existing code, no databases, no services, no secrets, no build artifacts to consider. This section is included to satisfy the research template but the answer is "nothing — first-phase greenfield."

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified by `ls` of repo root showing no databases/data dirs | none |
| Live service config | None — no running services exist | none |
| OS-registered state | None — no daemons/scheduled tasks registered for this project | none |
| Secrets/env vars | None — no `.env` exists yet; `.env.example` is created in this phase | none |
| Build artifacts | None — verified by absence of `node_modules`, `.next`, `__pycache__`, `.venv`, `dist/` in `ls -la` of repo root | none |

## Common Pitfalls

### Pitfall 1: Async Alembic env.py used with sync DBAPI URL (asyncpg DSN mismatch)

**What goes wrong:** Developer copies a "normal" Alembic env.py snippet expecting `postgresql://` URLs; `asyncpg` requires `postgresql+asyncpg://`. Migration fails with `InvalidRequestError`.
**Why it happens:** Alembic's default template uses sync engine; the async template uses `async_engine_from_config` but the URL still needs the `+asyncpg` driver suffix.
**How to avoid:** Set `DATABASE_URL=postgresql+asyncpg://...` in `.env.example` (already done in §Pattern 9). The Alembic env.py reads `DATABASE_URL` from env, so the same URL is used by app AND migrations.
**Warning signs:** `pg8000` or default-driver errors during `make migrate`; `RuntimeError: cannot run async code...` if env.py is the sync template by accident.

### Pitfall 2: `make migrate` runs before Postgres is ready

**What goes wrong:** `make dev` starts containers; user runs `make migrate` immediately; Alembic connects before Postgres finishes its first-time-init. Connection refused.
**Why it happens:** Postgres takes 5-15s to come up first time; depends_on with `condition: service_healthy` only governs container start order, not migrate order.
**How to avoid:** docker-compose.yml uses a Postgres `healthcheck` (already included in §Pattern 6). Document that `make migrate` is a separate step after `make dev` and should be run only once Postgres logs show "ready to accept connections". Alternative: bake `alembic upgrade head` into the api container's entrypoint (commented out in Phase 0; revisited at v1.0 ship per PITFALLS.md O2).
**Warning signs:** `OperationalError: connection refused` from asyncpg when `make migrate` runs immediately after `make dev`.

### Pitfall 3: Structured logging breaks contextvars when BaseHTTPMiddleware is used

**What goes wrong:** Developer writes `@app.middleware("http")` to bind request_id; downstream handler bound vars are not visible to the middleware's "after" boundary log lines. Some log lines have request_id; others don't.
**Why it happens:** BaseHTTPMiddleware creates a separate asyncio context copy. Contextvars don't propagate back across that boundary.
**How to avoid:** Use pure ASGI middleware (subclass-less class with `__call__(scope, receive, send)`). See §Pattern 3.
**Warning signs:** Inconsistent presence of `request_id` field in JSON log output; some lines correlated, others orphaned.

### Pitfall 4: Tailwind v4 setup vs v3 muscle memory (no `tailwind.config.ts`)

**What goes wrong:** Developer (or LLM) follows a 2024 Tailwind v3 tutorial: creates `tailwind.config.ts`, points it at `content: ["./src/**/*"]`, expects shadcn/ui to consume it. v4 ignores that file; CSS doesn't load.
**Why it happens:** v4's CSS-based config (`@theme` in `globals.css`) replaces JS config; `create-next-app --yes` correctly omits `tailwind.config.ts`.
**How to avoid:** Do NOT add `tailwind.config.ts`. Edit `globals.css` for any theme tokens. `components.json` from `shadcn init` has `tailwind.config: ""` (empty string) — verified in 2026 docs.
**Warning signs:** A `tailwind.config.ts` appears in `apps/web/` during scaffolding; `pnpm dlx shadcn@latest init` prompts about a "config path" — leave it blank.

### Pitfall 5: Forgetting `asgi-lifespan` in tests — DB engine is None

**What goes wrong:** First pytest run: `AttributeError: 'NoneType' object has no attribute 'connect'` because the lifespan that creates the engine never ran.
**Why it happens:** httpx `AsyncClient` does not trigger ASGI lifespan events. Without `LifespanManager(app)` wrapping, startup/shutdown handlers don't fire.
**How to avoid:** Always wrap tests in `LifespanManager(app)` (see §Pattern 5). The dependency is explicitly required.
**Warning signs:** `engine` is `None`; `await session.execute(text("SELECT 1"))` raises `RuntimeError: 'Connection' has not been initialized`.

### Pitfall 6: Procrastinate scoped-creep into Phase 0

**What goes wrong:** Researcher reads "we need procrastinate" in STACK.md and adds it to `requirements.txt` "for forward-compat". Phase 0 ships with an unused dependency. Self-hoster sees procrastinate logs about missing tables and worries.
**Why it happens:** STACK.md mentions procrastinate as a locked decision; easy to confuse "decided" with "installed in phase 0".
**How to avoid:** STACK.md §2.2 explicitly says "Phases 0–8 don't need a job queue at all — keep it out of `docker-compose.yml` and `requirements.txt` until Phase 9." (Note: roadmap moved jobs forward to Phase 4 for CSV imports; same principle — Phase 0 OMITS it.) The planner must explicitly check that procrastinate does NOT appear in `apps/api/requirements.txt`.
**Warning signs:** `procrastinate` in `requirements.txt`; a `apps/worker/` directory appearing in Phase 0.

### Pitfall 7: Adminer port collision with other devs' local stack

**What goes wrong:** Adminer's `8080` collides with Tomcat, Jenkins, or another dev tool the user runs on `8080`.
**Why it happens:** `8080` is a default for many tools.
**How to avoid:** Use `ADMINER_PORT` env var with default `8080` in docker-compose, document fallback in README ("if 8080 is in use, set `ADMINER_PORT=8081` in `.env`"). Not blocking — but a kindness.
**Warning signs:** `make dev` errors with "port already allocated".

### Pitfall 8: `.env` committed by accident on first install

**What goes wrong:** Self-hoster (or future contributor) copies `.env.example` to `.env`, edits it, runs `git add .`, commits `.env` with real secrets.
**Why it happens:** `.env` not in `.gitignore`.
**How to avoid:** `.gitignore` MUST include `.env` from Phase 0 (it's the first thing planner should add). Optionally add a pre-commit hook (PITFALLS.md O9) — deferred to v1.0 ship.
**Warning signs:** `.env` shows in `git status`.

### Pitfall 9: Postgres custom GUC syntax — readers vs writers

**What goes wrong:** Developer writes `SELECT current_setting('app.current_household_id')` (without the second arg); when the GUC is unset, Postgres raises `unrecognized configuration parameter "app.current_household_id"`. The query fails instead of returning NULL.
**Why it happens:** `current_setting(name)` is strict; `current_setting(name, missing_ok=true)` returns NULL when unset.
**How to avoid:** Document the convention in `docs/MIGRATIONS.md`: **always use** `current_setting('app.current_household_id', true)::uuid` in policies. The `true` second arg is non-negotiable. Phase 1's RLS policy migrations must follow this.
**Warning signs:** A Phase 1 RLS policy migration that omits the `, true` argument.

### Pitfall 10: `make check` passes locally, fails in CI (Python version drift)

**What goes wrong:** Developer has Python 3.13 locally; CI uses 3.12; subtle stdlib differences cause type-check failures.
**Why it happens:** No version pinning in development setup.
**How to avoid:** `apps/api/.python-version` set to `3.12`; CI workflow uses `python-version: "3.12"`; Dockerfile uses `python:3.12-slim`. All three must align.
**Warning signs:** pyright or pytest passing locally but failing in CI.

### Pitfall 11: shadcn/ui init runs before Tailwind classes work

**What goes wrong:** `pnpm dlx shadcn@latest init` runs against a fresh `create-next-app` directory but Tailwind hasn't been verified to compile yet. shadcn writes its CSS variables to `globals.css` and the dev server breaks.
**Why it happens:** Ordering — shadcn assumes Tailwind already works.
**How to avoid:** After `pnpm create next-app@latest`, run `pnpm dev` and verify Tailwind classes render (the default page has utility classes — visually confirm) BEFORE running `shadcn init`.
**Warning signs:** First load of `localhost:3000` shows unstyled HTML.

## Code Examples

All code examples have been inlined in §Architecture Patterns above (Patterns 1-11). They are the canonical Phase 0 templates and should be copied verbatim (or with minimal edits) into the plan's tasks.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `passlib[bcrypt]` for password hashing | `pwdlib[argon2]` | FastAPI tutorial updated in 2024 | Phase 1 install spec — Phase 0 just installs the package. |
| `python-jose` for JWT | `PyJWT>=2.9` | FastAPI tutorial updated in 2024 | Same — install in Phase 0, use in Phase 1. |
| Next.js Pages Router | App Router (RSC + Server Actions) | Next.js 13 (2022), default since 14 | Phase 0 uses App Router. |
| Tailwind 3 with `tailwind.config.ts` | Tailwind 4 with `@theme` in CSS | Tailwind 4 GA early 2025 | Phase 0 uses Tailwind 4; no JS config file. |
| Webpack | Turbopack (default in Next 16) | Next.js 16 (Oct 2025) | Phase 0 takes the default; `--webpack` flag available. |
| BaseHTTPMiddleware for context binding | Pure ASGI middleware | Best practice solidified by 2026 | Phase 0 uses pure ASGI middleware for structlog. |
| `next lint` command | `eslint` CLI direct via package.json scripts | Next.js 16 deprecated `next lint` | Phase 0 uses `pnpm lint` → `eslint` directly. |
| `tailwind.config` field in `components.json` non-empty | Empty string for Tailwind 4 | shadcn updated for Tailwind 4 | Phase 0 init produces `components.json` with `"config": ""`. |
| SQLAlchemy 1.x ORM style | 2.0 select() + AsyncSession | SQLAlchemy 2.0 GA May 2023 | Phase 0 uses 2.0 idioms. |
| docker-compose `version: "3.x"` | (omit version key) | Compose v2 deprecated it | Phase 0 omits the `version` field. |
| Celery / ARQ for jobs | procrastinate (Postgres-native) | Project decision per STACK.md | NOT Phase 0; Phase 4. |

**Deprecated/outdated to avoid:**
- `setup.py` / `setup.cfg` build systems — use `pyproject.toml` (only for tool config in Phase 0; no build needed).
- `tailwind.config.ts` in new Tailwind 4 projects.
- `next/legacy/image` — use `next/image`.
- `getServerSideProps` / `getStaticProps` — App Router uses async server components.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The phase-0 migration's `COMMENT ON DATABASE` trick is the cleanest way to document the RLS GUC convention; the alternative is a `_phase0_marker` table comment | Pattern 4 | Low — both work; cosmetic only. Planner can pick. |
| A2 | `ENVIRONMENT` is the env var name (not `ENV` or `APP_ENV`) | Pattern 1, Pattern 9 | Low — convention choice; planner can rename. |
| A3 | `make migrate` is a separate step after `make dev`, NOT baked into the api container's entrypoint | Pattern 8, Pitfall 2 | Medium — alternative is entrypoint runs `alembic upgrade head` then exec uvicorn. Some self-hosters expect that. PITFALLS.md O2 recommends documenting the upgrade flow explicitly; both designs are defensible. Recommendation: keep separate in Phase 0 (one less moving part to debug); revisit at v1.0 ship. |
| A4 | The web container uses bind mounts for hot reload in dev (per Pattern 6) | Pattern 6 | Low — works on macOS/Linux; Windows users may have perf issues. Document fallback in README. |
| A5 | `POSTGRES_DB=pranav` (not `finbrain` per CLAUDE.md's legacy spec) | Pattern 6, Pattern 9 | Medium — CLAUDE.md mentions `finbrain` as the DB name in `make shell-db`. Recommendation: use `pranav` to match the project rename (PROJECT.md updated 2026-05-23); update CLAUDE.md's `make shell-db` example as part of Phase 0. |
| A6 | shadcn/ui init produces a `components.json` with `tailwind.config: ""` and `cssVariables: true` | Pattern 7 (mentioned in §Standard Stack notes) | Low — verified via shadcn/Tailwind 4 docs, but if `shadcn init` prompt format has changed, accept whatever it generates. |
| A7 | Pure ASGI middleware (not BaseHTTPMiddleware) is the correct pattern for structlog request_id binding | Pattern 3, Anti-pattern, Pitfall 3 | Low — strong consensus in 2026 best practices and is the official recommendation. |
| A8 | We install `psycopg2-binary` only IF Alembic raises a sync-context error; otherwise omit | Standard Stack alternatives | Low — Alembic async template + asyncpg should not need psycopg2; if it does, add then. |
| A9 | Phase 0 does NOT enable RLS on any specific table; the migration only reserves the GUC convention via comment + marker table | Pattern 4, INFRA-09 | Medium — INFRA-09 says "enabled at the cluster level"; "cluster level" in PG terminology usually refers to features like `wal_level`, not RLS. There's no Postgres command to "enable RLS at the cluster level" — RLS is a per-table feature. Recommendation: the planner asks the user (via /gsd-discuss-phase) whether INFRA-09 means (a) reserve the GUC convention with no policies (this research's interpretation), or (b) enable RLS on a single placeholder table to prove the mechanism works end-to-end. Both are defensible; the requirements wording is ambiguous. **This is the single deferred-decision worth surfacing to the user.** |
| A10 | `version: "0.1.0"` for the app starting value | Pattern 1 | Low — convention; planner can pick. |
| A11 | Adminer image is `adminer:latest` (no tag pin) | Pattern 6 | Low — Adminer is stable; recommendation accepts `latest` for a dev-only tool. |
| A12 | The `recharts` version in STACK.md (`>=2.13,<3`) is stale; v3 is current | Supporting (Web) | Low — Phase 0 does NOT install recharts; flag for Phase 8. |
| A13 | `nyquist_validation` is enabled (it's `true` in `.planning/config.json`) — Validation Architecture section required | config.json | none — already verified |
| A14 | `security_enforcement` is enabled (it's `true` in `.planning/config.json`) — Security Domain section required | config.json | none — already verified |

## Open Questions

1. **INFRA-09 wording: "Postgres RLS is enabled at the cluster level"** — Postgres has no "cluster-level RLS enable" — RLS is per-table. Two possible interpretations:
   - (a) Reserve the `app.current_household_id` GUC convention now; no RLS-enabled tables in Phase 0; Phase 1 will `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` per domain table.
   - (b) Create a single throwaway/placeholder table in Phase 0 with RLS enabled to end-to-end prove the pattern works, and Phase 1 drops it once real tables exist.
   - **What we know:** PITFALLS.md C3 and ARCHITECTURE.md §Multi-tenancy describe RLS as a per-table feature. STATE.md says "RLS scaffolded in Phase 0, activated in Phase 1".
   - **What's unclear:** Whether "scaffolded" means (a) or (b).
   - **Recommendation:** Surface to user via /gsd-discuss-phase. Default to (a) unless user wants the demo from (b). Either way, the marker table in §Pattern 4 proves migrations work; that requirement is satisfied.

2. **Does the planner ship a "make backup" target in Phase 0?**
   - **What we know:** PITFALLS.md O6 lists this under Phase 0 work; phase 0 success criteria (INFRA-01–09) do NOT mention it.
   - **What's unclear:** Whether the user wants infrastructure overhead now for a v1.0-ship concern.
   - **Recommendation:** OMIT from Phase 0; document in `docs/BACKLOG.md` as a v1.0-ship item. If user disagrees in /gsd-discuss-phase, add a 3-line target.

3. **Does the api container's entrypoint run `alembic upgrade head` automatically?**
   - See assumption A3.
   - **Recommendation:** Keep separate (`make migrate` is its own step). Document explicitly in README.

4. **What about `import-linter` for cross-module boundary enforcement?**
   - **What we know:** CLAUDE.md says "no cross-module internal imports" — needs enforcement.
   - **What's unclear:** Whether to install `import-linter` in Phase 0 (no modules to lint yet) or wait until Phase 3+ (when 2nd module arrives).
   - **Recommendation:** Defer to Phase 1 (when `auth/` and `households/` arrive). Add a stub `.importlinter` config file to Phase 0 as a no-op marker if desired.

5. **Pre-commit hooks (ruff format, ruff check, prettier, secret scan)?**
   - **What we know:** PITFALLS.md O9 mentions pre-commit hooks for secret scanning.
   - **What's unclear:** Whether to set up `pre-commit` framework in Phase 0.
   - **Recommendation:** Defer to milestone close unless explicit.

6. **CLAUDE.md updates needed in Phase 0?**
   - The CLAUDE.md in the repo currently says (in places) "Next.js 14" — STATE.md confirms it was already updated to 16.2+ in the .planning research. Need to verify CLAUDE.md is consistent.
   - Also: `make shell-db` example uses `finbrain` as the DB name; should be `pranav`.
   - **Recommendation:** Phase 0 plan includes one task to audit CLAUDE.md against STACK.md and patch any stale references.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker (engine) | INFRA-01, all Compose orchestration | ✓ | 29.0.1 (verified `docker --version`) | none — required |
| Docker Compose v2 | INFRA-01, `make dev` | ✓ | bundled with Docker 29 | none — required |
| Node.js | Web build (host-side build before `make dev`, and for `make check-web`) | ✓ | v23.3.0 (verified `node --version`) | Use `node:22-alpine` in container; host version only matters if running outside Docker. **Risk: Next 16 requires Node 20.9+; host has 23.3.0 which is newer than the docker image's 22 — both are >= 20.9, so OK.** |
| pnpm | Web package management | ✗ | — | Install via `corepack enable pnpm` (Node 16.10+ ships corepack); docs MUST include a "install pnpm" step. |
| Python | API host-side dev (Optional — Docker handles container Python) | ✓ | 3.13.7 (verified `python3 --version`) | Docker uses `python:3.12-slim`; host version only matters for editor tools. **Risk: host is 3.13; if developer runs ruff/pyright outside container they may see different behavior. Recommend `make check` always runs inside Docker for reproducibility.** |
| pip | Python dep install during Docker build | ✓ | 25.2 (verified `pip3 --version`) | bundled with Python image |
| psql client | `make shell-db` | ✗ | — | Runs inside `postgres` container; `make shell-db` execs into the container; no host install needed. |
| GitHub CLI (`gh`) | CI workflow setup (optional) | not checked | — | not required for Phase 0 success criteria |
| `make` | `make dev`, `make check`, etc. | not explicitly checked — assumed present on macOS and Linux dev machines | — | none — required; standard on Unix. Windows users use WSL2. |
| `git` | `git clone` (INFRA-01 success criteria literally) | ✓ (repo exists at this path) | — | none — required |

**Missing dependencies with no fallback:**
- pnpm (host side) — but installable via one command (`corepack enable`); document explicitly in README.

**Missing dependencies with fallback:**
- None blocking.

## Validation Architecture

> nyquist_validation is `true` in `.planning/config.json`. This section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework (api) | pytest 9.x + pytest-asyncio 1.3 + anyio 4.13 + httpx 0.28 + asgi-lifespan 2.1 |
| Framework (web) | tsc --noEmit + eslint flat config (no unit test framework in Phase 0 — defer Vitest/Playwright to first phase that ships UI logic, likely Phase 1) |
| Config file (api) | `apps/api/pyproject.toml` (tool.pytest.ini_options section + tool.ruff + tool.pyright) — created in Phase 0 Wave 0 |
| Config file (web) | `apps/web/tsconfig.json` + `apps/web/eslint.config.mjs` — generated by `create-next-app --yes` |
| Quick run command (api) | `cd apps/api && pytest tests/test_health.py -x` |
| Quick run command (web) | `cd apps/web && pnpm tsc --noEmit && pnpm lint` |
| Full suite command | `make check` (runs both api and web pipelines) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | All four containers start cleanly | manual-smoke | `make dev` then `docker compose ps` shows 4 running services | ❌ Wave 0 — Makefile + docker-compose.yml |
| INFRA-02 | `/health` returns `{status, version, environment, db_connected}` with real SELECT 1 | integration | `pytest apps/api/tests/test_health.py -x` (uses LifespanManager + AsyncClient against the in-process app + real Postgres via service container in CI; in local dev, against the Docker Postgres) | ❌ Wave 0 — `apps/api/tests/test_health.py` |
| INFRA-03 | `make check` exits 0 | gate | `make check` | ❌ Wave 0 — Makefile target + at least one passing test in each language |
| INFRA-04 | `make migrate` applies the baseline migration; marker row exists | integration | `pytest apps/api/tests/test_health.py::test_baseline_migration_applied` (queries `_phase0_marker`) | ❌ Wave 0 — extend test file with marker query |
| INFRA-05 | Adminer reachable at localhost:8080 and can connect to postgres | manual-smoke | Visit http://localhost:8080, log in with `Server: postgres`, `User: pranav`, `Password: pranav_dev_password`, `Database: pranav` | manual — no automated test (UI side-channel) |
| INFRA-06 | `.env.example` lists all required vars | static | `pytest apps/api/tests/test_env_example.py` (parses `.env.example`, asserts known keys present) | ❌ Wave 0 — optional; one-line script could also assert by grep in CI |
| INFRA-07 | structlog emits JSON in production env and contextvars carry request_id | unit | `pytest apps/api/tests/test_logging.py` (captures a log via structlog testing harness, asserts JSON shape includes request_id key) | ❌ Wave 0 — `apps/api/tests/test_logging.py` |
| INFRA-08 | MIGRATIONS.md exists and mentions "nullable-first" + "CREATE INDEX CONCURRENTLY" | static | `grep -E "nullable-first" docs/MIGRATIONS.md && grep -E "CREATE INDEX CONCURRENTLY" docs/MIGRATIONS.md` | ❌ Wave 0 — file creation |
| INFRA-09 | Migration runs that proves DB connectivity + RLS GUC convention documented | integration | `pytest apps/api/tests/test_health.py::test_baseline_migration_applied` + `grep -E "current_setting\\('app.current_household_id'" docs/MIGRATIONS.md` | ❌ Wave 0 — file creation + test |

### Sampling Rate

- **Per task commit:** `make check-api` (api lints + tests) or `make check-web` (web typecheck + lint) — depending on which side was edited. Each is <15s.
- **Per wave merge:** `make check` (both pipelines). <60s.
- **Phase gate:** `make check` green AND `make dev` then `curl localhost:8000/health` shows `db_connected: true` AND `make migrate` returns 0 AND visit localhost:8080 to confirm Adminer. Documented in PHASE-VERIFICATION.md if `/gsd-verify-work` is run.

### Wave 0 Gaps

- [ ] `apps/api/pyproject.toml` — ruff config + pyright config + pytest config. Required before any api code can be linted.
- [ ] `apps/api/tests/conftest.py` — async client fixture + lifespan manager. Required for every test.
- [ ] `apps/api/tests/test_health.py` — covers INFRA-02, INFRA-04, INFRA-09 (db_connected, marker row, GUC convention by virtue of migration applied).
- [ ] `apps/api/tests/test_logging.py` — covers INFRA-07 (JSON renderer in prod, request_id field in contextvars).
- [ ] `apps/api/.python-version` — pins 3.12 for editor tooling.
- [ ] `apps/web/Dockerfile` and `apps/web/.nvmrc` (22) — pin Node for editor tooling.
- [ ] `.github/workflows/check.yml` — runs both pipelines on push/PR.
- [ ] `docs/MIGRATIONS.md` — documents nullable-first + CONCURRENTLY discipline (also serves INFRA-08 grep test).
- [ ] No framework install needed for api (`pytest` etc. in `requirements-dev.txt`).
- [ ] Web: no unit-test framework added in Phase 0 (Vitest deferred to Phase 1 minimum). `tsc --noEmit` + `eslint` is the test gate. Document explicitly in `docs/BACKLOG.md` "add Vitest in Phase 1".

## Security Domain

> `security_enforcement` is `true` and `security_asvs_level: 1` in `.planning/config.json`. Section required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | NO (Phase 0 has no auth) | n/a — Phase 1 work; libraries (PyJWT, pwdlib[argon2]) installed in Phase 0 for forward-compat |
| V3 Session Management | NO (Phase 0 has no sessions) | n/a — Phase 1 |
| V4 Access Control | NO (no protected routes; `/health` is intentionally unauthenticated) | n/a — Phase 1 introduces `get_current_context` dependency |
| V5 Input Validation | partial (only `/health` exists; no inputs) | Pydantic v2 already wired for future routes — declarative validation is the standard control |
| V6 Cryptography | partial — `SECRET_KEY` env var is set up | `cryptography` library install deferred to Phase 9 (Plaid token encryption); Phase 0 establishes the env-var convention only — `SECRET_KEY` is loaded from env, never hard-coded |
| V7 Error Handling & Logging | YES — INFRA-07 explicitly requires it | structlog with redactor processor (drops `password`, `token`, `secret`, `authorization` keys at any nesting); request_id binding via pure ASGI middleware |
| V8 Data Protection | partial (no user data yet; but `.env` discipline matters) | `.env` in `.gitignore`; `.env.example` committed; README warns against committing `.env` |
| V9 Communications | YES (CORS) | `CORSMiddleware` with explicit `allow_origins` list (never `["*"]` with `allow_credentials=True`); HTTPS deferred to deployment phase |
| V10 Malicious Code | YES — package legitimacy | slopcheck applied to all api packages on 2026-05-23 (19/19 [OK]); npm packages cross-verified via registry |
| V11 Business Logic | n/a (no logic yet) | — |
| V12 File Resources | n/a (no file handling) | Phase 12 work |
| V13 API Security | partial | OpenAPI spec auto-generated from FastAPI; `/health` is intentionally public; CORS configured tightly |
| V14 Configuration | YES | `pydantic-settings` for typed env loading; secrets never in git; Docker base images pinned to `python:3.12-slim` and `node:22-alpine` (immutable tags, but not digest-pinned — accept that risk for Phase 0); RLS GUC convention reserved as defense-in-depth for multi-tenancy (PITFALLS.md C3) |

### Known Threat Patterns for FastAPI + Next.js + Postgres stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via user input | Tampering | SQLAlchemy parameterized queries (use `text()` with bind params, never f-string SQL); `text("SELECT 1")` in `/health` has no user input → safe. |
| Secret leakage via logs | Information Disclosure | structlog redactor processor drops `password`/`token`/`secret`/`authorization` keys at any nesting level (§Pattern 3) |
| Secret leakage via repo commit | Information Disclosure | `.env` in `.gitignore`; `.env.example` is the committed template; README warning (PITFALLS.md O9) |
| CORS over-permissive | Spoofing | `allow_origins` is an explicit list (`http://localhost:3000` for dev); `allow_credentials=True` so wildcard is impossible (FastAPI raises) |
| Cross-household data leak (RLS-related, future phases) | Information Disclosure | RLS GUC convention reserved in Phase 0; policies wired in Phase 1; defense-in-depth alongside repository-layer `household_id` filtering (PITFALLS.md C3) |
| Container running as root | Elevation of Privilege | Phase 0 Dockerfiles run as default Python/Node user; future hardening (USER directive) deferred to v1.0 ship — documented in `docs/BACKLOG.md` |
| Outdated dependencies | Tampering | All deps pinned with upper bounds (`<X` floors); `pip3 index versions` checked on 2026-05-23; slopcheck verified all packages |
| `/health` endpoint information disclosure | Information Disclosure | Returns version + environment + db_connected — all are non-sensitive (no internal IPs, no auth state, no PII). Confirmed by Phase 0 scope. |

## Project Constraints (from CLAUDE.md)

These directives from `./CLAUDE.md` must be honored by every Phase 0 plan:

1. **Grep before adding any function/class** — Phase 0 introduces ~10 new functions (`get_session`, `get_health`, `configure_logging`, etc.); planner should still confirm no duplicates exist in the (empty) repo. Trivially satisfied in Phase 0.
2. **Domain types in `packages/shared/schemas.py` and `packages/shared/types.ts`** — Phase 0 creates these files empty; no schemas yet.
3. **DB ops through SQLAlchemy models** — Phase 0 has only the `SELECT 1` text query in `/health`; documented as exceptional with a comment. Phase 1+ uses models.
4. **Money as INTEGER cents** — no money in Phase 0; convention documented in `docs/SCHEMA.md` for future contributors.
5. **Dates as DATE/TIMESTAMPTZ with both transaction_date and post_date** — no transactions in Phase 0; convention documented in `docs/SCHEMA.md` and `docs/MIGRATIONS.md`.
6. **Modules in `apps/api/src/modules/<name>/`** — Phase 0 creates only `health/`.
7. **No untracked TODOs** — any deferred work goes in `docs/BACKLOG.md`.
8. **`make check` passes before declaring task complete** — every plan step ends with `make check` passing.

## Sources

### Primary (HIGH confidence)

- **Postgres 16 docs** — https://www.postgresql.org/docs/16/ddl-rowsecurity.html — RLS syntax, ENABLE ROW LEVEL SECURITY, CREATE POLICY, BYPASSRLS, default-deny policy semantics. Fetched 2026-05-23.
- **Next.js installation page** — https://nextjs.org/docs/app/getting-started/installation — version 16.2.6, Node 20.9+ minimum, `--yes` defaults (TypeScript + ESLint + Tailwind + App Router + Turbopack + `@/*` alias + AGENTS.md/CLAUDE.md), `next lint` removed in 16. Fetched 2026-05-23.
- **FastAPI CORS tutorial** — https://fastapi.tiangolo.com/tutorial/cors/ — `CORSMiddleware` setup, `allow_credentials` caveat with wildcards. Fetched 2026-05-23.
- **Alembic cookbook** — https://alembic.sqlalchemy.org/en/latest/cookbook.html — programmatic async API use, `run_async_migrations` pattern. Fetched 2026-05-23.
- **Alembic async env.py template** — https://github.com/sqlalchemy/alembic/blob/main/alembic/templates/async/env.py — reference for `alembic init -t async`.
- **PyPI** — `pip3 index versions <pkg>` on 2026-05-23 for all api packages.
- **npm registry** — `npm view <pkg> version` on 2026-05-23 for all web packages.
- **slopcheck** — v0.6.1 ran `slopcheck install <pkgs>` on 2026-05-23; 21 packages verified [OK], 0 [SLOP], 0 [SUS].
- **`.planning/research/STACK.md`** — project canon for stack decisions; consulted for `procrastinate` deferral, structlog, asgi-lifespan, etc.
- **`.planning/research/ARCHITECTURE.md`** — project canon for module layout, async session pattern, RLS layering.
- **`.planning/research/PITFALLS.md`** — project canon for Phase 0 pitfalls (O1, O2, O6, O7, O9 are explicitly Phase 0).
- **`CLAUDE.md`** — project canon for repo structure, package list, naming, exit criteria.

### Secondary (MEDIUM confidence)

- **Procrastinate docs** — https://procrastinate.readthedocs.io/en/stable/howto/production/migrations.html — schema migration pattern via `procrastinate schema --apply`. Coexistence with Alembic is a known issue (procrastinate-org/procrastinate#1040) but irrelevant to Phase 0 (procrastinate deferred to Phase 4).
- **Web search results** on FastAPI + structlog + 2026 best practices — confirmed pure ASGI middleware over BaseHTTPMiddleware for contextvars; multiple corroborating 2026 sources (oneuptime.com 2026-02-02, wazaari.dev, angelospanag.me).
- **Web search results** on Postgres custom GUCs — confirmed `app.*` dotted-name GUCs require no registration since PG 9.2 (pgEdge blog, fluca1978.github.io, Crunchy Data blog).
- **shadcn/ui Tailwind v4 docs** — https://ui.shadcn.com/docs/tailwind-v4 — `components.json` has empty `tailwind.config` for v4 projects.

### Tertiary (LOW confidence — re-verify if used)

- Recharts v3 as the current major (npm view confirmed v3.8.1) — STACK.md cited v2; not used in Phase 0 so no immediate impact, but flag for Phase 8 to re-research.
- shadcn/ui CLI exact prompts in `pnpm dlx shadcn@latest init` — accept whatever the current CLI generates.

## Metadata

**Confidence breakdown:**
- Standard stack (versions): **HIGH** — every package verified via PyPI/npm registry on 2026-05-23 + slopcheck.
- Architecture patterns: **HIGH** — every pattern verified against official docs (FastAPI, Alembic, Next.js, Postgres) on 2026-05-23.
- Pitfalls: **HIGH** — drawn from project-canon PITFALLS.md and corroborated by current best-practice search results.
- INFRA-09 RLS interpretation: **MEDIUM** — the wording is ambiguous (see Open Question 1); planner should surface to user.
- Procrastinate / Alembic coexistence: **MEDIUM** — verified there's a known integration friction but it's irrelevant to Phase 0 (procrastinate deferred).
- Tailwind 4 + shadcn/ui setup: **MEDIUM-HIGH** — verified against current docs; minor risk of CLI prompt drift.

**Research date:** 2026-05-23
**Valid until:** 2026-06-22 (30 days for a stable foundation phase; the only fast-moving piece is Next.js, where 16.3 may ship in 4-6 weeks — none of that breaks Phase 0).
