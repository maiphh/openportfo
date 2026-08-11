# Review S00–S11 (final, orchestrator)

## Summary
**Verdict: PASS for MVP through temp frontend.** Sprints 00–11 implemented without AWS deploy (S12 blocked by design). Backend is ports-first; **147 tests passed** at S10 completion. Frontend-temp exercises APIs via token paste.

## Scope delivered
| Sprint | Deliverable | Status |
|--------|-------------|--------|
| 00 | FastAPI skeleton, health, settings | done |
| 01 | Domain Decimal math + FX apply | done |
| 02 | TokenVerifier + profile; fake/cognito | done |
| 03 | Holdings + watchlist CRUD | done |
| 04 | Market clients + PriceCache + search | done |
| 05 | Portfolio GET/refresh (no FX HTTP) | done |
| 06 | Admin FX refresh; keep last rates on fail | done |
| 07 | History ObjectStorage cache-aside | done |
| 08 | News read + keyword filter | done |
| 09 | Admin settings / RSS / job-runs | done |
| 10 | Jobs news/price/snapshot + handler | done |
| 11 | `frontend-temp/` Vite vanilla viewer | done |
| 12–13 | AWS deploy / stretch | **not implemented** (per request) |

## Architecture compliance
| Rule | Status |
|------|--------|
| No boto3 in api/services/domain/jobs | OK |
| Portfolio never calls ExchangeRateClient | OK |
| Jobs have no ExchangeRateClient on context | OK |
| Money as Decimal in domain | OK |
| Fake token `fake:<userId>` | OK |
| Role from profile repo | OK |

## Strengths
- Consistent DI via `deps.py` + in-memory fakes
- Clear sprint handoffs and locked key schemes
- TDD-style unit/API tests for critical paths
- Temp UI covers all major demo flows

## Findings

### Major (none blocking for course MVP)
None identified that fail the suite or violate PRD hard rules.

### Minor
1. **Process-global deps** — fine for single-process local/demo; not multi-worker safe without redesign.
2. **Price job always enabled** — no dedicated `jobs.price` flag (only news/snapshot/email in settings).
3. **News job keywords** — aggregates all users’ keywords globally; acceptable for demo.
4. **History synthetic fallback** — when fixture chart empty, service synthesizes points (good for demo; document when wiring live APIs).
5. **Frontend manual QA** — structure complete; operator should click-through against live uvicorn.

### Nits
- `asyncio_mode` unused in pytest.ini
- Admin API imports typed as bare `Depends(get_*)` without annotations (works)

## Recommended next (S12 when allowed)
- Dynamo/S3/Cognito real adapters
- Beanstalk + Lambda event wiring to `handler`
- Next.js CSR for assessment UI

## Test command
```
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```
