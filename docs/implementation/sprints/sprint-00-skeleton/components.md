# Sprint 00 — Components

## 1. Layout
Create:
```
backend/
  app/
    __init__.py
    main.py
    api/__init__.py
    domain/__init__.py
    services/__init__.py
    ports/__init__.py
    adapters/__init__.py
    jobs/__init__.py
    core/
      __init__.py
      config.py
      deps.py
  tests/
    __init__.py
    unit/
      __init__.py
      test_health.py
      test_settings.py
    fakes/__init__.py
  requirements.txt
  requirements-dev.txt
  pytest.ini
```

## 2. Settings (`core/config.py`)
Use pydantic-settings `BaseSettings`:
- `app_name: str = "OpenPortfo"`
- `app_env: str = "local"`  # local|test|prod
- `auth_mode: str = "fake"`  # fake|cognito
- `aws_region: str = "us-east-1"`
- `cors_origins: str = "http://localhost:3000,http://127.0.0.1:5500"` (parse to list property)
- Placeholders for later: cognito_*, table names, buckets, exchange_rate_api_key, coingecko (optional)

`get_settings()` lru_cache; clear cache in tests.

## 3. App factory (`main.py`)
- `create_app() -> FastAPI`
- CORSMiddleware from settings
- Include health router prefix optional: `/health` at root
- Title OpenPortfo API

## 4. Health
- `GET /health` → `{"status": "ok"}`

## 5. Deps stub (`core/deps.py`)
- `get_settings` dependency only for now

## 6. Dependencies
requirements.txt: fastapi, uvicorn[standard], pydantic-settings
requirements-dev.txt: pytest, httpx
pytest.ini: `pythonpath = .` or `backend`, testpaths=tests
