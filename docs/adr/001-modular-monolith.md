# ADR 001 — Modular Monolith over Microservices

- **Status:** Accepted
- **Date:** 2026-05-23
- **Deciders:** Project owner (solo developer at Phase 0)
- **Phase:** 0 (Repo Skeleton)

## Context

PRANAV ("Personal Resource & Asset Navigator for Abundant Value") is a
self-hostable personal finance application following the Bitwarden model:
open source, run-it-yourself or hosted. Phase 0 builds the repo skeleton on
which Phases 1-11 will incrementally land features (auth, accounts,
transactions, CSV import, rules engine, recurring transactions, budgets,
forecast, reports, bill-pay, onboarding).

Two design constraints shape this decision:

1. **Solo-developer velocity.** The project is a single-developer codebase
   for the foreseeable future. Refactor-across-boundaries is the dominant
   activity; cross-team-coordination cost does not exist.
2. **Self-hostability.** The user-facing target is a person running the app
   on their own hardware (or a cheap VPS). The deployment unit must be small
   enough that `docker compose up` is the complete install instruction. Each
   additional container is a fresh failure mode for someone who is not a
   sysadmin.

The architecture choice has to support fast feature iteration today, hard
multi-tenant data isolation (Postgres Row-Level Security), and a credible
scale-out path if the cloud-hosted version ever needs to handle thousands of
households.

## Decision

**PRANAV is a modular monolith.**

- **One deployable for the api.** `apps/api/` produces a single Docker image
  containing every business module. There is no per-feature service.
- **Modules live under `apps/api/src/modules/<name>/`.** Each module owns a
  router (`router.py`), its handlers, and any module-private helpers. A
  module **may not** import from another module's internal files.
- **Cross-module logic lives in `packages/domain/`.** When module `A` needs
  logic from module `B`, that logic is lifted into the pure-domain layer and
  imported from both sides. `packages/domain/` has zero DB imports, zero
  FastAPI imports, zero HTTP framework imports — it's pure Python.
- **Boundaries enforced by convention in Phase 0; by `import-linter` in
  Phase 1+.** Phase 0 has only one module (`health/`), so the constraint is
  dormant. The first cross-module concern arrives in Phase 1 (auth + household)
  and that's when `import-linter` lands.
- **Shared types in `packages/shared/`.** Pydantic schemas in `schemas.py`
  (backend), TypeScript types in `types.ts` (frontend). The shapes that
  cross the api/web wire boundary live here so both sides see the same
  definition.
- **The web app (`apps/web/`) is a separate process.** Next.js requires its
  own runtime; running it as a second deployable is unavoidable. But it
  shares the wire-format types via `packages/shared/` and is fetched by
  the same `make dev` orchestration.
- **Multi-tenancy via Postgres Row-Level Security**, not per-tenant
  databases. The `app.current_household_id` GUC convention reserved in
  Phase 0 (see [`docs/MIGRATIONS.md`](../MIGRATIONS.md) §RLS Convention) is
  the substrate; Phase 1 activates per-table policies.

## Consequences

### Positive

- **One deploy unit means one Dockerfile, one CI pipeline, one process to
  monitor.** The self-hoster runs `make dev` and gets four containers; the
  api container is the only thing that holds business logic.
- **Refactoring across modules is cheap.** Single repo, single language per
  layer, single typecheck pass. Lifting code from `modules/foo/` to
  `packages/domain/` is a file move — no inter-service contract negotiation,
  no version skew, no API versioning ceremony.
- **RLS handles multi-tenancy without per-tenant databases.** One Postgres
  instance, one schema, household isolation enforced at the row level. No
  schema-per-tenant fan-out, no database-per-tenant operational burden.
- **A future microservices split is cheap.** Because module boundaries are
  already enforced (by `import-linter` from Phase 1+), the modules can be
  lifted out one at a time if cloud-scale ever demands it. The shape of the
  monolith mirrors the shape of the eventual services — no big-bang rewrite.
- **Type sharing via `packages/shared/` keeps the wire boundary honest.**
  When a Pydantic schema changes, the TypeScript type must change too
  (manually in Phase 0; via codegen in a future improvement). No silent
  shape drift between api and web.

### Negative

- **Cannot scale individual modules independently.** If the forecast endpoint
  (Phase 8) becomes the chattiest endpoint and needs 10x the api workers,
  the whole api scales. Acceptable for the project's scale target — a
  personal finance app does not need per-endpoint horizontal scaling.
- **A single bad query can block the whole process.** Mitigated by async
  SQLAlchemy + the Postgres connection pool (10 base + 20 overflow). A slow
  query holds a connection, not a process. Pathological cases would need
  rate-limiting (deferred to v1.0, tracked in `BACKLOG.md`).
- **Local dev runs everything in containers.** Approximately 2GB of RAM is
  needed to run `make dev` happily (postgres + api + web + adminer). That's
  acceptable for the target audience (developers and tech-comfortable
  self-hosters) but excludes very-low-spec dev machines.
- **`import-linter` is enforcement-by-policy, not enforcement-by-runtime.**
  A developer could still import across module boundaries and the test suite
  would catch it (CI runs import-linter), but the violation isn't a Python-
  level error. The cost of full runtime enforcement (e.g., separate Python
  packages with no shared sys.path) was judged too high for the velocity
  gain.

### Neutral / observed

- **The api Dockerfile installs both `requirements.txt` and
  `requirements-dev.txt`.** This keeps `make check-api` runnable via
  `docker compose exec api`, at the cost of a larger image. Acceptable for
  Phase 0; revisit (drop dev deps from the runtime stage) as part of v1.0
  ship hardening.
- **The Phase 0 baseline migration creates a `_phase0_marker` singleton
  table** and reserves the RLS GUC via `COMMENT ON DATABASE`. No domain
  tables, no enforced policies — just a sentinel and a documentation
  contract. Phase 1 builds the first real schema on this foundation.

## Alternatives considered

### Microservices (rejected)

Separate api services per business module (auth-service, accounts-service,
transactions-service, …). Each with its own Postgres database, its own
deployment, its own observability surface.

- **Per-service Postgres** would force coordination of cross-domain queries
  (e.g., "list transactions in this account" spans two databases).
  Either rebuild that as an HTTP fan-out (slow, brittle) or duplicate state
  across services (sync hazard).
- **Service mesh** (Istio, Linkerd, even a managed Nomad/Consul setup) is
  enterprise complexity. A self-hoster does not run a service mesh.
- **Per-service deployment** multiplies the failure modes for a single
  developer to debug. The signal-to-noise of "which service crashed and why"
  is dramatically worse than a single api process.

The forecast view (Phase 8) is the chattiest endpoint and would be the
obvious first candidate for a separate service if scaling demanded it. But
async FastAPI handles thousands of concurrent forecast requests per process;
the scale at which a split becomes necessary is far beyond v1.0's design
target.

### Single Django (or Rails) monolith (rejected)

Conventional Django would give us ORM, admin, auth, and migrations out of
the box. Rails would give Convention Over Configuration and a single-command
scaffold.

- **Sync-first.** Django's async story is a Frankenstein graft; the ORM is
  still sync underneath. PRANAV's forecast endpoint (Phase 8) does
  hundreds of small queries to assemble a projection — async + asyncpg is
  the right shape for that load pattern. CLAUDE.md mandates async SQLAlchemy
  (constraint #3), which closes this option.
- **Django admin** would be a wonderful debugging tool but inviting a Django
  admin into a finance app feels like teaching it to bypass RLS. Better to
  build admin tooling at the application layer.
- **Built-in auth** would save Phase 1 code, but Django's user model is
  user-centric (not household-centric) and would need a custom user model
  the moment we wired `household_id` into every domain row.

### Phase 1 immediate multi-tenant (rejected)

Defer the RLS GUC convention to Phase 1 — Phase 0 just ships the api with
no multi-tenancy scaffolding.

- **Risk:** Phase 1's first migration would need to retrofit RLS into a
  schema we just wrote. Easier to reserve the convention now and write all
  Phase 1+ tables with `household_id + RLS policy` from day one.
- **Cost of doing it now:** ~10 lines of SQL (`COMMENT ON DATABASE`) in
  `0001_phase0_baseline.py`. Trivial. The Phase 0 reservation buys correctness
  with no real cost.

## Source documents

- [`CLAUDE.md`](../../CLAUDE.md) — repo-wide conventions; constraints #2,
  #3, #6 directly encode this decision.
- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — running architecture
  reference; this ADR is the durable record behind §1 Overview's
  "modular-monolith over microservices" framing.
- [`docs/MIGRATIONS.md`](../MIGRATIONS.md) §RLS Convention — the
  `app.current_household_id` GUC convention referenced above.
- `.planning/research/ARCHITECTURE.md` — the deeper architecture research
  this decision was distilled from.
- `.planning/phases/00-repo-skeleton/00-RESEARCH.md` — Phase 0 specific
  research; §Architectural Responsibility Map (lines 92-105) operationalizes
  the modular-monolith decision.

## Notes

This ADR is **accepted** as of Phase 0 sign-off (2026-05-23). Phase 1 starts
under this architecture. Any future decision to split out a service (or
collapse a module boundary) lands as a new ADR — this one stays as the
record of why the project started monolithic.
