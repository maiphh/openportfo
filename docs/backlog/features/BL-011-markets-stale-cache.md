# BL-011 — Markets stock load: shared BE cache + FE stale-while-revalidate

| Field | Value |
|-------|--------|
| **ID** | `BL-011` |
| **Title** | `/markets/stock` faster repeat loads + persist boards across refresh |
| **Priority** | `P0` |
| **Status** | `ready` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | — |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | BL-004 markets live; sprint-04 market cache; vnstock adapter |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | |

---

## Review findings (why stock is slow / always reloads)

Stock `/markets/stock` is slower than crypto, and a browser refresh always shows skeletons again, for three independent reasons:

1. **Cold vnstock path is many sequential calls.** Crypto heatmap/quotes share one CoinGecko `GET /coins/markets` (plus a 120s in-process cache). Stock heatmap/quotes, when Insights heatmap is missing, each independently:
   - fetch industry map (`Listing().symbols_by_industries`)
   - fetch exchange listing
   - fetch catalog names
   - batch-quote ~`limit*2` tickers in chunks of 40 (`Market.quote`)
   Heatmap and quotes **do not share** that quote-board work, so a first paint can run the expensive path **twice**.

2. **Backend cache exists but is process-RAM only.** `HttpVnstockClient` keeps `_heatmap_cache` / `_quotes_cache` for **120 seconds**. Crypto `_markets_cache` is also 120s. Neither is written to Dynamo, neither is sent as HTTP `Cache-Control`, and a new uvicorn/EB worker starts empty. After TTL expiry or process restart, stock pays the full vnstock cost again.

3. **Frontend never reuses the last board.** `StockHeatmap` and `MarketQuotes` `useEffect` on mount call `fetch(..., cache: "no-store")`, clear local state to `[]`, and show skeletons. A refresh / tab revisit always looks like a cold load even when the backend would have answered from TTL in milliseconds.

**Does it use cache?** Yes — **adapter in-memory TTL (120s)** on the API process. No browser cache, no sessionStorage, no shared stock quote-board cache between heatmap and quotes.

---

## 1. Problem / user value

Investors opening `/markets/stock` wait through a long skeleton on every visit. Repeat views (refresh, stock↔crypto tab, back navigation) should show the last live board immediately and refresh in the background.

---

## 2. User story

As a **visitor**, I want **the last stock heatmap and quotes to appear instantly on refresh**, so that **I am not blocked by vnstock while the board revalidates**.

---

## 3. Scope

### In scope

- **FE stale-while-revalidate** for heatmap + quotes on **stock and crypto** (same components):
  - Persist last successful payload in `sessionStorage` (survives refresh in the tab; clears when the tab is closed)
  - On mount: if a cached payload exists, render it immediately (label as cached / updating)
  - Fetch live in the background; on success replace + write cache
  - On fetch failure: keep cached board + non-blocking error/retry; if no cache, keep existing error + Retry
- **BE stock path:** share industry map / listing / batch-quote work between `get_heatmap` and `get_quotes` within the same TTL window (one quote-board fetch should feed both)
- Optional HTTP `Cache-Control: public, max-age=60, stale-while-revalidate=120` on `/api/markets/*` (harmless; FE still owns SWR)
- Source label: distinguish **live** vs **cached (updating…)** vs **cached (refresh failed)**
- Unit tests for FE cache helper and BE shared cache / TTL

### Out of scope

- Dynamo / S3 persistence of market boards (still process TTL)
- Changing heatmap/quotes JSON shape
- Removing vnstock fixture fallback
- WebSocket / live tick
- Changing default `limit` (heatmap 100, quotes 80)

---

## 4. Behaviour

### Happy path

1. First visit (empty sessionStorage): skeleton → live fetch → render → write sessionStorage.
2. Refresh / revisit within the tab: last board paints immediately; background fetch updates tiles when ready.
3. Second widget (quotes) after heatmap already warmed the BE quote-board cache: quotes should not re-run the full vnstock batch.

### Edge cases / errors

| Case | Behaviour |
|------|-----------|
| No cache, fetch fails | Existing error + Retry |
| Cache present, fetch fails | Keep cached board; banner/label + Retry |
| Cache present, empty live payload | Treat as failure; keep cache |
| Tab switch stock↔crypto | Use per-market cache keys; abort in-flight |
| Corrupt sessionStorage JSON | Ignore cache; load as first visit |
| sessionStorage quota / private mode | Skip persist; still fetch live |

### UX notes

- Screens: `/markets/stock`, `/markets/crypto` (shared `StockHeatmap` / `MarketQuotes`)
- Do **not** flash skeleton over a valid cached board
- Keep BL-004 rule: never seed mock tickers

---

## 5. Acceptance criteria

- [ ] **AC1** First visit with empty session cache still shows skeleton, then live data (no mock).
- [ ] **AC2** Refresh / remount with a valid session cache paints heatmap and quotes **without** a full-page skeleton.
- [ ] **AC3** After a successful fetch, sessionStorage holds the payload; a later remount reads it.
- [ ] **AC4** Failed revalidation keeps the cached board and offers Retry; no mock fallback.
- [ ] **AC5** Stock heatmap and quotes share BE listing/quote-board work (or a shared TTL cache) so the second call in the same TTL window does not re-batch vnstock.
- [ ] **AC6** Crypto still uses CoinGecko markets TTL; FE SWR applies to crypto too.
- [ ] **AC7** Cache keys are per market (`stock` / `crypto`) and per widget (`heatmap` / `quotes`).
- [ ] **AC8** Unit tests cover: read/write/ignore-corrupt cache helper; BE shared/TTL path (existing vnstock http tests extended).

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | Existing `/api/markets/heatmap\|quotes` (+ crypto) |
| FE cache | `sessionStorage` keys e.g. `artryx.markets.{heatmap\|quotes}.{stock\|crypto}` |
| BE cache | Existing 120s TTL; **share** stock quote-board internals |
| Auth | Public |
| Jobs | None |

### Suggested key shape

```text
artryx.markets.heatmap.stock
artryx.markets.quotes.stock
artryx.markets.heatmap.crypto
artryx.markets.quotes.crypto
```

Value: `{ savedAt: ISO, payload: HeatmapResponse | QuotesResponse }`.

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `StockHeatmap.tsx`, `MarketQuotes.tsx`, new `lib/markets-cache.ts` (+ tests), `lib/api.ts` only if headers change |
| Backend | `adapters/vnstock/http_client.py`, `api/markets.py` (optional Cache-Control), unit tests |
| Routes | `/markets/stock`, `/markets/crypto` |

---

## 8. Dependencies & risks

- Depends on: BL-004 live-only boards
- Risk: showing a stale board after market close is acceptable if labelled
- Risk: sessionStorage size — boards are modest JSON; if write fails, degrade silently

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | FE persist medium | resolved | sessionStorage (tab-scoped) |
| 2 | Persist Dynamo? | resolved | Out of scope |
| 3 | Crypto too? | resolved | Yes, same SWR helper |
| 4 | Share stock quote-board? | resolved | Yes |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Why stock slower + always reloads | vnstock multi-call + dual widgets; FE `cache: no-store` + no session persist |
| 2026-08-19 | Fix | FE SWR + shared BE quote-board TTL |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach:
  - FE: `lib/markets-cache.ts` persists last heatmap/quotes JSON in `sessionStorage` (`artryx.markets.{widget}.{market}`). `StockHeatmap` / `MarketQuotes` hydrate after mount via `useLayoutEffect` (no skeleton flash, no hydration mismatch), revalidate in the background, write on success, and keep the cached board + Retry when live/empty fetch fails.
  - BE: `HttpVnstockClient` shares a 120s `_quote_board` snapshot (industry map, exchange listing, batch `Market.quote`) so heatmap and quotes do not re-batch vnstock in the same TTL window. `/api/markets/*` sets `Cache-Control: public, max-age=60, stale-while-revalidate=120` (FE still uses `cache: "no-store"` + session SWR).
- PR / branch: `feat/BL-011-markets-stale-cache`
- Verification:
  - `cd frontend; npx vitest run lib/markets-cache.test.ts components/dashboard/StockHeatmap.test.tsx components/dashboard/MarketQuotes.test.tsx`
  - `cd backend; python -m pytest tests/unit/adapters/test_vnstock_http.py tests/unit/api/test_markets.py tests/unit/api/test_markets_heatmap.py tests/unit/api/test_markets_quotes.py tests/unit/api/test_markets_crypto.py -q`
