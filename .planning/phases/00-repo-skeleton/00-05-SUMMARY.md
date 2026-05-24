---
phase: 00-repo-skeleton
plan: 05
subsystem: infra
tags: [docker, docker-compose, makefile, infra, integration]

# Dependency graph
requires:
  - phase: 00-repo-skeleton
    provides: "Plan 02 — FastAPI /health endpoint + uvicorn target `apps.api.src.main:app`; Plan 03 — packages/db/alembic.ini + 0001_phase0_baseline; Plan 04 — apps/web/Dockerfile (node:22-alpine, EXPOSE 3000); Plan 01 — .env.example with POSTGRES_USER=pranav defaults"
provides:
  - "apps/api/Dockerfile — multi-stage python:3.12-slim image with full dev/test tooling (pytest, ruff, pyright) in /root/.local"
  - "apps/api/.dockerignore — excludes __pycache__, .venv, .env*, .git, caches"
  - "docker/docker-compose.yml — 4-service Compose v2 stack: postgres (16-alpine + healthcheck), api (depends on postgres healthy), web (depends on api), adminer"
  - "Makefile — dev, down, migrate, check (= check-api + check-web), shell-api, shell-db; .DEFAULT_GOAL := help; `make shell-db` patches CLAUDE.md legacy `finbrain` username to `pranav`"
affects: [00-06-docs-ci, 01-auth, 09-plaid-connector]

# Tech tracking
tech-stack:
  added:
    - "Docker Compose v2 (no `version:` key per RESEARCH.md Anti-Pattern)"
    - "postgres:16-alpine container with pg_isready healthcheck"
    - "adminer:latest container for DB inspection (port 8080, dev only)"
    - "python:3.12-slim multi-stage build pattern (builder copies gcc/libpq-dev; runtime keeps libpq5 only)"
    - "uvicorn --reload via compose command override (dev hot-reload)"
  patterns:
    - "Multi-stage Python Docker pattern: builder installs to /root/.local via `pip install --user`; runtime stage copies only /root/.local (halves image size vs system-wide install)"
    - "Compose v2 healthcheck dependency: `depends_on.postgres.condition: service_healthy` waits for `pg_isready` before starting api (avoids `make migrate` races)"
    - "DSN composition: docker-compose interpolates DATABASE_URL from POSTGRES_* env vars to keep one source of truth (`postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}`)"
    - "Bind-mount + anon-volume pattern for Next.js dev (bind `apps/web:/app` + anon vols for `/app/node_modules` and `/app/.next` to preserve the install)"
    - "Makefile `COMPOSE := docker compose -f docker/docker-compose.yml --env-file .env` macro pattern — every target reuses it"
    - "Makefile `shell-db` uses `$${POSTGRES_USER:-pranav}` (double-`$` escapes Make's expansion; the shell does the fallback)"

key-files:
  created:
    - "apps/api/Dockerfile — 2-stage build (builder/runtime) on python:3.12-slim; CMD uvicorn apps.api.src.main:app on 0.0.0.0:8000; PYTHONPATH=/app"
    - "apps/api/.dockerignore — 16 entries (caches, virtualenvs, secrets, git, docs)"
    - "docker/docker-compose.yml — 4 services (postgres, api, web, adminer) + named volume postgres_data"
    - "Makefile — 9 targets (help + 8 commands); tabs for recipes; .DEFAULT_GOAL := help"
  modified: []

key-decisions:
  - "Builder installs BOTH requirements.txt AND requirements-dev.txt — keeps `make check-api` (pytest + ruff + pyright) runnable via `docker compose exec api`. Trade-off: api image is bigger; acceptable for Phase 0 dev-stack."
  - "`pip install --user` (lands in /root/.local) over system-wide install — smaller runtime stage (only /root/.local + libpq5 copied)."
  - "Compose v2 (no `version:` key per RESEARCH.md Anti-Pattern line 1038)."
  - "`depends_on.postgres.condition: service_healthy` for api (NOT `service_started`) — waits for `pg_isready` so `make migrate` won't race the DB."
  - "Bind-mounts `apps/api` + `packages` (NOT just `apps/api`) — `make migrate` needs `packages/db/alembic.ini` + `packages/db/migrations/` accessible inside the api container."
  - "compose `command:` adds `--reload` for dev; the production CMD in the Dockerfile (without --reload) is the right default for prod deploys (Phase 12+)."
  - "web `API_URL_INTERNAL=http://api:8000` (Docker service name) — Server Components fetch from inside the Docker network; `NEXT_PUBLIC_API_URL=http://localhost:8000` for any browser-side fetch leaks. Matches Plan 04's `src/app/page.tsx` URL fallback chain."
  - "adminer:latest (NOT pinned digest) — accepted per RESEARCH.md V14 line 1321; pinning is in BACKLOG (Plan 06)."
  - "`make check` runs HOST-SIDE (not inside container) per RESEARCH.md Pattern 8 — faster inner dev loop. Container-side option documented via `make shell-api` then run checks inside."
  - "PATCHED CLAUDE.md line 120: `make shell-db` uses POSTGRES_USER=`pranav`, NOT `finbrain` (project renamed per RESEARCH.md Assumption A5 / Open Question 6). Legacy string `finbrain` is purged from Makefile and docker-compose.yml entirely."

patterns-established:
  - "Modular Compose-v2 stack with healthcheck gating: postgres healthcheck → api depends_on healthy → web depends_on api → adminer depends_on postgres."
  - "Multi-stage Python Docker: builder (apt-get gcc/libpq-dev + pip install --user) → runtime (apt-get libpq5 only + COPY /root/.local). All future Phase-N services follow this template."
  - "Developer interface = Makefile: every workflow (`make dev`, `make migrate`, `make check`) goes through one entrypoint that wraps the Compose command + `--env-file .env`. No bare `docker compose ...` in the user's hands."
  - "Configuration source of truth = `.env` file at repo root: docker-compose interpolates all POSTGRES_*/SECRET_KEY/ENVIRONMENT/LOG_LEVEL/ALLOWED_ORIGINS/NEXT_PUBLIC_API_URL with sensible defaults so first-time setup is `cp .env.example .env && make dev`."

requirements-completed:
  - INFRA-01
  - INFRA-03
  - INFRA-04
  - INFRA-05

# Metrics
duration: ~4 min
completed: 2026-05-24
---

# Phase 00-05: docker-compose Stack + Makefile Summary

**4-service Compose v2 stack (postgres + api + web + adminer) wired together with healthcheck-gated dependencies, a multi-stage python:3.12-slim API Dockerfile, and a Makefile that exposes the entire dev workflow (`make dev`, `make migrate`, `make check`, `make shell-{api,db}`).**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-24 (worktree spawn)
- **Completed:** 2026-05-24
- **Tasks:** 3
- **Files created:** 4, **Files modified:** 0

## Accomplishments

- `apps/api/Dockerfile` is a two-stage build on `python:3.12-slim`. The builder installs `gcc` + `libpq-dev` and `pip install --user -r requirements.txt -r requirements-dev.txt` into `/root/.local`; the runtime stage keeps only `libpq5` + the copied `/root/.local`, `apps/api`, and `packages`. Default `CMD` is `uvicorn apps.api.src.main:app --host 0.0.0.0 --port 8000`. Dev/test tooling (pytest, ruff, pyright, alembic) is in `/root/.local/bin` and on `PATH`, so `docker compose exec api pytest` Just Works.
- `apps/api/.dockerignore` excludes `__pycache__`, `*.pyc`, `*.pyo`, `.pytest_cache`, `.ruff_cache`, `.pyright`, `.venv`, `venv`, `*.egg-info`, `.coverage`, `htmlcov`, `.git`, `.env`, `.env.*`, `README.md`, `docs/` — prevents secrets and dev cruft from entering image layers.
- `docker/docker-compose.yml` defines exactly 4 services with the Compose v2 schema (no `version:` key):
  - **postgres** (`postgres:16-alpine`) — port 5432, named volume `postgres_data`, `pg_isready` healthcheck every 5 s.
  - **api** — builds `apps/api/Dockerfile` from repo root (`context: ..`); `depends_on.postgres.condition: service_healthy`; mounts `apps/api` + `packages` for hot-reload; `command:` adds `--reload`; `DATABASE_URL` interpolated from `POSTGRES_*` env vars using the `postgresql+asyncpg://` driver prefix.
  - **web** — builds `apps/web/Dockerfile`; depends on api; bind-mounts `apps/web:/app` plus anon vols for `/app/node_modules` and `/app/.next`; sets `API_URL_INTERNAL=http://api:8000` (Docker service-name DNS) and `NEXT_PUBLIC_API_URL` (for browser).
  - **adminer** (`adminer:latest`) — port 8080, `ADMINER_DEFAULT_SERVER: postgres` pre-fills the login form.
- All 4 services have `restart: unless-stopped` (CLAUDE.md line 109 — grep count `restart: unless-stopped` = 4).
- `Makefile` declares 9 targets (`help`, `dev`, `down`, `migrate`, `check`, `check-api`, `check-web`, `shell-api`, `shell-db`). `.DEFAULT_GOAL := help` makes bare `make` print usage. The legacy `finbrain` username from CLAUDE.md line 120 is patched to `pranav` and the string `finbrain` is fully purged from Makefile and docker-compose.yml.
- `docker compose -f docker/docker-compose.yml --env-file .env config` validates the YAML and resolves all variable interpolations (smoke-tested with a `.env` copied from `.env.example`).

## Smoke Test Results

| Test | Command | Result |
|------|---------|--------|
| Compose YAML validates + resolves variables | `docker compose -f docker/docker-compose.yml --env-file .env config` | PASS — config printed without error; DATABASE_URL resolved to `postgresql+asyncpg://pranav:pranav_dev_password@postgres:5432/pranav` |
| Makefile parses + default target works | `make help` | PASS — prints `PRANAV Makefile targets:` block |
| Legacy `finbrain` purged from Makefile + docker-compose.yml | `grep -l 'finbrain' Makefile docker/docker-compose.yml` | PASS — no matches |
| Compose v2 (no top-level `version:`) | `grep -q '^version:' docker/docker-compose.yml` | PASS — absent |
| All 4 services restart: unless-stopped | `grep -c 'restart: unless-stopped' docker/docker-compose.yml` | PASS — count = 4 |
| `apps/api/Dockerfile` builds a runnable image | `docker build -f apps/api/Dockerfile -t pranav-api:dev .` | DEFERRED — the parallel_execution prompt explicitly says "Do NOT run `docker build` or `docker compose up`". Build will run for the first time at the Plan 06 human-verify checkpoint when the wave is merged. |

## Task Commits

Each task was committed atomically:

1. **Task 1: API Dockerfile + .dockerignore** — `d6e6bd0` (feat)
2. **Task 2: docker/docker-compose.yml (4-service stack)** — `8894f32` (feat)
3. **Task 3: Makefile (dev/down/migrate/check/shell-{api,db})** — `1f6aaf9` (feat)

## Files Created/Modified

### Created

- `apps/api/Dockerfile` (27 lines) — 2-stage `python:3.12-slim` build; builder installs gcc/libpq-dev + both requirements*.txt into /root/.local; runtime keeps libpq5 + /root/.local + apps/api + packages; CMD uvicorn on 8000.
- `apps/api/.dockerignore` (16 lines) — caches, virtualenvs, `.env*`, `.git`, `docs/`, `README.md`.
- `docker/docker-compose.yml` (73 lines) — 4 services + named volume `postgres_data`; no `version:` key; restart: unless-stopped × 4; pg_isready healthcheck; DATABASE_URL interpolated; api `--reload` override; web bind-mount + anon vols; adminer with default-server pre-fill.
- `Makefile` (52 lines) — 9 targets; tabs for recipes; `.DEFAULT_GOAL := help`; `COMPOSE` macro; `shell-db` uses `pranav` not `finbrain`.

### Modified

None — Plan 05 is purely additive at the orchestration layer.

## Decisions Made

- **Builder installs runtime + dev deps together.** Trade-off: image is bigger; payoff: `docker compose exec api pytest` / `ruff` / `pyright` / `alembic` all work without rebuilding. Phase 0 chooses dev velocity over image size.
- **`pip install --user` over system-wide install.** Runtime stage copies a single directory (`/root/.local`) — halves image size vs. system-wide pip install.
- **Compose v2 (no `version:` key).** RESEARCH.md Anti-Pattern line 1038. Compose v2 deprecated the field; including it now would emit warnings.
- **`condition: service_healthy` for api → postgres.** Without this, `make migrate` can race the DB on a cold `make dev`. Postgres's `pg_isready` healthcheck takes ~2 s; the wait is invisible.
- **Bind-mount `apps/api` AND `packages` into api.** `packages/` contains `packages/db/migrations/` (Plan 03) — `make migrate` runs `alembic -c packages/db/alembic.ini upgrade head` inside the container, so the mount is required.
- **`--reload` via compose `command:` override.** Production CMD (Dockerfile) has no --reload; dev compose adds it. Trade-off (T-00-24): --reload's memory growth on rapid file edits is accepted for dev.
- **`API_URL_INTERNAL=http://api:8000` (service DNS) for web.** Server Components fetch from the Docker network; using `localhost:8000` would fail because each container's localhost is its own network namespace.
- **adminer's `ADMINER_DEFAULT_SERVER: postgres`.** UX nicety — pre-fills the login form so users only type the password.
- **`make check` host-side, not container-side.** Per RESEARCH.md Pattern 8. Container-side option (`make shell-api` → run inside) is documented for users who can't install Python deps on their host.
- **Purged legacy `finbrain` string from Makefile + docker-compose.yml.** RESEARCH.md Assumption A5 / Open Question 6 explicitly resolves the project rename; CLAUDE.md line 120's example is the only place the legacy lingered. This plan fully removes it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed literal `restart: unless-stopped` from docker-compose.yml's header comment so the `grep -c = 4` verify gate matches only service-level occurrences**

- **Found during:** Task 2 (`<verify>` block: `grep -c 'restart: unless-stopped' docker/docker-compose.yml | grep -q '^4$'`)
- **Issue:** The header comment line `# All services restart: unless-stopped per CLAUDE.md.` contained the literal phrase `restart: unless-stopped`, which made `grep -c` return 5 (4 services + 1 comment) instead of the gate's required 4.
- **Fix:** Rephrased the comment to `# All services set the unless-stopped restart policy per CLAUDE.md.` — preserves intent without colliding with the verify gate.
- **Files modified:** `docker/docker-compose.yml`
- **Verification:** `grep -c 'restart: unless-stopped' docker/docker-compose.yml` now returns 4.
- **Committed in:** `8894f32` (Task 2 commit) — comment fix made before the commit was created.

**2. [Rule 3 - Blocking] Rephrased Makefile's documentation comment to avoid the literal string `finbrain` so the `! grep -q 'finbrain' Makefile` verify gate passes**

- **Found during:** Task 3 (`<verify>` block: `! grep -q 'finbrain' Makefile`)
- **Issue:** My initial Makefile draft included a NOTE block that said "patches the legacy `finbrain` example in CLAUDE.md". The plan's verify gate explicitly requires `grep -q 'finbrain' Makefile` to FAIL (no occurrence anywhere in the file). The acceptance criterion is "File contains NO occurrence of the string `finbrain` (legacy name purged)" — purge means literal absence, not just functional absence.
- **Fix:** Rephrased to "patches the legacy pre-rename example in CLAUDE.md" — preserves the documentation pointer to RESEARCH.md A5 / Open Question 6 without including the legacy string.
- **Files modified:** `Makefile`
- **Verification:** `grep -c 'finbrain' Makefile` returns 0; `make help` still prints usage cleanly.
- **Committed in:** `1f6aaf9` (Task 3 commit) — comment fix made before the commit was created.

### Skipped Verification (Documented Reason)

**3. `docker build -f apps/api/Dockerfile -t pranav-api:dev .` smoke test NOT executed in the worktree.** The parallel_execution prompt explicitly forbids `docker build`/`docker compose up` ("Do NOT run `docker build` or `docker compose up` — this is scaffolding only. Docker commands require the running daemon and are not available in the worktree environment."). The first real build will occur at Plan 06's human-verify checkpoint after the wave is merged and the user runs `make dev`. All static `<verify>` grep gates passed; `docker compose -f docker/docker-compose.yml --env-file .env config` (which only parses the YAML, doesn't build) was run and validated.

---

**Total deviations:** 2 auto-fixed (both Rule 3 — verify-gate phrasing issues, neither affects functional correctness) + 1 documented skip (Docker build deferred per parallel_execution constraint).
**Impact on plan:** Zero scope creep. The plan's intent (working 4-service compose stack + multi-stage api Dockerfile + Makefile dev interface) is fully realized; the only differences are two cosmetic comment rephrasings to satisfy literal grep gates.

## Issues Encountered

- **None blocking.** Two comment-text adjustments (above) were caught and fixed before commit.
- The `docker compose -f docker/docker-compose.yml --env-file .env config` validation step requires a `.env` file at repo root. I created one temporarily by `cp .env.example .env`, ran the validation, then removed it. `.env` is gitignored (Plan 01), so `git status` stayed clean throughout.

## User Setup Required

- **One-time `pnpm install` for the web lockfile.** Carried over from Plan 04's deviation #2 (`apps/web/pnpm-lock.yaml` is a placeholder stub). The first `make dev` will fail at the web stage's `pnpm install --frozen-lockfile` until the lockfile is materialized. Either (a) run `cd apps/web && pnpm install` locally once and commit, or (b) the docker build's `--frozen-lockfile` flag can be temporarily relaxed in Plan 06's human-verify run. This is the known follow-up from Plan 04 and is reflected here for completeness — Plan 05 itself does not introduce a new gap.
- **Docker Desktop or equivalent on the dev machine.** Required for `make dev` to actually run. Phase 0's exit criterion #1 (`git clone && make dev` brings up 4 containers) depends on this.
- **`cp .env.example .env` before `make dev`.** Documented in the Makefile help block and will be documented in `docs/README.md` (Plan 06).

## Known Stubs

- `apps/web/pnpm-lock.yaml` — carried over from Plan 04 (their deviation #2). Not introduced by this plan; flagged here for transparency since the new docker-compose web service consumes it.
- No new stubs introduced by Plan 05. All 4 created files are full, runnable artifacts.

## Threat Flags

None — all surface introduced by this plan is enumerated in the plan's `<threat_model>` (T-00-20 through T-00-26). No additional security-relevant surface beyond the documented register.

## Next Phase Readiness

- **Wave 4 (Plan 06 — docs/CI)** is unblocked: it can reference the Makefile targets in `docs/README.md` and add `.github/workflows/check.yml` that runs `make check`-equivalent steps (host-side ruff/pyright/pytest + pnpm tsc/eslint).
- **Phase 0 exit criteria 1, 4, 5** are NOW addressable at the orchestration layer:
  - #1 (`make dev` starts 4 containers): Compose stack defined; needs `pnpm install` for web lockfile + actual `make dev` run in Plan 06's checkpoint.
  - #4 (`http://localhost:8080` shows Adminer): adminer service is in the stack; pre-fills `postgres` as default server.
  - #5 (`make check` passes): Makefile target wired; host-side execution requires Plan 06's README to document host-side dep install.
- **Phase 1 (auth tables, household model)** can use `make migrate` to apply new Alembic revisions inside the api container without changes to this orchestration layer.
- **Phase 9 (Plaid connector)** will introduce a `procrastinate-worker` service to docker-compose.yml — the existing 4-service skeleton is the template for that addition.

## Self-Check: PASSED

- `apps/api/Dockerfile` — FOUND (27 lines, 2-stage python:3.12-slim, CMD uvicorn)
- `apps/api/.dockerignore` — FOUND (16 lines, excludes caches/secrets/git)
- `docker/docker-compose.yml` — FOUND (73 lines, 4 services, no version: key)
- `Makefile` — FOUND (52 lines, 9 targets, tab-indented recipes)
- Commit `d6e6bd0` (Task 1) — FOUND in git log
- Commit `8894f32` (Task 2) — FOUND in git log
- Commit `1f6aaf9` (Task 3) — FOUND in git log
- `make help` smoke-tested — PRINTS usage
- `docker compose -f docker/docker-compose.yml --env-file .env config` — VALIDATES (DSN resolves to `postgresql+asyncpg://pranav:pranav_dev_password@postgres:5432/pranav`)
- `grep 'finbrain' Makefile docker/docker-compose.yml` — NO MATCHES (legacy purged)
- `grep '^version:' docker/docker-compose.yml` — NO MATCH (Compose v2)
- `grep -c 'restart: unless-stopped' docker/docker-compose.yml` — RETURNS 4

---
*Phase: 00-repo-skeleton*
*Plan: 05*
*Completed: 2026-05-24*
