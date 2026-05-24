---
phase: 00-repo-skeleton
plan: 01
subsystem: infra
tags: [python, pytest, anyio, asgi-lifespan, httpx, ruff, pyright, structlog, env, gitignore, bootstrap]

# Dependency graph
requires:
  - phase: 00-repo-skeleton
    provides: ROADMAP + REQUIREMENTS + RESEARCH (validated stack pins, INFRA-* contracts, slopcheck audit)
provides:
  - Repo-root .gitignore that excludes .env, __pycache__, .venv, node_modules, .next, .pytest_cache, .ruff_cache (T-00-01 mitigation)
  - .gitattributes forcing LF eol cross-platform (Docker parity)
  - .env.example documenting the 8 required env vars (POSTGRES_USER/PASSWORD/DB, SECRET_KEY, ENVIRONMENT, LOG_LEVEL, ALLOWED_ORIGINS, NEXT_PUBLIC_API_URL) + commented native-dev DATABASE_URL line
  - apps/api/.python-version pinning 3.12
  - apps/api/requirements.txt with 12 pinned runtime deps (fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic, pydantic-settings, structlog, PyJWT, pwdlib[argon2], python-multipart, greenlet)
  - apps/api/requirements-dev.txt with 7 dev/test deps (pytest, pytest-asyncio, anyio, asgi-lifespan, httpx, ruff, pyright)
  - apps/api/pyproject.toml with tool config only ([tool.ruff], [tool.ruff.lint], [tool.pyright] strict, [tool.pytest.ini_options] asyncio_mode=auto)
  - Wave 0 failing-by-design test suite (4 tests across 3 test files + 1 conftest + 1 __init__) encoding INFRA-02, INFRA-04, INFRA-06, INFRA-07, INFRA-09 contracts that Waves 1-2 must satisfy
affects: [00-02 (Wave 1 FastAPI app), 00-03 (Wave 2 Alembic baseline + RLS marker), 00-04 (Docker/Compose), 00-05 (Makefile + make check), 00-06 (CI + docs)]

# Tech tracking
tech-stack:
  added:
    - fastapi (pinned >=0.136,<0.137)
    - uvicorn[standard] (>=0.36,<1)
    - sqlalchemy[asyncio] (>=2.0.36,<2.1)
    - asyncpg (>=0.30,<0.32)
    - alembic (>=1.18,<2)
    - pydantic / pydantic-settings (>=2.9 / >=2.5)
    - structlog (>=25.1,<26)
    - PyJWT (>=2.9,<3)
    - pwdlib[argon2] (>=0.3,<1)
    - python-multipart (>=0.0.20,<1)
    - greenlet (>=3.0,<4)
    - pytest + pytest-asyncio + anyio + asgi-lifespan + httpx
    - ruff (>=0.15) + pyright (>=1.1.400) — both gated to floor + upper bound
  patterns:
    - "tests-first / failing-by-design Wave 0 protocol (Nyquist mandate from 00-VALIDATION.md)"
    - "httpx AsyncClient + ASGITransport + asgi-lifespan.LifespanManager pattern for async API tests (mandatory; AsyncClient alone never fires ASGI lifespan)"
    - "pyproject.toml as TOOL CONFIG ONLY — requirements.txt is source of truth (no build-system / no project metadata sections)"
    - "Floor + ceiling version pins on every dep to prevent silent major-version drift"
    - ".env never committed; .env.example is the single allow-listed env template"

key-files:
  created:
    - .gitignore
    - .gitattributes
    - .env.example
    - apps/api/.python-version
    - apps/api/requirements.txt
    - apps/api/requirements-dev.txt
    - apps/api/pyproject.toml
    - apps/api/tests/__init__.py
    - apps/api/tests/conftest.py
    - apps/api/tests/test_health.py
    - apps/api/tests/test_logging.py
    - apps/api/tests/test_env_example.py
  modified: []

key-decisions:
  - "Added pytest-asyncio explicitly to requirements-dev.txt (already listed in the plan) so the fixture decorator @pytest_asyncio.fixture is available; anyio_backend fixture pins backend=asyncio so SQLAlchemy 2.0 async dialect compatibility is unambiguous."
  - "pyproject.toml file-header comment uses 'build-system' / 'project metadata' phrasing rather than the bracketed TOML section names so the plan's automated verify (`! grep -q '\\[build-system\\]'`) succeeds without conflicting with documentation intent."
  - "test_logging.py runs the middleware via asyncio.run() and snapshots structlog.contextvars from inside the inner ASGI app — capturing AFTER the call would race against contextvars.clear_contextvars() in subsequent requests."

patterns-established:
  - "Pattern A — Async test client fixture: `LifespanManager(app)` wraps `AsyncClient(transport=ASGITransport(app=app))`. Without LifespanManager, app.state.engine is never populated and any DB-touching handler raises AttributeError. Every future async API test inherits this fixture from conftest.py."
  - "Pattern B — Failing-by-design Wave 0 tests: imports from `src.main`, `src.database`, `src.logging_config` are intentional and cause collection-time ImportError until Wave 1 lands. This is the canonical red signal — never skip/xfail to suppress it."
  - "Pattern C — Pyproject as tool-config-only: requirements*.txt remains the dependency source of truth. No `[build-system]`, no `[project]`, no setuptools/poetry/uv metadata. The api ships as a directory under apps/, never as a wheel."
  - "Pattern D — Env templating: .env (gitignored) is the runtime file; .env.example (committed, allow-listed in .gitignore) documents every required key with safe dev defaults flagged as 'change me'."

requirements-completed: [INFRA-03, INFRA-06, INFRA-07]

# Metrics
duration: 4.2min
completed: 2026-05-24
---

# Phase 00 Plan 01: Wave 0 Test Infrastructure & Repo-Root Guards Summary

**Phase 0 Wave 0 scaffolding — `.gitignore` + `.env.example` + apps/api dependency manifest + ruff/pyright/pytest tool config + a 4-test failing-by-design suite that encodes the INFRA-02/04/06/07/09 contracts Wave 1 production code must satisfy.**

## Performance

- **Duration:** 4.2 min
- **Started:** 2026-05-24T02:10:30Z
- **Completed:** 2026-05-24T02:14:40Z
- **Tasks:** 3 of 3
- **Files created:** 12
- **Files modified:** 0

## Accomplishments

- Repo-root guards prevent `.env` from ever being committed (`!.env.example` allow-list + `.env` deny pattern) and document the 8 env vars docker-compose interpolates in Wave 4.
- apps/api now has its full dependency manifest (12 runtime + 7 dev/test deps), all pinned with floor + ceiling and all slopchecked OK per 00-RESEARCH.md §Package Legitimacy Audit.
- pyproject.toml configures ruff + pyright (strict mode) + pytest (asyncio_mode=auto, testpaths=["tests"]) — `make check` (Wave 5) has a valid target.
- 4 Wave 0 tests landed across 3 test files + conftest, encoding the behavioral contracts for `/health`, the Phase 0 baseline migration marker, the structlog request-id middleware, and the `.env.example` env-var documentation requirement.
- `.gitattributes` forces LF line endings cross-platform so dev-on-macOS / build-on-Linux Docker images don't diverge on CRLF handling.

## Task Commits

Each task was committed atomically:

1. **Task 1: Repo-root guards (.gitignore, .gitattributes, .env.example)** — `987392f` (chore)
2. **Task 2: apps/api requirements files + pyproject.toml + .python-version** — `c83104b` (chore)
3. **Task 3: Wave 0 failing-by-design test suite** — `fc5b44e` (test)

_Plan metadata commit (this SUMMARY + REQUIREMENTS) lands in worktree-mode group-commit owned by the orchestrator after the wave merges._

## Files Created/Modified

- `.gitignore` — secrets / Python / Node / editor / build ignore patterns (T-00-01 mitigation)
- `.gitattributes` — `* text=auto eol=lf` forces LF line endings
- `.env.example` — 8 env-var template + commented native-dev DATABASE_URL example, with `NEVER COMMIT .env` warning header
- `apps/api/.python-version` — pins `3.12` for pyenv/asdf parity with `python:3.12-slim` Docker image and CI matrix
- `apps/api/requirements.txt` — 12 runtime deps pinned per 00-RESEARCH.md Standard Stack (no procrastinate, no cryptography, no redis, no celery, no arq, no fastapi-users)
- `apps/api/requirements-dev.txt` — `-r requirements.txt` + 7 dev/test deps; asgi-lifespan is non-optional per RESEARCH.md Pitfall 5
- `apps/api/pyproject.toml` — tool config only (`[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.lint.per-file-ignores]`, `[tool.pyright]` strict, `[tool.pytest.ini_options]`); no build-system or project metadata sections
- `apps/api/tests/__init__.py` — empty package marker so pyright can resolve relative imports
- `apps/api/tests/conftest.py` — `anyio_backend` (asyncio) + `client` fixture that yields `AsyncClient(transport=ASGITransport(app), base_url="http://test")` wrapped in `LifespanManager(app)`
- `apps/api/tests/test_health.py` — `test_health_ok` (INFRA-02 envelope) + `test_baseline_migration_applied` (INFRA-04/09 `_phase0_marker` row check)
- `apps/api/tests/test_logging.py` — `test_request_id_bound_via_middleware` (INFRA-07: middleware binds `x-request-id` header into structlog contextvars)
- `apps/api/tests/test_env_example.py` — `test_env_example_documents_all_required_keys` (INFRA-06: 8 required keys present in `.env.example`)

## Decisions Made

- **Added `pytest-asyncio` import in `conftest.py`** — `@pytest_asyncio.fixture` is the supported decorator for async fixtures under pytest-asyncio 1.0; `@pytest.fixture` on an async generator works in some versions but is not the documented contract. pytest-asyncio is already listed in `requirements-dev.txt` per the plan, so this is purely a usage detail.
- **Phrased pyproject.toml header comment around "build-system" / "project metadata" rather than the bracketed TOML section names** — the plan's automated `<verify>` block runs `! grep -q '\[build-system\]'` and `! grep -q '\[project\]'`; the verify would have tripped on the literal section names appearing in a documentation comment. The semantic intent (no build/project sections) is preserved.
- **In `test_logging.py`, snapshot `get_contextvars()` from inside the inner ASGI app rather than after `middleware(scope, receive, send)` returns** — the RESEARCH.md Pattern 3 reference middleware calls `clear_contextvars()` at the *start* of each request and only re-binds inside. Reading contextvars after the call returns would still work for this single-call test, but reading from inside is the more durable assertion: it proves the bind is visible to downstream handlers, which is the actual INFRA-07 contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Renamed `pyproject.toml` header comment to satisfy the plan's `<verify>` automated check**

- **Found during:** Task 2 (apps/api requirements + pyproject.toml + .python-version), running the plan's own `<automated>` verify block.
- **Issue:** The plan's verify pipeline includes `! grep -q '\[build-system\]' apps/api/pyproject.toml && ! grep -q '\[project\]' apps/api/pyproject.toml`. My initial header comment used the literal section-name strings to *explain* their intentional absence ("Intentionally no `[build-system]` and no `[project]` sections..."), which caused both negative greps to match the comment and fail.
- **Fix:** Rewrote the header comment to use phrasing ("No build-system or project metadata sections — the api package is delivered as a directory inside `apps/`, never as a wheel.") that preserves the documentation intent without embedding the bracketed TOML section names. Verify now passes cleanly.
- **Files modified:** `apps/api/pyproject.toml`
- **Verification:** Re-ran the full Task 2 `<verify>` chain — all 21 individual checks return OK; the chain prints `VERIFY PASS`.
- **Committed in:** `c83104b` (part of Task 2 commit — fixed before the commit was made)

---

**Total deviations:** 1 auto-fixed (1 blocking — Rule 3)
**Impact on plan:** Cosmetic. No package was added, removed, or re-pinned; no test contract changed; no acceptance criterion was relaxed. The fix was a header-comment rephrase to keep the plan's literal grep-based verify gate green.

## Issues Encountered

- None. All three tasks executed cleanly. The Wave 0 tests intentionally fail at import time (`from src.main import app`, `from src.database import AsyncSessionLocal`, `from src.logging_config import RequestContextMiddleware`) because Wave 1 has not yet shipped — this is the documented red signal, not an issue.

## User Setup Required

None — no external service configuration required at Wave 0. The 8 env vars documented in `.env.example` are dev defaults; production deployments will replace `SECRET_KEY` per the inline warning.

## Threat Mitigations Realized

| Threat ID | Disposition | How this plan realized it |
|-----------|-------------|---------------------------|
| T-00-01 (Info Disclosure: `.env` leak) | mitigate | `.gitignore` `.env` deny + `!.env.example` allow-list combo; verify gate confirms both lines present |
| T-00-02 (Info Disclosure: template defaults) | mitigate | `.env.example` `SECRET_KEY` value reads `change-me-in-prod-use-openssl-rand-hex-32`; README + Plan 06 follow up with prod warnings |
| T-00-03, T-00-04, T-00-SC (Supply chain) | mitigate | All 12 runtime + 7 dev/test deps pinned with `>=floor,<ceiling`; all 19 already slopchecked [OK] in 00-RESEARCH.md §Package Legitimacy Audit |

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries were introduced by this plan. All surface added (gitignore patterns, dep pins, test scaffolding) sits inside the dev/test trust boundary.

## Known Stubs

None. The Wave 0 tests are not stubs — they encode required behavioral contracts and will turn green when Waves 1-2 ship the production code (`src/main.py`, `src/database.py`, `src/logging_config.py`, baseline Alembic migration). The plan's success criteria explicitly require the tests to exist now and fail at execution until Wave 1/2 land.

## Next Phase Readiness

- **Wave 1 (Plan 02 — FastAPI app):** Has a non-empty test suite to satisfy. `src/main.py` must expose `app`; `src/database.py` must expose `AsyncSessionLocal`; `src/logging_config.py` must expose `configure_logging` + `RequestContextMiddleware`. `/health` must return the documented envelope and `db_connected: True`.
- **Wave 2 (Plan 03 — Alembic baseline + RLS marker):** Must create the `_phase0_marker` table and seed `id=1` with `note` starting `Phase 0 migration succeeded`. `test_baseline_migration_applied` is the regression gate.
- **Wave 4 (Plan 04 — Docker / Compose):** `.env.example` is the authoritative env-var manifest for docker-compose interpolation. The api Dockerfile should `pip install -r requirements-dev.txt` (which pulls runtime via `-r requirements.txt`) so `make check` runs inside the container.
- **Wave 5 (Plan 05 — Makefile + `make check`):** `pyproject.toml` already configures ruff, pyright, and pytest with sensible defaults so the Makefile targets are one-liners: `ruff check apps/api`, `pyright apps/api`, `pytest apps/api/tests/`.

## Self-Check: PASSED

- All 12 files declared in `key-files.created` exist on disk (verified via `[ -f <path> ]`).
- All 3 task commits (`987392f`, `c83104b`, `fc5b44e`) found in `git log --oneline --all`.
- HEAD is on `worktree-agent-a6bb63e3fd1f1eaa0`, base matches the spawn-time root (`9233b62`), no protected-ref drift.
- No accidental deletions in any task commit (`git diff --diff-filter=D` returns empty for all three).

---
*Phase: 00-repo-skeleton*
*Plan: 01*
*Completed: 2026-05-24*
