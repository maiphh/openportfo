# Sprint 00 — Skeleton

| Field | Value |
|-------|--------|
| **Status** | in_progress |
| **Depends on** | — |
| **PRD** | Foundation for all FR |

## Goal
Runnable FastAPI app, config, pytest, DI stub, `GET /health`. No business routes.

## In scope
- Package layout under `backend/`
- `Settings` via env
- `create_app()`, CORS, health
- requirements + pytest
- Empty `ports/`, `adapters/`, `fakes/` packages

## Out of scope
- Auth, DynamoDB, domain math, any feature API

## Owns
- `backend/app/main.py`
- `backend/app/core/**`
- `backend/app/api/health.py` (or inline)
- `backend/tests/unit/test_health.py`, `test_settings.py`
- `backend/requirements.txt`, `requirements-dev.txt`, `pytest.ini`
- Package `__init__.py` placeholders for ports/adapters/services/domain/api

## Shared files
Creates `core/deps.py` and `main.py` — later sprints append routers carefully.

## Agent prompt
```
You are implementing OpenPortfo Sprint 00 only.
Read docs/implementation/sprints/sprint-00-skeleton/{README,components,tests}.md
and docs/implementation/SPRINTS.md global rules.
TDD: write tests first from tests.md, then implement.
Do NOT add business routes, boto3, or Cognito.
When done, fill handoff.md.
```

## Exit criteria
- [ ] `pytest` green
- [ ] `uvicorn app.main:app` serves GET /health → 200 `{"status":"ok"}`
- [ ] handoff.md updated
