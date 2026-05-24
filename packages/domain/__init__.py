"""packages/domain — Pure business logic. No DB or HTTP imports.

Cross-module calls between api modules (apps/api/src/modules/<name>/) MUST
flow through this package (per CLAUDE.md constraint #6). A module may NOT
import from another module's internal files.

Phase 0: empty. Future phases populate:
  - packages/domain/money/      (cents <-> display; Phase 3)
  - packages/domain/dates/      (transaction_date vs post_date; Phase 3)
  - packages/domain/categorization/  (pure rule evaluator; Phase 5 — zero DB calls)
  - packages/domain/transactions/totals.py  (canonical list_transactions_for_totals; Phase 3)
  - packages/domain/forecast/   (rolling 90-day projection; Phase 8)
  - packages/domain/connectors/ (abstract Connector interface; Phase 9)

Convention:
  - Pure functions where possible. Side effects belong in api modules.
  - No SQLAlchemy imports; no FastAPI imports.
  - Tested without a database (CLAUDE.md "domain layer tests are mandatory").
"""
