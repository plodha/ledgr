# Stack Research — Personal Finance App

**Project:** PRANAV (formerly FinBrain) — self-hostable personal finance app
**Domain:** Multi-user personal finance with bank integrations + receipt parsing
**Researched:** 2026-05-23
**Verification sources:** fastapi.tiangolo.com (official), nextjs.org (official), CLAUDE.md, ROADMAP.md, PROJECT.md
**Overall confidence:** HIGH for already-chosen stack and frontend; MEDIUM for gap-filling library versions (only fastapi.tiangolo.com + nextjs.org were reachable for live verification — other libraries were verified against training data and cross-referenced with the FastAPI tutorial's current recommendations)

> Note on dates: Today is **2026-05-23**. The official FastAPI release notes confirm 0.136.1 (2026-04-23) and Next.js docs confirm 16.2.6 (2026-05-19). All version pins below assume that timeline.

---

## TL;DR — The Stack

| Layer | Pick | Version | Confidence |
|---|---|---|---|
| Backend framework | FastAPI | `>=0.136,<0.137` | HIGH (verified) |
| Python | CPython | `3.12.x` | HIGH (per CLAUDE.md) |
| ORM | SQLAlchemy async | `>=2.0.36,<2.1` | HIGH |
| Migrations | Alembic | `>=1.13,<2` | HIGH |
| DB driver | asyncpg | `>=0.30,<0.31` | HIGH |
| Validation | Pydantic v2 + pydantic-settings | `pydantic>=2.9,<3`, `pydantic-settings>=2.5,<3` | HIGH |
| Auth (Phase 1) | Hand-rolled OAuth2 + JWT (PyJWT) + pwdlib[argon2] | `PyJWT>=2.9`, `pwdlib>=0.2` | HIGH (matches official FastAPI tutorial) |
| Background jobs | ARQ (Redis) **or** procrastinate (Postgres-native) | `arq>=0.26` / `procrastinate>=3` | MEDIUM — see decision section |
| Encryption-at-rest | `cryptography` (Fernet + AES-GCM via envelope) | `cryptography>=43` | HIGH |
| File storage | filesystem-by-default, S3-compatible via boto3 abstracted | `boto3>=1.35` | HIGH |
| Email (transactional) | `fastapi-mail` (SMTP-only in self-host) | `fastapi-mail>=1.4` | MEDIUM |
| Email (inbound receipts) | SMTP catch via `aiosmtpd` (self-host) or SendGrid Inbound Parse (cloud) | `aiosmtpd>=1.4` | MEDIUM |
| Bank: Plaid | official `plaid-python` | `>=27,<28` | HIGH |
| Bank: SimpleFIN | hand-rolled httpx client (no official Python SDK) | n/a | HIGH — verified by absence |
| LLM (receipt parse) | `anthropic` + `openai` SDKs, dispatched by provider id | `anthropic>=0.40`, `openai>=1.50` | HIGH |
| OCR fallback | `pytesseract` or skip — let multimodal LLMs do vision | — | MEDIUM |
| Frontend framework | Next.js App Router | **upgrade target: 16.2**, baseline 15.x acceptable | HIGH — **Next.js 14 is no longer current; revisit choice** |
| React | React 19.x (canary via Next 16) | — | HIGH |
| Styling | Tailwind CSS | `>=4.0,<5` | MEDIUM |
| UI primitives | shadcn/ui on Radix UI | latest | HIGH |
| Server state | TanStack Query v5 | `>=5.60,<6` | HIGH |
| Client state | Zustand (only where needed) | `>=5,<6` | HIGH |
| Forms | React Hook Form + Zod | `react-hook-form>=7.53`, `zod>=3.23` | HIGH |
| Charts (forecast) | Recharts | `>=2.13,<3` | HIGH |
| Money on wire | INTEGER cents (per CLAUDE.md) | — | HIGH |
| Testing (api) | pytest + pytest-asyncio + httpx AsyncClient + ASGITransport | `pytest>=8`, `pytest-asyncio>=0.24`, `httpx>=0.27` | HIGH (verified) |
| Testing (web) | Vitest + React Testing Library + Playwright | latest | HIGH |
| Linting (api) | ruff + pyright | `ruff>=0.6`, `pyright>=1.1.380` | HIGH |
| Linting (web) | ESLint flat config + Prettier (or Biome) | — | HIGH |

---

## 1. Chosen Stack (Validated)

### FastAPI 0.136.x — VALIDATED

Verified live against `https://fastapi.tiangolo.com/release-notes/`: **0.136.1 released 2026-04-23**. The 0.13x series is API-stable and `tutorial/security/`, `tutorial/cors/`, and `tutorial/bigger-applications/` still reflect the same recommended patterns the project assumes. Python 3.12 is well within supported range (and 0.136 even adds free-threaded 3.14t support).

**Rationale (still holds):**
- Async-first, dependency injection model fits the modular-monolith design in CLAUDE.md (`apps/api/src/modules/<name>/router.py` → `APIRouter` is canonical).
- Pydantic v2 integration gives free schema validation that matches the "domain types live in `packages/shared/schemas.py`" rule.
- The official tutorial's "bigger applications" pattern is *exactly* the module layout CLAUDE.md describes — no fighting the framework.

**Pin guidance:** `fastapi>=0.136,<0.137` for the foreseeable future. Bump minor only after smoke-testing the OpenAPI surface.

### Python 3.12 — VALIDATED

3.12 is the current production sweet spot (3.13 is GA but ecosystem coverage of async DB drivers lags; 3.14 is too new). Stay on **3.12.x** through v1.0.

### SQLAlchemy 2.0 async — VALIDATED

The 2.0 series shipped May 2023; async is GA and battle-tested. As of training cutoff the latest 2.0.x line is in the 2.0.3x range — pin `sqlalchemy[asyncio]>=2.0.36,<2.1`.

**Important caveat (HIGH confidence, from FastAPI docs):** The current FastAPI SQL tutorial promotes **SQLModel** as the "official" recommendation. **Do NOT switch to SQLModel.** Reasons:
1. CLAUDE.md mandates SQLAlchemy models in `packages/db/models/` separate from Pydantic schemas in `packages/shared/schemas.py`. SQLModel deliberately fuses them — using it would violate the schema-separation rule that exists *to keep DB shape independent of wire shape* (critical for the cents-vs-decimal money rule).
2. SQLModel still wraps SQLAlchemy 2.0 underneath, so you gain nothing while losing flexibility on relationship loading strategies you'll need for the forecast query (Phase 7).
3. SQLModel's async story is thinner than raw SA 2.0's.

**Decision:** Use raw `sqlalchemy.ext.asyncio` (`AsyncEngine`, `AsyncSession`, `async_sessionmaker`). Stays consistent with the existing architecture.

### Alembic — VALIDATED

`alembic>=1.13,<2`. Async migrations are supported via `env.py`'s `run_async_migrations` pattern (using `engine.connect().run_sync(do_run_migrations)`). Standard. No alternative worth considering.

### Postgres 16 — VALIDATED

Phase 0 already pins `postgres:16-alpine`. Stay there through v1.0. Postgres 17 GA'd late 2024 but offers nothing this project specifically needs and adds a migration. Stick with 16.

### asyncpg — VALIDATED

`asyncpg>=0.30,<0.31`. The fastest pure-Python async Postgres driver. Pair with `sqlalchemy[asyncio]` via `postgresql+asyncpg://` DSN. Do **not** use `psycopg` (v3) for the async path — asyncpg is faster and the FastAPI/SQLAlchemy ecosystem is more tested against it. Keep `psycopg2-binary` only as an Alembic sync fallback if needed (it usually isn't — Alembic handles async with the run_sync wrapper).

### Pydantic v2 + pydantic-settings — VALIDATED

`pydantic>=2.9,<3`, `pydantic-settings>=2.5,<3`. Pydantic v2 is Rust-backed and ~5-50x faster than v1. `pydantic-settings` reads from env / `.env` files, which Phase 0 already requires.

### Next.js App Router + TypeScript + Tailwind — VALIDATED PATTERN, VERSION FLAGGED

The architectural choice (App Router, server components, TypeScript, Tailwind) is right — official docs confirm App Router is the recommended path and Tailwind is the default in `create-next-app`. **However, the *version* in CLAUDE.md (14) is now two majors behind.** See "Recommendations → Frontend" below.

### Docker Compose — VALIDATED

Modular-monolith deployment via Compose with web + api + postgres + adminer is the standard self-hostable shape (Bitwarden, Vaultwarden, Linkwarden, Outline, Cal.com, and dozens more ship this way). Adminer is the right "no extra config" DB inspector for dev.

---

## 2. Gaps to Fill (And Recommendations)

The question listed eight gaps. For each, here is the specific call.

### 2.1 Auth — **Hand-rolled OAuth2 password flow + JWT in HttpOnly cookie**

**Recommendation:** Build it yourself in `apps/api/src/modules/auth/` using:
- `PyJWT>=2.9` for token encode/decode (this is what the **official FastAPI tutorial uses today** — verified).
- `pwdlib[argon2]>=0.2` for password hashing (also the **current official FastAPI tutorial recommendation** — verified; replaces the older `passlib[bcrypt]` advice from pre-2024 tutorials).
- `OAuth2PasswordBearer` from FastAPI for header-based JWT during dev/local tooling.
- A second dependency that reads the same JWT from an **HttpOnly, SameSite=Lax, Secure cookie** for the actual browser flow.
- Refresh-token rotation: short-lived (15min) access JWT in cookie + long-lived (30d) opaque refresh token stored in a `refresh_token` table (revocable). Rotate on every refresh.

**Why not fastapi-users?**

`fastapi-users` is the obvious "batteries-included" answer and you might be tempted. Skip it. Reasons:
1. **Household model collision.** `fastapi-users` assumes user-centric auth. The whole project hinges on `household_id` being on every domain row from Phase 1; bolting that onto fastapi-users' opinionated user model fights the library more than rolling your own.
2. **The hand-roll is ~150 lines.** The official FastAPI security tutorial *is* the implementation. You'll write `register`, `login`, `logout`, `refresh`, `get_current_user` dependency, and `require_household_role(role)` dependency — that's it. Adding fastapi-users gives you a base User model, password reset emails, OAuth social login (which you don't need yet), and tightly-coupled session backends, in exchange for ceding control of the table you'll touch most.
3. **Verifiability.** A 150-line auth module is auditable. fastapi-users + its dependencies (databases, fastapi-users-db-sqlalchemy) is several thousand lines you'd be on the hook for if it breaks.

**Why JWT-in-cookie over pure-cookie sessions?**
- The frontend (Next.js server components) needs to call the API from a server context. JWT-in-cookie + a `verify_token` dependency Just Works for both browser fetches and server-side `fetch` from RSC.
- Pure server-side sessions (Redis-backed) add an extra moving piece for self-hosters with no security gain at this scale.
- Stateless verification means the forecast endpoint (which will be the chattiest endpoint in the app, Phase 7) doesn't hit Redis per request.

**Confidence:** HIGH (both library choices verified against current official FastAPI tutorial 2026-04).

### 2.2 Background Jobs — **procrastinate (Postgres-native)** ✅ recommended

**Recommendation:** Use **procrastinate** for Phase 9 onwards. `procrastinate>=3,<4`.

**Why procrastinate over ARQ:**
- The project is already running Postgres. procrastinate uses Postgres `LISTEN/NOTIFY` + a `procrastinate_jobs` table; **no Redis container required**, which keeps the self-hostable Docker Compose footprint smaller (one less service, one less env var, one less thing for users to misconfigure).
- It's async-native, supports cron-like periodic tasks (needed for nightly Plaid sync in Phase 9), retries with backoff, and integrates cleanly with the existing SQLAlchemy migration story (its tables are managed by its own CLI; you wire it into Alembic as a one-time `alembic stamp`).
- The "pg-boss equivalent in Python" framing in the original question is literally procrastinate's positioning. pg-boss is Node-only; procrastinate is the closest 1:1 Python analog.

**Why not ARQ:**
- ARQ is excellent but requires Redis. Adding Redis to the self-hostable stack means: another container, another credential, another backup target, another set of "is my Redis healthy?" questions for self-hosters. Not worth it for a job queue that won't exceed ~10k jobs/day per household.

**Why not Celery:**
- Heavyweight, sync-first, has a complex broker story, and the async support is a Frankenstein. Wrong fit for an async FastAPI codebase.

**Why not taskiq:**
- Younger, less battle-tested, broker abstraction is its main selling point — but you don't want broker flexibility, you want one obvious choice that uses your existing Postgres.

**Why not FastAPI BackgroundTasks for everything:**
- BackgroundTasks are *in-process*. Fine for "send a single email" but unusable for nightly Plaid sync, retries, and observability. Use them only for fire-and-forget post-response work.

**Confidence:** MEDIUM-HIGH. procrastinate v3 hit GA in 2025 and is in production at French government scale (it originated at the French Ministry of Culture / beta.gouv.fr). Pin to `>=3,<4`.

**Phase implications:** procrastinate is only needed at Phase 9 (Plaid). Phases 0–8 don't need a job queue at all — keep it out of `docker-compose.yml` and `requirements.txt` until Phase 9. (Update the ROADMAP's Phase 9 to specify procrastinate, not pg-boss.)

### 2.3 File Storage (Receipts) — **Abstract behind a `Storage` interface; filesystem default, S3 optional**

**Recommendation:** Create `packages/domain/storage/` with a tiny interface, exactly like the `Connector` interface:

```python
class Storage(ABC):
    async def put(self, key: str, data: bytes, content_type: str) -> str: ...   # returns storage URI
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def presigned_url(self, key: str, expires_in: int) -> str | None: ...  # may return None for FS
```

Two implementations:
- `LocalFilesystemStorage` — writes to a bind-mounted volume (`/data/receipts/{household_id}/{yyyy-mm}/{uuid}.jpg`). Default for self-host.
- `S3Storage` — uses `boto3>=1.35` with the async client (`aioboto3`) against any S3-compatible service (AWS S3, Cloudflare R2, MinIO, Backblaze B2). Configured by env vars: `STORAGE_BACKEND=s3`, `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`.

**Why not boto3 only:**
- A first-time self-hoster shouldn't need an S3 account to use the app. Filesystem-default is the Bitwarden/Vaultwarden norm.

**Why not Cloudinary / Imgur / other:**
- Receipts are sensitive financial data. A third-party image CDN is the wrong default. Self-hosted file or self-hosted S3-compatible only.

**Security note (CRITICAL):** Receipts contain merchant + amount + sometimes card-last-4. Treat the file path as a secret. The storage layer must verify `household_id` on every read — never serve files by URL without auth. Use signed short-lived URLs for direct downloads in the UI, OR proxy through the API. Pick the proxy approach for v1 — simpler, no presign infrastructure required.

**Confidence:** HIGH.

### 2.4 Email — **SMTP for outbound, two paths for inbound**

**Outbound (invites, password reset, etc.):**

**Recommendation:** `fastapi-mail>=1.4`. Configure with SMTP only — no proprietary providers in the default config. Self-hosters bring their own SMTP credentials (Postmark, Mailgun, AWS SES, Resend, or a home Postfix). Cloud deployment uses whichever provider you pick.

**Why fastapi-mail:**
- Async, integrates with FastAPI's dependency injection, supports templates via Jinja2.
- Pure SMTP transport means no vendor lock-in.

**Alternative considered:** `aiosmtplib` directly. Fine if you want zero abstraction; fastapi-mail adds template handling that's worth the 200KB.

**Inbound (receipt intake at `receipts@yourdomain.com`):**

This is Phase 12 work. Two paths, as the ROADMAP already notes:
- **Self-host path:** `aiosmtpd>=1.4` running as a separate container (or in-process if you must). Listens on port 25/465, hands message bodies + attachments to a procrastinate job that runs the same receipt parse pipeline as photo upload. Document that users need a public IP + reverse DNS + ideally MX records, OR they forward from their main email via filters.
- **Cloud path:** SendGrid Inbound Parse (free tier covers small volumes) posts a webhook to `/webhooks/email-inbound`. Same handler, same parse pipeline.

**Why not have inbound at all in v1.0:**
- It isn't needed before Phase 12. Don't build it. Defer to Phase 12 explicitly.

**Confidence:** MEDIUM. fastapi-mail is fine but unmaintained-ish (last sustained release pattern was 2023-2024 by training data). Worth a re-evaluation at Phase 1; if it looks stale, fall back to `aiosmtplib` directly. Flag for re-verification.

### 2.5 Encryption (Plaid / SimpleFIN credentials) — **Envelope encryption with `cryptography`**

**Recommendation:** `cryptography>=43`. Use envelope encryption — never store secrets encrypted directly with a single key.

**Pattern:**

```
APP_ENCRYPTION_KEY (env var, 32 bytes base64)
  └─ wraps  data_encryption_key (DEK, per-row, 32 bytes random)
                └─ encrypts  plaid_access_token (AES-256-GCM)
```

Schema: each row that stores a secret has three columns:
- `wrapped_dek BYTEA` — the DEK encrypted with the app key (Fernet or AES-KW).
- `nonce BYTEA` — the GCM nonce (12 bytes).
- `ciphertext BYTEA` — the encrypted secret with auth tag appended.

**Why envelope rather than single-key Fernet:**
1. **Key rotation** is local — re-wrap DEKs against a new app key without re-encrypting the secrets themselves.
2. **Blast radius** of a compromised app key is limited if you later move to a KMS (cloud HSM, Vault, AWS KMS) — only the wrapping changes.
3. Cloud deployment can swap the local app key for a KMS-backed `kms:Decrypt` call **without touching any row** in the secrets table.

**Why not just Fernet:**
- Fernet is fine for "the token" but commits you to one key forever (rotation is painful) and uses AES-128-CBC + HMAC, which is older than AES-GCM. Use Fernet only to *wrap* DEKs (it's convenient for that — combined enc+auth + base64).

**Implementation location:** `packages/domain/crypto/` — pure functions, no DB access. The `connector` module calls into it.

**Anti-patterns to forbid:**
- Storing the master key in the database (yes, people do this).
- Reusing a GCM nonce across rows (always 12-byte random per encryption).
- Storing Plaid `access_token` in a column called `access_token` (call it `credentials_encrypted` per the ROADMAP, store the whole envelope).

**Confidence:** HIGH. This is the standard pattern (1Password, Bitwarden, AWS Secrets Manager all do envelope).

### 2.6 Testing (FastAPI async + pytest) — **pytest-asyncio + httpx AsyncClient + ASGITransport**

**Recommendation (verified against official FastAPI docs at `tutorial/advanced/async-tests`):**

```python
# conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager
from app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    async with LifespanManager(app):  # so lifespan runs (DB engine init)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

# tests/test_health.py
import pytest

@pytest.mark.anyio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["db_connected"] is True
```

**Packages:**
- `pytest>=8`
- `pytest-asyncio>=0.24` (or `anyio[trio]>=4` — official docs use anyio markers; either works, anyio is more flexible)
- `httpx>=0.27` — includes `ASGITransport`
- `asgi-lifespan>=2.1` — **REQUIRED**; the official FastAPI docs flag that `AsyncClient` doesn't trigger lifespan events on its own, and the project's `main.py` uses a lifespan to init the DB engine

**Database in tests:**
- Use a separate `finbrain_test` database (or a fresh schema per test session).
- Wrap each test in a SAVEPOINT-rollback fixture so tests don't pollute each other.
- For Phase 0, a single test against `/health` is enough.
- For domain logic (Phase 5 rule engine, Phase 7 forecast), prefer pure-function tests with no DB — CLAUDE.md says "domain layer tests are mandatory; route tests are nice-to-have" and that's exactly right.

**What NOT to use:**
- `TestClient` from `fastapi.testclient` — official docs explicitly say it doesn't work in async test functions; use `AsyncClient` instead.
- `pytest-anyio` (separate package) — `anyio` itself provides the pytest plugin via the `anyio` marker.

**Confidence:** HIGH (pattern verified directly against fastapi.tiangolo.com).

### 2.7 Frontend State Management with Next.js App Router

The App Router shifts most data-fetching to **server components** (RSC) by default — fetched inline with `async function Page()`. Three categories of state remain:

**Category A — Server data fetched in RSCs:**
- Don't manage at all in client state. Re-fetch on navigation (Next.js handles cache via `fetch`).
- For Phase 0: the placeholder `/health` call is exactly this pattern.

**Category B — Server data needed in interactive client components (e.g. transaction filter, forecast slider):**
- **Use TanStack Query v5 (`@tanstack/react-query>=5.60`).**
- Why: stale-while-revalidate, optimistic updates, mutation handling, request dedup, devtools. Industry standard.
- Wrap a `<QueryClientProvider>` at the root client boundary. Define a `getQueryClient()` server-side helper for prefetching from RSCs and hydrating into the client.

**Category C — Pure client state (form drafts, dialog open/closed, current filters):**
- **Use Zustand v5 sparingly.**
- Why: tiny (~1KB), no boilerplate, no Context Provider needed, works fine with RSC because stores are client-only.
- Only reach for it when `useState` lifted to a parent is awkward.

**Why not Redux Toolkit:**
- The App Router pattern + TanStack Query removes 90% of what people historically used Redux for. RTK is overkill for this project.

**Why not Jotai:**
- Atomic state is elegant but Zustand is simpler for the team and gives the same outcome.

**Why not Context + useReducer:**
- Fine for very small state, but the moment you need persistence (e.g. "remember the user's last forecast horizon"), Zustand's middleware (`persist`) is one line.

**Forms:**
- **React Hook Form + Zod** (`react-hook-form>=7.53`, `zod>=3.23`).
- Shared validation: define `transactionSchema` in `packages/shared/types.ts` (technically as a Zod schema, then `z.infer<>` the TS type). Use the same Zod schema in API responses (via TS) and form validation.

**Confidence:** HIGH.

### 2.8 Chart Library (Forecast View — Phase 7) — **Recharts**

**Recommendation:** **Recharts v2** (`recharts>=2.13,<3`).

**Why Recharts:**
- Built on D3, declarative React components, designed for time-series and financial charts.
- Composable: `<LineChart>` with `<ReferenceLine>` for "today", `<Brush>` for the 30/60/90 selector, `<Tooltip>` for hover values — all out of the box. The forecast view is exactly Recharts' wheelhouse.
- shadcn/ui ships a Recharts wrapper (`chart.tsx`) that gives you themed tooltips and legends for free.
- Excellent SSR support (renders in RSC without hydration mismatch headaches).

**Why not Chart.js / react-chartjs-2:**
- Imperative Canvas-based API; harder to compose, no built-in React idioms.
- Tooltips and overlays for "what if" scenarios in Phase 7 require custom canvas plugins.

**Why not Visx (Airbnb):**
- More powerful but more low-level. You'd be reimplementing things Recharts gives you for free.

**Why not Tremor:**
- Beautiful but opinionated, and the team scaled back maintenance through 2025. Risk of stagnation.

**Why not D3 directly:**
- Too low-level for this project's pace.

**Why not ApexCharts / Highcharts / Plotly:**
- Either heavy, license-encumbered (Highcharts), or way too much surface area (Plotly).

**Confidence:** HIGH.

---

## 3. Frontend: The Next.js 14 → 16 Decision (RAISE TO USER)

**This is the single most important finding of this research.**

The CLAUDE.md document specifies "Next.js 14, App Router." But as verified live at nextjs.org on 2026-05-19:
- Next.js 16.2.6 is current.
- Next.js 16 GA was October 2025.
- Next.js 14 still receives security patches (CVE-2025-66478 was patched across 13/14/15/16) but is *not* the recommended target for new projects.

**Material changes between 14 and 16:**
- `middleware.ts` → `proxy.ts` (deprecation, not removal).
- Async `params`, `searchParams`, `cookies()`, `headers()`, `draftMode()` — these are *breaking changes* if you write any code today against the 14 pattern, you'll have to rewrite for 16.
- Turbopack is the default bundler (significant dev-loop speedup).
- React 19.2 features available (View Transitions, useEffectEvent).
- React Compiler is stable (automatic memoization).
- New caching APIs (`updateTag`, `refresh`, `revalidateTag` with cacheLife).
- Cache Components (the successor to PPR).
- Node 20.9+ required (Phase 0 currently doesn't pin Node version — should pin in Dockerfile).

**Recommendation:**

**Start Phase 0 on Next.js 16.2.** Specifically:
- Use `pnpm create next-app@latest` with `--yes` defaults (TypeScript, Tailwind, ESLint, App Router, Turbopack, `@/*` alias) — that's what CLAUDE.md describes anyway, just on the current major.
- Update CLAUDE.md "Stack" line from "Next.js 14 App Router" to "Next.js 16+ App Router".
- Add `node>=20.9` to the web Dockerfile (use `node:22-alpine` to be safe and forward-compatible).
- Get used to `await params` from day one — no migration pain later.

**If Next.js 16 must be deferred** (e.g., a critical-path dependency only supports 14 — unlikely):
- Stay on the latest 15.x (which still has the App Router and is closer to 16's patterns).
- Do **not** start a new project on 14 in May 2026 — every line of code you write today will need migration in 6 months when something forces the upgrade.

**Confidence:** HIGH (verified live against nextjs.org/blog).

---

## 4. Money + Date Handling (No Change — Validated)

CLAUDE.md and PROJECT.md both mandate:
- Money: INTEGER cents in DB and on wire.
- Dates: TIMESTAMPTZ in Postgres, ISO 8601 strings on wire.
- Always store both `transaction_date` and `post_date`.

These are the right calls. No library change recommended. Implementation notes:
- For currency *display* (`$1,234.56` formatting), use `Intl.NumberFormat` in the browser; do **not** ship a JS money library. Cents-to-display is a one-line `(cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" })`.
- For *parsing* user input ("12.34" → 1234), write one shared helper in `packages/shared/types.ts` (Zod `transform`). Do not duplicate this logic.
- For currency arithmetic in the API (Phase 7 forecast aggregation), Python `int` is sufficient — no `decimal.Decimal` needed because we're already in integer cents.
- For multi-currency (deferred / out of scope for v1.0 — confirm), store `currency` (ISO 4217 3-letter) alongside every amount column. Don't mix currencies in any aggregation.

---

## 5. Plaid + SimpleFIN Connectors (Phase 9 / 11)

### Plaid: official `plaid-python` SDK

**Recommendation:** `plaid-python>=27,<28` (the official Plaid SDK; tracks Plaid's API version 2020-09-14+).

**Pattern:**
- `apps/api/src/modules/connectors_plaid/` — thin route layer that handles Link token creation and webhook receipt.
- `packages/domain/connectors/plaid.py` — `PlaidConnector(Connector)` implementing the abstract interface from ROADMAP § Connector Interface.
- Self-host: settings page captures `PLAID_CLIENT_ID` + `PLAID_SECRET` + `PLAID_ENV` (sandbox/development/production), stored encrypted via the envelope crypto from §2.5.
- Webhook handler: `TRANSACTIONS_SYNC`, `ITEM_ERROR`, `AUTH_STATUS_UPDATED` → enqueue procrastinate job → reconcile.
- Use Plaid's `/transactions/sync` cursor-based endpoint (not the deprecated `/transactions/get`). Persist `last_cursor` per `plaid_account` row (already in the ROADMAP schema).
- Pending → posted transition: Plaid transaction IDs change when status flips. Use `pending_transaction_id` from Plaid's response to find the row to update, **not** the `transaction_id`. Document this loudly in the reconciliation module.

**Confidence:** HIGH.

### SimpleFIN: hand-rolled httpx client

**Recommendation:** There is no official Python SDK for SimpleFIN — the protocol is small enough that one isn't needed. Build a 100-line `httpx.AsyncClient`-based client in `packages/domain/connectors/simplefin.py`.

**Protocol:** SimpleFIN Bridge exchanges a setup token for an access URL (basic-auth in the URL). You GET `https://{access_url}/accounts` and parse the response. That's the whole thing.

**Confidence:** HIGH (verified by absence of any maintained SDK in training data — SimpleFIN's spec page documents the protocol directly).

---

## 6. LLM (Receipt Parsing — Phase 12)

**Recommendation:** Don't lock in. Build a `ReceiptParser` interface in `packages/domain/receipts/`, with implementations for:
- `AnthropicReceiptParser` — `anthropic>=0.40`, uses Claude's vision capability on a `claude-3-5-sonnet`-class or `claude-4-sonnet`-class model.
- `OpenAIReceiptParser` — `openai>=1.50`, uses `gpt-4o`/`gpt-4.1`-class with the vision input.
- `StructuredReceiptParser` — deterministic regex/template parser for known formats (Costco, Amazon order emails); no LLM cost.

User configures which provider in settings; falls back to next on failure.

**Why interface-first:** Same logic as the Connector pattern — the rest of the app (line item linking, tracked-item observation triggering) shouldn't care which LLM produced the JSON.

**OCR specifically:** Skip dedicated OCR for v1. Multimodal LLMs (Claude/GPT vision) are now better at receipts than Tesseract + post-processing, and adding `pytesseract` means shipping ImageMagick + Tesseract binaries in the Docker image. If a true offline OCR fallback is required (no LLM API key), add `pytesseract` then — not before.

**Confidence:** HIGH.

---

## 7. Logging + Observability

CLAUDE.md mandates "structured JSON logging" for FastAPI. Specifics:

**Recommendation:** `structlog>=24.4` configured to render JSON in production and pretty console in dev. Standard pattern:

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer() if ENV != "dev" else structlog.dev.ConsoleRenderer(),
    ],
)
```

Pair with a request-id middleware that binds `request_id`, `household_id`, `user_id` to `structlog.contextvars` — every log line in the request gets these for free.

**No Sentry / no OpenTelemetry in Phase 0.** Add Sentry at v1.0 ship if a self-hosted Sentry feels worth it, or skip entirely until pain demands it.

**Confidence:** HIGH.

---

## 8. UI Components (Phase 1+)

**Recommendation:** **shadcn/ui** on top of Radix UI primitives + Tailwind.

**Why:**
- It's a CLI-installable copy-paste component library — components live *in your repo*, not in `node_modules`. You own them, you can modify them, no breaking-change risk from upstream.
- Built on Radix UI (accessibility, keyboard navigation handled).
- Tailwind-native, so it composes with the rest of the styling story.
- Free, MIT, no licensing.
- Includes the Recharts wrapper out of the box (for Phase 7).

**Why not MUI / Mantine / Chakra:**
- All ship runtime CSS-in-JS or large CSS bundles; the App Router story is worse than Tailwind+Radix.
- All are heavier than necessary for a self-hosted personal app.

**Why not Headless UI (Tailwind Labs):**
- Smaller surface area than Radix. shadcn standardized on Radix; staying on shadcn's path is easier.

**Tables (transaction list, Phase 3):** **TanStack Table v8** (`@tanstack/react-table>=8.20`). The shadcn data-table example uses it. Headless, virtualization-ready, sorting/filtering/pagination logic separated from rendering.

**Confidence:** HIGH.

---

## 9. CI/CD

ROADMAP Phase 0 mentions "CI: typecheck + lint + pytest on every push."

**Recommendation:** GitHub Actions (since repo is at github.com/plodha/ledgr). One workflow file:

```yaml
# .github/workflows/check.yml
name: check
on: [push, pull_request]
jobs:
  api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r apps/api/requirements.txt
      - run: cd apps/api && ruff check . && pyright && pytest
  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: "22" }
      - run: cd apps/web && pnpm install && pnpm tsc --noEmit && pnpm lint && pnpm test
```

Mirror what `make check` runs. No Docker in CI for Phase 0 — that's slower than just running pytest natively against a Postgres GitHub service container.

**Confidence:** HIGH.

---

## 10. What NOT to Use (Anti-Recommendations)

| Reject | Why |
|---|---|
| **SQLModel** | Conflates SQLAlchemy + Pydantic; violates CLAUDE.md's domain-types-separate-from-DB-models rule; redundant for this architecture. |
| **fastapi-users** | Opinionated user model fights the household-centric schema; auth is ~150 lines of well-documented FastAPI tutorial code. |
| **Celery** | Sync-first, broker-heavy, wrong fit for async FastAPI; procrastinate replaces it. |
| **ARQ** | Requires Redis. Adds a container with no benefit over Postgres-backed procrastinate at this scale. |
| **Redis** (as infrastructure) | Not needed at all in v1.0. Postgres handles jobs (procrastinate), sessions (JWT is stateless), and rate-limiting (Postgres advisory locks or in-memory). Resist the urge. |
| **passlib + bcrypt** | Officially superseded in the FastAPI tutorial by `pwdlib[argon2]`. passlib hasn't shipped a release in years. |
| **python-jose** | Replaced by PyJWT in the official FastAPI tutorial; python-jose's maintenance has been spotty. |
| **psycopg (sync) for async path** | asyncpg is faster and more battle-tested for FastAPI/SQLAlchemy 2.0 async. |
| **Float for money** | Mandated by CLAUDE.md; reiterating for emphasis. |
| **Decimal in the database** | Use INTEGER cents per CLAUDE.md; Decimal display conversion is a Pydantic concern, not a storage concern. |
| **Next.js Pages Router** | App Router is the framework's recommended default; Pages Router is maintained for backcompat. |
| **JavaScript (no TS)** | Mandated by CLAUDE.md; reiterating. |
| **Synchronous SQLAlchemy** | Mandated by CLAUDE.md; reiterating. |
| **Chart.js** | Imperative Canvas API; Recharts composes better with React for the forecast UI. |
| **Tremor** | Maintenance scaled back; risk for a chart library you'll lean on heavily in Phase 7. |
| **MUI / Chakra / Mantine** | Heavier than shadcn+Radix+Tailwind for this project; runtime CSS-in-JS is the wrong fit for the App Router. |
| **Cloudinary / Imgur (receipt storage)** | Sensitive financial data; third-party image CDNs are wrong by default. |
| **Floating point dates / Unix epoch ints for dates** | Use TIMESTAMPTZ; ISO 8601 on wire. CLAUDE.md mandates. |
| **SQLite in production** | The data model needs Postgres-specific features (LISTEN/NOTIFY for procrastinate, robust DATE handling, JSON columns for `csv_import_mapping.column_map`). Keep SQLite firmly off the table. |
| **Hand-rolled OCR pipeline (Tesseract pre-LLM)** | Multimodal LLMs do this better; only add OCR if a truly-offline mode is needed later. |
| **Redis-backed sessions** | JWT-in-cookie is stateless, sufficient, and removes a container. |
| **GraphQL / tRPC** | REST + OpenAPI from FastAPI is the simpler, well-trodden path for a self-hostable app. |

---

## 11. Stack Decisions Cheat Sheet (One-Liner Each)

| Question | Answer |
|---|---|
| Backend? | FastAPI 0.136+ on Python 3.12 |
| ORM? | SQLAlchemy 2.0 async (NOT SQLModel) |
| DB? | Postgres 16 with asyncpg |
| Migrations? | Alembic with async env.py |
| Validation? | Pydantic v2 + pydantic-settings |
| Auth? | Hand-rolled OAuth2 + JWT in HttpOnly cookie; PyJWT + pwdlib[argon2] |
| Background jobs? | procrastinate (Postgres-native), introduce at Phase 9 |
| Encryption? | `cryptography` lib, envelope pattern (AES-256-GCM + Fernet-wrapped DEK) |
| File storage? | Filesystem default, S3-compatible via `Storage` interface |
| Email out? | fastapi-mail + SMTP (BYO provider) |
| Email in (receipts)? | aiosmtpd (self-host) or SendGrid Inbound Parse (cloud) — Phase 12 only |
| Plaid? | Official `plaid-python` SDK, behind Connector interface |
| SimpleFIN? | Hand-rolled httpx client (no SDK), behind Connector interface |
| LLM (receipts)? | Anthropic + OpenAI SDKs, behind ReceiptParser interface |
| Testing API? | pytest + anyio + httpx AsyncClient + ASGITransport + asgi-lifespan |
| Logging? | structlog with JSON output |
| Frontend? | **Next.js 16.2** (upgrade from CLAUDE.md's 14) + TypeScript + Tailwind |
| UI lib? | shadcn/ui (Radix + Tailwind) |
| Server state? | TanStack Query v5 |
| Client state? | Zustand v5 (sparingly) |
| Forms? | React Hook Form + Zod (schema shared with API) |
| Tables? | TanStack Table v8 |
| Charts? | Recharts v2 |
| CI? | GitHub Actions (`.github/workflows/check.yml`) |
| Linters? | ruff + pyright (api); ESLint + Prettier (web) |
| Package manager? | pip + requirements.txt (api); pnpm (web) |

---

## 12. Confidence Notes / Gaps

**Live-verified (HIGH confidence):**
- FastAPI 0.136.1 current version → fastapi.tiangolo.com/release-notes
- FastAPI security tutorial uses PyJWT + pwdlib[argon2] → fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- FastAPI async tests use httpx AsyncClient + ASGITransport + anyio marker → fastapi.tiangolo.com/advanced/async-tests
- FastAPI CORS via CORSMiddleware with allow_credentials caveats → fastapi.tiangolo.com/tutorial/cors
- FastAPI bigger-applications uses APIRouter per module → matches CLAUDE.md exactly
- Next.js 16.2.6 current; Next.js 14 superseded → nextjs.org/blog/next-16, nextjs.org/docs/app/getting-started/installation
- Node.js 20.9+ required for Next 16; defaults include App Router, Turbopack, TS, Tailwind → confirmed installation page

**Verified-against-training-data only (MEDIUM confidence — flag for re-check at Phase 0 close):**
- SQLAlchemy 2.0.36+ as latest in 2.0.x line — training data says ~2.0.35; 2.0.36 is reasonable extrapolation but not live-checked.
- procrastinate v3 is current — strong training signal but not live-verified.
- fastapi-mail maintenance status — last known release pattern was 2023-2024; **explicit re-verification needed at Phase 1** (when first invite emails ship).
- Plaid SDK at v27 — strong signal from training data; verify against PyPI at Phase 9 start.
- anthropic / openai SDK versions — these move fast; pin loosely (`>=0.40`, `>=1.50`) and lock at Phase 12 start.
- Recharts v2.13 — training data current; verify at Phase 7 start.

**Not verified (LOW confidence — known unknowns):**
- Whether `procrastinate` v3 supports Postgres 16 partitioning if/when transaction tables get large. Probably yes; verify before Phase 9.
- SimpleFIN protocol stability — should be near-zero risk but the spec is community-maintained.
- Whether `aiosmtpd` is the right inbound MX choice vs an external service for self-hosters in 2026. Re-check at Phase 12 — DKIM/SPF handling for inbound is fiddly and might warrant a managed solution even for self-host (e.g., Cloudflare Email Routing → webhook).

**Open questions for the user:**
1. **Confirm: upgrade CLAUDE.md to "Next.js 16+" before any frontend code is written?** This single change saves a migration in 6 months.
2. **Confirm: procrastinate over ARQ?** This is the highest-leverage architecture decision in this research — it eliminates a Redis container forever.
3. **Confirm: hand-rolled auth over fastapi-users?** The trade-off is small effort now vs. household-model friction with fastapi-users later. The recommendation is hand-roll, but if you want a fastapi-users PoC first, that's defensible.
4. **Confirm: SQLAlchemy 2.0 async vs SQLModel?** FastAPI's official tutorial *now* recommends SQLModel; CLAUDE.md's architecture mandates SQLAlchemy. The recommendation is to keep CLAUDE.md's choice — but flagging the divergence from current official docs.

---

*Sources cited live (verified 2026-05-23):*
- `https://fastapi.tiangolo.com/release-notes/`
- `https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/`
- `https://fastapi.tiangolo.com/tutorial/cors/`
- `https://fastapi.tiangolo.com/tutorial/bigger-applications/`
- `https://fastapi.tiangolo.com/tutorial/testing/`
- `https://fastapi.tiangolo.com/advanced/async-tests/`
- `https://fastapi.tiangolo.com/tutorial/sql-databases/`
- `https://nextjs.org/blog/next-16`
- `https://nextjs.org/docs/app/getting-started/installation` (lastUpdated: 2026-05-19, version: 16.2.6)
