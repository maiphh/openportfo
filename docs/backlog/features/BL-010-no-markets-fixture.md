# BL-010 — Markets APIs: no catalog fixture fallback

| Field | Value |
|-------|--------|
| **ID** | `BL-010` |
| **Title** | HTTP market clients must not serve catalog fixtures on `/api/markets/*` |
| **Priority** | `P1` |
| **Status** | `done` |
| **Owner (BA)** | BA |
| **Owner (Eng)** | Eng |
| **Requested by** | Stakeholder |
| **Related PRD / sprint** | BL-004 (FE already dropped mock); adapter fallback still demo-like |
| **Created** | 2026-08-19 |
| **Ready date** | 2026-08-19 |
| **Done date** | 2026-08-19 |

---

## 1. Problem / user value

BL-004 stopped the **frontend** from seeding mock boards. The **backend** still falls back to catalog fixtures when vnstock/CoinGecko fail:

- `HttpVnstockClient(use_fixture_fallback=True)` default
- `HttpCoinGeckoClient` same
- `deps.get_*_market_client()` on import/construct failure swaps in `Fixture*Client`
- Heatmap/quotes then look “live” but are demo tickers

`/api/markets/*` should **502** (existing handlers) rather than return fixtures when `MARKET_CLIENT_MODE=http`.

---

## 2. User story

As a **visitor**, I want **heatmap/quotes to fail honestly when the provider is down**, so that **I never mistake catalog fixtures for the market**.

---

## 3. Scope

### In scope

- When `MARKET_CLIENT_MODE=http`:
  - Construct HTTP clients with **`use_fixture_fallback=False`**
  - Do **not** replace HTTP client with `Fixture*Client` on construct exception — raise / leave unset so API 502
  - `get_heatmap` / `get_quotes` (stock + crypto) must **not** return fixture sectors/groups
- Keep fixture mode (`MARKET_CLIENT_MODE=fixture`) for unit tests / local without keys
- FE already shows error + Retry (BL-004 / BL-011) — no FE mock reintroduction
- Unit tests: http client with fallback off raises/empty so API 502; fixture mode unchanged

### Out of scope

- Removing fixture classes (tests still need them)
- Dynamo market cache
- Changing FE empty/error UI beyond what BL-011 already does

---

## 4. Behaviour

### Happy path

1. Live vnstock/CoinGecko succeeds → same JSON as today, `source: vnstock|coingecko`.
2. Provider failure in http mode → **502** `Heatmap/Quotes unavailable`, FE Retry.

### Edge cases

| Case | Behaviour |
|------|-----------|
| `MARKET_CLIENT_MODE=fixture` | Tests/local still get fixtures |
| Insights heatmap missing, quote-board works | Still live (not fixture) |
| Both live paths fail | 502, not catalog |

---

## 5. Acceptance criteria

- [x] **AC1** `MARKET_CLIENT_MODE=http` heatmap/quotes never return catalog fixture boards.
- [x] **AC2** Provider failure surfaces as HTTP 502 (or empty that FE already treats as error).
- [x] **AC3** `MARKET_CLIENT_MODE=fixture` unit tests still pass.
- [x] **AC4** Crypto and stock markets both covered.
- [x] **AC5** New/updated adapter + API tests prove no fallback in http mode.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Config | `MARKET_CLIENT_MODE=http` ⇒ `use_fixture_fallback=False` |
| APIs | `/api/markets/heatmap\|quotes` + crypto variants |
| Auth | Public |

---

## 7. Affected surfaces

| Layer | Paths |
|-------|--------|
| Backend | `deps.py`, `vnstock/http_client.py`, `coingecko/http_client.py`, `api/markets.py` (if needed), unit tests |
| Frontend | None required (error UI exists) |

---

## 8. Dependencies & risks

- Local http mode without vnstock will show markets errors — intended
- Coordinate with BL-011 cache: do not persist fixture payloads if any appear during rollout

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Scope | resolved | Markets heatmap/quotes in http mode |
| 2 | Tests/fixture mode | resolved | Keep |

*No open questions blocking DoR.*

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-19 | Hardens BL-004 | Disable HTTP fixture fallback for market boards |

---

## 11. Implementation notes

- Approach:
  - `MARKET_CLIENT_MODE=http` constructs `HttpVnstockClient` / `HttpCoinGeckoClient` with `use_fixture_fallback=False`. Construct exceptions are not swapped to `Fixture*Client` (client stays unset; next call retries).
  - HTTP client default is now no catalog fallback. `get_heatmap` / `get_quotes` raise `MarketDataError` when live paths fail so existing `/api/markets/*` handlers return **502**, not fixture boards.
  - `MARKET_CLIENT_MODE=fixture` still wires `Fixture*Client` for unit tests / local without keys.
  - BL-011 shared `_quote_board` cache is unchanged (live vnstock batch still shared by heatmap+quotes; no fixture payloads persisted).
- PR / branch: `feat/BL-010-no-markets-fixture`
- Verification:
  - From `backend/`: `.venv\Scripts\python.exe -m pytest tests/unit/adapters/test_vnstock_http.py tests/unit/adapters/test_coingecko_http.py tests/unit/api/test_markets.py tests/unit/api/test_markets_heatmap.py tests/unit/api/test_markets_quotes.py tests/unit/api/test_markets_crypto.py tests/unit/test_deps_market_clients.py tests/unit/services/test_market_service.py -q` (79 passed)
  - Full `tests/unit` (excluding jobs): 323 passed

