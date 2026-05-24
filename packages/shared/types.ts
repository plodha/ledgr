/**
 * packages/shared/types.ts — TypeScript domain types shared across the web app.
 *
 * ALL domain types live here (per CLAUDE.md constraint #2).
 * Never define a domain shape inline in a component.
 *
 * Phase 0: empty. Phase 1+ adds:
 *   - HouseholdSchema (Zod) + Household (z.infer type)
 *   - UserSchema (Zod) + User
 *   - AccountSchema, TransactionSchema, etc.
 *
 * Convention:
 *   - Define Zod schemas; derive TS types via z.infer<typeof Schema>.
 *   - Share validation between API requests (TypeScript types) and form
 *     validation (React Hook Form + @hookform/resolvers/zod).
 *   - Monetary fields are number (INTEGER cents per CLAUDE.md constraint #4).
 *     Display conversion uses Intl.NumberFormat at render time.
 *   - Date fields are string (ISO 8601). Convert to Date only at render time.
 *   - Always pair `transaction_date` and `post_date` on transactions
 *     (CLAUDE.md constraint #5).
 */

export {};
