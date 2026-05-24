# PRANAV

**Personal Resource & Asset Navigator for Abundant Value** — a self-hostable
personal finance application built on the Bitwarden model: fully open source,
run it yourself or use the cloud version. Built for people who want to own
their financial data.

> **Core value:** see where your money is going *before* it goes there. A
> trustworthy cash-flow forecast built on real account balances, recurring
> transactions, and your actual spending patterns.

## Quickstart

```bash
git clone https://github.com/plodha/ledgr.git
cd ledgr
cp .env.example .env
# (edit .env if you want to change passwords; defaults are dev-only)
make dev               # builds and starts 4 containers (postgres + api + web + adminer)

# (in a second terminal, once Postgres reports healthy)
make migrate           # applies the Phase 0 Alembic baseline

# Open http://localhost:3000  — placeholder page + API health status
# Open http://localhost:8000/health  — JSON envelope from the api
# Open http://localhost:8080  — Adminer (Server: postgres, User: pranav,
#                                Password: pranav_dev_password, Database: pranav)
```

To stop the stack: `make down`. The `postgres_data` volume persists across
restarts, so your data survives. To completely reset: `docker volume rm
ledgr_postgres_data` (after `make down`).

## Prerequisites

- **Docker Engine 27+** and **Docker Compose v2** (bundled with Docker Desktop
  on macOS/Windows, or `docker-compose-plugin` on Linux).
- **`make`** (preinstalled on macOS and most Linux distros; on Windows use
  WSL2).
- **`git`** to clone the repo.

For running `make check` host-side (CI does this too):

- **pnpm** — install via `corepack enable` (ships with Node 16.10+) or
  `npm install -g pnpm@10`.
- **Python 3.12** — pinned by `apps/api/.python-version`; use pyenv or asdf.

## Make targets

| Target | What it does |
|--------|--------------|
| `make dev`        | Build and start all 4 containers (postgres, api, web, adminer) |
| `make down`       | Stop and remove containers (`postgres_data` volume persists) |
| `make migrate`    | Run `alembic upgrade head` inside the api container |
| `make check`      | Run api + web checks: ruff + pyright + pytest, then tsc + eslint |
| `make check-api`  | Run only api checks (ruff + ruff format --check + pyright + pytest) |
| `make check-web`  | Run only web checks (pnpm tsc --noEmit + pnpm lint) |
| `make shell-api`  | Open a bash shell in the api container |
| `make shell-db`   | Open a psql session against the postgres container (user: pranav) |

Run `make` (or `make help`) with no target to see the same list.

## Project structure

```
ledgr/
├── apps/
│   ├── web/                  # Next.js 16.2 App Router (TypeScript, Tailwind 4)
│   └── api/                  # FastAPI 0.136 (async SQLAlchemy, structlog)
├── packages/
│   ├── db/                   # Alembic async env.py + migrations
│   ├── shared/               # Pydantic schemas (schemas.py) + TS types (types.ts)
│   └── domain/               # Pure business logic — no DB / no HTTP imports
├── docker/
│   └── docker-compose.yml    # 4-service stack
├── docs/                     # ARCHITECTURE / SCHEMA / MIGRATIONS / BACKLOG / ADRs
├── .github/workflows/        # CI: check.yml (api + web jobs on push + PR)
├── .env.example              # 8 env vars + commented native-dev DATABASE_URL
├── CLAUDE.md                 # Repo-wide conventions (Claude Code reads this)
├── Makefile                  # The developer interface
└── README.md                 # this file
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the deeper walk-through.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the running architecture
  reference: 4-container stack, module layout, async DB engine, structlog,
  CORS, RLS reservation.
- [`docs/SCHEMA.md`](docs/SCHEMA.md) — what the database looks like today and
  what each future phase will add.
- [`docs/MIGRATIONS.md`](docs/MIGRATIONS.md) — migration discipline rules
  (nullable-first, `CREATE INDEX CONCURRENTLY`, RLS GUC convention with the
  `missing_ok` flag).
- [`docs/BACKLOG.md`](docs/BACKLOG.md) — tracked deferred items with source
  citations. Per CLAUDE.md, no TODO ever lives in code without a backlog entry.
- [`docs/adr/`](docs/adr/) — Architecture Decision Records. ADR-001 records
  the modular-monolith decision.

## Phase progress

PRANAV is built in 12 phases (0 through 11). Phase 0 (this repo state) is the
foundation; **v1.0 ships after Phase 11**.

See [`.planning/ROADMAP.md`](.planning/ROADMAP.md) for the full phase map and
each phase's success criteria.

| Phase | Theme | Status |
|-------|-------|--------|
| 0 | Repo Skeleton | This commit |
| 1 | Auth + Household + RLS Activation | Next |
| 2 | Accounts + Net Worth History | — |
| 3 | Categories + Manual Transactions + Tags + Transfers | — |
| 4 | CSV Import + Background Worker | — |
| 5 | Rules Engine | — |
| 6 | Recurring Transactions | — |
| 7 | Budget View | — |
| 8 | Forecast View (the differentiator) | — |
| 9 | Reports | — |
| 10 | Bill Pay Tracking | — |
| 11 | Onboarding Wizard → **v1.0 ship** | — |

## Security note

`.env` is in `.gitignore` and the `.env.example` allow-list is the only
env-shaped file that belongs in git. **Never commit `.env`.**

The default values in `.env.example` (`pranav_dev_password`, `change-me-in-prod`)
are **dev-only**. Before deploying anywhere that isn't localhost:

1. Rotate `SECRET_KEY` to a fresh value:
   `python3 -c 'import secrets; print(secrets.token_hex(32))'`.
2. Rotate `POSTGRES_PASSWORD` to a strong random value.
3. Restrict `ALLOWED_ORIGINS` to your deployed web URL.
4. Set `ENVIRONMENT=production` so logs render as JSON.

The full hardening checklist (`USER` directive in Dockerfiles, image digest
pinning, branch protection rules, etc.) lives in
[`docs/BACKLOG.md`](docs/BACKLOG.md) under "Phase 0 deferred items".

## License & repo

- **Repo:** https://github.com/plodha/ledgr
- **License:** TBD before v1.0 ship.
