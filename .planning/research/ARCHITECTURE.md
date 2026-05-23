# Architecture Research — Personal Finance App

**Project:** PRANAV (Personal Resource & Asset Navigator for Abundant Value)
**Researched:** 2026-05-23
**Confidence:** MEDIUM (Context7 / WebSearch unavailable during research; recommendations rest on well-established Python/FastAPI patterns from training data. Validate version-pinning against current docs in Phase 0.)

> **Research tooling note:** WebSearch and the Context7 MCP/CLI were unavailable during this run. Findings draw on Python/FastAPI/SQLAlchemy 2.0 ecosystem knowledge through January 2026. Anything marked LOW confidence should be re-verified before phase execution.

---

## Component Map

The system is a **modular monolith**: one deployable FastAPI process, internally partitioned into modules that communicate only through `packages/domain/`. Long-running work (sync, OCR/LLM, forecast warm-up) runs in a sibling worker process that shares the same database and the same `packages/domain` and `packages/db` code.

```
┌───────────────────────────────────────────────────────────────────────┐
│                          CLIENT (Next.js 14)                          │
│                  Server Components + RSC fetch /api/*                 │
└─────────────────────────────────┬─────────────────────────────────────┘
                                  │ HTTPS (JSON)
                                  ▼
┌───────────────────────────────────────────────────────────────────────┐
│                       apps/api (FastAPI process)                      │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  src/modules/<name>/                                            │  │
│  │  ─ router.py      (HTTP only — parse, validate, return)         │  │
│  │  ─ service.py     (orchestrates domain + db; per-module)        │  │
│  │  ─ deps.py        (FastAPI dependencies: session, current user) │  │
│  │                                                                 │  │
│  │  health · auth · households · accounts · categories ·           │  │
│  │  transactions · imports · rules · scheduled · forecast ·        │  │
│  │  bills · connectors · receipts · tracked_items · invest         │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │              packages/domain/  (pure business logic)            │  │
│  │  ─ accounts (net worth)                                         │  │
│  │  ─ categorization (rule evaluator — pure fn)                    │  │
│  │  ─ reconciliation (dedupe, pending→posted, merge)               │  │
│  │  ─ forecast (engine: balances+scheduled+spend → projection)     │  │
│  │  ─ connectors (Connector ABC + RawTransaction/RawBalance DTOs)  │  │
│  │  ─ money (cents↔Decimal helpers — single source)                │  │
│  │  ─ dates (transaction_date/post_date helpers)                   │  │
│  │  ─ household (access guard — household_id check)                │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  packages/db/  (SQLAlchemy 2.0 async models + Alembic)          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────┬─────────────────────────┘
                          │                   │
                          ▼                   ▼
                ┌──────────────────┐  ┌────────────────────────────────┐
                │   PostgreSQL 16  │  │   apps/worker (same image)     │
                │  (single DB,     │◀─│   ARQ on Redis  OR  pg-jobs    │
                │   household_id   │  │   - nightly Connector.sync()   │
                │   on every row)  │  │   - OCR/LLM receipt parse      │
                │                  │  │   - forecast warm-up           │
                └──────────────────┘  │   - rule re-apply              │
                                      └────────────────────────────────┘
                                                   │
                                                   ▼
                                      ┌────────────────────────────────┐
                                      │  External (per-tenant, BYO):   │
                                      │  Plaid · SimpleFIN · Anthropic │
                                      │  / OpenAI · SMTP-in            │
                                      └────────────────────────────────┘

      ┌──────────────────────────────────┐
      │  Object Storage (abstract iface) │
      │  - LocalFSStorage  (self-host)   │
      │  - S3Storage       (cloud)       │
      └──────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Talks To |
|-----------|---------------|----------|
| `apps/web` (Next.js) | UI, server components, fetches `/api/*` | `apps/api` over HTTP |
| `apps/api` modules | HTTP shape: parse, validate, authorize, return | `packages/domain`, `packages/db` (read-only models), `packages/shared` |
| `packages/domain` | Pure business logic — no DB session, no HTTP, no I/O | DTOs from `packages/shared`; receives data as args |
| `packages/db` | SQLAlchemy 2.0 async models, repositories, Alembic migrations | Postgres |
| `packages/shared` | Pydantic schemas (BE) + TypeScript types (FE) | nobody (leaf) |
| `apps/worker` | Background jobs (ARQ recommended) | `packages/domain`, `packages/db`, external APIs |
| `Connector` impls | Provider-specific I/O (Plaid, SimpleFIN, CSV) | External APIs / files; expose `RawTransaction`/`RawBalance` |
| `ObjectStorage` iface | Receipt blobs | Filesystem (self-host) or S3-compatible (cloud) |
| Postgres | System of record + job queue (if pg-jobs) + caches | — |

**Hard rule:** `packages/domain/*` must be importable in a unit test with no DB and no network. If a domain function needs data, the caller hands it in. Confidence: HIGH — directly mandated by `CLAUDE.md` and is the standard hexagonal/clean-architecture practice.

---

## Data Flow

### Read path (e.g. `GET /forecast?days=90`)
1. Next.js server component fetches `/api/forecast?days=90` with the user's session cookie.
2. FastAPI middleware resolves the session → `current_user` and `current_household` (the active household).
3. `forecast.router` accepts the request, calls `forecast.service.get_forecast(session, current_household, days=90)`.
4. The service performs scoped reads via repository functions (`list_accounts(household_id)`, `list_scheduled(household_id)`, `avg_spend_by_category(household_id, last_n_days=90)`) — every query filters on `household_id`.
5. Data is passed to `packages/domain/forecast/engine.py` as plain DTOs; the engine returns a `ForecastResult`.
6. Service serializes via Pydantic schema from `packages/shared/schemas.py` and returns.
7. (Optional cache: see "Caching the Forecast" below.)

### Write path (e.g. CSV import)
1. `POST /imports/csv` uploads file → `imports.service.create_import_batch()` stores file + creates `import_batch` row.
2. Service enqueues a background job: `enqueue("process_csv_import", batch_id)`.
3. Returns 202 with batch_id; UI polls or streams progress.
4. Worker picks job → loads `import_batch` → calls `packages/domain/csv/parser.py` → calls `packages/domain/reconciliation/dedupe.py` → bulk inserts transactions inside one transaction → calls `packages/domain/categorization/apply_rules.py` for each new transaction → marks batch `complete`.
5. UI long-poll/SSE sees `complete` and refreshes.

### Connector sync (nightly)
1. Scheduler fires `sync_all_connectors()` per household.
2. Worker resolves a concrete `Connector` (Plaid/SimpleFIN) from the `connector` row's `type`, decrypts credentials.
3. Calls `connector.sync(connector_id)` — implementation returns `RawTransaction[]` + `RawBalance[]`.
4. `packages/domain/reconciliation` merges into `transaction` table (dedupe, pending→posted remap, preserve user notes).
5. `packages/domain/categorization.apply_rules` runs on new rows.
6. Cached forecast (if any) for that household is invalidated.

### Receipt parsing
1. `POST /receipts` uploads image → stored via `ObjectStorage` interface (local FS path or s3:// URI).
2. `receipt` row inserted, status=`pending_parse`. Job enqueued.
3. Worker: OCR (or structured parser for Costco/Amazon) → if needed, LLM call with BYO key from settings → returns line items.
4. Status=`needs_confirmation`. UI shows parsed items; user accepts.
5. Acceptance writes `line_item` rows, attaches to transaction, fires `tracked_item` price observation hooks.

### Direction rules
- HTTP/UI → service → domain → repository → DB. Never the reverse.
- Worker uses the same domain + repository layer (no separate logic path).
- A connector never reads `transaction` rows — it returns raw provider data; reconciliation owns the merge.

---

## Module Structure Recommendation

Confirm the `CLAUDE.md` direction. Each module under `apps/api/src/modules/<name>/` follows the same skeleton:

```
apps/api/src/modules/<name>/
├── __init__.py
├── router.py          # FastAPI APIRouter — HTTP only
├── service.py         # Orchestration: composes domain + repos; per-module
├── deps.py            # FastAPI Depends for this module (e.g., load_account)
├── repository.py      # OPTIONAL: module-scoped queries; for cross-module
│                      # queries, lift into packages/db/repositories/
└── (no models.py — all SQLAlchemy models live in packages/db/models/)
```

### Suggested Phase-1+ module list

```
modules/
├── health/             # Phase 0 — already planned
├── auth/               # Phase 1 — register/login/session
├── households/         # Phase 1 — membership, invites (UI in Phase 13)
├── accounts/           # Phase 2
├── categories/         # Phase 3
├── transactions/       # Phase 3 — manual CRUD; also receives writes from imports/connectors
├── imports/            # Phase 4 — CSV upload + mapping
├── rules/              # Phase 5 — rule CRUD + "re-apply" trigger
├── scheduled/          # Phase 6 — scheduled_transaction CRUD + generator endpoint
├── forecast/           # Phase 7 — read-only; calls domain.forecast
├── bills/              # Phase 8 — bill reminders view
├── connectors/         # Phase 9, 11 — Connector CRUD; provider switch lives in domain
├── receipts/           # Phase 12 — upload + confirm
├── tracked_items/      # Phase 10
└── investments/        # Phase 14
```

### Inter-module communication rules

1. A module **never** imports from `apps/api/src/modules/<other>/` (enforce with an import-linter rule in CI).
2. Cross-module logic lives in `packages/domain/`. Example: when an import batch produces transactions, the `imports` module calls `packages/domain/reconciliation.merge_raw_transactions()` and `packages/domain/categorization.apply_rules()` — it does **not** call `transactions.service`.
3. Cross-module data access uses repository functions in `packages/db/repositories/<entity>.py`. Modules call repositories; modules don't call other modules' services.
4. Pydantic request/response schemas live in `packages/shared/schemas.py` (`schemas/transactions.py`, `schemas/accounts.py` etc. — split file once it grows past ~300 lines).

Confidence: HIGH — this matches the constraint set in `CLAUDE.md` and standard FastAPI modular-monolith practice (e.g., Sebastián Ramírez's "bigger applications" guidance plus standard hexagonal layering).

### Router wiring

`apps/api/src/main.py`:

```python
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router,    prefix="/auth",    tags=["auth"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
# ...
```

One central place, no auto-discovery — explicit beats implicit and grep-able beats clever.

---

## Background Jobs

**Recommendation: ARQ (Redis-backed) for v1.** Validated alternative: **pg-jobs / Procrastinate** (Postgres-only, matches the "no extra infra" instinct).

### Why ARQ over Celery

| Criterion | ARQ | Celery | Dramatiq | Procrastinate |
|---|---|---|---|---|
| Async-native (asyncio jobs) | yes | partial / awkward | partial | yes |
| Setup complexity | minimal | high | medium | minimal |
| Broker | Redis | Redis / RabbitMQ | Redis / RabbitMQ | **Postgres** |
| Scheduled / cron jobs | yes (cron syntax) | yes (beat) | yes (periodiq) | yes |
| Result backend | Redis | Redis / DB | Redis | Postgres |
| Self-host footprint | +1 service (Redis) | +1 service | +1 service | **0 services** |

Confidence: HIGH for ARQ being a fit for async FastAPI; MEDIUM on the "best choice" claim — Procrastinate is genuinely competitive for this product because it avoids adding Redis to the self-host stack.

### Recommendation rationale

For a **self-hosted** product, every extra container is friction. Two viable paths:

**Path A — ARQ + Redis (v1 simplicity-of-code wins):**
- Pros: best-in-class async ergonomics, mature, simple cron via `WorkerSettings.cron_jobs`.
- Cons: adds Redis container to docker-compose.

**Path B — Procrastinate (Postgres-only):**
- Pros: zero new infra; transactional enqueue (enqueue + DB write in one tx is a real feature for the import flow); first-class asyncio.
- Cons: smaller community, fewer dashboards, throughput ceiling lower than Redis (irrelevant at personal-finance scale).

**Suggested decision:** Go with **Procrastinate** unless throughput concerns appear. The self-host story is the headline; saving a Redis container is worth more than the Celery-ecosystem maturity ARQ buys you. Document this as ADR-002 when Phase 4 (the first job consumer) lands.

Confidence: MEDIUM — verify Procrastinate's current asyncio/SQLAlchemy 2.0 story before Phase 4. ARQ is the safe fallback.

### Worker deployment

- New service `apps/worker/` (same Dockerfile base image as `apps/api`, different entrypoint).
- Reuses `packages/domain`, `packages/db`, `packages/shared` directly.
- One worker process is fine until Phase 9 sync volume grows; horizontally scale by running more replicas.

### Job catalog (anticipated)

| Phase | Job | Trigger | Idempotency key |
|---|---|---|---|
| 4 | `process_csv_import(batch_id)` | API call | `batch_id` |
| 5 | `reapply_rules(household_id)` | API call | `household_id`+`started_at` |
| 9 | `sync_connector(connector_id)` | Cron nightly | `connector_id`+`run_date` |
| 9 | `handle_plaid_webhook(payload)` | Webhook | payload signature hash |
| 12 | `parse_receipt(receipt_id)` | Upload | `receipt_id` |
| 12 | `intake_email_receipt(email_id)` | SMTP intake | `email_id` |

Every job must be **idempotent**: re-running it twice produces the same DB state. Store last-run cursors (`plaid_account.last_cursor`) explicitly; never trust "the worker won't crash mid-job".

### Scheduling

Use the job runner's native cron (ARQ `cron_jobs`, Procrastinate periodic tasks). Do **not** add APScheduler in-process inside FastAPI — that breaks horizontal scaling and Kubernetes-friendliness.

---

## Async SQLAlchemy Session Management

Confidence: HIGH — this is settled SQLAlchemy 2.0 async practice.

### Pattern

```python
# packages/db/session.py
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.LOG_LEVEL == "DEBUG",
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,   # critical: don't expire after commit; we return ORM objects
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

### Lifespan

```python
# apps/api/src/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()
```

### Usage in routes

```python
# apps/api/src/modules/accounts/router.py
@router.get("/")
async def list_accounts(
    session: Annotated[AsyncSession, Depends(get_session)],
    current: Annotated[CurrentContext, Depends(get_current_context)],
):
    return await accounts_service.list_accounts(session, current.household_id)
```

### Rules

1. **One session per request.** Created by `Depends(get_session)`, committed/rolled back at the end. Never share a session across requests or threads.
2. **`expire_on_commit=False`.** With it on, accessing an ORM attribute after commit triggers another DB roundtrip — surprises and warnings under async.
3. **Workers** create their own session per job (`async with AsyncSessionLocal() as session:` inside the job handler). One session per job is the analog of one session per request.
4. **Long-running jobs** that process many rows should commit in batches (e.g., every 500 rows in a CSV import) to avoid one giant transaction holding row locks.
5. **No `lazy="select"` cross-request.** All relationships use `lazy="raise"` or `selectinload()`/`joinedload()` explicitly — async sessions do not survive lazy access from a different scope.
6. **Repository functions accept a session.** They never create one. This makes a single request able to compose multiple repository calls in one transaction.

```python
# packages/db/repositories/accounts.py
async def list_accounts(session: AsyncSession, household_id: UUID) -> list[Account]:
    stmt = select(Account).where(Account.household_id == household_id, Account.is_archived == False)
    return list((await session.scalars(stmt)).all())
```

### Testing

- Use `pytest-asyncio` with a fixture that creates an engine against a disposable Postgres (testcontainers) or a transactional rollback fixture (`SAVEPOINT` per test).
- Domain layer tests use no session at all — they receive Python objects.

---

## Connector Interface Design (for testability)

Reproduce and extend the interface from `ROADMAP.md`:

```python
# packages/domain/connectors/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

@dataclass(frozen=True, slots=True)
class RawTransaction:
    provider_txn_id: str          # e.g., Plaid transaction_id
    provider_account_id: str
    amount_cents: int
    currency: str
    transaction_date: date
    post_date: date | None
    status: Literal["pending", "posted", "cancelled"]
    merchant_name: str | None
    merchant_category: str | None
    mcc: str | None

@dataclass(frozen=True, slots=True)
class RawBalance:
    provider_account_id: str
    current_balance_cents: int
    available_balance_cents: int | None
    currency: str
    as_of: datetime

@dataclass(frozen=True, slots=True)
class SyncResult:
    transactions: list[RawTransaction]
    balances: list[RawBalance]
    next_cursor: str | None

class Connector(ABC):
    @abstractmethod
    async def link(self, credentials: Mapping[str, str]) -> ConnectorLinkResult: ...
    @abstractmethod
    async def sync(self, connector_id: UUID, *, cursor: str | None) -> SyncResult: ...
    @abstractmethod
    async def get_transactions(self, account_id: UUID, since: date) -> list[RawTransaction]: ...
    @abstractmethod
    async def get_balances(self, account_id: UUID) -> list[RawBalance]: ...
```

### Testability constraints

1. **Pure DTOs.** `RawTransaction`/`RawBalance` are frozen dataclasses, not ORM rows. They are easy to construct in tests.
2. **Credentials injected.** A `Connector` instance is constructed with credentials passed in (not read from DB inside the class). The connectors module loads credentials and constructs the connector; the connector itself stays unit-testable.
3. **No DB writes inside connectors.** A connector returns raw data. `packages/domain/reconciliation` owns the merge. This means a `FakeConnector` test double is enough to test reconciliation end-to-end.
4. **HTTP client injected.** `PlaidConnector(http_client: httpx.AsyncClient)` — the test passes a `MockTransport`/`respx` mock.
5. **One factory:** `def get_connector(connector_row: ConnectorRow, http: httpx.AsyncClient) -> Connector`. The router resolves type → constructor. Adding SimpleFIN is one line in the factory.

```python
# packages/domain/connectors/factory.py
def get_connector(connector_row, http: httpx.AsyncClient, settings: Settings) -> Connector:
    match connector_row.type:
        case "plaid":      return PlaidConnector(http=http, creds=decrypt(connector_row.credentials_encrypted), settings=settings)
        case "simplefin":  return SimpleFINConnector(http=http, creds=decrypt(connector_row.credentials_encrypted))
        case "csv":        return CSVConnector()
        case _:            raise UnknownConnectorType(connector_row.type)
```

Confidence: HIGH for the pattern (textbook ports-and-adapters); MEDIUM that the exact field set matches what Plaid/SimpleFIN return — refine in Phase 9.

---

## Caching the Forecast

The forecast is expensive: balances + scheduled + rolling 90-day spend windows + per-day projection × 30/60/90 days × N accounts. Recomputing on every page load is wasteful. But the forecast must also be **fresh** — stale data kills trust, which is the whole product thesis.

### Recommendation: invalidation-driven cache, not TTL.

| Approach | Verdict |
|---|---|
| No cache | Fine for v1. Forecast for one household is sub-second on Postgres. |
| TTL cache (e.g., 1h) | Bad — user adds a transaction, forecast is stale until TTL expires. |
| Invalidation-driven | Right — cache result, invalidate on any household write. |
| Materialized view | Overkill for one-household-at-a-time queries. |

### Implementation

1. Skip caching until measured. Phase 7 ships uncached. Profile real usage.
2. If needed, add a **per-household keyed cache** of the projection result keyed by `(household_id, days, scenario_hash)`.
3. Store cache rows in Postgres (`forecast_cache` table) — survives restart, no Redis dependency:
   ```sql
   CREATE TABLE forecast_cache (
     household_id UUID NOT NULL,
     cache_key    TEXT NOT NULL,    -- hash of inputs (days, scenario, account filter)
     projection   JSONB NOT NULL,
     computed_at  TIMESTAMPTZ NOT NULL,
     PRIMARY KEY (household_id, cache_key)
   );
   ```
4. Invalidate by deleting rows where `household_id = ?` on any of: transaction insert/update/delete, account balance change, scheduled_transaction change, rule change. Centralize this in `packages/domain/forecast/cache.py::invalidate(household_id)`.
5. Treat the cache as a hint. If it's missing, recompute. If recomputing is slow, materialize after first miss.

Confidence: MEDIUM — assumes forecast cost is sub-second at personal scale; reassess after Phase 7 benchmarking.

---

## Multi-tenancy Pattern (Household Isolation)

The single most important architectural rule. One leak = product-ending bug.

### Layered defense (defense in depth)

#### Layer 1 — Schema: `household_id` NOT NULL on every domain table
Already mandated by `PROJECT.md`. Plus index:
```sql
CREATE INDEX ix_transaction_household_id ON transaction(household_id);
-- composite indexes for common filters:
CREATE INDEX ix_transaction_household_date ON transaction(household_id, transaction_date DESC);
```

#### Layer 2 — Repository: every query takes `household_id` as a required argument
```python
async def list_transactions(session: AsyncSession, household_id: UUID, ...) -> list[Transaction]:
    stmt = select(Transaction).where(Transaction.household_id == household_id, ...)
```
**No repository function exists that doesn't take a household_id**, except admin tooling clearly tagged as such. Enforce via code review and a CI lint rule (e.g., grep for `select(Transaction).where` not followed by `household_id` in repository files).

#### Layer 3 — Service: load the household from the session, never from request body
```python
async def list_transactions(session, current: CurrentContext, ...):
    return await tx_repo.list_transactions(session, current.household_id, ...)
```
The request body never contains a `household_id` field for reads. For writes, the service inserts the current household_id; any client-supplied value is dropped.

#### Layer 4 — Route guard: `get_current_context` dependency resolves user → membership → active household
```python
async def get_current_context(
    session: AsyncSession = Depends(get_session),
    token: str = Depends(oauth2_scheme),
) -> CurrentContext:
    user = await auth_service.user_from_token(session, token)
    membership = await households_repo.get_active_membership(session, user.id)
    if not membership:
        raise HTTPException(403)
    return CurrentContext(user_id=user.id, household_id=membership.household_id, role=membership.role)
```
This dependency is applied via `dependencies=[Depends(get_current_context)]` on every router except `health` and `auth` — enforced by a single line in `apps/api/src/main.py` (use an `include_router(..., dependencies=[Depends(get_current_context)])` on a parent router that mounts all protected modules).

#### Layer 5 — Postgres Row-Level Security (RLS) — recommended, not required
For belt-and-suspenders, enable RLS on every household-scoped table and set `app.current_household_id` per session:
```sql
ALTER TABLE transaction ENABLE ROW LEVEL SECURITY;
CREATE POLICY transaction_household_isolation ON transaction
  USING (household_id = current_setting('app.current_household_id')::uuid);
```
Then in `get_session`, after auth resolves the household, issue `SET LOCAL app.current_household_id = '<uuid>'`. This catches developer error: even a query that forgot to filter by household_id will return zero rows for other households.

Trade-off: RLS makes background jobs (which run as a service role) slightly more complex — they must set the household_id explicitly when acting on behalf of a household, which is actually a feature (forces thinking about it).

Confidence: HIGH for layers 1-4 (standard practice); MEDIUM for RLS recommendation — it adds operational complexity, and layers 1-4 are usually sufficient. Recommend enabling RLS in Phase 13 (multi-user UI) when bug cost spikes; before then, layers 1-4 are enough.

### Cross-household forbidden cases to test
- `GET /transactions/{id}` for a tx in another household → 404 (not 403; don't leak existence).
- `PATCH /accounts/{id}` where id belongs to another household → 404.
- `POST /transactions {account_id: <other household's account>}` → 400 (validate account belongs to current household).

These tests live in `apps/api/tests/test_multitenancy.py` and run in CI. Confidence: HIGH.

---

## Object Storage Abstraction (Receipts)

Trivial abstraction, but worth getting right early because Phase 12 isn't far away:

```python
# packages/domain/storage/base.py
class ObjectStorage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> str: ...   # returns URI
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def signed_url(self, key: str, ttl_seconds: int) -> str: ...

# Implementations:
#   packages/infra/storage/local.py     -- LocalFSStorage   (self-host)
#   packages/infra/storage/s3.py        -- S3Storage        (cloud)
```

Selection by config: `STORAGE_BACKEND=local|s3`. The `receipt.image_path` column stores the URI (`file://...` or `s3://bucket/key`). Confidence: HIGH.

---

## Build Order

Logical dependency-driven order. This is what `ROADMAP.md` already does well; here is the architecture-component view of the same ordering:

```
Phase 0:  Skeleton                 → main, lifespan, get_session, /health, modules/ shell
Phase 1:  Auth + Household         → CurrentContext, get_current_context dependency,
                                     household_id pattern established in code
Phase 2:  Accounts                 → first non-trivial CRUD; net worth domain fn
Phase 3:  Transactions             → packages/domain/money + dates helpers must land here
Phase 4:  CSV Import               → FIRST background-job consumer
                                     → ADR-002: choose Procrastinate vs ARQ
                                     → apps/worker/ container added
                                     → reconciliation/dedupe domain module born
Phase 5:  Rules Engine             → packages/domain/categorization (pure fn) — must NOT
                                     depend on DB; imports + future connectors both call it
Phase 6:  Scheduled                → generator is pure domain (no writes)
Phase 7:  Forecast                 → engine consumes accounts + scheduled + spend;
                                     ALL prior phases are inputs — this is why ordering matters
Phase 8:  Bill Pay                 → small; computed view over account fields
─── v1.0 ───
Phase 9:  Plaid Connector          → Connector ABC + RawTransaction DTOs land here;
                                     reconciliation MUST already exist (proven via CSV in Phase 4)
Phase 10: Tracked Items            → independent; can slot earlier if needed
Phase 11: SimpleFIN Connector      → second impl of same ABC — proves the abstraction
Phase 12: Receipt Parsing          → ObjectStorage abstraction lands; LLM client (BYO key)
Phase 13: Multi-User UI            → enable RLS here; invite/role enforcement
Phase 14: Investments              → independent domain
```

### Architectural prerequisites for each phase

| Phase | New architectural component | Why now |
|---|---|---|
| 0 | `get_session` dep, lifespan, module skeleton | Foundation |
| 1 | `CurrentContext`, `get_current_context`, household guard | Every later phase scopes by household |
| 3 | `money` + `dates` helpers in `packages/domain/` | First time we deal with cents and pending/posted |
| 4 | Job runner (Procrastinate/ARQ) + `apps/worker` | First long-running task |
| 4 | `reconciliation/dedupe` domain module | Reused by Plaid in Phase 9 |
| 5 | `categorization` (pure fn) | Reused by all import paths |
| 9 | `Connector` ABC + `RawTransaction`/`RawBalance` DTOs | First provider integration |
| 9 | Credential encryption (libsodium / `cryptography.fernet`) | Plaid tokens are secrets |
| 12 | `ObjectStorage` abstraction | First binary blob |
| 12 | LLM client wrapper (BYO key, provider-agnostic) | Receipt parse |
| 13 | Postgres RLS | Hardening for multi-user |

Confidence: HIGH — this matches the `ROADMAP.md` ordering; the only insertion is "decide on Procrastinate vs ARQ" before Phase 4 starts.

---

## Open Questions

| # | Question | Decide by phase | Notes |
|---|---|---|---|
| 1 | Procrastinate vs ARQ for jobs | Phase 4 start | Recommendation: Procrastinate (no Redis). Verify SQLAlchemy 2.0 compatibility on current version before committing. |
| 2 | Session strategy: JWT vs server-side session cookie | Phase 1 | Recommendation: HTTP-only secure cookie + server session (simpler logout, self-host friendly). JWT only if a mobile client appears. |
| 3 | Credential encryption library: `cryptography.fernet` vs libsodium (`pynacl`) | Phase 9 | Fernet is sufficient and stdlib-adjacent; pynacl is overkill for symmetric secrets. |
| 4 | Forecast caching: lazy compute vs eager warm-up via worker | Phase 7 | Default to lazy + invalidation; revisit if user-perceived latency >300ms. |
| 5 | RLS enablement timing | Phase 13 vs Phase 9 | Earlier is safer but adds friction; recommendation: Phase 13 (when external connectors + multi-user converge). |
| 6 | OCR engine for receipts: Tesseract local vs cloud OCR vs LLM-only | Phase 12 | LLM vision models can now OCR + structure in one call; benchmark before committing to a separate OCR step. |
| 7 | Schema for cardholder attribution before Phase 13 UI exists | Phase 3 | `transaction.cardholder_id` is on the schema in `ROADMAP.md` Phase 3 — confirm we add the column nullable from day 1 so Phase 13 doesn't migrate. |
| 8 | Email intake architecture for receipts (Phase 12) | Phase 12 | Self-host: in-bound SMTP catch container (e.g., `inbucket`)? Or "forward to a polling IMAP mailbox"? Latter is simpler. |
| 9 | Webhook receiver isolation for Plaid | Phase 9 | Plaid signs webhooks; receiver is an unauthenticated route (`/webhooks/plaid`) — must verify signature, then enqueue, then 200. |
| 10 | Connection pool sizing under worker + api combined load | Phase 9 | Default `pool_size=10` per process. With 2 api + 1 worker = 30 conns. Postgres default max is 100. Plenty of headroom, but document. |

---

## Sources

- `CLAUDE.md`, `.planning/PROJECT.md`, `ROADMAP.md` (project canon) — HIGH confidence.
- Training-data knowledge of SQLAlchemy 2.0 async, FastAPI dependency patterns, Procrastinate/ARQ/Celery characteristics, Plaid SDK, Postgres RLS — MEDIUM-HIGH confidence; version-pinning and exact API surface to be verified in Phase 0 docs research.
- External documentation (Context7, official docs, WebSearch) was unavailable during this research run; all version-sensitive claims (FastAPI 0.111+, SQLAlchemy 2.0 async, ARQ, Procrastinate compatibility) should be re-verified against current docs at the start of each consuming phase.
