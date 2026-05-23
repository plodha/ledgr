# Pitfalls Research — Personal Finance App

**Domain:** Self-hostable personal finance / cash-flow forecasting (Bitwarden model)
**Researched:** 2026-05-23
**Confidence (overall):** MEDIUM — external tool access (WebSearch, WebFetch, Context7) was denied for this run, so findings are drawn from training data on Plaid, SimpleFIN, Firefly III, Actual Budget, YNAB, GnuCash, Maybe Finance, and Lunch Money behaviors. All claims here should be revalidated against current docs in the phase where they apply (notes are inline).

---

## Critical (Build Wrong = Rebuild)

These pitfalls cause architectural damage — schema migrations, full reimport, or losing user trust. Catch them at the schema/interface level **before** Phase 3 and Phase 9.

### C1. Storing money as float (or letting it become float anywhere)
**What goes wrong:** `0.1 + 0.2 != 0.3` is famous, but the real damage in finance apps is silent. A category total over 6 months drifts $0.03; user opens a CSV export and the sum is off by a penny vs. the bank statement. Trust dies.
**Why it happens:** A single careless `parseFloat`/`float()` in CSV parsing, a JSON.parse on the wire, an ORM column declared `Numeric` instead of `BigInteger`, or a JS frontend that does `amount / 100` for display and later sends that back to the API.
**Consequences:** Forecast totals don't match account totals. Reconciliation against bank statements fails. Once data is corrupt, you cannot reverse it without redoing imports.
**Prevention (already in CLAUDE.md, reinforce):**
- INTEGER cents in DB and on the wire — **including JSON request/response bodies**.
- Frontend never does arithmetic on cents-divided-by-100. Display uses a formatter; arithmetic happens server-side or on integer cents.
- Add a Pydantic validator that rejects non-integer amount inputs.
- Property-based test: `sum(transactions.amount_cents) for category == category_total_cents` must hold for any random sample.
**Warning signs:** Any `Decimal`, `float`, or `number * 100` appearing in a transaction code path. `.toFixed(2)` in any data-handling (not display) code.
**Phase:** Phase 3 (introduce transactions) — write the property test then. Phase 4 (CSV) and Phase 9 (Plaid) re-verify on import.
**Confidence:** HIGH (standard finance-software discipline; ROADMAP already enforces).

### C2. Conflating `merchant_category` with `intent_category_id`
**What goes wrong:** A developer "simplifies" by storing one category field. When the user re-categorizes a Whole Foods purchase from "Groceries" to "Gifts," the bank-provided merchant label is lost. Six months later, "what did Whole Foods say this was?" is unanswerable. Auditability is gone.
**Why it happens:** It feels redundant. A rules engine adds pressure to keep them in sync. A junior dev sees two columns "doing the same thing" and refactors.
**Consequences:** Cannot retrain rules from bank-truth. Cannot answer "is this merchant always Groceries?" Cannot detect when a bank's MCC mapping changes. User cannot toggle a "show bank labels" view.
**Prevention:**
- Two columns, comment in the model file explaining why.
- `merchant_category` and `mcc` are immutable after insert — enforce via a DB trigger or a domain-layer guard. Plaid/CSV ingestion writes them once; nothing else does.
- `intent_category_id` is the only category column writable post-creation.
- An ADR (`adr/00X-merchant-vs-intent-category.md`) so future contributors don't "fix" this.
**Warning signs:** PR adds `UPDATE transaction SET merchant_category=...`. A migration "consolidates" the two fields. Rules engine writes back to `merchant_category`.
**Phase:** Phase 3. Lock this down with the ADR before any rules engine work in Phase 5.
**Confidence:** HIGH (explicit ROADMAP decision; danger is future drift, not initial design).

### C3. Missing `household_id` on a domain table or in a query
**What goes wrong:** A new feature in Phase 10 (price observations) ships with a query that filters by `tracked_item_id` but not by `household_id`. Two households happen to track the same item. User A sees user B's price observations. In the worst case, a settings page exposes another household's account list.
**Why it happens:** Developer thinks "this is scoped by the FK chain" — but the FK chain isn't always tight (e.g. a many-to-many table, or a `price_snapshot` keyed only by `symbol`). Or: developer adds `WHERE user_id = ?` instead of `WHERE household_id = ?`. Or: a webhook handler runs un-scoped because it's "system context."
**Consequences:** Privacy breach. Multi-tenant data leakage. In a self-hosted single-household instance this is dormant; in the cloud version it's a P0.
**Prevention:**
- Every domain table has a `household_id` column. **Add it even if it feels redundant** (e.g. `line_item` could reach household via `receipt → transaction → household`, but store it anyway). Cost: one UUID per row. Benefit: every query is one-step scoped.
- **Row-level security in Postgres** as a defense-in-depth layer: `ALTER TABLE x ENABLE ROW LEVEL SECURITY` + a policy on `current_setting('app.household_id')`. The app sets the GUC at request start; even a buggy query cannot leak.
- A `HouseholdScoped` base class / SQLAlchemy mixin: any query that doesn't go through it raises in tests.
- A pytest fixture creates two households with overlapping data; every list/get endpoint test asserts the second household's data is invisible.
- CI lint rule: any `select(Model)` without `.where(Model.household_id == ...)` is flagged unless the model is in an allowlist of global tables (`mcc_codes`, `price_snapshot`).
**Warning signs:** Any new endpoint without a corresponding "cross-household isolation" test. Webhook code that fetches by external ID (`plaid_item_id`) without re-asserting household scope.
**Phase:** Phase 1 (introduce the mixin and RLS at the same time as `household`). Re-audit at every phase that adds a new table. **Phase 13 is too late** — by then there are 14 tables.
**Confidence:** HIGH (standard multi-tenant practice; this is the single highest-stakes pitfall for the cloud version).

### C4. Using bank/provider transaction IDs as your primary key
**What goes wrong:** You make `transaction.id = plaid_transaction_id`. Then Plaid changes the ID on pending → posted transition. Foreign keys break, user notes vanish, line items detach.
**Why it happens:** Convenience. It feels like a natural unique ID.
**Consequences:** Either you redesign the FK graph mid-flight, or you keep the old ID as a "ghost" row and double-count.
**Prevention:**
- Your own UUID is the PK. **Always.**
- `external_id` columns (one per provider) are nullable, indexed, and unique-per-provider.
- The connector layer is the only code that reads/writes `external_id`. Domain logic uses your UUID exclusively.
- Reconciliation maps external → internal with a separate `external_transaction_ref` table if a transaction can have multiple external identities (e.g. CSV import + later Plaid backfill of same row).
**Warning signs:** A migration that sets `transaction.id = ?` with a non-UUID source. A foreign key from a child table to a column named `plaid_transaction_id`.
**Phase:** Phase 3 (transaction PK design). Lock before Phase 9.
**Confidence:** HIGH (Plaid documents transaction_id can change on pending → posted; SimpleFIN IDs are also not guaranteed stable across institutions — re-verify both in Phase 9/11 against current docs).

### C5. Soft-deletion semantics that lie
**What goes wrong:** "Delete category" cascades to NULL on `transaction.intent_category_id`. User had 800 transactions in "Restaurants." They delete the category. All 800 are now uncategorized. Reports break silently.
**Why it happens:** Cascade defaults. Or the inverse: hard ON DELETE RESTRICT blocks the user with an error they can't action.
**Consequences:** Either silent data loss (cascade NULL) or unusable UI (RESTRICT with no path forward).
**Prevention:**
- Categories are `is_archived` (soft-deleted), not hard-deleted, when transactions reference them.
- Hard-delete is only allowed when reference count is zero — UI shows "X transactions still use this category, reassign them first."
- Same model for accounts (already in schema as `is_archived`), connectors, rules.
- An archived category still appears in historical transaction views, but is hidden from the category picker on new transactions.
- Test: archive a category, edit a transaction that used it, verify the old category is shown in a "(archived)" state and not in the dropdown.
**Warning signs:** `ON DELETE CASCADE` or `ON DELETE SET NULL` on any FK pointing to a user-facing dimension table (category, account, cardholder, tracked_item).
**Phase:** Phase 3 (category model), revisited every phase that adds a dimension table.
**Confidence:** HIGH.

### C6. Category hierarchy without cycle prevention
**What goes wrong:** Parent/child categories. User makes "Food" → child of "Restaurants" → which is already a child of "Food." Infinite recursion on any rollup query. Or: deleting a parent orphans children with no UI to reparent them.
**Why it happens:** The schema permits cycles; nothing prevents them.
**Consequences:** Hung queries, crashed pages, support tickets.
**Prevention:**
- DB-level constraint: a recursive CTE check, or store `path` as `ltree` (Postgres extension) and CHECK that no path contains the row itself.
- Domain-layer guard in `update_category(parent_id=...)`: walk parents and reject if loop detected.
- Cap depth at 2 (parent → child, no grandchildren) unless there's a documented reason otherwise. Most personal finance apps that allow unlimited depth regret it.
- On parent archive: children are reparented to grandparent (or root) automatically and shown in an "Auto-reparented" notification.
**Warning signs:** `category.parent_id` exists without a corresponding update guard. Rollup queries written as recursive CTEs without depth limits.
**Phase:** Phase 3.
**Confidence:** HIGH.

### C7. Pending transactions counted in totals
**What goes wrong:** User's dashboard shows "Restaurants this month: $342." Half of that is pending Uber Eats authorizations that will be voided. User makes a budget decision on inflated numbers.
**Why it happens:** Simplest query is `SUM(amount_cents) WHERE category_id = X`. Filtering by `status = 'posted'` is an "obvious" omission.
**Consequences:** Forecasts are wrong (the headline feature). Budgets feel arbitrary. Users abandon.
**Prevention:**
- A canonical domain function `list_transactions_for_totals(...)` that always filters `status = 'posted'`. All sum/aggregate code routes through it.
- "Pending" is its own visible bucket on dashboards — shown but separated.
- Test: insert 10 posted + 5 pending, assert category total only includes the 10.
- ROADMAP's "transaction date reference" table already calls this out; codify it in `packages/domain/transactions/totals.py`.
**Warning signs:** Any `SUM(amount_cents)` without a status filter. A view definition that doesn't filter pending.
**Phase:** Phase 3. Critical to lock before Phase 7 (forecast).
**Confidence:** HIGH.

### C8. Connector interface leaks provider details into domain
**What goes wrong:** Phase 9 ships with `transaction.plaid_pending_transaction_id` directly in the domain model. Phase 11 (SimpleFIN) adds `simplefin_id`. Phase 14 (Plaid Investments) adds three more. The "abstract Connector interface" is now a fiction.
**Why it happens:** Each provider exposes useful metadata; the path of least resistance is to add a column. The Connector interface is observed in spirit but not in implementation.
**Consequences:** Reconciliation logic special-cases each provider. The "swap Plaid for SimpleFIN with zero logic changes" promise breaks. Adding a fourth provider is a month of work.
**Prevention:**
- One `external_account_ref` and `external_transaction_ref` table, polymorphic on `provider`. JSON column for provider-specific blobs.
- The Connector interface returns normalized `RawTransaction` and `RawBalance` Pydantic models — provider-specific fields don't cross that boundary.
- ADR locking the interface signature; PRs that widen it require justification.
- Integration test: `PlaidConnector` and `SimpleFINConnector` (mocked) both feed the same reconciliation function; assert identical output for identical normalized input.
**Warning signs:** A column named `plaid_*` or `simplefin_*` in any table not in `packages/db/models/connectors/`. A `if connector.type == 'plaid':` branch in domain or reconciliation code.
**Phase:** Phase 9 (Plaid). Build the interface so deliberately that Phase 11 (SimpleFIN) really is "implement the interface, ship."
**Confidence:** HIGH.

---

## Important (Easy to Fix Later, But Painful)

### I1. CSV duplicate detection that's too strict or too loose
**What goes wrong:**
- **Too strict** (hash of date+amount+merchant): two genuinely separate $5.00 Starbucks visits on the same day are deduped into one. User loses a real transaction.
- **Too loose** (hash of date+amount only): a Plaid sync of the same week's data on top of a CSV import double-counts everything.
**Why it happens:** ROADMAP Phase 4 proposes `hash(account_id + transaction_date + amount_cents + merchant_name)`. This is the right starting point but fails on the legitimate-duplicate case.
**Consequences:** Either missing real transactions or doubled totals. Both kill trust.
**Prevention:**
- Dedup is a **suggestion**, never silent. Always show "X potential duplicates" in the preview UI with side-by-side rows. User confirms.
- Allow user to mark a "duplicate" as "actually a different transaction" — store `duplicate_override = true` so re-imports honor the decision.
- Use a "soft hash" (date + amount + merchant_normalized) to flag candidates, but require user resolution on collisions.
- Reconciliation between CSV and Plaid uses a wider window (±3 days, ±$0.01 for amounts < $10 to handle tip adjustments) and is **always a user-confirmation flow**, never automatic merge unless an exact external_id match exists.
**Warning signs:** Any import path that silently drops rows without surfacing a count and a list. A "skipped duplicates" log nobody reads.
**Phase:** Phase 4 (CSV), revisited in Phase 9 (Plaid reconciliation).
**Confidence:** HIGH.

### I2. Date format hell in CSV imports
**What goes wrong:** Chase exports `MM/DD/YYYY`. American Express exports `MM/DD/YY`. International cards export `DD/MM/YYYY`. Some banks export `YYYY-MM-DD`. Some use `1/5/24` (no leading zero, ambiguous year). A naive parser will turn `01/05/2024` into May 1 for half your users and January 5 for the other half.
**Why it happens:** Python's `dateutil` "helpfully" guesses. JavaScript's `Date()` constructor is famously inconsistent.
**Consequences:** Off-by-many-days transactions. Pending appears in the wrong week. Forecast accuracy drops. User loses faith.
**Prevention:**
- Mapping wizard **forces** the user to pick the date format from a dropdown of explicit formats (no guessing): `MM/DD/YYYY`, `DD/MM/YYYY`, `YYYY-MM-DD`, `M/D/YY`, etc.
- Preview screen shows "first row date parsed as: 2024-05-01 (Wednesday)" — user must visually confirm before commit.
- `csv_import_mapping` remembers the format per institution.
- Never use `dateutil.parser.parse(string)` with no `dayfirst` argument on unknown data.
- Test fixtures with each of the 6 common formats; assert parser raises (not guesses) when format is ambiguous and not specified.
**Warning signs:** Any `parse(...)` without an explicit format string. A successful import where the user didn't see a preview.
**Phase:** Phase 4.
**Confidence:** HIGH.

### I3. CSV amount sign convention chaos
**What goes wrong:** Some banks export charges as positive ("you spent $30"), some as negative ("balance changed by -$30"). Some put debits in one column and credits in another. Some use parentheses for negatives. Refunds are inconsistent across all of them.
**Consequences:** Spending shows up as income; income shows up as spending. Net worth swings wildly. Once imported, hard to reverse without remembering which rows came from which file.
**Prevention:**
- Mapping wizard has an explicit "What does a positive number mean here?" question per institution: `outflow (charges positive)` or `inflow (deposits positive)` or `two-column (debit/credit)`.
- Preview shows "this CSV will create $X in spending and $Y in income — does that match the statement?" before commit.
- `import_batch` stores the sign convention used, so a re-import or audit can verify.
- For credit card accounts specifically: payments TO the card show up as positive in some exports (reducing balance is "positive" to them), which is the opposite of how a checking export looks. Test with both.
**Warning signs:** A CSV import that doesn't ask the user about sign. An import that creates "income" of exactly $0 when the statement period had payments.
**Phase:** Phase 4.
**Confidence:** HIGH.

### I4. Split transactions in CSV (and elsewhere) modeled inconsistently
**What goes wrong:** ROADMAP has `transaction.is_split` boolean on Phase 3 but no split children table. Half the codebase reads `is_split` and looks for children that don't exist; the other half SUMs over a phantom split column.
**Why it happens:** Split is added late, with a bolt-on table, and the parent transaction still has its original `amount_cents` while children also sum to that amount. Reports double-count.
**Consequences:** Category totals double-count or single-count depending on how the query was written. Forecast input is wrong.
**Prevention:**
- One canonical model from Phase 3: either
  - **(A)** parent transaction is a "container" with `amount_cents = sum(children)` and is excluded from totals (totals only sum leaves), or
  - **(B)** parent owns `amount_cents`, children are virtual rows that share an ID and re-categorize portions, where totals always go through a view that picks one of them.
- Document which one in `docs/SCHEMA.md` with a concrete example.
- Single domain function `list_transactions_leaf_view()` that always returns the rows that should be summed. Forecast, reports, dashboard all use it.
- Test: a $100 transaction split into $60 Groceries + $40 Household. Sum of all transactions should equal $100, not $200, not $40, not $60.
**Warning signs:** A new query that doesn't go through the leaf-view function.
**Phase:** Phase 3 (decide the model), Phase 4 (importer respects it).
**Confidence:** HIGH.

### I5. Naïve recurring transaction generation (off-by-one, DST, month-end)
**What goes wrong:**
- Monthly bill due "on the 31st" — what happens in February? In April?
- Biweekly paycheck — does the user mean "every other Friday" or "the 1st and 15th"? They mean different things and you have to ask.
- DST transitions move "9am Friday" by an hour twice a year; if you store as TIMESTAMPTZ and treat as wall-clock, you'll generate the wrong date.
- Year boundaries: "every January 15" generated from December 31 should produce next year's January, not this year's.
**Why it happens:** Date math is famously brittle. `+ relativedelta(months=1)` does the right thing for most cases; the corner cases are where bugs hide.
**Consequences:** Forecast misses a paycheck (off by a day → off by a week of cash flow). Bill reminders fire on wrong dates. Phase 7 forecast becomes untrustworthy because the inputs are wrong.
**Prevention:**
- Use `python-dateutil`'s `rrule` (RFC 5545) for cadence calculations, not hand-rolled month arithmetic. It handles end-of-month, leap years, DST correctly.
- Store cadence as `RRULE`-compatible fields (`freq`, `interval`, `byday`, `bymonthday`) — not just a `cadence` enum. The enum becomes the UI presentation; the rrule is the truth.
- For "biweekly," store the **first occurrence date** explicitly; everything is computed from there.
- For "monthly on the 31st" — store `bymonthday=-1` (last day of month) if that's the intent, or `bymonthday=31` with documented behavior on shorter months ("skip" or "clamp to last day").
- Dates only, no times, for recurring financial events — store as `DATE` not `TIMESTAMPTZ`. Avoids DST entirely.
- Test fixture: generate 24 months of "monthly on the 31st," assert February maps correctly per your chosen policy.
**Warning signs:** Hand-written `if month == 12: year += 1` logic. `next_date + timedelta(days=30)`. Any cadence math that doesn't use rrule.
**Phase:** Phase 6. Critical input to Phase 7.
**Confidence:** HIGH.

### I6. Forecast that doesn't decay or quantify uncertainty
**What goes wrong:** Forecast shows a single line. User mentally treats it as a guarantee. Day 60 it's off by $400; user loses trust in the headline feature.
**Why it happens:** Avg spend by category over 90 days is a point estimate. Variance is huge for irregular categories (travel, gifts). Showing one line implies certainty you don't have.
**Consequences:** First time the forecast misses by 10%, the user stops opening the app.
**Prevention:**
- Show a band, not a line: median + p25/p75 (or stdev) per day. Even if the methodology is simple, the visual communicates uncertainty.
- Weight recent data heavier than old data (exponential decay) so a one-time spike doesn't poison the next 90 days.
- Exclude outliers from "avg spend" calculation — a one-time $2000 vet bill in March shouldn't be projected forward as monthly.
- Track forecast accuracy explicitly (per ROADMAP Phase 7 already calls for this) — and show it to the user: "Last month's forecast was within 7% of actuals." Builds trust through honesty.
- Pre-flight check: if scheduled-transaction coverage < some threshold (e.g. the user hasn't added a paycheck), banner says "Add your income source for a more accurate forecast."
**Warning signs:** Forecast endpoint returns a single number per day. No accuracy metric visible. No outlier handling in the avg calc.
**Phase:** Phase 7.
**Confidence:** MEDIUM (forecasting design is a judgment call; uncertainty visualization is broadly recognized as best practice but specific approach varies).

### I7. Timezone handling on `transaction_date`
**What goes wrong:** Bank posts a transaction "April 1" in their local timezone (often Eastern). User is in Pacific. App stores it as `TIMESTAMPTZ` and converts to UTC midnight Pacific, which lands on April 2. User's "March" view is missing the transaction.
**Why it happens:** `transaction_date` semantically is a calendar date — but a `TIMESTAMPTZ` column will be timezone-converted on read.
**Consequences:** Off-by-one transactions at month boundaries. Quarterly reports are wrong. Reconciliation against bank statements fails on the last day of a month.
**Prevention:**
- `transaction_date` is `DATE`, not `TIMESTAMPTZ`. Same for `post_date`. (CLAUDE.md says "store as DATE or TIMESTAMPTZ" — for transaction calendar dates, choose DATE explicitly.)
- `post_date` is also `DATE`.
- `created_at` / `updated_at` / `synced_at` are `TIMESTAMPTZ` (events with a wall-clock moment).
- Bank-provided timestamps that arrive as full datetimes get truncated to the bank's local date (store the bank's timezone per institution if available; default to user's account-level timezone setting; if neither, log a warning).
**Warning signs:** `transaction_date` declared as `TIMESTAMPTZ` or `TIMESTAMP`. Any timezone conversion logic on transaction dates.
**Phase:** Phase 3. Hard to fix later.
**Confidence:** HIGH.

### I8. LLM receipt parsing with no cost/failure guardrails
**What goes wrong:** Phase 12 ships. User has a stack of 200 old receipts. They upload all at once. App fires 200 LLM calls. User's BYO API key hits a rate limit (cloud) or a $200 bill (self-host). Or: parser returns valid-looking JSON with hallucinated line items that don't match the receipt; user trusts it and saves; tracked-item prices are corrupted forever.
**Why it happens:**
- No rate limiting.
- No "you're about to spend $X" warning.
- No structured-output validation.
- No human-in-the-loop confirmation (ROADMAP does call for this — easy to skip under pressure).
**Consequences:** Runaway costs, hallucinated price data, "auto-trigger price observations" (Phase 12) writes garbage to the tracked-item history that breaks Phase 10 charts.
**Prevention:**
- Hard rate limit per household: e.g. 50 receipts/day, configurable per self-host.
- Per-upload cost estimate shown to the user: "this will cost ~$0.02 against your Anthropic key" before firing.
- Structured output validation: parser MUST return JSON conforming to a Pydantic schema; on validation failure, mark parse_status='failed' and require manual entry.
- Confirmation UI is **mandatory**, not optional (per ROADMAP). Don't add a "trust auto-parse" shortcut.
- Total receipt amount validation: sum(line_items.amount_cents) must equal receipt.total_cents within $0.05; otherwise flag as parse failure even if JSON is valid.
- Deterministic structured parsers for Costco/Amazon (ROADMAP already plans this) cut LLM volume by 50%+ — prioritize.
- Cache OCR results so re-parsing doesn't re-OCR.
- Use the LLM provider's structured-output / tool-use mode (Anthropic tool_use, OpenAI structured outputs) rather than asking for "JSON" in a prompt — much lower hallucination rate.
- Auto-price-observation (line item → tracked_item match) only fires on **fuzzy match score above threshold AND user-confirmed receipt**. Never automatic from a low-confidence parse.
**Warning signs:** Receipt endpoint that fires LLM call without preview. No per-household rate limit. Auto-observation that doesn't require receipt confirmation first.
**Phase:** Phase 12.
**Confidence:** HIGH.

### I9. Plaid token storage & rotation
**What goes wrong:** `access_token`s are stored in plaintext or with a single hardcoded key. Self-hoster's DB backup leaks; all bank credentials are compromised. Or: secret rotation is impossible because the encryption key is in code.
**Why it happens:** "Encrypted" is a checkbox; the implementation cuts corners.
**Consequences:** Catastrophic for the cloud version. Embarrassing for self-hosters. Plaid will deactivate keys on report of a leak.
**Prevention:**
- Encrypt tokens with a key from `SECRET_KEY` env var (or a separate `ENCRYPTION_KEY` for rotation). Use `cryptography.fernet` or libsodium secretbox — not a hand-rolled XOR.
- Store an `encryption_key_version` column on the row so rotation is possible: new tokens encrypted with key v2; old tokens decrypted with v1 on access and re-encrypted with v2.
- For self-hosters: document `make rotate-keys` workflow in README.
- For cloud: use AWS KMS / similar; never put a real key in the env.
- The `access_token` is never logged, never returned in API responses, never visible in admin UIs (show "•••" or last 4 only).
- An audit log of token use ("Plaid sync ran at T using item X") so unusual access is detectable.
**Warning signs:** Plaintext `access_token` column. `SECRET_KEY` re-used for both JWT signing and token encryption. Any code path that logs the full token.
**Phase:** Phase 9. Design before any real token is stored.
**Confidence:** HIGH.

### I10. Plaid `ITEM_LOGIN_REQUIRED` not surfaced to the user
**What goes wrong:** Bank requires reauth (MFA expired, password changed). Plaid returns `ITEM_LOGIN_REQUIRED`. Background sync job logs an error and moves on. Two weeks later, user wonders why no new transactions are showing up. Forecast is now based on stale balances.
**Why it happens:** Webhook handler logs errors silently. No UI surface for "this connector is broken." Sync job runs in background, no foreground signal.
**Consequences:** Silent data staleness. Forecast accuracy drops. Users can't tell whether "no transactions" means "no spending this week" or "we're broken."
**Prevention:**
- `connector.status` enum: `active | needs_reauth | error | disabled`.
- Webhook handler maps Plaid `ITEM_ERROR` / `ITEM_LOGIN_REQUIRED` / `USER_PERMISSION_REVOKED` (re-verify exact error codes against current Plaid docs in Phase 9) → `connector.status` and stores `last_error_at`, `last_error_message`.
- Banner on dashboard: "X connector needs attention — last synced N days ago."
- Forecast caveats: if any connector is in `needs_reauth` state and `last_synced_at > 3 days ago`, the forecast view shows "Some accounts may be out of date."
- `update_link_token` flow (Plaid's reauth-without-relink) wired into Settings UI per current Plaid docs.
**Warning signs:** Webhook handler with a bare `except`. No UI element that shows last-sync-at and status per connector. Forecast doesn't disclaim staleness.
**Phase:** Phase 9.
**Confidence:** MEDIUM (general principle is clear; specific Plaid error codes/flows should be reconfirmed against current docs in Phase 9 — could not verify in this research run).

### I11. Webhook idempotency
**What goes wrong:** Plaid retries a webhook. You process it twice. A transaction is created twice. Or: a webhook arrives during a sync you're already running; race condition produces partial duplicates.
**Why it happens:** Webhooks are at-least-once. Handlers are written as if at-most-once.
**Prevention:**
- Every webhook handler is idempotent on a `(item_id, webhook_code, webhook_id_from_provider)` key, stored in a `webhook_event` table; second attempt is a no-op.
- Sync logic uses Plaid's `cursor` (Transactions Sync API) which is itself idempotent — store the cursor per item, only advance after successful write.
- A row-level advisory lock per connector during sync so concurrent webhooks queue rather than collide.
**Warning signs:** Webhook handler that doesn't dedup. Sync that re-fetches "the last 30 days" rather than using the cursor.
**Phase:** Phase 9.
**Confidence:** HIGH.

### I12. Rules engine that runs against the DB (not pure)
**What goes wrong:** Phase 5 ships a rule evaluator that does `db.session.query(Transaction).filter(...)` inside the rule logic. To re-apply rules to history, you replay the live DB. The function is impossible to test without a DB, impossible to dry-run, and impossible to parallelize.
**Why it happens:** Convenience. The first rule needs to look up a category by name; it's "easier" to query.
**Consequences:** Rules engine can't be tested in isolation. "Preview what this rule would do" is impossible. Re-apply to history is slow and risky.
**Prevention (ROADMAP already mandates this):**
- Rule evaluator signature: `evaluate(rule: Rule, transaction: NormalizedTransaction) -> CategoryId | None`. Pure function. No I/O.
- Categories looked up by ID (passed in), not by name (queried).
- Unit tests with no DB fixture.
- Re-apply-to-history is a separate orchestrator: it pages transactions from DB, runs the pure function, writes results.
**Warning signs:** `import db` or `Session` inside `packages/domain/categorization/`.
**Phase:** Phase 5.
**Confidence:** HIGH.

### I13. Bill reminder false negatives (timezone, holidays, autopay flips)
**What goes wrong:**
- User's card is on autopay; they un-toggle it temporarily. Bill is now due in 5 days; the "action needed" widget doesn't refresh until tomorrow. They miss the payment.
- A bill due "the 1st" actually drafts on Friday the 29th because the 1st is a Sunday. Reminder fires too late.
- `payment_due_day = 31`, current month has 30 days, computed due date is invalid.
**Why it happens:** Day-of-month math is naïve. State changes (autopay toggle) don't invalidate cached projections.
**Consequences:** Missed payments, late fees, broken core promise of "never miss a payment."
**Prevention:**
- Compute the "next due date" using rrule-style logic (same engine as recurring transactions, Phase 6).
- For credit cards: due date is computed from statement close date + grace period (typically 21–25 days), not a fixed day-of-month. Allow user to override but default to the bank-statement model.
- On autopay toggle: invalidate any cached reminder for that account.
- "Action needed" widget queries live, not a materialized view, until perf demands otherwise.
- Test: account with `payment_due_day=31` in a 30-day month, assert behavior is clamp-to-last-day with no exception.
**Phase:** Phase 8.
**Confidence:** MEDIUM (specifics depend on bill model design; principle holds).

### I14. Encryption-at-rest for sensitive columns half-done
**What goes wrong:** Plaid access tokens encrypted. But: `account.account_number_last4` is plaintext. `csv_import_mapping` stores institution name in plaintext. `email` is plaintext. An attacker with DB read access knows the user's bank, last 4, and email — enough for social engineering.
**Why it happens:** "Encrypt the obviously sensitive" pattern; the rest is forgotten.
**Prevention:**
- Threat model in `docs/THREAT_MODEL.md` lists every column with sensitivity classification (public / household-private / encrypted-at-rest / pseudonymized).
- Email is hashed-for-lookup + encrypted-for-display if it must be retrievable; otherwise just hashed.
- Bank account numbers: only last 4, never full. Mask in logs.
- Postgres at-rest encryption (disk/EBS) is not a substitute for column encryption — it only protects against stolen disks, not stolen DB credentials.
**Phase:** Phase 1 (auth/user table) for email/password. Phase 9 for Plaid tokens. Audit at v1.0 ship.
**Confidence:** MEDIUM (depends on threat model decisions yet to be made).

---

## Operational (Post-Launch Issues)

### O1. Migrations with downtime self-hosters can't tolerate
**What goes wrong:** A `ALTER TABLE transaction ADD COLUMN new_thing NOT NULL DEFAULT 'x'` on a household with 500K transactions locks the table for 30 seconds. Self-hoster restarts the container during the lock; migration half-applies; DB is broken.
**Why it happens:** Alembic generates the simple migration; developer doesn't think about lock duration.
**Prevention:**
- Migration style guide in `docs/MIGRATIONS.md`:
  - Add columns nullable, backfill in a separate step, then add NOT NULL.
  - Index creation: always `CONCURRENTLY` for tables > 10K rows (or just always, for safety).
  - Long-running migrations chunked in a separate "data migration" script, not Alembic.
- `make migrate` shows an estimated lock duration if it can be predicted.
- Self-host docs: "do not interrupt migrations. Always back up before upgrade. Container restart during migration may corrupt your DB."
- Backup-before-migrate as part of `make upgrade` flow: snapshot DB to a file, then run migrate, instruct user to delete snapshot only after upgrade verified.
- Major-version migrations get tested against a corpus of "1 year of real-shaped data" in CI.
**Phase:** Phase 0 (set the style), then audited every phase.
**Confidence:** HIGH.

### O2. Docker compose upgrade path nobody documents
**What goes wrong:** Self-hoster on v0.4 wants to upgrade to v0.7. They `git pull && docker compose up`. New container image expects a column that doesn't exist; API crashes; web crashes; user is stranded.
**Why it happens:** Upgrade order isn't documented or enforced. "Just pull and restart" is implied.
**Prevention:**
- `docker compose up` runs migrations as part of api container startup (Alembic upgrade head before serving).
- Migration container is separate from API container so a failed migration doesn't kill the running API on rollback. Or: a `make upgrade` target that runs migrate first, only starts the new api on success.
- Versioned `docker-compose.yml` per release; bumping versions in a single file is the documented upgrade. (Bitwarden's pattern.)
- `UPGRADE.md` per major version with explicit "this version requires these manual steps."
- Compatibility matrix: API v0.7 supports DB schema v0.5 — v0.7 (overlap window) so the "old API + new DB" intermediate state during rolling upgrade works.
**Phase:** Phase 0 (compose setup) and revisited at v1.0 ship.
**Confidence:** HIGH.

### O3. Plaid sandbox != production behavior
**What goes wrong:** Everything works against Plaid sandbox. First real bank link fails because the institution uses MFA flows that don't exist in sandbox. Or: real institution returns pending transactions with edge-case shapes sandbox doesn't generate.
**Why it happens:** Sandbox is too clean.
**Prevention:**
- Test against Plaid's `dev` environment (real banks, throttled, free for low volume) before declaring Phase 9 done.
- Maintain a corpus of "real transaction shapes" captured (anonymized) from your own accounts, used as fixtures.
- Document Plaid environment switching clearly so self-hosters can use sandbox for testing then flip to production.
**Phase:** Phase 9.
**Confidence:** MEDIUM (Plaid dev environment access policy may have changed — re-verify in Phase 9).

### O4. SimpleFIN bridge tokens expire / institution coverage varies
**What goes wrong:** SimpleFIN is a thinner protocol; bridge tokens are tied to a paid bridge service (e.g. SimpleFIN Bridge). User's bridge subscription lapses; sync silently stops. Or: a bank changes their data and the bridge breaks for weeks.
**Why it happens:** SimpleFIN is a community-driven protocol; institution coverage and bridge reliability vary.
**Prevention:**
- Same `connector.status` model as Plaid — surface "no data received in N days" prominently.
- Document SimpleFIN's reality clearly: it's a different model from Plaid, with different reliability characteristics. Don't promise feature parity.
- Test the "what if sync hasn't run in a week" UI explicitly.
**Phase:** Phase 11.
**Confidence:** LOW (SimpleFIN ecosystem details may have shifted; re-verify in Phase 11).

### O5. Performance: transaction table grows unbounded
**What goes wrong:** Year 3 user has 50K transactions. Dashboard query that filters by date range without an index does a full scan. Page takes 8 seconds.
**Common missing indexes (based on standard finance-app query patterns):**
- `(household_id, transaction_date DESC)` — the dashboard query
- `(household_id, intent_category_id, transaction_date)` — category reports
- `(household_id, account_id, transaction_date DESC)` — per-account view
- `(household_id, status, transaction_date)` — pending/posted splits
- Partial index `WHERE status = 'posted'` on `transaction(household_id, transaction_date)` if pending is rare
- Unique indexes on external_id columns per provider
**Prevention:**
- Add the indexes when each query pattern is first introduced (not when slow).
- `EXPLAIN ANALYZE` on every list endpoint at build time; document in PR.
- Pagination on every list endpoint (cursor-based on `(transaction_date, id)`, not offset).
- Plan partitioning by `household_id` at v2 ship if cloud version sees >10 households with >100K rows each. Don't over-engineer at v1.
**Warning signs:** A list endpoint without LIMIT. A query plan that says "Seq Scan" on transaction.
**Phase:** Phase 3 (initial indexes), Phase 7 (forecast queries — likely the biggest cost), v1.0 audit.
**Confidence:** HIGH.

### O6. Backup story for self-hosters is "good luck"
**What goes wrong:** User's DB volume corrupts. They have no backup. All financial history lost. They didn't know they should have configured backups; the README didn't help.
**Prevention:**
- `make backup` target that pg_dumps to a configurable location with timestamped filenames.
- README has a prominent "Set up backups" section with example cron entries.
- An optional sidecar container (e.g. `postgres-backup-local` or similar) included in a `docker-compose.backup.yml` overlay file.
- Restore-from-backup tested as part of release checklist.
- For cloud version: automated daily backups, point-in-time recovery, documented in customer-facing docs.
**Phase:** Phase 0 (Make target) for minimum viable. Hardened at v1.0 ship.
**Confidence:** HIGH.

### O7. Logging financial data
**What goes wrong:** A debug log line `logger.info(f"Processing transaction: {tx}")` writes amounts, merchants, and possibly account numbers to disk. Container logs are aggregated to a log shipper; financial data is now in three places nobody audits.
**Prevention:**
- A `RedactedTransaction` repr for logging — drops `amount_cents`, `merchant_name`, masks `account_number_last4`.
- Lint rule: any log line that includes a model object goes through a redactor.
- Structured logging (already in CLAUDE.md) makes this auditable: only fields you allowlist appear.
- Sensitive request bodies (Plaid webhook payloads, CSV uploads) never logged at INFO level.
**Phase:** Phase 0 (set logging defaults), audited every phase.
**Confidence:** HIGH.

### O8. CSRF / session security gaps
**What goes wrong:** Login uses cookie-based sessions. A malicious site triggers a POST to your API; browser sends cookies; transaction is created without user knowledge.
**Prevention:**
- SameSite=Strict cookies (or Lax with explicit CSRF tokens on state-changing requests).
- CORS configured tightly: `ALLOWED_ORIGINS` enforced, not wildcarded.
- For JWT in localStorage: shorter expiry, refresh-token rotation. (CLAUDE.md notes "JWT or cookie-based"; pick deliberately.)
- Auth ADR documents which choice and why.
**Phase:** Phase 1.
**Confidence:** HIGH.

### O9. Secrets in env files committed to git
**What goes wrong:** Self-hoster fills in `.env`, accidentally commits it to their fork. Plaid keys are now public. Plaid deactivates them.
**Prevention:**
- `.env` is in `.gitignore` from Phase 0. `.env.example` is the committed file.
- README warns prominently: "never commit `.env`."
- Optional: pre-commit hook that scans for known patterns (`PLAID_SECRET=`, `ANTHROPIC_API_KEY=sk-`) and blocks.
**Phase:** Phase 0.
**Confidence:** HIGH.

### O10. Per-household resource exhaustion (denial of self)
**What goes wrong:** User uploads a 500MB CSV. API parses it all in memory. Container OOMs. Other households on the same instance go down.
**Prevention:**
- CSV upload size limit (e.g. 50MB hard cap).
- Streaming CSV parser (don't `df = pd.read_csv(...)` the whole file).
- Background job for imports > some row count, with progress polling.
- Per-household rate limits on receipt parsing (already noted in I8), CSV imports, Plaid sync triggers.
**Phase:** Phase 4 (CSV limits), Phase 12 (receipts).
**Confidence:** HIGH.

---

## Per-Phase Warnings

### Phase 0 — Skeleton
- **O9** Secrets discipline (`.gitignore` for `.env`).
- **O1, O2** Migration & upgrade story established now (even if no migrations exist yet). Document `docs/MIGRATIONS.md` and `docs/UPGRADE.md` skeletons.
- **O6** `make backup` target stub.
- **O7** Structured logging with redaction-friendly conventions.

### Phase 1 — Auth + Household
- **C3** `household_id` mixin + Postgres RLS introduced **here**, before any data table exists. Cost: low. Skip cost: every future table is a leak risk.
- **I14** Email/password handling: bcrypt or argon2 for password hash; email encryption decision documented.
- **O8** Auth security model (cookie vs JWT, CSRF stance) chosen in an ADR.

### Phase 2 — Accounts
- **C5** Account archive vs delete model.
- Account currency field exists but assume single-currency-per-household for v1 (multi-currency is a Phase TBD pitfall on its own — FX rates, rate sources, snapshot dates).

### Phase 3 — Categories + Manual Transactions
- **C1** Money-as-cents property test introduced.
- **C2** ADR: `merchant_category` vs `intent_category_id` immutability locked.
- **C4** Transaction PK is your UUID; `external_id` column nullable.
- **C5** Category archive model.
- **C6** Category hierarchy depth limit (≤2) and cycle prevention.
- **C7** `list_transactions_for_totals()` is the canonical aggregation entry point.
- **I4** Split transaction model decided and documented in `docs/SCHEMA.md` with example.
- **I7** `transaction_date` is `DATE`, not `TIMESTAMPTZ`.
- **O5** Initial indexes added on day one.

### Phase 4 — CSV Import
- **I1** Duplicate detection is suggest-then-confirm, never silent.
- **I2** Date format is user-selected, never guessed.
- **I3** Sign convention is user-confirmed per institution.
- **O10** Upload size cap; streaming parser.
- Edge case: bank's CSV includes the user's email or full account number → strip from `notes` or anywhere it gets stored unless intentional.

### Phase 5 — Rules Engine
- **I12** Rule evaluator is pure; no DB in `packages/domain/categorization/`.
- Rule conflict: when two rules match, priority resolves it; what if priorities are equal? Tie-breaker documented (e.g. higher-priority-numeric wins; on tie, oldest rule wins).
- "Re-apply to history" only re-categorizes where `intent_category_id` was set by a previous rule run or is null — **never** overwrite manual user overrides. Track `intent_set_by` enum (`user | rule | initial_import`).

### Phase 6 — Recurring
- **I5** Use `rrule`; never hand-rolled date math.
- Generator output is read-only — never writes to `transaction` table. Tested.
- Skip / pause functionality: user wants to mark "no paycheck this month" (vacation/unpaid leave). Schema should allow exceptions per scheduled transaction.

### Phase 7 — Forecast ⭐
- **I6** Uncertainty visualization; accuracy tracking from day one.
- **C7** Forecast inputs go through `list_transactions_for_totals()` (posted only).
- Forecast caching: forecast is expensive to recompute; cache per (household, day_of_compute, params); invalidate on new transaction insert or scheduled transaction change. Don't serve a 24-hour-old forecast as if fresh.
- Edge case: an account in `is_archived` shouldn't appear in forecast. Test.
- "What if" scenarios must not mutate stored data — pure functional projection from the same engine.

### Phase 8 — Bill Pay
- **I13** Due date math; autopay toggle invalidates cache.
- "Mark as paid" creates a transaction — what account does it debit? Force user to specify; don't guess.

### Phase 9 — Plaid Connector
- **C4** External IDs never become PKs.
- **C8** Connector interface holds; no Plaid-isms in domain.
- **I9** Token encryption with rotation versioning.
- **I10** `ITEM_LOGIN_REQUIRED` (and current Plaid error taxonomy — re-verify in this phase) surfaced in UI.
- **I11** Webhook idempotency.
- **O3** Test against Plaid dev, not just sandbox.
- Pending → posted: when Plaid changes `transaction_id`, the reconciler matches on `account_id + amount + transaction_date + merchant_name` (and previous pending status), updates external_id to new value, preserves user-set fields (intent_category_id, notes, tags).
- "Removed" transactions: Plaid `/transactions/sync` returns `removed` array. Map to soft-delete with `is_removed_by_provider=true`; don't hard-delete (the user might have notes attached and the bank might restore it).
- Backfill window: when first linking, Plaid offers up to 24 months of history. User option: import all? last 90 days? Default sensibly and let user adjust.

### Phase 10 — Price Tracking
- **C3** `price_observation.household_id` even though reachable via tracked_item.
- Fuzzy line-item-to-tracked-item matching has a confidence score; below threshold = ask user, above threshold + receipt confirmed = auto.
- Same tracked item bought at multiple stores: don't average across stores by default; per-store chart is the primary view.

### Phase 11 — SimpleFIN
- **C8** No SimpleFIN-isms leak into reconciliation. The new connector is the only code that touches the protocol.
- **O4** Connector status surfaces lapsed bridge tokens.
- Quirk: SimpleFIN transaction IDs are bridge-dependent. Treat them with the same "may not be stable" caution as Plaid. Re-verify current SimpleFIN docs in this phase.

### Phase 12 — Receipt Parsing
- **I8** Rate limit, cost preview, structured output validation, mandatory confirmation.
- OCR failure mode: OCR returns garbage on a bad photo. Parser shouldn't silently fail — show "couldn't read this receipt; enter manually?" with a retry option.
- Email intake: SMTP catch needs spam/abuse prevention. Per-household secret address (e.g. `receipts+<token>@yourdomain`) to prevent spam dumping into the system.
- Image storage: receipts may contain PII (loyalty card numbers, payment info on top of receipt). Document retention policy. Allow user to delete the image after parsing while keeping line items.

### Phase 13 — Multi-User UI
- **C3** Final audit: cross-household isolation test for every endpoint that has been built so far. **Don't trust that scoping was done correctly in earlier phases** — verify.
- Role enforcement: owner can invite/remove, member can write, viewer is read-only. Tested per endpoint; CI test that every protected route checks role.
- Invite token expiry, single-use, scoped to one household.
- Transfer-ownership: if owner leaves without transferring, what happens? Force transfer before leave; if last member, household is archived (not deleted, in case of misclick).
- `cardholder_id` on transaction is FK to `household_membership`, not `user` directly — if a member is removed, their historical attribution is preserved via the membership row (don't hard-delete memberships).

### Phase 14 — Investments
- Money for shares is still cents — but quantity is decimal (fractional shares). New rule: position math uses Decimal for `quantity_decimal`, never float, even in JS.
- Price source rate-limited: don't hammer Yahoo Finance. Cache aggressively.
- Cost basis tracking gets ugly fast (FIFO vs specific lot vs average); v1 scope to "single cost basis per position." Document it as a known limitation.

---

## Cross-Cutting Reminders

- **The forecast is the headline feature (PROJECT.md core value).** Every pitfall above that affects data accuracy in Phases 3, 6, and 9 affects the forecast. Treat those phases as load-bearing for the product, not just stepping stones.
- **Household isolation is the single highest-stakes correctness concern** when the cloud version exists. Audit per phase, never "we'll do it later."
- **Self-host vs cloud parity:** every BYO-key path (Plaid, SimpleFIN, LLM) needs equivalent UX (clear "your key, your cost" messaging) and equivalent guardrails (rate limits, cost preview). Self-hosters foot-shoot themselves the same way cloud users would, just with their own wallet.
- **Trust is earned through accuracy and lost through one bad number.** A single $0.03 drift or one wrong-month transaction is enough for a careful user to lose faith. Test for it.

---

## Confidence Assessment

| Category | Confidence | Note |
|---|---|---|
| C1–C7 (data model pitfalls) | HIGH | Standard finance-software practice; well-aligned with ROADMAP intent. |
| C8 (connector abstraction) | HIGH | Pattern is well-established; ROADMAP already commits to it. |
| I1–I7 (import/forecast) | HIGH | Common pitfalls documented across many personal-finance projects. |
| I8 (LLM cost/parsing) | HIGH | Recent industry experience with LLM pipelines; structured output is now standard. |
| I9–I11 (Plaid specifics) | MEDIUM | Principles solid; **specific Plaid error codes, webhook formats, and Transactions Sync cursor behavior must be re-verified against current Plaid docs in Phase 9** — external doc access was denied for this research run. |
| I12 (rules engine) | HIGH | ROADMAP already commits to pure functions. |
| I13 (bills) | MEDIUM | Specifics depend on yet-undecided bill model. |
| I14 (encryption) | MEDIUM | Depends on threat model decisions. |
| O1–O10 (operational) | HIGH | Standard ops discipline. |

## Sources

External documentation access (WebSearch, WebFetch, Context7 MCP, ctx7 CLI) was denied during this research session. Findings are drawn from training data on:
- Plaid Transactions Sync API & webhook conventions (re-verify in Phase 9)
- SimpleFIN protocol notes (re-verify in Phase 11)
- Firefly III community-known issues (duplicate detection, CSV mapping, OFX gotchas)
- Actual Budget design choices (date handling, reconciliation flow)
- YNAB and Lunch Money UX patterns (pending vs posted)
- General Postgres / SQLAlchemy / FastAPI multi-tenancy practice
- LLM structured-output best practice (Anthropic tool_use, OpenAI structured outputs)

**Recommended next step at each phase boundary:** revalidate provider-specific claims (Plaid, SimpleFIN, LLM provider) against current official docs at the phase that consumes them. Do not treat this document as a source of truth for current provider error codes or API shapes.
