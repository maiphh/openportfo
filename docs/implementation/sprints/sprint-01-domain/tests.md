# Sprint 01 — Tests

- [x] 1. single USD holding math
- [x] 2. mixed USD+VND native subtotals (two currency groups)
- [x] 3. apply_fx with USD_VND rate → single display total
- [x] 4. missing fx → status missing, native only
- [x] 5. cost_basis 0 → pnl% defined behavior (`None`)
- [x] 6. allocation sums ~1.0 within display currency

Additional coverage: missing quote flag, get_rate same/direct/inverse/missing, zero market-value allocation edge.

File: `backend/tests/unit/domain/test_portfolio_math.py` (15 tests)
