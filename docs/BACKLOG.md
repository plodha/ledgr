# PRANAV — Backlog

> **The home for tracked deferred work.** CLAUDE.md constraint #7 — "No TODO
> comments that aren't tracked" — means any deferred work goes here, with a
> source citation (research doc, threat ID, or open question) and a target
> milestone or phase. Items leave this list either by getting done or by an
> explicit decision to drop them (recorded in an ADR if architectural).

## Phase 0 deferred items

Each item below was identified during Phase 0 research/execution and
explicitly deferred. Source citations point to `.planning/phases/00-repo-skeleton/00-RESEARCH.md`
unless noted otherwise.

- [ ] **Hardening: Dockerfile `USER` directive** — both `apps/api/Dockerfile`
      and `apps/web/Dockerfile` currently run as root inside the container.
      Add `USER nonroot` (or a numbered UID) in the v1.0 ship hardening pass.
      Reduces blast radius of a container escape.
      *Source: 00-RESEARCH.md Threat T-00-19, T-00-23 + STRIDE table
      "Container running as root" (line 1332).*
      **Target:** v1.0 ship hardening pass.

- [ ] **Next.js `output: "standalone"` in `next.config.ts`** — produces a
      significantly smaller production image (drops `node_modules`, copies
      only the standalone server bundle).
      *Source: 00-RESEARCH.md Web Dockerfile caveat (line 876).*
      **Target:** v1.0 ship.

- [ ] **Image digest pinning** — pin `python:3.12-slim`, `node:22-alpine`,
      `postgres:16-alpine`, `adminer:latest` to specific `sha256` digests.
      Currently we pin by tag (e.g., `postgres:16-alpine`), which is mutable
      and lets a re-tagged upstream image change the build silently.
      *Source: 00-RESEARCH.md V14 Configuration note (line 1321) + Threat
      T-00-22.*
      **Target:** v1.0 ship hardening pass (alongside the `USER` directive).

- [ ] **Pre-commit hooks** — install `pre-commit` framework and configure
      `ruff format`, `ruff check`, `prettier` (if adopted), and a secret
      scan via `gitleaks`. Catches misformatted commits and leaked secrets
      before they reach the remote.
      *Source: 00-RESEARCH.md Open Question 5 (line 1221).*
      **Target:** Milestone close (post-Phase 11, pre-v1.0).

- [ ] **`make backup` target** — `pg_dump` of the `postgres_data` volume
      with a documented restore procedure. Important for self-hosters who
      run on a single machine without managed backups.
      *Source: 00-RESEARCH.md Open Question 2 (line 1208) + Deferred Ideas
      line 76.*
      **Target:** v1.0 ship.

- [ ] **`import-linter` configuration** — install and configure once Phase 1
      introduces the second api module (`auth/` joins `health/`). The CLAUDE.md
      constraint "modules may not import from another module's internal files"
      is currently enforced by convention; import-linter mechanizes it.
      *Source: 00-RESEARCH.md Open Question 4 (line 1216).*
      **Target:** Phase 1 (when the second module arrives).

- [ ] **Vitest + React Testing Library + Playwright** — Phase 0's web app
      has no tests. Install the test stack at Phase 1 (when the first UI
      logic — login form — ships).
      *Source: 00-RESEARCH.md Validation Architecture (line 1261).*
      **Target:** Phase 1 (when first UI logic ships).

- [ ] **Re-verify Recharts version (v2 → v3 migration)** — STACK.md pinned
      `recharts>=2.13,<3`; the current floor on npm is 3.8.1. Verify the API
      compatibility for the forecast chart components before Phase 8 (Forecast
      View) starts.
      *Source: 00-RESEARCH.md Assumption A12 (line 1194).*
      **Target:** Phase 8 start (before any forecast UI work).

- [ ] **Auto-run `alembic upgrade head` on api container start** — currently
      `make migrate` is a separate developer step. Some self-hosters expect
      the api to migrate itself on boot. Defer because one-less-moving-part
      is the right Phase 0 tradeoff; revisit at v1.0 ship.
      *Source: 00-RESEARCH.md Open Question 3 (line 1212) + Assumption A3
      (line 1185).*
      **Target:** v1.0 ship.

- [ ] **Verify `procrastinate` supports Postgres 16 partitioning** — before
      Phase 4 worker work begins. If transaction tables ever need
      partitioning (multi-household scale, cloud-hosted version), the job
      queue must coexist gracefully.
      *Source: 00-RESEARCH.md Confidence Notes (line 494).*
      **Target:** Phase 4 (CSV Import + Background Worker) — research step
      before code.

- [ ] **Verify `fastapi-mail` is still maintained** — its last visible
      release pattern was 2023-2024. Before Phase 1 invite emails ship,
      either confirm active maintenance or switch to a maintained alternative
      (e.g., `aiosmtplib` directly).
      *Source: 00-RESEARCH.md Confidence Notes (line 490).*
      **Target:** Phase 1 (Auth + Household) — research step before email
      code.

- [ ] **CLAUDE.md cleanup pass** — the repo-tree section uses `finbrain/`
      as the root directory name (legacy project name); should be `ledgr/`
      or kept generic. The `make shell-db` example references the
      `finbrain` Postgres user; the Makefile has already been patched to
      `pranav`, but CLAUDE.md's example block hasn't been updated to match.
      *Source: 00-RESEARCH.md Open Question 6 (lines 1226-1229).*
      **Target:** Phase 1 start — quick cleanup pass before any auth code lands.

- [ ] **REQUIREMENTS.md count fix** — the file states "71 total" requirements
      but enumerates 73. Verify the count and update either the header or the
      list.
      *Source: STATE.md Blockers/Concerns + ROADMAP.md line 219.*
      **Target:** Phase 1 start — alongside the CLAUDE.md cleanup pass.

- [ ] **Adminer port-collision documentation** — `8080` is a common port
      (Jenkins, Tomcat). If `make dev` fails with "port already allocated",
      the README should document the `ADMINER_PORT` override pattern.
      *Source: 00-RESEARCH.md Pitfall 7 (lines 1120-1123).*
      **Target:** v1.0 ship (or whenever first user reports the collision).

- [ ] **CI workflow: branch protection** — `.github/workflows/check.yml`
      runs on push + PR, but the repo's branch protection rules (require
      passing checks before merge to `main`) are not configured by code.
      The repo owner must enable them in the GitHub Settings UI. Document
      this in the README's "Setup" section once the repo goes public.
      *Source: 00-06-PLAN.md Task 2 acceptance criteria (line 375).*
      **Target:** Repo public-launch checklist.

- [ ] **CI workflow: pin GitHub Actions by SHA** — `actions/checkout@v4`,
      `actions/setup-python@v5`, `actions/setup-node@v4`, `pnpm/action-setup@v4`
      are tag-pinned. For supply-chain hardening (T-00-28), pin to specific
      SHA digests so a malicious re-tag cannot execute new code in CI.
      *Source: 00-06-PLAN.md threat model T-00-28 (line 527).*
      **Target:** v1.0 ship hardening pass.

## Architectural decisions log

When a deferred item is dropped (decided "no, we won't do this") rather than
done, the rationale lands in an ADR under `docs/adr/`. The first ADR
(`001-modular-monolith.md`) records the Phase 0 decision to build a modular
monolith rather than microservices.

---

*Last updated: 2026-05-24 (Phase 0 closeout). Add items here with a source
citation and a target phase or milestone — never as orphaned TODOs in code.*
