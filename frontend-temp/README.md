# OpenPortfo — Temp frontend (Sprint 11)

Vanilla JS + Vite viewer for local API verification. **Not** the assessment Next.js UI.

## Run

```bash
# Terminal 1 — API
cd backend
.\.venv\Scripts\Activate.ps1   # Windows
uvicorn app.main:app --reload --port 8000

# Terminal 2 — UI
cd frontend-temp
npm install
npm run dev
```

Open http://localhost:5173

## Auth

1. Paste token in the header bar, e.g. `fake:alice` (S02 FakeTokenVerifier).
2. Click **Save** (stored in `sessionStorage`).
3. **Me** bootstraps the profile on first call.

Admin screens need `role=admin` on the profile (set in tests/backend; not via this UI).
For local testing, the **Me** tab includes a debug-only promotion button. The backend endpoint returns 404 outside `APP_ENV=local/test`.

## Screens

| Tab | Calls |
|-----|--------|
| Health | `GET /health`, `GET /health/ready` |
| Me | `GET /api/auth/me`, `GET/PUT /api/settings` |
| Holdings | CRUD + `GET /api/holdings/export` |
| Watchlist | CRUD; list includes `price` / `stale`; click symbol → Asset |
| Portfolio | `GET` + `POST /api/portfolio/refresh`, `totalsByAssetClass`, `GET /api/portfolio/performance` |
| Asset | `GET /api/assets/{type}/{slug}?currency=&range=` + `/history`; hash `#/crypto/btc?currency=VND` |
| Market | search/list + quote; **Open detail** |
| FX | stored rates, conversion, admin refresh |
| News | `GET /api/news` |
| History | legacy `GET /api/assets/{id}/history` |
| Snapshots | `GET /api/snapshots`, `GET /api/snapshots/{date}` |
| S3 | local-only `GET /api/dev/s3` + `/object?key=` (memory or LocalStack) |
| DynamoDB | local-only table scan |
| Admin | settings, RSS, job-runs |

Asset deep-link example: http://localhost:5173/#/crypto/btc?currency=VND

Env: `VITE_API_URL` (default `http://127.0.0.1:8000`).
