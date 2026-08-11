# Sprint 01 — Detailed Plan: Domain math

| | |
|--|--|
| **ID** | S01 |
| **Depends on** | S00 done |
| **Unblocks** | S05 portfolio, S06 FX conversion, S10 snapshots |
| **PRD refs** | §8.5 formulas, D3 currency/FX apply (pure functions only) |

---

## 1. Objective

Implement **pure** portfolio and FX application logic with no I/O. All money math lives here so services stay thin and tests stay fast.

---

## 2. In / out

### In
- Domain models (Holding, PriceQuote, lines, summaries, FxRates)
- Native valuation per line and per currency
- FX conversion using **injected** rate map (not HTTP)
- Allocation, PnL, PnL% edge cases

### Out
- FastAPI routes, DynamoDB/boto3, ExchangeRate-API, persistence

---

## 3. File ownership

| Path | Action |
|------|--------|
| `backend/app/domain/models.py` | Create |
| `backend/app/domain/portfolio_math.py` | Create |
| `backend/app/domain/fx_math.py` | Create (or single module) |
| `backend/tests/unit/domain/test_*.py` | Create |

**Do not edit:** `main.py` routes, adapters, api.

---

## 4. Domain model specs

### Holding
`user_id`, `asset_type` (crypto|stock), `symbol`, `asset_id?`, `qty: Decimal`, `avg_cost: Decimal`, `currency`, `note?`

### PriceQuote
`asset_type`, `symbol`, `price: Decimal`, `currency`, `as_of`

### FxRates
- `base`, `rates` (document key scheme), `as_of?`
- `status`: `missing` | `stale_ok` | `fresh`

### PortfolioLine / PortfolioSummary
Native + optional display fields after FX; `totals_by_currency`; fx meta.

**Use `Decimal` for money**, not float.

---

## 5. Function specs

| Function | Behavior |
|----------|----------|
| `native_line(holding, quote)` | mv = qty*price; cost = qty*avg_cost; pnl = mv-cost |
| `compute_native_portfolio(holdings, quotes)` | Aggregate by currency; missing quote policy documented |
| `pnl_percent(pnl, cost)` | `None` if cost == 0 |
| `apply_fx(summary, fx, display_currency)` | Convert lines; allocation in display currency; pure |
| `get_rate(fx, src, dst)` | 1 if same; lookup; optional inverse fallback |

### Rate key convention (lock in handoff)
Recommended flat keys: `USD_VND`, `VND_USD`, or nested `rates[src][dst]`.

### Missing quote policy (lock)
Exclude line from totals and flag `missing_price` (preferred).

---

## 6. TDD sequence

1. native single USD holding  
2. mixed USD+VND subtotals  
3. pnl% zero cost  
4. apply_fx with rate  
5. missing fx → status missing  
6. allocation sums ≈ 1.0  

---

## 7. Exit criteria

- [x] Domain tests green  
- [x] No fastapi/boto3/httpx imports in domain  
- [x] handoff: rate scheme + missing quote behavior + example fixture numbers  

---

## 8. Agent prompt

```
Sprint 01 ONLY. Pure domain math. Read PLAN.md. TDD per tests.md.
No API, no AWS. Decimal money. Fill handoff with rate key scheme.
```
