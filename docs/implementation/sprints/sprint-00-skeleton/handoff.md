# Handoff — Sprint 00 — Skeleton

## Status
- [x] Not started
- [x] In progress
- [x] Done

## Ports / modules added
- Empty packages: `app/domain`, `app/services`, `app/ports`, `app/adapters`, `app/jobs`, `tests/fakes`
- `app/core/config.py` — Settings + `get_settings` / `clear_settings_cache`
- `app/core/deps.py` — `settings_dep` only
- `app/api/health.py` — health router
- `app/main.py` — `create_app()` + CORS + health

## API routes added
- `GET /health` → `{"status":"ok"}` (no auth)

## Env vars added
| Var | Default | Notes |
|-----|---------|--------|
| APP_NAME | OpenPortfo | |
| APP_ENV | local | local\|test\|prod |
| AUTH_MODE | fake | fake\|cognito |
| AWS_REGION | us-east-1 | |
| CORS_ORIGINS | localhost origins | comma-separated |
| COGNITO_* | empty / us-east-1 | Sprint 02 placeholders |
| *_TABLE | openportfo-* | Dynamo placeholders |
| DATA_BUCKET | empty | Sprint 07/12 |
| EXCHANGE_RATE_API_KEY | empty | Sprint 06 |
| COINGECKO_API_KEY | empty | Sprint 04 |

Template: `backend/.env.example`

## Shared files touched (`main.py`, `deps.py`, …)
- Created `main.py`, `core/deps.py`, `core/config.py` — later sprints append only

## Tests
- Command: `cd backend && .venv\Scripts\activate && pytest -q` (Windows)
- Result: **3 passed** (T00-1 health, T00-2 defaults, T00-3 env override)

## Known gaps / deferred
- None for skeleton scope
- `asyncio_mode` in pytest.ini unused until async tests (ignore warning)

## Next sprint needs
- Sprint 01: pure domain modules under `app/domain/` (no API changes)
- Empty `ports/` / `tests/fakes/` ready for Sprint 02+
