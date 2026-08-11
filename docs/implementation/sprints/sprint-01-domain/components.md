# Sprint 01 — Components

## Models (Pydantic or dataclass)
- [x] `Holding`: user_id, asset_type, symbol, qty, avg_cost, currency, asset_id?, note?
- [x] `PriceQuote`: asset_type, symbol, price, currency, as_of
- [x] `PortfolioLine`: holding fields + market_value, cost_basis, pnl, allocation?
- [x] `FxRates`: base, rates dict (e.g. USD_VND, VND_USD), as_of, status: missing|stale_ok|fresh
- [x] `PortfolioSummary`: lines, totals_by_currency, totals_display?, fx meta, pnl fields
- [x] `CurrencyTotals`: currency, market_value, cost_basis, pnl

## Functions
- [x] `line_native` / `native_line(holding, quote) -> market_value, cost_basis, pnl`
- [x] `compute_native_portfolio(holdings, quotes) -> per-currency totals + lines`
- [x] `apply_fx(summary_native, fx_rates, display_currency) -> converted totals/allocations`
  - rate(C→D)=1 if C==D
  - missing rate → skip conversion / status missing
- [x] pnl% : **None** if cost_basis==0 (documented in code + test)
- [x] `get_rate(fx, src, dst)` with inverse fallback

## Rules (PRD)
- Crypto typically USD, stocks VND
- No HTTP; rates are inputs only
