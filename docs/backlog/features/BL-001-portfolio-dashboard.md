# BL-001 — Portfolio (1 per user): holdings + PnL dashboard

| Field | Value |
|-------|--------|
| **ID** | `BL-001` |
| **Title** | Portfolio dashboard & holdings (1 portfolio per user) |
| **Priority** | `P0` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | PRD M4–M5, FR-H*, FR-P*; sprints 03–05 (backend baseline); Artryx FE gap |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |
| **Implement when** | After additional backlog features are clarified (stakeholder hold) |

---

## 1. Problem / user value

Investors need one place to track **VN stock + crypto** positions, manage holdings, and see **PnL / status / allocation** — without multi-portfolio complexity.

---

## 2. User story

As an **authenticated investor**, I want **one implicit portfolio with validated stock/crypto holdings and a PnL dashboard**, so that **I can add real positions and see value, cost, PnL, and allocation in my chosen display currency**.

---

## 3. Scope

### In scope

- **Full stack polish:** Artryx `/portfolio` UI + backend gaps (especially **server-side asset validity** on holdings write)
- **One portfolio per user**, created **implicitly** when the first holding is added (no Create Portfolio entity/API)
- Holdings **full CRUD** (add, edit qty/avgCost/note, delete)
- Assets: **VN-listed stocks** (HOSE/HNX/UPCOM via vnstock) + **crypto** resolvable via CoinGecko-backed search
- Dashboard: **totals, PnL, PnL%, allocation pie, holdings table**, asset-type filter, **Refresh**, empty state CTA
- Uses app-wide session **display currency** from **BL-003** (VND / USD / EUR; header switcher owned there — portfolio must not add a second switcher)
- Cost entry shown in session currency; **convert and store in native** on save (stock→VND, crypto→USD)
- Per-line **missingPrice / stale** badges
- Auth: **Cognito required** to view/manage `/portfolio`

### Out of scope

- Multiple / named / shared portfolios
- Watchlist (separate backlog item)
- Historical portfolio value / PnL time-series chart (not in this BL)
- Order execution / brokerage
- Real-time WebSocket prices
- Persisting display currency to user profile
- Daily email / CSV export (unless already available elsewhere; not part of this BL UI)

---

## 4. Behaviour

### Happy path

1. User signs in (Cognito).
2. Opens **Portfolio** from nav → `/portfolio`.
3. If no holdings: **empty state** with **Add holding** CTA.
4. Add holding: search valid asset → select → enter **qty** + **avg cost in session currency** → submit.
5. Backend validates asset exists; converts cost to **native currency**; stores holding.
6. Dashboard shows totals (in session `displayCurrency`), allocation pie, holdings table.
7. User can filter **All | Crypto | Stock**, **Refresh** prices, edit or delete rows.
8. Changing session currency re-fetches/re-renders totals via `displayCurrency` (no profile write).

### Edge cases / errors

| Case | Behaviour |
|------|-----------|
| Unauthenticated | Redirect or sign-in CTA; no portfolio data |
| Invalid / unknown symbol | Reject (FE + **BE**); do not create holding |
| Duplicate `(assetType, symbol)` | **409**; show clear error |
| qty ≤ 0 or bad avgCost | **400** |
| FX rate missing for session currency | Show best-effort: native `totalsByCurrency` and/or null unified totals + visible FX status; do not crash |
| Quote missing / stale | Row badge; line PnL may be null; totals exclude or flag per existing API rules |
| Empty search | No results; cannot submit free-text unknown symbol |

### UX notes

- **Route:** `/portfolio` + nav item (home `/` stays market dashboard)
- **Currency:** consume BL-003 session context (header control lives in BL-003)
- **Add/Edit:** modal or panel with asset search, qty, avg cost (session currency label), optional note
- **Loading / error:** skeleton or spinner on load; toast/inline error on failed mutate/refresh

---

## 5. Acceptance criteria

- [x] **AC1** Authenticated user can open `/portfolio`; unauthenticated user cannot access portfolio data.
- [x] **AC2** User with zero holdings sees empty state + Add holding CTA (no separate “create portfolio” step).
- [x] **AC3** User can **add** a VN stock only if it resolves via stock asset search (vnstock universe).
- [x] **AC4** User can **add** a crypto only if it resolves via crypto asset search (CoinGecko-backed).
- [x] **AC5** `POST`/`PUT` holdings **server-side** reject assets that do not resolve in the catalog/search (not FE-only).
- [x] **AC6** User can **edit** qty, avgCost (session→native conversion on save), and note; can **delete** a holding.
- [x] **AC7** Duplicate holding for same user+assetType+symbol returns conflict and UI shows error.
- [x] **AC8** Dashboard shows market value, cost basis, PnL, PnL% in the **session display currency** when FX allows.
- [x] **AC9** Allocation **pie** uses converted market values when display totals exist.
- [x] **AC10** Holdings **table** lists lines with key fields; supports filter **all | crypto | stock**.
- [x] **AC11** **Refresh** triggers `POST /api/portfolio/refresh` (or equivalent) and updates quotes/PnL.
- [x] **AC12** Portfolio money UI follows BL-003 session currency (VND/USD/EUR); no duplicate switcher on this page.
- [x] **AC13** Cost is entered in session currency; stored holding currency is **VND for stock**, **USD for crypto** after FX conversion at save.
- [x] **AC14** Rows with `missingPrice` or `stale` show a basic badge/indicator.
- [x] **AC15** Watchlist UI is **not** delivered in this BL.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | Dynamo holdings + price cache + stored FX (existing) |
| APIs | `GET/POST/PUT/DELETE /api/holdings`; `GET /api/portfolio`; `POST /api/portfolio/refresh`; asset **search**; **new/extended validation** on holdings write |
| Auth | Cognito Bearer required |
| Caching / freshness | Cache-first GET; manual Refresh forces fetch |
| Display currency | Query/header `displayCurrency` from session (VND/USD/EUR); not profile persist |
| Cost currency | UI = session; persist = native (stock VND, crypto USD) via stored FX at write time |
| Jobs | Not required for this BL’s charts (no history chart) |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `app/portfolio/page.tsx`, nav, holdings modal, pie + table, auth gate; currency via BL-003 context |
| Backend API | Holdings create/update validation hook; possibly shared asset-resolve helper; portfolio already supports `displayCurrency` |
| Domain / services | `HoldingsService` (+ market/search dependency); FX read for cost conversion on write |
| Adapters | vnstock catalog / CoinGecko search (existing market ports) |
| Infra / jobs | None new for BL-001 |
| Docs / tests | Unit tests for reject-invalid holding; FE verification on `/portfolio` |

---

## 8. Dependencies & risks

- **Depends on:** Cognito wired in Artryx FE; asset search APIs; stored FX rates (admin refresh) for VND/USD/EUR
- **Risks:** EUR (or other) rate missing → conversion/display degraded; cost conversion at write needs clear error if FX missing; FE auth may still be incomplete

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Delivery scope | resolved | Full stack polish (FE + BE validity) |
| 2 | Portfolio create | resolved | Implicit on first holding |
| 3 | Holdings ops | resolved | Full CRUD |
| 4 | Valid assets | resolved | Search-resolved; VN stocks + CoinGecko crypto; BE enforce |
| 5 | Dashboard visuals | resolved | Totals, PnL, pie, table (+ filter, refresh, empty CTA, badges) |
| 6 | Route | resolved | `/portfolio` + nav |
| 7 | Display currency | resolved | Session VND/USD/EUR via **BL-003** (this BL consumes) |
| 8 | Watchlist | resolved | Out of scope |
| 9 | Cost currency | resolved | Enter session → convert/store native |
| 10 | Auth | resolved | Cognito required |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Intake | 1 portfolio/user; holdings stock+crypto; valid only; charts + PnL |
| 2026-08-19 | Backend discovery | Holdings + portfolio APIs exist (S03–S05); no Artryx portfolio UI; holdings do **not** yet catalog-validate symbols |
| 2026-08-19 | Slice | Full stack polish |
| 2026-08-19 | Create model | Implicit |
| 2026-08-19 | CRUD | Full |
| 2026-08-19 | Validity | Asset search + BE enforce |
| 2026-08-19 | Visuals | Totals + PnL + pie + table (no history chart) |
| 2026-08-19 | Nav | `/portfolio` |
| 2026-08-19 | Display currency | Session switcher like language; VND/USD/EUR; session only |
| 2026-08-19 | Watchlist | Separate BL |
| 2026-08-19 | BE polish | Enforce asset validity on POST/PUT |
| 2026-08-19 | Auth | Cognito required |
| 2026-08-19 | UI extras | Refresh, filter, empty CTA; + missing/stale badges |
| 2026-08-19 | Stocks | VN-listed only |
| 2026-08-19 | Crypto | CoinGecko search |
| 2026-08-19 | Cost currency | UI session → store native via FX |
| 2026-08-19 | Ready | Spec finalized; **implement after more features are added** |

---

## 11. Implementation notes (Eng fills after start)

- Approach: Artryx `/portfolio` dashboard (summary, SVG pie, table, filter, refresh, modal CRUD) + BE `HoldingsService` catalog resolve on POST/PUT and session→native cost FX via stored rates. Auth gate uses `artryx.accessToken` localStorage + paste CTA when Cognito Hosted UI is incomplete.
- PR / branch: `execute-plan/6cc30007-pr-3-bl-001-portfolio-dashboard`
- Verification: `pytest backend/tests/unit/api/test_holdings.py`; `npm test` in `frontend/` (NavItems + portfolio helpers).
### Current implementation note (Sprint 05)

Portfolio auth uses canonical `openportfo.accessToken`; older
`artryx.*` references below are retained as historical context and migration
compatibility notes.
