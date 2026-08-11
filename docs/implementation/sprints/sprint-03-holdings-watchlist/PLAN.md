# Sprint 03 — Detailed Plan: Holdings & Watchlist

| | |
|--|--|
| **ID** | S03 |
| **Depends on** | S02 |
| **Unblocks** | S04–S05, S10 |
| **PRD** | M3, M4, FR-H*, FR-W* |

---

## 1. Objective

User-scoped CRUD for **holdings** (qty + cost basis) and **watchlist**, behind repository ports, protected by S02 auth.

---

## 2. In / out

### In
- HoldingsRepo, WatchlistRepo + in-memory fakes  
- Validation services  
- REST APIs  
- Cross-user isolation tests  
- Optional DynamoDB adapter skeleton (no live AWS required)

### Out
- Market prices, portfolio, FX  

---

## 3. File ownership

| Path | Action |
|------|--------|
| `app/ports/holdings.py`, `watchlist.py` | Create |
| `tests/fakes/holdings.py`, `watchlist.py` | Create |
| `app/services/holdings_service.py`, `watchlist_service.py` | Create |
| `app/api/holdings.py`, `watchlist.py` | Create |
| `main.py`, `deps.py` | Register routes/deps only |
| `tests/unit/api/test_holdings.py`, `test_watchlist.py` | Create |

---

## 4. Data contracts

### Holding body
```json
{
  "assetType": "crypto|stock",
  "symbol": "BTC",
  "assetId": "bitcoin",
  "qty": "1.5",
  "avgCost": "40000",
  "currency": "USD",
  "note": "optional"
}
```

### Logical keys
- Holding: `HOLD#{assetType}#{symbol}` under `userId`  
- Watchlist: `WATCH#{assetType}#{symbol}`  

---

## 5. API

| Method | Path | Notes |
|--------|------|-------|
| GET | /api/holdings | list mine |
| POST | /api/holdings | 201; **409** if duplicate |
| PUT | /api/holdings/{assetType}/{symbol} | update |
| DELETE | /api/holdings/{assetType}/{symbol} | remove |
| GET/POST | /api/watchlist | list / add |
| DELETE | /api/watchlist/{assetType}/{symbol} | remove |

**Validation:** qty > 0, avgCost >= 0 → 400.  
**Authz:** never trust userId from body; always `current_user.user_id`.

**Duplicate policy (locked):** POST duplicate holding → **409 Conflict**.

---

## 6. TDD sequence

1. In-memory repo CRUD  
2. POST + GET holdings  
3. invalid qty 400  
4. user A vs B isolation  
5. update/delete  
6. watchlist add/list/remove  
7. duplicate 409  

---

## 7. Exit criteria

- [ ] All tests green  
- [ ] Services use ports only  
- [ ] handoff: path param scheme + 409 rule  

---

## 8. Agent prompt

```
Sprint 03 ONLY. Holdings + watchlist CRUD behind ports. Auth from S02 fakes.
TDD isolation + validation. 409 on duplicate holding. No market/portfolio.
```
