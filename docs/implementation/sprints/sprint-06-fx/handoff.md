# Handoff — Sprint 06 — FX

## Status
- [x] Not started
- [x] In progress
- [x] Done

## Ports / modules added
- `backend/app/ports/fx.py` — `RateSnapshot`, `StoredRates`, `ExchangeRateRepo` (get+save), `ExchangeRateClient`, `ProviderError`
- `backend/tests/fakes/fx.py` — `InMemoryExchangeRateRepo`, `FakeExchangeRateClient`
- `backend/app/adapters/exchangerate/client.py` — `HttpExchangeRateClient` (httpx, adapter only)
- `backend/app/services/fx_service.py` — `FxService.get_rates` / `refresh`; `ensure_pair_rates`; `stored_to_api`
- `backend/app/api/fx.py` — routes below
- Tests: `tests/unit/services/test_fx_service.py`, `tests/unit/api/test_fx.py`

## API routes added
| Method | Path | Auth | Behavior |
|--------|------|------|----------|
| GET | `/api/fx/rates` | user | Stored only; **0** provider calls |
| POST | `/api/admin/fx/refresh` | admin | One provider call; save on success |

### Failure shape (locked) — HTTP **502**
```json
{
  "detail": "upstream error message",
  "rates": { /* same shape as GET /api/fx/rates; previous rates if any */ }
}
```
DB/repo **unchanged** on failure (`save` not called).

### GET /api/fx/rates shape
```json
{
  "base": "USD",
  "rates": {"USD_VND": "25000", "VND_USD": "0.00004"},
  "asOf": "…",
  "provider": "exchangerate-api",
  "status": "fresh|missing|…",
  "lastRefreshStatus": "success|error|null",
  "lastRefreshError": null,
  "updatedBy": "adminUserId"
}
```

## Rate key scheme
- Flat `USD_VND`, `VND_USD` (uppercased)
- `ensure_pair_rates` derives missing inverse

## Env vars added
| Var | Notes |
|-----|--------|
| `EXCHANGE_RATE_API_KEY` | Already in Settings; empty → no HTTP client until set |

## Shared files touched
- `core/deps.py` — `get/set_exchange_rate_client`, `get/set_fx_service`
- `main.py` — fx router
- S05 portfolio tests updated: client may exist for admin FX; portfolio path still repo-only

## Tests
- Command: `cd backend && .\.venv\Scripts\python.exe -m pytest -q`
- Result: **130 passed**

## Known gaps / deferred
- Live provider not exercised in CI (fakes only)
- Dynamo FX adapter deferred to S12

## Next sprint needs
- S07 history uses ObjectStorage, not FX
- S11: show FX fail 502 + previous rates UI
