# BL-004 — Markets live data (no mock) + loading skeletons

| Field | Value |
|-------|--------|
| **ID** | `BL-004` |
| **Title** | `/markets` live heatmap & quotes — cache APIs, skeletons, remove mock fallback |
| **Priority** | `P0` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | Markets overview APIs; Artryx `MarketDashboard`; BL-002 AssetLink; BL-003 currency for money amounts |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |
| **Implement when** | After additional backlog features are clarified (stakeholder hold) |

---

## 1. Problem / user value

`/markets` currently **seeds and falls back to US/demo mock** heatmap & quotes while calling live APIs. Users should see **real market boards** (from public `/api/markets/*`, which use adapter **in-memory cache** of heatmap/quotes — **not** the asset **catalog** list), with **skeletons while loading** and **errors + retry** — never fake tickers.

---

## 2. User story

As a **visitor/investor**, I want **stock and crypto market pages to load live boards with a clear loading state**, so that **I never mistake demo data for the market, and I can retry if the API fails**.

---

## 3. Scope

### In scope

- **`/markets/stock`** and **`/markets/crypto`** (and any route that renders the same heatmap/quotes widgets — today **`/` redirects** to `/markets/stock`)
- Data from existing public APIs only:
  - Stock: `GET /api/markets/heatmap`, `GET /api/markets/quotes`
  - Crypto: `GET /api/markets/crypto/heatmap`, `GET /api/markets/crypto/quotes`
- FE must **not** use asset **catalog** / `SEARCH_UNIVERSE` / list-assets for these boards
- **Remove mock fallback** for heatmap & quotes (no initial mock seed, no catch → mock)
- **Skeleton** UI while each section loads
- **Error state + Retry** per section (or shared) when fetch fails / empty
- Delete **unused market mock fixtures** from `lib/mock-data.ts` (e.g. `HEATMAP_SECTORS`, `QUOTE_GROUPS`, crypto equivalents) once unreferenced
- Move shared **types** used by `lib/api.ts` out of mock-data if needed (e.g. `types/markets.ts`)

### Out of scope

- **TopStories** — leave mock for a later news BL
- Deleting all of `mock-data.ts` (NAV, MOCK_USER, search universe, logos helpers may remain until their BLs)
- Forcing BE to stop **catalog fixture fallback** inside vnstock adapter when live heatmap/quotes fail (residual server behaviour; FE still must not ship FE mock)
- Admin cache warm jobs / new Dynamo-S3 market cache (use existing `/api/markets/*` as-is)
- Auth gate for markets (APIs are public today — keep public unless product changes)

---

## 4. Behaviour

### Happy path

1. User opens `/markets` → redirect `/markets/stock` (existing) or `/markets/crypto`.
2. Heatmap and Quotes sections show **skeletons** immediately (empty data, not mock).
3. FE fetches `/api/markets/*` (stock or crypto).
4. On success, render live treemap / quote table; source label shows provider (e.g. HOSE · vnstock / CoinGecko).
5. Symbols/names should remain compatible with **BL-002 `AssetLink`** when that ships (same batch OK).

### Edge cases / errors

| Case | Behaviour |
|------|-----------|
| Loading | Skeleton placeholders; **no** mock tickers |
| HTTP/network error | Error message + **Retry**; sections empty of demo data |
| Empty `sectors` / `groups` | Treat as failure or dedicated empty state (no mock fill) |
| Abort on market tab switch | Ignore aborted request; show skeleton for new market |
| BE returns catalog fixtures behind `/api/markets/*` | Accept as server payload (still “live API”); do not add a second FE mock layer |

### UX notes

- Prefer **per-widget** skeleton (heatmap + quotes independent) so one can succeed while the other loads
- Retry re-runs that widget’s fetch
- Remove UI strings like “Demo data”

---

## 5. Acceptance criteria

- [ ] **AC1** `/markets/stock` heatmap & quotes load from stock `/api/markets/*` only.
- [ ] **AC2** `/markets/crypto` heatmap & quotes load from crypto `/api/markets/*` only.
- [ ] **AC3** While loading, user sees **skeleton** UI — not `HEATMAP_*` / `QUOTE_*` mock rows.
- [ ] **AC4** On fetch failure or empty payload, user sees **error + Retry**, not demo/mock data.
- [ ] **AC5** Successful load never falls back to mock after an error recovery path without an explicit new request.
- [ ] **AC6** Market mock fixtures unused by heatmap/quotes are **removed** from the codebase; types relocated if required.
- [ ] **AC7** Markets boards do not read asset **catalog** / search universe for their primary data.
- [ ] **AC8** TopStories may remain mock (explicitly deferred).
- [ ] **AC9** Home `/` continues to land on markets experience that obeys AC1–AC5 (via redirect or shared components).

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source | Public `/api/markets/heatmap|quotes` (+ crypto variants) |
| Cache | Adapter TTL cache on heatmap/quotes OK; not FE mock; not catalog list |
| Auth | Public (current API) |
| Catalog | Not used by FE markets boards |
| Currency | Money formatting may later use BL-003; % tiles stay % |

### Current gap (to fix)

`StockHeatmap` / `MarketQuotes` initialize and error-fallback to `mockSectors` / `mockGroups`. Replace with `[]` + `loading`/`error` states and skeletons.

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `StockHeatmap.tsx`, `MarketQuotes.tsx`, skeletons, `lib/api.ts` types, `lib/mock-data.ts` cleanup, tests |
| Backend | No change required for MVP of this BL |
| Routes | `/markets`, `/markets/stock`, `/markets/crypto`, `/` redirect |

---

## 8. Dependencies & risks

- **Depends on:** Backend reachable via `NEXT_PUBLIC_API_URL`; CORS if cross-origin
- **Risks:** Cold/slow vnstock → long skeleton time; BE catalog fixture fallback may still look “demo-like” if live fails server-side (out of scope unless follow-up BL)

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Surfaces | resolved | Stock + crypto market dashboards |
| 2 | Data source | resolved | Existing `/api/markets/*` (cached boards, not catalog) |
| 3 | Loading/error | resolved | Skeleton + error/retry; no mock |
| 4 | Remove mock extent | resolved | Heatmap/quotes fixtures + fallbacks; not entire mock-data.ts |
| 5 | TopStories | resolved | Out of scope |
| 6 | Home `/` | resolved | Same rules via shared widgets / redirect |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Intake | Markets: load cache, no catalog; loader+skeleton; remove mock entirely |
| 2026-08-19 | Discovery | FE already fetches live APIs but seeds/falls back to mock; `/` redirects to stock markets; BE has TTL cache + optional catalog fixture fallback |
| 2026-08-19 | Scope | Both stock+crypto; public markets APIs; skeleton+retry; strip FE market mocks; TopStories deferred |
| 2026-08-19 | Ready | Spec finalized; batch implement later |

---

## 11. Implementation notes (Eng fills after start)

- Approach:
- PR / branch:
- Verification:
