# Handoff — Sprint 03 — Holdings/Watchlist

## Status
- [x] Not started
- [x] In progress
- [x] Done

## Ports / modules added
- `backend/app/ports/holdings.py` — `HoldingRecord`, `HoldingsRepo` Protocol, `DuplicateHoldingError`, `HoldingNotFoundError`; logical SK `HOLD#{assetType}#{symbol}`
- `backend/app/ports/watchlist.py` — `WatchlistItem`, `WatchlistRepo` Protocol, `DuplicateWatchlistError`, `WatchlistNotFoundError`; logical SK `WATCH#{assetType}#{symbol}`
- `backend/tests/fakes/holdings.py` — `InMemoryHoldingsRepo` (user-scoped dict; symbol uppercased)
- `backend/tests/fakes/watchlist.py` — `InMemoryWatchlistRepo`
- `backend/app/services/holdings_service.py` — `HoldingsService` + `ValidationError` (qty > 0, avgCost ≥ 0, Decimal money)
- `backend/app/services/watchlist_service.py` — `WatchlistService` + `ValidationError`
- `backend/app/api/holdings.py` — REST holdings (camelCase JSON)
- `backend/app/api/watchlist.py` — REST watchlist (camelCase JSON)
- `backend/tests/unit/api/test_holdings.py` — repo + service + API + isolation
- `backend/tests/unit/api/test_watchlist.py` — repo + service + API + isolation

## Path param scheme (locked)
| Resource | Path | Path params |
|----------|------|-------------|
| Update/delete holding | `/api/holdings/{assetType}/{symbol}` | FastAPI names: `asset_type`, `symbol` (URL segment is case-sensitive for type; symbol normalized to **uppercase** in service/repo) |
| Remove watchlist | `/api/watchlist/{assetType}/{symbol}` | same |

**Not** opaque `itemId` — composite key matches Dynamo logical SK components.

Example: `PUT /api/holdings/crypto/BTC`, `DELETE /api/watchlist/stock/VNM`

## 409 rule (holdings)
| Case | Status |
|------|--------|
| `POST /api/holdings` when `(userId, assetType, symbol)` already exists | **409 Conflict** `{ "detail": "..." }` |
| Same symbol under different `assetType` | Allowed (different key) |
| Same symbol for different users | Allowed (user-scoped) |

## Watchlist duplicate policy (locked)
**409 Conflict** on `POST /api/watchlist` if item already exists for current user (same as holdings — not idempotent upsert).

## API routes added
| Method | Path | Auth | Behaviour |
|--------|------|------|-----------|
| GET | `/api/holdings` | Bearer | List mine |
| POST | `/api/holdings` | Bearer | Create; **201**; **409** duplicate; **400** invalid qty/avgCost |
| PUT | `/api/holdings/{assetType}/{symbol}` | Bearer | Update qty/avgCost/note/…; **404** if missing |
| DELETE | `/api/holdings/{assetType}/{symbol}` | Bearer | **204**; **404** if missing |
| GET | `/api/watchlist` | Bearer | List mine |
| POST | `/api/watchlist` | Bearer | Add; **201**; **409** duplicate |
| DELETE | `/api/watchlist/{assetType}/{symbol}` | Bearer | **204**; **404** if missing |

All routes require `Authorization: Bearer …` → **401** without valid token.  
`userId` is **never** taken from the request body; always `current_user.user_id` from S02.

### Holding JSON (response / create body camelCase)
```json
{
  "userId": "alice",
  "assetType": "crypto",
  "symbol": "BTC",
  "assetId": "bitcoin",
  "qty": "1.5",
  "avgCost": "40000",
  "currency": "USD",
  "note": "optional",
  "createdAt": "…",
  "updatedAt": "…"
}
```
`qty` / `avgCost` are **strings** in JSON; **Decimal** internally.

### Watchlist JSON
```json
{
  "userId": "alice",
  "assetType": "crypto",
  "symbol": "BTC",
  "assetId": "bitcoin",
  "addedAt": "…"
}
```

## Env vars added
- None (reuses S02 `AUTH_MODE` / Cognito settings)

## Shared files touched (`main.py`, `deps.py`, …)
- `backend/app/core/deps.py` — **appended**: `get_holdings_repo` / `set_holdings_repo`, `get_watchlist_repo` / `set_watchlist_repo` (process-local in-memory until Dynamo)
- `backend/app/main.py` — `include_router(holdings_router)`, `include_router(watchlist_router)`

## Auth for tests (S02 pattern unchanged)
```python
headers = {"Authorization": "Bearer fake:alice"}
from app.core.deps import set_holdings_repo, set_watchlist_repo, set_user_profile_repo
# override repos for isolation
```

## Tests
- Command (Windows):
  ```
  cd D:\rmit\cloud\a3\backend
  .\.venv\Scripts\python.exe -m pytest -q
  ```
- Result: **69 passed** (40 prior S00–S02 + 29 Sprint 03)
- Coverage: in-memory holdings/watchlist CRUD, service validation (qty/avgCost), API 401/201/400/409/404/204, user A vs B isolation, body `userId` ignored

## Known gaps / deferred
- DynamoDB adapters for `HoldingsRepo` / `WatchlistRepo` (deploy sprint)
- Watchlist prices from PriceCache (S04)
- Portfolio aggregation (S05)
- Asset search for picker (S04)
- Optional Dynamo adapter skeleton not added (not required; ports + fakes sufficient)

## Next sprint needs
- Sprint 04 (Market + cache): load holdings/watchlist symbols via ports; do not call market from S03 modules
- Reuse `get_holdings_repo` / `get_watchlist_repo` and test setters
- Path scheme: `{assetType}/{symbol}` as above
- Fake token still `Bearer fake:<userId>`
