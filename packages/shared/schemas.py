"""packages/shared/schemas.py — Pydantic v2 base schemas.

ALL domain types live here (per CLAUDE.md constraint #2).
Never define a domain shape inline in a route or component.

Phase 0: empty. Phase 1+ adds:
  - HouseholdCreate, HouseholdRead
  - UserCreate, UserRead, UserLogin
  - AccountCreate, AccountRead
  - TransactionCreate, TransactionRead (with INTEGER cents per CLAUDE.md constraint #4)

Convention:
  - Use Pydantic v2 BaseModel (not dataclasses, not SQLModel).
  - Read schemas separate from write schemas (e.g., UserCreate vs UserRead).
  - All monetary fields are int (cents). Display conversion lives client-side.
  - All dates are ISO 8601 strings on the wire; DATE/TIMESTAMPTZ in DB.
"""
