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
