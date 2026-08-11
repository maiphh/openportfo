# Handoff — Sprint 05 — Portfolio

## Status
- [x] Not started
- [x] In progress
- [x] Done

## Ports / modules added
- `backend/app/ports/fx.py` — `StoredRates`, `ExchangeRateRepo` (**`get_latest` only** for S05)
- `backend/tests/fakes/fx.py` — `InMemoryExchangeRateRepo` (`get_latest`, `seed`, call counter)
- `backend/app/services/portfolio_service.py` — `PortfolioService`, `PortfolioView`, mappers
- `backend/app/api/portfolio.py` — `GET /api/portfolio`, `POST /api/portfolio/refresh`, DTO serializer
- `backend/tests/unit/services/test_portfolio_service.py`
- `backend/tests/unit/api/test_portfolio.py`

## Portfolio DTO (for S11)

CamelCase JSON; all money fields are **Decimal serialized as strings**.

```json
{
  "lines": [
    {
      "userId": "alice",
      "assetType": "crypto",
      "symbol": "BTC",
      "assetId": "bitcoin",
      "qty": "1",
      "avgCost": "30000",
      "currency": "USD",
      "note": null,
      "price": "40000",
      "marketValue": "40000",
      "costBasis": "30000",
      "pnl": "10000",
      "pnlPercent": "0.333...",
      "missingPrice": false,
      "displayCurrency": "VND",
      "marketValueDisplay": "1000000000",
      "costBasisDisplay": "750000000",
      "pnlDisplay": "250000000",
      "allocation": "0.99..."
    }
  ],
  "totalsByCurrency": {
    "USD": {
      "marketValue": "40000",
      "costBasis": "30000",
      "pnl": "10000",
      "pnlPercent": "0.333..."
    }
  },
  "totalsDisplay": {
    "currency": "VND",
    "marketValue": "1000000000",
    "costBasis": "750000000",
    "pnl": "250000000",
    "pnlPercent": "..."
  },
  "fx": {
    "status": "fresh",
    "asOf": "2026-08-09T12:00:00+00:00",
    "rates": { "USD_VND": "25000" }
  },
  "asOf": "2026-08-09T12:00:00+00:00",
  "displayCurrency": "VND"
}
```

### Field notes
| Field | Meaning |
|-------|---------|
| `lines[]` | One per holding (after optional `assetType` filter). Missing quote → `missingPrice: true`, price/MV/cost/pnl null |
| `totalsByCurrency` | Native subtotals by holding currency; **excludes** missing-price lines |
| `totalsDisplay` | Converted totals when stored FX + display currency resolve; else `null` |
| `fx.status` | `missing` \| `stale_ok` \| `fresh` (from store / domain) |
| `fx.rates` | Flat keys `USD_VND`, `VND_USD` (S01 scheme); may be `{}` when never stored |
| `asOf` | Max quote `as_of` among resolved prices; `null` if no quotes |
| `displayCurrency` | Query `displayCurrency` or user `preferredCurrency` when conversion attempted |

### Query params
| Param | Endpoints | Notes |
|-------|-----------|--------|
| `displayCurrency` | GET, POST refresh | Override profile preferred currency for FX conversion |
| `assetType` | GET, POST refresh | `crypto` \| `stock`; invalid → **400** |

## Explicit no-FX-HTTP proof
1. **No client in deps:** `deps.py` has `get_exchange_rate_repo` only — **no** `get_exchange_rate_client` / `ExchangeRateClient` (asserted in `test_deps_has_no_exchange_rate_client`).
2. **Service surface:** `PortfolioService.__init__(holdings_repo, market_service, fx_repo=None)` — no FX HTTP client parameter (`test_portfolio_service_has_no_fx_http_client`).
3. **GET + refresh:** both call `fx_repo.get_latest()` only; portfolio API/service source contains no `ExchangeRateClient` (`test_get_and_refresh_never_need_fx_http_client`).
4. **S06 owns** provider client + `POST /admin/fx/refresh`.

## Algorithm (locked)
```
holdings = holdings_repo.list(user_id)  # optional assetType filter
quotes = market_service.get_quotes(keys, force=force_refresh)
native = compute_native_portfolio(domain_holdings, quotes)  # S01 only
stored = fx_repo.get_latest()  # optional
display = displayCurrency or preferredCurrency
if stored and display:
    return apply_fx(native, stored→FxRates, display)  # S01 only
else:
    native with fx.status=missing
```

Math is **only** `compute_native_portfolio` + `apply_fx` + `pnl_percent` (serializer); no duplicate formulas in the service.

## API routes added
| Method | Path | Auth | Behaviour |
|--------|------|------|-----------|
| GET | `/api/portfolio` | Bearer | Cache-first quotes; stored FX read; same DTO |
| POST | `/api/portfolio/refresh` | Bearer | `force=True` market fetch for user symbols; **no** FX HTTP |

## Env vars added
- None (reuses `PRICE_CACHE_TTL_SECONDS`, auth settings)

## Shared files touched (`main.py`, `deps.py`, …)
- `backend/app/core/deps.py` — **appended**: `get/set_exchange_rate_repo`, `get/set_portfolio_service` (no FX client)
- `backend/app/main.py` — `include_router(portfolio_router)`

## Auth for tests
```python
headers = {"Authorization": "Bearer fake:alice"}
# seed holdings via InMemoryHoldingsRepo; prices via fixture market + cache;
# FX via InMemoryExchangeRateRepo.seed(StoredRates(...))
```

## Tests
- Command (Windows):
  ```
  cd D:\rmit\cloud\a3\backend
  .\.venv\Scripts\python.exe -m pytest -q
  ```
- Result: **119 passed** (95 prior S00–S04 + 24 Sprint 05)
- Coverage: one-holding totals, mixed USD/VND, refresh client call, warm-cache skip, no ExchangeRateClient, API 401/200 shape, assetType filter, stored FX display conversion (S01 numbers)

## Known gaps / deferred
- ExchangeRateClient + admin refresh + repo `save` → **S06**
- DynamoDB adapters for FX / price cache
- Stale price flag on portfolio lines (PRD FR-P6 partial; market layer has stale fallback)
- History / S3 / news / jobs / boto3 → later sprints

## Next sprint needs
- **S06 FX:** implement `save` on `ExchangeRateRepo`, `ExchangeRateClient`, admin refresh; portfolio already reads `get_latest` with flat `USD_VND` keys
- **S11 UI:** consume portfolio DTO above; Decimals as strings; handle `fx.status=missing` / null `totalsDisplay`
- Reuse `set_exchange_rate_repo` / `set_portfolio_service` / `set_market_service` test hooks
