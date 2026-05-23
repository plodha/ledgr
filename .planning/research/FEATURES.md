# Features Research — Personal Finance App

**Project:** PRANAV (Personal Resource & Asset Navigator for Abundant Value) — self-hostable personal finance
**Researched:** 2026-05-23
**Confidence:** MEDIUM (see "Research Limitations" below)

---

## Research Limitations (read first)

Both `WebSearch` and `WebFetch` were denied in this environment, so live source verification was not possible. Findings below draw from Claude's training data (cutoff Jan 2026, which is recent for the apps under study) and are categorized by confidence:

- **HIGH** = stable, widely-documented feature in the named app for years
- **MEDIUM** = known feature but exact current behavior may have shifted with recent updates
- **LOW** = inference from product positioning rather than direct knowledge

The parent agent should treat the *categorization* (table-stakes vs differentiator vs anti-feature) as the durable output; specific product behaviors should be re-verified once network access is restored, especially for:
- Monarch Money's current forecast/cash-flow surface (changed substantially in 2024-2025)
- Copilot's expansion outside iOS (web app launched 2024-2025)
- Firefly III and Actual Budget recent feature additions

---

## Table Stakes

These are features users actively expect. Missing them means a new arrival from Monarch/YNAB/Copilot will not stay long enough to evaluate the headline differentiator. Complexity ratings reflect *correct* implementation, not happy-path.

| Feature | Why Expected | Complexity | Phase in Roadmap | Notes |
|---|---|---|---|---|
| Account aggregation (link real banks) | Without it, the app is a glorified spreadsheet | High | Phase 9 (Plaid), 11 (SimpleFIN) | BYO keys is on-brand for self-hosters but unusual — flag in onboarding |
| Manual transaction entry | Even sync-heavy users add cash/Venmo manually | Low | Phase 3 | Roadmap covered |
| CSV import with column mapping | Required for banks Plaid doesn't cover; required for self-hosters who skip Plaid | Medium | Phase 4 | Roadmap covered |
| Category management (hierarchical) | "Food > Groceries > Costco" is the modern expectation | Low-Med | Phase 3 | Hierarchy is in schema — good |
| Auto-categorization rules | DoorDash should categorize itself after the second time | Medium | Phase 5 | Roadmap covered |
| Recurring transactions / scheduled bills | Foundation for forecasting AND for "you'll be charged Tuesday" awareness | Medium | Phase 6 | Roadmap covered |
| Budgeting (some flavor) | Every named competitor has it; absence will be the #1 complaint | Medium-High | **MISSING** | See Roadmap Gap Analysis |
| Net worth tracking + history chart | Standard since Mint; users assume it exists | Low | Phase 2 (current), needs history | Phase 2 only shows current; net-worth-over-time is missing |
| Search transactions (free-text, filterable) | Users routinely answer "did I pay X last month?" | Low-Med | Phase 3 (filtering) | Filter UI implied but search ergonomics matter — easy to underbuild |
| Split transactions | One Costco receipt = groceries + household + clothing | Medium | Phase 3 (`is_split` flag exists) | Implementation discipline needed — `transaction.is_split` is just a flag; need a split_line table or sibling-transaction model |
| Multi-currency *display* (not multi-currency conversion) | International users will balk if every value is "$" | Low | **MISSING** in MVP | Currency field exists on account/transaction; UI needs to honor it |
| Mobile-friendly UI (responsive web) | Most transaction-checking happens on phone | Medium | Implied across phases | Tailwind defaults make this easy; capturing receipts on-device is a Phase 12 concern |
| Reports / spending by category over time | Pie chart by category, trend line by category — every app has both | Medium | **MISSING** explicit phase | Inferred from "dashboard" but not a stated deliverable |
| Pending vs posted transaction visibility | Roadmap correctly flagged this | Low (schema), Med (UX) | Phase 3 | Already a key design decision — good |
| Data export (CSV download) | Self-hosters care about portability; even cloud users want it | Low | **MISSING** | Should be early — see Roadmap Gap Analysis |
| Account archive / "closed" state | People close credit cards; deleting history is unacceptable | Low | Phase 2 (`is_archived`) | Roadmap covered |
| Transaction notes / tags | Beyond category, users tag "tax-deductible", "reimbursable", "vacation" | Low-Med | **MISSING tags** | `notes` is in Phase 3; tags are a separate, very common feature |
| Multi-user / shared household | Couples and partners are a huge segment | High (security) | Phase 13 (UI), schema from Phase 1 | Roadmap correctly designed this in from day one — strong |
| Login / session / password reset | Obvious | Medium | Phase 1 | Password reset is *not* in Phase 1 — needs noting |
| Bill due-date reminders | Late fee avoidance is a top-3 reason users start using finance apps | Low-Med | Phase 8 | Roadmap covered |

---

## Differentiators

Features that meaningfully differentiate PRANAV from incumbents. The forecast is the headline; everything else should reinforce the "trust your future" narrative.

| Feature | Value Proposition | Complexity | Phase | Confidence Notes |
|---|---|---|---|---|
| **Self-hostable + open source** | Bitwarden positioning — own your financial data | High (ops, docs) | All phases | The single largest differentiator. None of Monarch/YNAB/Copilot offer this. Firefly III + Actual offer it but with weaker UX. |
| **Forecast / projected balance per account (30/60/90 days)** | "See where your money is going before it goes there" | High | Phase 7 | See "Is forecast actually differentiating?" below — answer: **partially**, with a real edge |
| **"What if" scenario sliders on forecast** | Active manipulation, not passive viewing | Medium | Phase 7 | This is the actual unique part — see analysis below |
| **Forecast accuracy tracking (vs actuals)** | Builds trust over time; quantifies the projection | Medium | Phase 7 | Genuinely rare. Most apps show projections; very few grade them. |
| **Strawberries Over Time / price tracking** | Personal inflation visibility — track grocery items across stores/time | Medium-High | Phase 10 | Confidence MEDIUM that no competitor does this well; some receipt apps do line items but not longitudinal price tracking. |
| **Bring-your-own-key LLM receipt parsing** | Self-host with your own Anthropic/OpenAI key; no vendor extracts your receipt data | Medium-High | Phase 12 | BYO-key is the on-brand answer to "AI in finance apps". Worth marketing. |
| **`merchant_category` vs `intent_category_id` never merged** | Auditability: bank's label and your label coexist | Low (schema), Med (UX) | Phase 3 | Few apps preserve the bank label cleanly. Power users will notice. |
| **Connector abstraction (Plaid + SimpleFIN + CSV behave identically downstream)** | Switch providers without losing rules or history | High (architecture) | Phases 9, 11 | Invisible to users in the good case; protects against Plaid pricing/policy shifts |
| **Household model from day 1 (not a paid upsell)** | Monarch couple-sharing was the original killer feature; PRANAV makes it free + structural | Medium | Phase 13 | Strong card vs YNAB (paid shared budgeting), Copilot (single-user origin) |
| **Per-cardholder spend attribution** | "How much did each of us spend this month?" — rare done well | Medium | Phase 13 | `cardholder_id` already in schema — implementation discipline is the only risk |
| **Email-intake receipt forwarding** | Forward Amazon/Costco/Uber emails → auto-parsed line items | Medium-High | Phase 12 | Differentiating *if* it works on day one for 3-5 common merchants |
| **Pure-domain rules engine, re-applicable to history** | "I made a new rule — recategorize everything past" works | Medium | Phase 5 | Several apps do this badly (only-future rules). Doing it well is a real edge. |

### Is the forecast actually differentiating in 2026?

**Short answer: yes, but the unique edge is the *sliders* and *accuracy grading*, not the projection itself.**

| App | Forecast / Cash Flow | Confidence |
|---|---|---|
| Monarch Money | Has "Cash Flow" view (income vs expense over month, trended). Added a forward-looking "projected" line for the upcoming month in 2024. Not 30/60/90-day projected daily balance per account. | MEDIUM |
| YNAB | Philosophically opposed to forecasting — "give every dollar a job" is *present*-tense budgeting. No real forecast. | HIGH |
| Copilot Money | Has a "Cash Flow" forecast (monthly projection based on recurring + average spend). Added in 2023-2024. Account-level daily projection is not their angle. | MEDIUM |
| Lunch Money | "Cash flow" tab shows trends; future projection is light. | MEDIUM |
| Actual Budget | Has scheduled-transaction-aware projections; somewhat hidden in UI. | MEDIUM |
| Firefly III | Has "Bills" and recurring; projection feature is present but minimal in default UI. | MEDIUM |
| Mint (defunct) | Never had real forecasting; Credit Karma replacement has none. | HIGH |
| Quicken Simplifi | "Projected cash flow" exists, monthly granularity, fewer scenarios. | MEDIUM |

The space is filling in. The defensible differentiation is:

1. **Daily granularity per account** (most do monthly, all-accounts-combined)
2. **Interactive what-if sliders** (most show one projection; you can't poke it)
3. **Self-graded accuracy** (almost no one shows you how wrong they were last month)
4. **Trust narrative built from infrastructure outward** — accounts → categories → rules → recurring → forecast. The forecast is only as good as the rails under it.

> Recommendation: stop calling it "forecast" in product copy. Call it "trusted cash flow" or "money runway" — emphasize the *trustworthiness* (accuracy grading) over the projection itself, because projections are now common.

---

## Anti-Features

Things to deliberately not build, even when users ask.

| Anti-Feature | Why Avoid | What to Do Instead |
|---|---|---|
| AI chatbot "ask your finances anything" | Hallucination risk on financial data is catastrophic; deterministic reports satisfy 95% of the use case | Build great filters, saved views, and CSV export — let users ask Excel |
| Stock buy/sell signals or recommendations | Regulatory risk (SEC), liability, totally different product | Show portfolio value only (Phase 14); never opinions |
| Credit score monitoring | Requires bureau partnerships, ad-tech model, conflicts with self-host ethos | Out — link to a free standalone tool if asked |
| "Free with ads" tier | Ad targeting on financial data is the Mint failure mode; users left Mint specifically because of this | Self-host is free; cloud has flat subscription |
| Bill negotiation / "we'll cancel your subscriptions" | Third-party-dependent; revenue model conflicts with user; mostly theater | Show subscription detection (Phase 8-adjacent); leave action to user |
| Crypto-native tracking (wallets, DeFi) | Different data model (on-chain, gas, lots), volatile API surface, niche audience | Out for v1-v2; revisit when ETF holdings via brokerage cover most users |
| Tax filing / optimization | CPA-level domain; one wrong recommendation = user audit | Tag transactions as "tax relevant"; export to CSV; let user's CPA do the rest |
| Bank-side rewards optimization ("use Card X here") | Affiliate-revenue conflict of interest; out of scope for "trusted" positioning | Out |
| Child / kid accounts with allowance | Distinct product (Greenlight, Step); different security model | Out until a real user requests it; household roles cover spouse case |
| Built-in goal tracking with motivational gamification | Easy to build badly; users want a forecast and a number, not streaks | Goals as named line items on the forecast (Phase 7 extension), not a separate feature |
| Phone-bill / utility direct integrations | Per-vendor scraping; breaks constantly; low ROI | Out — already correctly flagged in PROJECT.md |
| Auto-payment ("we'll pay your bill for you") | Money-movement license required (state-by-state), KYC, fraud surface | Bill reminders only (Phase 8) — user pays via their bank |
| Receipt auto-capture via bank partnership | Requires enterprise Plaid agreement | Already correctly flagged out |

---

## Competitive Analysis

### Monarch Money
- **Strengths:** Polished UI, joint-household budgeting (became *the* Mint replacement after Mint shut down), strong investment tracking, decent reports, good mobile apps. Spouse-sharing was the differentiator that won them the post-Mint market.
- **Weaknesses:** Subscription price ($14.99/mo or ~$100/yr) keeps creeping. Plaid sync reliability is constant user complaint. Forecast view is shallow. Closed source — when they raise prices, you can't leave with your data easily.
- **Confidence:** HIGH on strengths, HIGH on pricing complaints, MEDIUM on current forecast depth.

### YNAB (You Need A Budget)
- **Strengths:** Strong opinionated method (zero-based budgeting), excellent education content/community, scheduled transactions, multi-device sync, age-of-money metric.
- **Weaknesses:** Steep learning curve. Philosophically anti-forecast (present-tense only). Most expensive (~$15/mo or $109/yr). Not great for high-income/low-stress users who don't want to budget every dollar.
- **Confidence:** HIGH.

### Copilot Money
- **Strengths:** Best-in-class iOS design, fast/snappy, good auto-categorization, recently added Apple Card and Apple Cash support, cash-flow forecast added 2023-2024, expanded to web in 2024-2025.
- **Weaknesses:** Was iOS-only for years (alienating non-Apple users). No multi-user / shared household (as of last public info). US-only Plaid. Newer Android.
- **Confidence:** HIGH on iOS-first heritage; MEDIUM on current platform reach (changes fast).

### Lunch Money
- **Strengths:** Developer-friendly (real API), multi-currency, crypto support, single-developer-built with clear roadmap, transaction tagging, CSV-first workflows. Very loved by power users.
- **Weaknesses:** Limited account aggregation in some regions (Plaid for US, others manual or via Plaid/SaltEdge). Smaller team = slower feature pace. Subscription required even for self-effort.
- **Confidence:** HIGH.

### Actual Budget (self-hosted, open source)
- **Strengths:** True self-host, envelope/zero-based budgeting, scheduled transactions, rules, multi-device sync via a sync server. Active community fork after the original closed-source product was open-sourced.
- **Weaknesses:** UX is rougher than commercial apps. Onboarding for non-technical users is hard. Plaid integration requires bringing your own — same as PRANAV plans. Reporting is functional but not beautiful. No real cash-flow forecast.
- **Confidence:** HIGH on strengths/weaknesses; MEDIUM on most recent feature set.

### Firefly III (self-hosted, open source)
- **Strengths:** Mature (10+ years), very flexible, double-entry accounting model, good for power users, supports many currencies, has rules engine, bill reminders, recurring transactions.
- **Weaknesses:** UX is the #1 complaint — looks like 2015. Setup is hard (Docker, but config has sharp edges). Account aggregation is via separate "Data Importer" project, which has its own UX. Mobile experience weak. Documentation dense.
- **Confidence:** HIGH.

### Common complaints from Firefly III / Actual Budget users (the population PRANAV most directly competes with for migration)
*Synthesized from training data; verify with current GitHub issues + r/selfhosted once network access is restored.*

1. **Bank sync is painful or absent.** Both require BYO solutions; setup is fragile.
2. **Onboarding is brutal.** No first-run flow that holds your hand through "what do I do now that I have it running?"
3. **UI feels dated** (Firefly especially); commercial app refugees miss polish.
4. **Mobile is an afterthought.** No native apps, or limited.
5. **No good forecast.** Both show present + history; neither tells you next month convincingly.
6. **Reports are limited or hard to configure.** Power users build their own queries.
7. **Multi-user is hit-or-miss.** Actual has limited multi-user; Firefly's model is more single-user with workarounds.

> Several of these are exactly where PRANAV's roadmap concentrates: polished UI (Next.js 14 + Tailwind), forecast as headline, household-from-day-one, BYO-key sync abstracted cleanly. That's a real strategic position.

---

## Minimum Viable Feature Set to Switch from Monarch/YNAB

A user will *seriously consider* switching to a self-hosted PRANAV when they have:

1. ✅ Account linking that works (Plaid or SimpleFIN) — Phase 9 / 11
2. ✅ Reliable auto-categorization with rules — Phase 5
3. ✅ Recurring transactions tracked — Phase 6
4. ✅ Net worth that updates daily and shows a chart — **partially in Phase 2 (chart missing)**
5. ✅ A real budget view — **missing from current roadmap**
6. ✅ Bill reminders — Phase 8
7. ✅ Spending reports (by category, over time) — **inferred but not explicit phase**
8. ✅ Search/filter that's actually fast on 10k+ transactions — Phase 3 (UX risk)
9. ✅ Mobile-usable web — implied (Tailwind responsive)
10. ✅ Couple/household sharing — Phase 13
11. ✅ Data export — **missing**

Items in **bold/missing** are gap-closing work below.

### The forecast is the *reason to keep using it long term*, but the table-stakes list above is the reason to *try it past day 3*.

---

## Roadmap Gap Analysis

Items the 14-phase roadmap is missing or under-specifies. Priority is relative — these are not equally severe.

| Gap | Why It Matters | Suggested Placement | Priority |
|---|---|---|---|
| **Budget view** (allocated amount vs actual per category) | This is *the* feature competitors lead with. Phase 6 has scheduled transactions but no budget concept (allocated $X/month for groceries). | New Phase 8.5, or extend Phase 6 | **HIGH** |
| **Net worth history chart** | Phase 2 has current net worth only. Users expect a multi-year line chart. Needs `account_balance_snapshot (account_id, date, balance_cents)` table + nightly job. | Extend Phase 2 or new Phase 2.5 | **HIGH** |
| **Explicit reports phase** (spending by category, trends, year-over-year, monthly summary) | Implied but not a deliverable. Risk: shipped as a thin dashboard, not a real reports surface. | New phase or add to Phase 3 | **HIGH** |
| **Password reset / forgot password flow** | Phase 1 has register/login/logout but not reset. Cannot ship without it. | Add to Phase 1 | **HIGH** |
| **2FA / TOTP** | Financial app without 2FA is a non-starter for security-conscious users (the self-host audience). | Phase 1 or post-v1.0 | **HIGH** |
| **Data export (full CSV/JSON dump)** | Self-host users care intensely about data portability — it's why they self-host. | Phase 1 or 3 | **MEDIUM-HIGH** |
| **Backup / restore** | Self-host users need a documented backup strategy. Phase 0 should at least ship `make backup`. | Phase 0 or 1 | **MEDIUM-HIGH** |
| **Audit log** (who changed what when) | Phase 13 (multi-user) makes this essential — partner accidentally deletes a transaction, you need to recover. | Phase 13 | **MEDIUM** |
| **Transfers between own accounts** (not income/expense) | Moving $500 from checking to savings should not show as income to savings and expense from checking. Detection + linking is a known hard problem. | Phase 3 extension or new phase | **MEDIUM** |
| **Subscriptions detection / view** | Adjacent to recurring transactions (Phase 6) but specifically "which subscriptions am I paying for?" — high-perceived-value with low extra work once Phase 6 exists. | Phase 6 extension | **MEDIUM** |
| **Tags (in addition to categories)** | Many users want "tax-deductible", "reimbursable", "vacation:2026-italy" — orthogonal to category. `notes` field isn't enough. | Phase 3 | **MEDIUM** |
| **Goals (savings goals tied to accounts/categories)** | Lower priority for analytics audience but expected by Monarch/YNAB migrants. Can be light: "I want $X by date Y; show me on the forecast." | Phase 7 extension | **MEDIUM** |
| **Email notifications** (bill due, large transaction, low balance, weekly summary) | Foundation for engagement and the "we noticed" moments that build trust. | Phase 8 extension | **MEDIUM** |
| **Search across all transactions** (not just filtered list) | Easy to underbuild; users expect Cmd-K. | Phase 3 | **MEDIUM** |
| **Multi-currency handling** (storage works; UI rendering + cross-account aggregation needs design) | Schema supports `currency` per account; rendering net worth across currencies needs a base currency + exchange rate snapshot. | Phase 2 design note; implement later | **LOW-MEDIUM** if US-only audience |
| **Onboarding flow** (first-run wizard) | No phase covers what happens after register → first useful screen. | New, ideally before v1.0 | **MEDIUM** (see Onboarding section) |
| **Loan amortization view** | `account.type = loan` exists; amortization (principal vs interest, payoff date) is what makes loan accounts useful. | Phase 2 extension or later | **LOW-MEDIUM** |
| **Reconciliation workflow** (Actual/YNAB style: "mark all cleared up to balance X") | Power-user feature; manual users want it; Plaid users less so. | Post-v1.0 | **LOW** |

### Note on phase ordering

The roadmap ships v1.0 after Phase 8. Of the gaps above:
- **HIGH priority gaps before v1.0 ship:** budget view, net worth history, reports, password reset, 2FA, data export.
- That's a meaningful addition to phases 1-8. Consider whether v1.0 should slip a few weeks or whether some gaps move to a "v1.1 fast follow."

---

## Onboarding Considerations

Onboarding is **the single most-cited weakness of self-hosted finance apps** in the wild. The new user has just spent 30+ minutes wrestling Docker, env files, and a Plaid account — they are *not* ready for "you're in, good luck."

### Expected first-run experience for a new user

1. **Register → confirm household name** (auto-created but ask for a name)
2. **Wizard step 1: Add your first account manually** (forced — without an account, nothing works)
   - Pre-populated with common types (checking, primary credit card)
   - "We'll connect to your bank later — for now just give it a name and balance"
3. **Wizard step 2: Choose how you'll get transactions in**
   - "Connect a bank automatically (Plaid)" — requires Plaid keys
   - "Upload a CSV from your bank" — most common path for self-hosters first
   - "I'll enter manually" — escape hatch
4. **Wizard step 3: Confirm starter categories**
   - Show the seeded category list (Phase 3 seeds these)
   - Allow rename/delete; offer "use defaults"
5. **Wizard step 4 (optional): Add recurring income/bills**
   - "Add your paycheck and rent now — your forecast needs these"
   - Skippable but with clear "you'll get a flat forecast without this" warning
6. **Dashboard with a clear "what to do next" card** based on what they completed
   - "You have 0 transactions — import or add one"
   - "Your forecast is empty — add recurring income"
   - "Looking good — try the forecast view"

### Data import paths in priority order

1. **CSV import** (Phase 4) — the universal path; most self-hosters start here. Even Plaid users want to backfill 1-3 years from CSV before switching to sync.
2. **Plaid Link / SimpleFIN** (Phases 9, 11) — for ongoing sync once history is in.
3. **Manual entry** (Phase 3) — always available; primary path for cash, Venmo, etc.
4. **Migration from another app** — *not on the roadmap*; consider a "Import from Monarch / YNAB / Lunch Money CSV" presets in Phase 4 mapping wizard. Low effort, high migration friction reduction.

### Onboarding-specific gotchas

- **Don't make them link a bank to see the dashboard.** Plaid keys are a non-trivial step; the app should be useful before that.
- **Default categories must be opinionated.** A blank category list = decision paralysis = abandoned.
- **Show the forecast on the dashboard from day 1, even if it's mostly empty.** The point of the product is the forecast; bury it and users won't find it.
- **Mark "data quality" prominently.** New users will be confused that the forecast is bad — make it visible that "we need 30 days of data to be confident."

---

## Feature Dependency Graph (high level)

```
Auth (P1)
  └─> Household (P1)
        └─> Accounts (P2) ──> Net Worth (P2)
              └─> Categories (P3) ──> Manual Transactions (P3)
                    ├─> CSV Import (P4)
                    ├─> Rules Engine (P5) ──┐
                    └─> Recurring Tx (P6)   │
                          └─> Forecast (P7) <─┘
                                └─> Bill Reminders (P8) ──🚢 v1.0
                                      └─> Plaid (P9)
                                            └─> Price Tracking (P10) <─── Receipts (P12)
                                            └─> SimpleFIN (P11)
                                            └─> Multi-User UI (P13)
                                            └─> Investments (P14)
```

Roadmap ordering is **correct on dependencies**. The forecast genuinely is the convergence point of P2-P6. The risk is that several gaps above (budget, reports, net worth history) should sit inside or alongside P2-P7, not after.

---

## Sources

- Project context: `.planning/PROJECT.md`, `ROADMAP.md`
- Competitive feature knowledge: synthesized from Claude's training data (cutoff Jan 2026)
- **Not consulted (access denied):** monarchmoney.com, ynab.com, copilot.money, lunchmoney.app, actualbudget.org, firefly-iii.org, Reddit r/personalfinance / r/selfhosted, app GitHub repos

### Verification next steps when network access returns

Priority pages to fetch and re-verify:
1. Monarch's current "Cash Flow" / "Plans" page — confirm forecast depth claim
2. Copilot's current feature list — confirm web app + multi-user status
3. Actual Budget GitHub README and recent releases — confirm forecast/multi-user state
4. Firefly III docs and recent issues — confirm UX complaint pattern
5. r/selfhosted threads on "Firefly III vs Actual Budget" from last 6 months
6. Plaid + SimpleFIN current pricing and trial limits (affects BYO-key onboarding feasibility)
