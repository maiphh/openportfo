# Sprint 01 — Domain math

| Field | Value |
|-------|--------|
| **Depends on** | 00 done |
| **PRD** | Portfolio formulas, FX apply (stored rates only) |

## Goal
Pure domain models + portfolio/FX math. Zero I/O, zero AWS.

## Owns
- `backend/app/domain/**`
- `backend/tests/unit/domain/**`

## Out of scope
API, repos, market clients

## Agent prompt
```
Implement Sprint 01 only. Read sprint-01-domain docs + SPRINTS.md.
TDD domain math per tests.md. No FastAPI routes, no boto3.
Fill handoff.md when done.
```

## Exit
Domain unit tests green.
