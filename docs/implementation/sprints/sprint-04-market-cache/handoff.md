# Handoff — Sprint 04 — Market/Cache

## Status
- [x] Not started
- [x] In progress
- [x] Done

## Ports / modules added
- `backend/app/ports/market.py` — `AssetSearchResult`, `CryptoMarketClient`, `StockMarketClient`, `MarketDataError`
- `backend/app/ports/price_cache.py` — `CachedPrice`, `PriceCacheRepo` (`get` / `put`; `allow_expired` for last-good)
- `backend/app/adapters/coingecko/client.py` — `FixtureCoinGeckoClient` (fixture search + simple prices; chart stub)
- `backend/app/adapters/vnstock/client.py` — `FixtureVnstockClient` (fixture search + prices; history stub)
- `backend/tests/fakes/market.py` — aliases `FixtureCryptoMarketClient` / `FixtureStockMarketClient` (+ call counters)
- `backend/tests/fakes/price_cache.py` — `InMemoryPriceCacheRepo` with TTL / `allow_expired` / `seed`
- `backend/app/services/market_service.py` — `MarketService`, `QuoteKey`, `ValidationError`, `search_result_to_dict`
- `backend/app/api/assets.py` — `GET /api/assets/search`
- `backend/tests/unit/services/test_market_service.py` — search + cache hit/miss/stale/force
- `backend/tests/unit/api/test_assets_search.py` — DTO mapping, 400, 401

## Quote key + TTL default (locked)
| Item | Value |
|------|--------|
| **Quote key** | `(asset_type, symbol)` — symbol **uppercased**; asset_type lowercased `crypto` \| `stock` |
| **Dynamo logical PK** | `{assetType}#{symbol}` (for later adapter) |
| **Default TTL** | **600 seconds** (10 min) via `Settings.price_cache_ttl_seconds` / env `PRICE_CACHE_TTL_SECONDS` |
| **Fresh** | `now < expires_at` → `get(..., allow_expired=False)` returns entry |
| **Stale fallback** | On external failure, `get(..., allow_expired=True)` returns last-good if any; else `MarketDataError` |

## Search DTO shape
```json
{
  "symbol": "BTC",
  "name": "Bitcoin",
  "assetId": "bitcoin",
  "assetType": "crypto"
}
```
Stock example: `{"symbol":"VNM","name":"Vinamilk","assetId":"VNM","assetType":"stock"}`.

## How `get_quotes` works (for S05)
```python
from app.services.market_service import MarketService, QuoteKey

# keys: QuoteKey or (asset_type, symbol[, asset_id])
quotes = market_service.get_quotes(
    [
        ("crypto", "BTC", "bitcoin"),  # asset_id preferred for CoinGecko batch
        ("stock", "VNM"),
    ],
    force=False,  # True on POST /portfolio/refresh
)
# → list[PriceQuote] in request order; cache key always (asset_type, symbol)
```

Algorithm:
1. Parse/normalize keys; dedupe for fetch.
2. Unless `force`, read **fresh** cache per key → skip client.
3. Batch-miss: crypto → `get_simple_prices(ids)`; stock → `get_prices(symbols)`.
4. `put` each success with TTL (default 600s).
5. On client exception: use **stale** cache if present; else raise `MarketDataError`.

Wire via `get_market_service()` / `set_*` hooks in `deps.py`. Do **not** call CoinGecko/vnstock from portfolio API directly.

## API routes added
| Method | Path | Auth | Behaviour |
|--------|------|------|-----------|
| GET | `/api/assets/search?q=&type=crypto\|stock` | Bearer | Search DTO list; **400** empty `q` / invalid type; **401** without valid token |

## Env vars added
| Var | Default | Notes |
|-----|---------|--------|
| `PRICE_CACHE_TTL_SECONDS` | `600` | Logical price cache freshness |

## Shared files touched (`main.py`, `deps.py`, …)
- `backend/app/core/config.py` — `price_cache_ttl_seconds`
- `backend/app/core/deps.py` — **appended**: crypto/stock client factories + setters, price cache factory + setter, `get_market_service` / `set_market_service`
- `backend/app/main.py` — `include_router(assets_router)`
- `requirements.txt` — **unchanged** (fixture adapters; no live HTTP deps)

## Auth for tests (S02 pattern unchanged)
```python
headers = {"Authorization": "Bearer fake:alice"}
from app.core.deps import (
    set_crypto_market_client,
    set_stock_market_client,
    set_price_cache_repo,
    set_market_service,
    set_user_profile_repo,
)
```

## Tests
- Command (Windows):
  ```
  cd D:\rmit\cloud\a3\backend
  .\.venv\Scripts\python.exe -m pytest -q
  ```
- Result: **95 passed** (69 prior S00–S03 + 26 Sprint 04)
- Coverage: crypto/stock search DTOs, cache hit (client calls 0), miss + put, batch, force refresh, stale on failure, empty/invalid q type 400, unauthorized 401, TTL expiry

## Known gaps / deferred
- Live CoinGecko HTTP + `COINGECKO_API_KEY` header (fixture only)
- Live vnstock dependency (fixture only)
- DynamoDB `PriceCacheRepo` adapter
- `get_market_chart` / `get_history` stubs → S07
- Portfolio wiring of `get_quotes` → S05

## Next sprint needs
- Sprint 05 (Portfolio): inject `MarketService`; `get_quotes` for holdings symbols; `force=True` on refresh; never call ExchangeRate HTTP
- Reuse `get_market_service` / `get_price_cache_repo` and test setters
- Quote key `(asset_type, symbol)`; pass crypto `asset_id` from holdings when fetching
- Fake token still `Bearer fake:<userId>`
