# Handoff — Sprint 01 — Domain

## Status
- [x] Not started
- [x] In progress
- [x] Done

## Ports / modules added
- `backend/app/domain/models.py` — Holding, PriceQuote, FxRates, CurrencyTotals, PortfolioLine, PortfolioSummary
- `backend/app/domain/portfolio_math.py` — `native_line` / `line_native`, `compute_native_portfolio`, `pnl_percent`
- `backend/app/domain/fx_math.py` — `get_rate`, `rate_key`, `apply_fx`
- `backend/app/domain/__init__.py` — re-exports public API
- `backend/tests/unit/domain/test_portfolio_math.py` — 15 unit tests

## API routes added
- None (pure domain; no HTTP)

## Env vars added
- None

## Shared files touched (`main.py`, `deps.py`, …)
- None

## Rate key scheme (locked)
- Flat string keys: `"{SRC}_{DST}"` uppercased, e.g. `USD_VND`, `VND_USD`
- Semantics: `amount_dst = amount_src * rates["SRC_DST"]`
- `get_rate(fx, src, dst)`:
  1. `src == dst` → `Decimal("1")`
  2. direct key lookup
  3. inverse of opposite key if present (`1 / rates["DST_SRC"]`)
  4. else `None`

## Missing quote behavior (locked)
- Line is **kept** in `summary.lines` with `missing_price=True`
- `price`, `market_value`, `cost_basis`, `pnl`, `pnl_percent` are `None`
- Line is **excluded** from `totals_by_currency`

## Missing FX behavior (locked)
- `FxRates.status == "missing"` or empty `rates` → `apply_fx` sets `fx_status="missing"`, leaves display totals/allocations `None`, keeps native lines/totals
- If any priced line cannot resolve a rate to display currency → same: `fx_status="missing"`, no display conversion

## pnl% behavior (locked)
- `pnl_percent(pnl, cost)` returns `None` when `cost == 0` (not 0)

## Example fixture numbers
| Holding | qty | avg_cost | price | currency | market_value | cost_basis | pnl |
|---------|-----|----------|-------|----------|--------------|------------|-----|
| BTC | 1 | 30000 | 40000 | USD | 40000 | 30000 | 10000 |
| VNM | 100 | 70000 | 80000 | VND | 8_000_000 | 7_000_000 | 1_000_000 |

FX: `USD_VND = 25000`, display = VND  
- BTC display MV = 40000 × 25000 = **1_000_000_000**  
- VNM display MV = **8_000_000**  
- Total display MV = **1_008_000_000**  
- Total display cost = 30000×25000 + 7_000_000 = **757_000_000**  
- Total display pnl = **251_000_000**  
- Allocations sum to ≈ 1.0 within display currency

Single USD smoke: qty=2, price=20000, avg_cost=10000 → MV=40000, cost=20000, pnl=20000, pnl%=1

## Tests
- Command (Windows):
  ```
  cd D:\rmit\cloud\a3\backend
  .\.venv\Scripts\python.exe -m pytest -q tests/unit/domain
  .\.venv\Scripts\python.exe -m pytest -q
  ```
- Result: **15 passed** (domain) / **18 passed** (full suite incl. Sprint 00)
- Domain has **no** fastapi / boto3 / httpx imports

## Known gaps / deferred
- No persistence models for Dynamo shape (Sprint 03+)
- No service wiring (Sprint 05 portfolio)
- `stale_ok` status accepted on `FxRates` but not special-cased beyond pass-through when rates exist
- Inverse rate uses full Decimal division (precision left to caller/services if rounding needed for UI)

## Next sprint needs
- Sprint 02 (Auth): can ignore domain
- Sprint 05 (Portfolio): call `compute_native_portfolio` + `apply_fx` with rates from `ExchangeRateRepo` port; map API DTOs ↔ domain models
- Sprint 06 (FX admin): store rates with flat `USD_VND` / `VND_USD` keys matching this scheme
