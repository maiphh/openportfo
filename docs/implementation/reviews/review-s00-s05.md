# Review S00–S05 (orchestrator, post-timeout)

## Summary
**Verdict: PASS with minor notes.** Architecture holds: ports + fakes, Decimal domain math, auth isolation, portfolio cache-first and FX-store-only. Full suite green at handoff (119 tests at S05; 130 after S06).

## Strengths
- Clear layering: `domain` pure, `services` orchestrate ports, HTTP only in adapters
- Fake token `fake:<userId>` and role-from-profile locked consistently
- Portfolio reuses S01 `compute_native_portfolio` / `apply_fx`
- Market cache hit/miss/stale/force covered with call counters
- Holdings/watchlist user isolation + 409 duplicates

## Findings

### Minor
1. **Process-global DI in `deps.py`** — test setters work but concurrency/multi-tenant processes would need proper factories. Acceptable for course MVP.
2. **pytest `asyncio_mode` warning** — unused option in pytest.ini; remove when convenient.
3. **Starlette TestClient / httpx deprecation** — dependency churn only.

### Nits
- Some API query params use camelCase Python names (`displayCurrency`) for OpenAPI match; documented in portfolio module.

## Architecture compliance
| Rule | Status |
|------|--------|
| No boto3 in services/api/domain | OK |
| No ExchangeRateClient on portfolio GET/refresh | OK (proven; S06 client is admin-only) |
| Decimal money in domain | OK |
| Auth Bearer + profile bootstrap | OK |

## Test suite result
S05 complete: 119 passed. S06 complete: 130 passed.

## Recommended before later sprints
- Keep shared `deps.py` / `main.py` single-writer when parallelizing S07–S09
- Prefer fakes in tests; live adapters optional until S12
