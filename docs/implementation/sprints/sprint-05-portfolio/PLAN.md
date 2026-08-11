# Sprint 05 — Detailed Plan: Portfolio + price refresh

| | |
|--|--|
| **ID** | S05 |
| **Depends on** | S01, S03, S04 |
| **Unblocks** | S06 conversion UX, S10 snapshot, S11 UI |
| **PRD** | M5, M6, FR-P1–P10 |

---

## 1. Objective

Assemble holdings + prices into portfolio DTO using **domain math**. Support manual **price refresh**. May **read** stored FX from repo; must **never** call ExchangeRate HTTP client.

---

## 2. Critical constraints

| Rule | How to prove |
|------|----------------|
| No ExchangeRateClient on GET/refresh | Unit spy / dependency not injected |
| Warm cache → no market call on GET | Call-count assertion |
| Auth required | 401 test |
| Math only from S01 domain | No duplicate formulas in service |

---

## 3. File ownership

| Path | Action |
|------|--------|
| `app/services/portfolio_service.py` | Create |
| `app/api/portfolio.py` | Create |
| `tests/unit/services/test_portfolio_service.py` | Create |
| `tests/unit/api/test_portfolio.py` | Create |
| deps/main | Wire only |

**Reads ports:** HoldingsRepo, MarketService/PriceCache, ExchangeRateRepo.get only, UserProfile (preferred currency)

---

## 4. API contracts

### GET /api/portfolio
Optional query: `displayCurrency`, `assetType` filter  

Response sketch:
```json
{
  "lines": [],
  "totalsByCurrency": {
    "USD": {"marketValue": "0", "costBasis": "0", "pnl": "0", "pnlPercent": null}
  },
  "totalsDisplay": null,
  "fx": {"status": "missing", "asOf": null, "rates": {}},
  "asOf": null
}
```

### POST /api/portfolio/refresh
- Force market fetch for user’s holding symbols  
- Update PriceCache  
- Return same portfolio shape  
- **No** FX provider call  

---

## 5. Service algorithm

```
holdings = holdings_repo.list(user_id)
quotes = market_service.get_quotes(keys, force=force_refresh)
native = compute_native_portfolio(holdings, quotes)
fx = fx_repo.get_latest()  # optional
if fx and display_currency:
    return apply_fx(native, fx, display_currency)
return native with fx.status=missing
```

---

## 6. TDD sequence

1. One holding → correct totals (fakes)  
2. Mixed USD/VND native subtotals  
3. Refresh invokes market client  
4. GET warm cache → market not called  
5. ExchangeRateClient never called  
6. API 401 / 200 shape  

---

## 7. Exit criteria

- [ ] Portfolio tests green  
- [ ] DTO documented in handoff for S11  
- [ ] Explicit no-FX-HTTP test  

---

## 8. Agent prompt

```
Sprint 05 ONLY. PortfolioService + GET/POST portfolio.
Use domain math S01. Cache-first prices S04. FX repo get-only; never ExchangeRateClient.
TDD with spies. Fill handoff DTO.
```
