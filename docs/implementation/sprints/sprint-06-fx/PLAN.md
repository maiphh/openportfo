# Sprint 06 — Detailed Plan: FX on-demand (admin)

| | |
|--|--|
| **ID** | S06 |
| **Depends on** | S02, S05 |
| **Unblocks** | Converted portfolio totals, FX demo |
| **PRD** | M10b, FR-FX1–8, FR-AD6–9, D3 |
| **Provider docs** | https://www.exchangerate-api.com/docs/overview |

---

## 1. Objective

Admin **on-demand** refresh of exchange rates via ExchangeRate-API; persist last good rates; on failure **keep previous rates**. Portfolio uses store only. **No** scheduled FX.

---

## 2. In / out

### In
- ExchangeRateClient port + success/fail fakes  
- HTTP adapter (Standard `latest/USD` or Pair)  
- ExchangeRateRepo (never wipe on failure)  
- FxService.refresh  
- GET /api/fx/rates  
- POST /api/admin/fx/refresh  
- Tests that portfolio conversion uses stored rates  

### Out
- Auto FX on portfolio GET  
- Lambda FX job  
- Frontend (S11)  

---

## 3. Port contracts

### RateSnapshot
`base`, `rates` (include VND), `provider="exchangerate-api"`, `fetched_at`, optional `raw`

### ExchangeRateClient
`fetch_latest(base="USD") -> RateSnapshot`  
Raises `ProviderError` on failure  

### ExchangeRateRepo
`get_latest() -> StoredRates | None`  
`save(snapshot) -> StoredRates`  
**No clear-on-failure** in service path  

### StoredRates
rates, as_of, provider, last_refresh_status (`success`|`error`), last_refresh_error?, updated_by?

---

## 4. API

| Method | Path | Auth | Behavior |
|--------|------|------|----------|
| GET | /api/fx/rates | user | Stored only; **0** provider calls |
| POST | /api/admin/fx/refresh | admin | One provider call; save on success |

### Failure response (locked)
HTTP **502** with body including `detail` and previous `rates` if any; DB unchanged.

---

## 5. Adapter: ExchangeRate-API

- Example: `GET https://v6.exchangerate-api.com/v6/{KEY}/latest/USD`  
- Map `conversion_rates.VND` → store USD→VND; derive VND→USD = 1/rate if needed  
- Key: `EXCHANGE_RATE_API_KEY` server-only  
- Timeout ~10s  

---

## 6. TDD sequence

1. Repo save/get  
2. Refresh success  
3. Refresh failure keeps old  
4. Non-admin 403  
5. GET does not call client  
6. Portfolio uses stored rates after seed  

---

## 7. Exit criteria

- [ ] FX tests green  
- [ ] Fallback proven  
- [ ] handoff: error shape + rate keys  

---

## 8. Agent prompt

```
Sprint 06 ONLY. Admin on-demand FX via ExchangeRate-API behind ports.
On failure keep last good rates. GET /fx/rates never hits provider.
No Lambda. TDD failure path. Fill handoff.
```
