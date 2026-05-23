---
phase: 0
slug: repo-skeleton
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-23
---

# Phase 0 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (api) + Vitest/tsc (web) |
| **Config file** | `apps/api/pyproject.toml` (pytest) / `apps/web/tsconfig.json` (tsc) |
| **Quick run command** | `make check` |
| **Full suite command** | `make check` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make check` (or sub-command per layer)
- **After every plan wave:** Run `make check` (full suite)
- **Before `/gsd-verify-work`:** Full `make check` must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 00-01-01 | 01 | 1 | INFRA-01 | — | N/A | integration | `docker compose up --build -d && docker compose ps` | ❌ W0 | ⬜ pending |
| 00-01-02 | 01 | 1 | INFRA-02 | — | N/A | integration | `curl -s http://localhost:8000/health` | ❌ W0 | ⬜ pending |
| 00-01-03 | 01 | 1 | INFRA-03 | — | N/A | automated | `make check` | ❌ W0 | ⬜ pending |
| 00-01-04 | 01 | 1 | INFRA-04 | — | N/A | automated | `make migrate` | ❌ W0 | ⬜ pending |
| 00-01-05 | 01 | 1 | INFRA-05 | — | N/A | manual | Browse http://localhost:8080 | ❌ W0 | ⬜ pending |
| 00-01-06 | 01 | 1 | INFRA-06 | — | N/A | automated | `cat .env.example` contains all vars | ❌ W0 | ⬜ pending |
| 00-01-07 | 01 | 1 | INFRA-07 | — | request_id in log, passwords redacted | automated | `pytest apps/api/tests/test_health.py` | ❌ W0 | ⬜ pending |
| 00-01-08 | 01 | 1 | INFRA-08 | — | N/A | automated | `cat docs/MIGRATIONS.md` contains nullable-first + CONCURRENTLY | ❌ W0 | ⬜ pending |
| 00-01-09 | 01 | 1 | INFRA-09 | — | N/A | automated | psql query verifies rls_marker table exists | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/api/tests/conftest.py` — async test client fixture (httpx + ASGITransport + asgi-lifespan)
- [ ] `apps/api/tests/test_health.py` — GET /health → 200, db_connected=true
- [ ] `apps/api/pyproject.toml` — pytest-asyncio, httpx, asgi-lifespan deps listed
- [ ] `apps/web/tsconfig.json` — tsc noEmit passes
- [ ] `apps/web/.eslintrc` (flat config) — eslint passes

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Adminer shows DB at localhost:8080 | INFRA-05 | Browser-only UI | `make dev` → open http://localhost:8080, use postgres/pranav credentials |
| Docker Desktop shows all 4 containers running | INFRA-01 | Container orchestration | `docker compose ps` shows web/api/postgres/adminer all healthy |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
