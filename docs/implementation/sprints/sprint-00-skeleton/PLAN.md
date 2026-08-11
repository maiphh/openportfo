# Sprint 00 — Detailed Plan: Skeleton

| | |
|--|--|
| **ID** | S00 |
| **Name** | Skeleton |
| **Duration (guide)** | 0.5–1 day |
| **Depends on** | None |
| **Unblocks** | All later sprints |
| **PRD refs** | Foundation (NFR maintainability, config) |
| **Status source** | `docs/implementation/SPRINTS.md` |

---

## 1. Objective

Stand up a **runnable FastAPI backend** with configuration, health check, pytest, and empty package layout so every later sprint has a stable place for ports/adapters/services/API.

**Success:** `pytest` green; `GET /health` returns `{"status":"ok"}`.

---

## 2. In scope / out of scope

### In
- `backend/` package layout (`app/`, `tests/`)
- `Settings` from env (pydantic-settings)
- `create_app()` + CORS
- `GET /health`
- DI stub (`core/deps.py`)
- `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `.env.example`
- Empty packages: `ports`, `adapters`, `domain`, `services`, `jobs`, `tests/fakes`

### Out
- Any business API (auth, holdings, portfolio, FX, …)
- boto3, Cognito, DynamoDB, real AWS calls
- Frontend

---

## 3. File ownership (multiagent)

| Path | Action |
|------|--------|
| `backend/app/main.py` | Create |
| `backend/app/core/config.py` | Create |
| `backend/app/core/deps.py` | Create |
| `backend/app/api/health.py` | Create |
| `backend/tests/unit/test_health.py` | Create |
| `backend/tests/unit/test_settings.py` | Create |
| `backend/requirements*.txt`, `pytest.ini` | Create |
| `backend/app/{domain,services,ports,adapters,jobs}/__init__.py` | Create empty |

**Do not touch:** feature modules, `frontend-temp/`.

---

## 4. Component specifications

### 4.1 Settings (`core/config.py`)

| Field | Env | Default | Notes |
|-------|-----|---------|--------|
| app_name | APP_NAME | OpenPortfo | |
| app_env | APP_ENV | local | local\|test\|prod |
| auth_mode | AUTH_MODE | fake | fake\|cognito |
| aws_region | AWS_REGION | us-east-1 | |
| cors_origins | CORS_ORIGINS | localhost origins | comma-separated → list property |
| cognito_* | COGNITO_* | empty | placeholders Sprint 02 |
| *_table | *_TABLE | openportfo-* | placeholders |
| data_bucket | DATA_BUCKET | empty | Sprint 07/12 |
| exchange_rate_api_key | EXCHANGE_RATE_API_KEY | empty | Sprint 06 |
| coingecko_api_key | COINGECKO_API_KEY | empty | Sprint 04 |

- `get_settings()` with `@lru_cache`
- `clear_settings_cache()` for tests

### 4.2 App factory
- FastAPI title from settings
- CORSMiddleware from `cors_origin_list`
- Include health router only

### 4.3 Health
- `GET /health` → 200 `{"status":"ok"}`
- No auth, no DB

### 4.4 Deps
- `settings_dep()` only; later sprints append port factories

---

## 5. TDD sequence (strict order)

1. Write `test_health_returns_ok` (fails: no app)
2. Write `test_settings_loads_defaults`
3. Write `test_settings_loads_from_env` (monkeypatch + clear cache)
4. Implement config → settings tests green
5. Implement health + create_app → health test green
6. Document run commands in handoff

---

## 6. Test cases (acceptance)

| ID | Case | Expected |
|----|------|----------|
| T00-1 | GET /health | 200, `status=ok` |
| T00-2 | Settings defaults | app_name, auth_mode=fake, region |
| T00-3 | Env override | APP_ENV, AUTH_MODE, AWS_REGION applied after cache clear |

---

## 7. Agent prompt (copy-paste)

```
You own Sprint 00 ONLY (docs/implementation/sprints/sprint-00-skeleton/).
Follow PLAN.md + components.md + tests.md. TDD first.
Global rules: docs/implementation/SPRINTS.md
Do not implement auth, domain math, or AWS.
When done: fill handoff.md and update SPRINTS.md status (or ask orchestrator).
```

---

## 8. Exit criteria checklist

- [ ] Layout exists as specified
- [ ] All T00-* tests pass via `cd backend && pytest -q`
- [ ] Manual: uvicorn serves /health
- [ ] handoff.md lists env vars and how to run
- [ ] No business routes registered

---

## 9. Handoff contract

- How to run tests and server
- Settings env var list
- Empty ports package ready for Sprint 01–02
- Shared files created: `main.py`, `deps.py` (later sprints append only)

---

## 10. Risks

| Risk | Mitigation |
|------|------------|
| pythonpath on Windows | pytest.ini `pythonpath = .` from `backend/` |
| pydantic version drift | Pin pydantic-settings v2 |
