# Sprint 04 — Detailed Plan: Market data + PriceCache

| | |
|--|--|
| **ID** | S04 |
| **Depends on** | S03 |
| **Unblocks** | S05, S07, S10 price job |
| **PRD** | M2, FR-S*, cache-first pricing |

---

## 1. Objective

Abstract CoinGecko + vnstock behind market client ports; implement **PriceCache**; expose **search** API. Cache-first quote resolution with TTL.

---

## 2. In / out

### In
- CryptoMarketClient, StockMarketClient ports  
- PriceCacheRepo + fake  
- Fixture fakes for market clients  
- Real HTTP adapters optional (tests use fakes)  
- MarketService (search, get_quotes cache-first)  
- GET /api/assets/search  

### Out
- Portfolio endpoint, browser→external APIs, history API (S07)  

---

## 3. Port contracts

### CryptoMarketClient
`search(q)`, `get_simple_prices(ids, vs="usd")`, `get_market_chart(id, range)` (stub OK if S07 completes)

### StockMarketClient
`search(q)`, `get_prices(symbols)`, `get_history(symbol, range)` (stub OK)

### PriceCacheRepo
`get(asset_type, symbol)`, `put(quote, ttl_seconds)`

**Quote key:** `(asset_type, symbol)`  
**Default TTL:** 600s (10 min) unless settings override

---

## 4. API

`GET /api/assets/search?q=&type=crypto|stock`  
- Auth required  
- 400 if empty q or invalid type  
- Returns search DTO list  

---

## 5. Service rules

1. Search → client by type  
2. `get_quotes`: fresh cache hit skips client; miss batch-fetch + put  
3. External failure: return stale cache if any; else error (last-good prices)

---

## 6. TDD sequence

1. Fake crypto search mapping  
2. Fake stock search  
3. Cache hit → client call count 0  
4. Cache miss → client called + put  
5. Validation 400  
6. Unauthorized 401  

---

## 7. Adapter notes

| Provider | Notes |
|----------|--------|
| CoinGecko | /search, /simple/price; optional API key header |
| vnstock | Server-side only; fixture mode if lib breaks |

---

## 8. Exit criteria

- [ ] Search + cache tests green  
- [ ] handoff: quote key + TTL default  

---

## 9. Agent prompt

```
Sprint 04 ONLY. Market client ports + PriceCache + GET /api/assets/search.
TDD cache hit/miss. No portfolio route. No boto3 required.
```
