---
phase: 00-repo-skeleton
plan: 06
subsystem: docs
tags: [docs, ci, github-actions, verification, adr, readme]

# Dependency graph
requires:
  - phase: 00-repo-skeleton
    provides: "Plans 01-05 — repo-root guards, apps/api Settings + /health + structlog + RequestContextMiddleware, packages/db Alembic async env + 0001_phase0_baseline (_phase0_marker + RLS GUC reservation via COMMENT ON DATABASE), apps/web Next.js 16.2 placeholder, apps/api Dockerfile + docker/docker-compose.yml + Makefile"
provides:
  - "docs/ARCHITECTURE.md — running architecture reference (4-container modular monolith, async DB engine, /health envelope, RLS reservation, structlog + pure-ASGI middleware, CORS, money/dates conventions, Architectural Responsibility Map)"
  - "docs/SCHEMA.md — Phase 0 state (_phase0_marker only) + per-phase table reservations through Phase 11 (household, user, refresh_token, account, transaction, category, rule, recurring_transaction, budget_allocation, forecast_snapshot, etc.) + mandatory schema conventions (household_id, RLS, INTEGER cents, TIMESTAMPTZ, UUID PKs)"
  - "docs/BACKLOG.md — 16 tracked Phase 0 deferred items with source citations + target milestone (CLAUDE.md constraint #7)"
  - "docs/MIGRATIONS.md — six discipline rules (nullable-first, CREATE INDEX CONCURRENTLY, NOT VALID + VALIDATE, two-phase drops, FK semantics, procrastinate batched backfills) + RLS GUC convention with the non-negotiable `, true` missing_ok flag (RESEARCH.md Pitfall 9) — satisfies INFRA-08"
  - "docs/adr/001-modular-monolith.md — Accepted 2026-05-23; records the modular-monolith decision over microservices / Django / Phase-1-immediate-multi-tenant alternatives"
  - "README.md — quickstart (clone → cp .env.example .env → make dev → make migrate → localhost:3000/8000/8080) + make-target table + project structure tree + documentation links + phase progress table + security/secret-rotation notes"
  - ".github/workflows/check.yml — api + web CI on push + PR using postgres:16-alpine service container (matches local dev Postgres version exactly — RESEARCH.md Pitfall 10 mitigation)"
affects:
  - "01-foundation (Phase 1 inherits docs/MIGRATIONS.md discipline + the RLS GUC convention; first per-table policies land here)"
  - "Every future phase (uses docs/SCHEMA.md as the running schema reference and docs/BACKLOG.md as the tracked-deferral home)"
  - "End-of-phase human-verify checkpoint — confirms all 6 CLAUDE.md exit criteria (lines 159-168)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Architecture Decision Record (ADR) format — Status / Context / Decision / Consequences (positive + negative + neutral) / Alternatives Considered / Source Documents"
    - "Backlog discipline (CLAUDE.md #7) — every deferred item has a source citation (RESEARCH.md / Threat ID / Open Question) and a target milestone or phase; no orphan TODOs in code"
    - "Quickstart README pattern — clone → cp .env → make dev → make migrate → 3 URLs; six sentences max for the happy path"
    - "GitHub Actions service-container pattern for the api job — postgres:16-alpine + pg_isready healthcheck matches local dev exactly (RESEARCH.md Pitfall 10 — Python version drift mitigation)"
    - "Pip cache keyed on BOTH requirements.txt AND requirements-dev.txt — cache invalidates when either file changes"
    - "Phase 0 CI verifies CODE (ruff + ruff format --check + pyright + pytest + tsc + eslint), NOT container orchestration — docker compose orchestration is verified by the human-verify checkpoint (one human-gate per phase)"

key-files:
  created:
    - "docs/ARCHITECTURE.md"
    - "docs/SCHEMA.md"
    - "docs/BACKLOG.md"
    - "docs/MIGRATIONS.md"
    - "docs/adr/001-modular-monolith.md"
    - "README.md"
    - ".github/workflows/check.yml"
  modified: []

key-decisions:
  - "Bump pnpm/action-setup@v4 version from 9 → 10 (RESEARCH.md Pattern 10 line 981 had `version: 9`; pnpm 10 is the current major as of 2026-05-23, matches `corepack enable pnpm` default on Node 22)"
  - "Phase 0 CI does NOT invoke `docker compose` or `docker build` — it runs ruff/ruff-format/pyright/pytest/tsc/eslint against the source. Container orchestration is verified once per phase by the human-verify checkpoint (Task 3). Adding docker-in-docker to CI would be enterprise complexity for no Phase 0 benefit; deferred to Phase 12+ deployment-flow work."
  - "ARCHITECTURE.md §9 'Conventions / Dates' phrases the transaction_date + post_date rule as a single inline sentence (`transaction_date` (DATE — purchase date) and `post_date` (TIMESTAMPTZ — bank settlement timestamp)) so the plan's automated grep gate `grep -qi 'transaction_date.*post_date|post_date.*transaction_date'` matches on a single line; the original two-line phrasing was semantically identical but failed the gate."
  - "BACKLOG.md uses GitHub-style `- [ ]` checkbox items with bold-italic source citations — grep-able for ticket extraction, and the format degrades gracefully if rendered as plain text"
  - "README.md project-structure tree is a *summarized* version of ARCHITECTURE.md §2 (showing only top-level directories with one-line role descriptions) so the README stays at quickstart length while ARCHITECTURE.md owns the deeper tree"

patterns-established:
  - "Pattern H — Documentation tier separation: README.md is quickstart (5-minute read), docs/ARCHITECTURE.md is the running architectural reference (30-minute read), docs/SCHEMA.md tracks schema as it grows, docs/MIGRATIONS.md is the migration rule book, docs/BACKLOG.md is the deferral ledger, docs/adr/*.md is the durable decision record. Each future phase adds to these files in place — never creates parallel documentation."
  - "Pattern I — CI workflow shape: GitHub Actions, two parallel jobs (api + web), service-container Postgres pinned to the same major as local dev (Pitfall 10), pip + pnpm caches keyed on the actual dep manifest paths. Phase 1+ extends this same workflow with additional jobs (deploy preview, integration tests, etc.) rather than spinning up parallel workflow files."
  - "Pattern J — ADR storage: docs/adr/NNN-kebab-case-title.md, sequential NNN (001 onward). Status starts as 'Proposed' during discussion, flips to 'Accepted' when merged. A 'Superseded' status references the new ADR. Never rewrite an Accepted ADR — supersede it."

requirements-completed: [INFRA-08]

# Metrics
duration: ~9min (Task 1 + Task 2; Task 3 checkpoint stop)
completed: 2026-05-24
---

# Phase 00 Plan 06: Phase 0 Documentation + CI Workflow + End-of-Phase Checkpoint

**Six documentation files (ARCHITECTURE / SCHEMA / BACKLOG / MIGRATIONS / ADR-001 / README) and the GitHub Actions CI workflow are shipped. The end-of-phase human-verify checkpoint (Task 3) is the gate that turns over Phase 0 — agent has STOPPED at the checkpoint and is returning structured state to the developer for the 10-step verification.**

## Performance

- **Duration:** ~9 min (Task 1 + Task 2 + SUMMARY)
- **Started:** 2026-05-24T02:53:01Z
- **Completed (Tasks 1-2):** 2026-05-24T03:01:57Z
- **Checkpoint reached:** Task 3 (human-verify) — agent paused, awaiting developer
- **Tasks completed:** 2 of 3 (Task 3 is a human-verify checkpoint, not work for the agent)
- **Files created:** 7
- **Files modified:** 0

## Accomplishments

- **Phase 0 documentation set is complete** — future contributors can read
  `docs/ARCHITECTURE.md` to understand the running architecture, `docs/SCHEMA.md`
  to see the road ahead through Phase 11, `docs/MIGRATIONS.md` to learn the
  discipline (six rules + RLS GUC convention with the non-negotiable
  `missing_ok` flag), `docs/BACKLOG.md` to find every tracked deferral with
  its source citation, and `README.md` to bootstrap in five minutes.
- **`docs/adr/001-modular-monolith.md` records the architectural decision**
  for the modular-monolith pattern over microservices, Django/Rails, and
  Phase-1-immediate-multi-tenant alternatives. Accepted 2026-05-23. This is
  the first ADR; the pattern is set for all future decisions.
- **`.github/workflows/check.yml` ships** with two parallel jobs (`api` +
  `web`). The api job uses a `postgres:16-alpine` service container with
  `pg_isready` healthcheck (matches local dev Postgres exactly — RESEARCH.md
  Pitfall 10 mitigation). The api job applies the Alembic baseline before
  pytest so `test_baseline_migration_applied` has a `_phase0_marker` row to
  query. CI does NOT invoke `docker compose` or `docker build` — Phase 0 CI
  verifies the code; container orchestration is verified by the human-verify
  checkpoint.
- **INFRA-08 is fully satisfied** — `docs/MIGRATIONS.md` documents
  nullable-first column adds, `CREATE INDEX CONCURRENTLY`, NOT VALID +
  VALIDATE for constraints, two-phase column drops, FK ON DELETE semantics,
  and procrastinate-deferred backfills. The RLS GUC convention with the
  `, true` missing_ok flag is documented as non-negotiable per RESEARCH.md
  Pitfall 9.
- **All four CLAUDE.md exit criteria that this plan owns are met:**
  exit criterion #6 (docs/ARCHITECTURE.md populated) is green via the doc
  set; exit criteria #1, #2, #3, #4, #5 are verified at the Task 3
  human-verify checkpoint (the remaining 5 are runtime checks the developer
  performs).

## Task Commits

Each task was committed atomically:

1. **Task 1 — Phase 0 docs (ARCHITECTURE, SCHEMA, BACKLOG, MIGRATIONS, ADR-001) + README** — `bfbdcb8` (docs)
2. **Task 2 — `.github/workflows/check.yml` (api + web CI on push + PR)** — `7440f83` (ci)
3. **Task 3 — End-of-phase human-verify checkpoint** — **NOT COMMITTED — paused, awaiting developer verification of all 10 steps**

_Plan metadata commit (this SUMMARY.md) lands separately in the orchestrator-owned merge commit after the wave merges. Per parallel_execution protocol, this executor does NOT modify STATE.md or ROADMAP.md._

## Files Created / Modified

### Created (7 files)

- `docs/ARCHITECTURE.md` (~430 lines) — running architecture reference; 10
  sections (Overview, Directory Layout, Backend, Frontend, Database, Logging,
  CORS, Architectural Responsibility Map, Conventions, Phase 0 status).
- `docs/SCHEMA.md` (~155 lines) — Phase 0 state + per-phase table reservations
  through Phase 11 + mandatory schema conventions.
- `docs/BACKLOG.md` (~110 lines) — 16 tracked Phase 0 deferred items with
  RESEARCH.md / Threat-ID / Open-Question citations and target milestones.
- `docs/MIGRATIONS.md` (~210 lines) — INFRA-08: six discipline rules + RLS
  GUC convention (with the `, true` missing_ok flag flagged as non-negotiable)
  + naming convention + run instructions + pre-merge checklist.
- `docs/adr/001-modular-monolith.md` (~135 lines) — Accepted 2026-05-23.
  Records the modular-monolith decision; alternatives considered include
  microservices, Django/Rails, Phase-1-immediate-multi-tenant.
- `README.md` (~110 lines) — quickstart + prerequisites + make-target table +
  project structure tree + documentation links + phase progress table +
  security note + repo link.
- `.github/workflows/check.yml` (74 lines) — GitHub Actions; api + web
  parallel jobs; `pull_request` + `push.branches: [main]`; postgres:16-alpine
  service container; pip + pnpm caches; pnpm/action-setup@v4 version: 10.

### Modified (0 files)

(No existing files were edited. CLAUDE.md is intentionally untouched —
the BACKLOG entry "CLAUDE.md cleanup pass" tracks the legacy `finbrain`
references that will be patched at Phase 1 start.)

## Decisions Made

- **Bumped `pnpm/action-setup@v4` `version:` from 9 → 10.** RESEARCH.md
  Pattern 10 line 981 specified `version: 9`; pnpm 10 is the current major
  release line as of 2026-05-23 and matches what `corepack enable pnpm`
  installs on Node 22. The plan's acceptance criteria explicitly allows
  either (line 366) and recommends 10. No functional difference for Phase 0
  (no pnpm features unique to 10 are exercised); future-compatible.
- **Phase 0 CI does NOT invoke `docker compose` or `docker build`.** The
  workflow runs ruff/ruff-format/pyright/pytest/tsc/eslint directly against
  the source. Reasons: (a) container orchestration is verified once per
  phase by the human-verify checkpoint — duplicating that in CI is double
  work; (b) docker-in-docker on GitHub-hosted runners is slow and flaky;
  (c) the api job's Postgres service container gives the api tests a real
  Postgres without needing the full compose stack. Deferred to Phase 12+
  deployment-flow work.
- **ARCHITECTURE.md §9 phrases the transaction_date + post_date rule as a
  single inline sentence** to satisfy the plan's `<verify>` automated grep
  `grep -qi 'transaction_date.*post_date|post_date.*transaction_date'`,
  which only matches when both identifiers appear on the *same* line. The
  original two-line phrasing was semantically identical but failed the
  literal-substring gate (captured below as Deviation #1).
- **BACKLOG.md uses GitHub-style `- [ ]` checkbox items.** Each item has
  bold title + italic source citation + Target milestone. Grep-able
  (`grep '^- \[ \]' docs/BACKLOG.md` enumerates the list); degrades
  gracefully to plain text on terminals without checkbox rendering.
- **README.md project-structure tree is a summarized version of
  ARCHITECTURE.md §2** (top-level directories + one-line role descriptions)
  so the README stays at quickstart length while ARCHITECTURE.md owns the
  deeper file-level tree. Avoids duplication of the full tree in two places.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Reflowed transaction_date / post_date phrasing in `docs/ARCHITECTURE.md` to satisfy a single-line grep gate**

- **Found during:** Task 1 verify gate run.
- **Issue:** The plan's automated verify includes
  `grep -qi 'transaction_date.*post_date\|post_date.*transaction_date'
   docs/ARCHITECTURE.md`. `grep` is line-oriented; the regex only matches
  if both substrings appear on the *same* physical line. My initial
  Conventions §Dates block phrased the rule across two lines
  (`...store BOTH \`transaction_date DATE\` (when the user made the
  purchase) and \`post_date TIMESTAMPTZ\` (when the bank settled it).`),
  which was semantically perfect but failed the gate.
- **Fix:** Reflowed to a single line:
  `Transactions always store BOTH \`transaction_date\` (DATE — purchase
  date) and \`post_date\` (TIMESTAMPTZ — bank settlement timestamp).`
  Identical meaning; the grep gate now passes.
- **Files modified:** `docs/ARCHITECTURE.md`
- **Verification:** Re-ran the Task 1 verify chain end-to-end — all 32
  checks pass.
- **Committed in:** `bfbdcb8` (fix applied before the commit was made).

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking issue caused by my
initial multi-line phrasing clashing with the plan's line-oriented grep
verify gate).

**Impact on plan:** Zero functional / semantic impact. The reflow preserves
the architectural intent and the rule's full meaning. No content was
removed; no acceptance criterion was relaxed.

## Issues Encountered

- None. Both tasks executed cleanly. The plan's automated verify gates ran
  green after the one reflow fix above. PyYAML was not available on the host
  for the optional `python3 -c "import yaml" check`, so the workflow YAML
  was validated via a structural check (no tabs in indentation; no obvious
  malformed lines; structure matches RESEARCH.md Pattern 10). GitHub's own
  YAML validation will run on first push.

## User Setup Required

The human-verify checkpoint (Task 3) requires the developer to run 10
verification steps. The agent has STOPPED at the checkpoint and is awaiting
the `approved` (or failure report) signal. See the CHECKPOINT REACHED block
below for the full step list.

## Threat Mitigations Realized

| Threat ID | Disposition | How this plan realized it |
|-----------|-------------|---------------------------|
| T-00-27 (Info Disclosure: CI placeholder SECRET_KEY) | accept | Workflow YAML embeds `SECRET_KEY: ci-secret-do-not-use-in-prod` — clearly labeled as not-for-production. Real prod secrets will use GitHub repository secrets (`${{ secrets.SECRET_KEY }}`) in Phase 12+ deployment workflows. |
| T-00-28 (Tampering: third-party GitHub Actions) | accept | All actions used are first-party-equivalent: `actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4` are GitHub-owned; `pnpm/action-setup@v4` is npm-foundation-owned. SHA-pinning is tracked in `docs/BACKLOG.md` for v1.0 ship hardening. |
| T-00-29 (Info Disclosure: docs leak secrets) | mitigate | Verified at Task 1 commit time — neither `README.md` nor `docs/ARCHITECTURE.md` contains literal credentials beyond the documented dev defaults (`pranav_dev_password` mentioned in README's Adminer login example, with an explicit warning to rotate before non-localhost deployment). |
| T-00-30 (Repudiation: commit signing) | accept | Commit signing is a repo-level policy (not a Phase 0 code deliverable). Phase 12+ deployment work will add branch protection + signing requirements. |
| T-00-31 (DoS: CI job timeout) | accept | GitHub Actions default 360-minute timeout is far above the ~3-5 minute Phase 0 job runtime. pip + pnpm caches keyed on dep manifests speed subsequent runs. |

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or
schema changes at trust boundaries were introduced by this plan. All surface
added (documentation files, CI workflow YAML) sits in the build/CI trust
boundary already mapped in the Phase 0 threat model.

## Known Stubs

None. The 7 files this plan creates are content-complete:

- `docs/ARCHITECTURE.md` is a full architectural reference, not a TOC.
- `docs/SCHEMA.md` lists every Phase 1-11 table by name with purpose; the
  per-table column lists are intentionally deferred to the phases that
  create them (this is the documented contract — SCHEMA.md grows as tables
  are added).
- `docs/BACKLOG.md` has 16 concrete items with citations — none are
  placeholder "TODO add items later".
- `docs/MIGRATIONS.md` is the full rule book (six rules + RLS convention +
  naming + run instructions + pre-merge checklist).
- `docs/adr/001-modular-monolith.md` is a full ADR; no sections are
  "TBD".
- `README.md` is a complete quickstart.
- `.github/workflows/check.yml` is functionally complete; first run on
  next push to main (assuming the worktree merges to main) will exercise it.

## CHECKPOINT REACHED

**Type:** human-verify
**Plan:** 00-06
**Progress:** 2/3 tasks complete (Task 3 is the human-verify checkpoint and is not work for the agent)

### Completed Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Phase 0 docs (ARCHITECTURE / SCHEMA / BACKLOG / MIGRATIONS / ADR-001 / README) | `bfbdcb8` | `docs/ARCHITECTURE.md`, `docs/SCHEMA.md`, `docs/BACKLOG.md`, `docs/MIGRATIONS.md`, `docs/adr/001-modular-monolith.md`, `README.md` |
| 2 | `.github/workflows/check.yml` (api + web CI) | `7440f83` | `.github/workflows/check.yml` |

### Current Task

**Task 3:** End-of-Phase Human-Verify Checkpoint — confirm all six CLAUDE.md exit criteria
**Status:** awaiting verification
**Blocked by:** Developer must run the 10 verification steps below and confirm each succeeds

### Checkpoint Details

This is the **single human gate for Phase 0** (per
`workflow.human_verify_mode=end-of-phase`). The agent has automated everything
it can automate; the remaining checks require a human to (a) boot the
4-container stack, (b) verify all four containers run, (c) verify the
3 URLs render correctly, (d) verify `make migrate` applies the baseline,
(e) verify `make check` passes, and (f) verify the doc files are coherent
prose. The agent cannot do any of these — they all require interactive
browser inspection or running Docker, which is outside the parallel
executor's permitted surface.

### How to Verify (run in order from the repo root)

> NOTE TO DEVELOPER: These steps assume the worktree's commits have been merged to a branch where Docker can build (the parallel executor cannot run `docker build` itself). If you're verifying directly from the worktree branch, that's fine too — but `make dev` needs Docker access on your host.

**Step 1 — Set up env:**

```bash
cp .env.example .env
# (no need to edit — the dev defaults work)
```

**Step 2 — Boot the stack (CLAUDE.md exit criterion #1):**

```bash
make dev
```

Wait until you see logs from all 4 services. In a second terminal:

```bash
docker compose -f docker/docker-compose.yml --env-file .env ps
```

**EXPECTED:** 4 services listed. Postgres shows `Up (healthy)`. api/web/adminer show `Up` (no healthcheck on these in Phase 0).

**Step 3 — Apply migrations (CLAUDE.md exit criterion implied by INFRA-04):**

Once Postgres is healthy:

```bash
make migrate
```

**EXPECTED:** Output includes a line like `INFO  [alembic.runtime.migration] Running upgrade  -> 0001_phase0_baseline`. Exit code 0.

**Step 4 — Hit /health (CLAUDE.md exit criterion #3):**

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

**EXPECTED:**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "dev",
  "db_connected": true
}
```

`db_connected: true` is the load-bearing assertion — proves the FastAPI app, the async DB engine, asyncpg, and the Postgres container all communicate.

**Step 5 — Verify the web page (CLAUDE.md exit criterion #2):**

Open a browser to `http://localhost:3000`.

**EXPECTED:**

- Page renders without error (no Next.js error overlay)
- Heading reads: "Personal Resource & Asset Navigator for Abundant Value"
- Subtitle: "Coming soon."
- A code block shows the JSON output from /health (matching Step 4's curl result)

If the web page shows "API unavailable" instead of the JSON, verify Step 4 succeeds — the web container fetches via `API_URL_INTERNAL=http://api:8000`; if Step 4 works from the host, restart the web container: `docker compose -f docker/docker-compose.yml --env-file .env restart web`.

**Step 6 — Verify Adminer (CLAUDE.md exit criterion #4):**

Open a browser to `http://localhost:8080`.

**EXPECTED:** Adminer login page. Fields:

- System: PostgreSQL (default)
- Server: `postgres` (pre-filled via `ADMINER_DEFAULT_SERVER`)
- Username: `pranav`
- Password: `pranav_dev_password`
- Database: `pranav`

Click "Login". **EXPECTED:** Adminer dashboard listing the `pranav` database with two tables (`_phase0_marker` and `alembic_version`).

Click on `_phase0_marker`. **EXPECTED:** One row with `id=1`, `applied_at` populated, `note` starting with "Phase 0 migration succeeded".

**Step 7 — Verify make check passes (CLAUDE.md exit criterion #5):**

From the repo root (with host-side deps installed):

```bash
# Install api deps host-side (one-time):
pip install -r apps/api/requirements.txt -r apps/api/requirements-dev.txt
# Install web deps host-side (one-time, if not already done):
cd apps/web && pnpm install --frozen-lockfile && cd ../..

make check
```

**EXPECTED:** Both `check-api` and `check-web` exit 0. `ruff` prints "All checks passed!"; `pyright` prints "0 errors, 0 warnings"; pytest collects and runs 4 tests (`test_health_ok`, `test_baseline_migration_applied`, `test_request_id_bound_via_middleware`, `test_env_example_documents_all_required_keys`) — all PASS. `tsc` and `eslint` print no errors.

NOTE: For the api tests to pass, the Docker stack MUST be up (the tests use the in-process app via httpx ASGITransport, but the database queries need a real Postgres on localhost:5432 — the docker-compose maps Postgres to localhost:5432, so this works concurrently with `make dev`).

**Step 8 — Verify docs (CLAUDE.md exit criterion #6):**

Check these files exist and are non-empty:

```bash
wc -l docs/ARCHITECTURE.md docs/SCHEMA.md docs/BACKLOG.md docs/MIGRATIONS.md docs/adr/001-modular-monolith.md README.md
```

**EXPECTED:** All non-zero line counts. `docs/ARCHITECTURE.md` should be the largest (~400+ lines).

Open `docs/ARCHITECTURE.md` and `README.md` and skim for content quality. Each should be coherent prose, not lorem ipsum.

**Step 9 — Tear down cleanly:**

```bash
make down
```

**EXPECTED:** Containers stop and are removed. The `postgres_data` volume persists (verify with `docker volume ls | grep postgres_data`).

**Step 10 — Re-up to verify persistence:**

```bash
make dev
# in a second terminal:
curl -s http://localhost:8000/health | python3 -c "import sys, json; d=json.load(sys.stdin); assert d['db_connected'] is True"
```

**EXPECTED:** `db_connected` is still true; the migration's `_phase0_marker` row is still present (verify via `make shell-db` → `SELECT * FROM _phase0_marker;`).

### Common failures

- `make migrate` fails with "connection refused" → Postgres healthcheck didn't pass yet; wait 10s and retry (RESEARCH.md Pitfall 2)
- `make check` fails on pyright → likely a type-import path issue; check `pyright` output for specific line
- `http://localhost:3000` shows "API unavailable" → check `docker compose logs api` for crash; check `docker compose logs web` for fetch errors
- `http://localhost:8080` shows blank page → wait 5s for Adminer to start (no healthcheck on Adminer in Phase 0)

### Awaiting

The developer must run all 10 verification steps and reply with:

- `approved` — if all 10 steps pass; Phase 0 is officially closed and Phase 1 can begin
- `failed-on-step-N` — with the exact failure output, so the agent (or a fresh agent) can fix the underlying plan output and re-attempt

### Phase 0 verdict (provisional, pending Task 3 sign-off)

- **INFRA-01** (4-container stack via `make dev`) — pending Step 2 confirmation
- **INFRA-02** (FastAPI `/health` envelope) — pending Step 4 confirmation
- **INFRA-03** (`make check` runs lints + types + tests) — pending Step 7 confirmation
- **INFRA-04** (Alembic baseline applies via `make migrate`) — pending Step 3 confirmation
- **INFRA-05** (Adminer accessible at :8080) — pending Step 6 confirmation
- **INFRA-06** (`.env.example` documents all required keys) — Plan 01 satisfied; test_env_example_documents_all_required_keys re-confirms at Step 7
- **INFRA-07** (structlog JSON-in-prod + request_id middleware) — Plan 02 satisfied; test_request_id_bound_via_middleware re-confirms at Step 7
- **INFRA-08** (`docs/MIGRATIONS.md` documents nullable-first + CREATE INDEX CONCURRENTLY + GUC convention) — **THIS PLAN — satisfied via Task 1**
- **INFRA-09** (RLS GUC reserved + Phase 1 activation path documented) — Plan 03 satisfied; `docs/MIGRATIONS.md` §RLS Convention re-documents

If Steps 2-7 all succeed at the human-verify checkpoint, Phase 0 is **COMPLETE** and **Phase 1 can begin** under the Phase 0 architecture recorded in `docs/adr/001-modular-monolith.md`.

## Open Phase 1 prep notes

When Phase 1 starts, the following BACKLOG items should be addressed at the
top of the phase (small chores; clear the deck before auth code lands):

- **CLAUDE.md cleanup pass** — patch the legacy `finbrain` references in
  the embedded repo-tree block (line 39) and the `make shell-db` example
  (line 120) to match the post-rename Makefile and docker-compose.yml.
- **REQUIREMENTS.md count fix** — header says "71 total" but the file
  enumerates 73 requirements.
- **`import-linter` install + config** — needed once `auth/` joins
  `health/` under `apps/api/src/modules/`. Without it, the "no cross-module
  internal imports" rule is policy only.
- **Vitest + RTL + Playwright install** — Phase 1 ships the first UI logic
  (login form, signup form) and needs the test stack.
- **fastapi-mail maintenance check** — verify the package is still maintained
  before wiring it into Phase 1 invite emails. Switch to `aiosmtplib`
  directly if not.

The rest of `docs/BACKLOG.md` items target later phases or v1.0 ship.

## Next Phase Readiness

Once Task 3's checkpoint is `approved`:

- **Phase 1 (Auth + Household + RLS Activation)** can begin. It inherits:
  - The async DB engine + `get_session()` pattern from Plan 02
  - The Alembic baseline + RLS GUC convention from Plan 03 and `docs/MIGRATIONS.md`
  - The module-router pattern (`apps/api/src/modules/<name>/router.py`) from Plan 02
  - The CI workflow that will run Phase 1 PRs against postgres:16-alpine
  - The documentation tier separation (README quickstart / ARCHITECTURE running reference / SCHEMA per-phase growth / MIGRATIONS rule book / BACKLOG deferral ledger / ADR durable decisions)

## Self-Check: PASSED

- All 7 files declared in `key-files.created` exist on disk (verified via `[ -f <path> ]`):
  - `[FOUND] docs/ARCHITECTURE.md`
  - `[FOUND] docs/SCHEMA.md`
  - `[FOUND] docs/BACKLOG.md`
  - `[FOUND] docs/MIGRATIONS.md`
  - `[FOUND] docs/adr/001-modular-monolith.md`
  - `[FOUND] README.md`
  - `[FOUND] .github/workflows/check.yml`
- Both task commits found in `git log --oneline -3`:
  - `[FOUND] bfbdcb8` — Task 1 docs commit
  - `[FOUND] 7440f83` — Task 2 CI workflow commit
- HEAD is on `worktree-agent-a9121236b9de2727c` (per-agent branch, no protected-ref drift).
- Base matches the spawn-time root (`4d6770a30c34acff7eee5cd92df810d194e4b2ae`).
- No file deletions in either task commit (`git diff --diff-filter=D --name-only HEAD~2 HEAD` returned empty).
- Task 1 verify gate runs green (32 grep checks, all OK after the single reflow fix).
- Task 2 verify gate runs green (24 grep checks, all OK).
- The plan's `<key_links>` from frontmatter resolve correctly: `.github/workflows/check.yml` references `apps/api/requirements-dev.txt` via `pip install -r apps/api/requirements.txt -r apps/api/requirements-dev.txt`; `README.md` instructs `make dev` after `cp .env.example .env`.

---

*Phase: 00-repo-skeleton*
*Plan: 06*
*Completed (Tasks 1-2): 2026-05-24*
*Checkpoint (Task 3): awaiting developer verification*
