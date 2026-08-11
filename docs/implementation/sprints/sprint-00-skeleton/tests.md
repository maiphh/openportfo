# Sprint 00 — Tests (TDD order)

## test_health_returns_ok
- Create app via `create_app()`
- TestClient GET `/health`
- Assert 200 and body `status == "ok"`

## test_settings_loads_defaults
- Instantiate Settings with clean env (or defaults)
- Assert app_name, auth_mode, aws_region defaults

## test_settings_loads_from_env
- monkeypatch env `APP_ENV=test`, `AUTH_MODE=fake`, `AWS_REGION=us-east-1`
- get_settings() reflects values (clear lru_cache first)

## Run
```
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```
