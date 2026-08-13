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
| Health | `GET /health` |
| Me | `GET /api/auth/me`, `PUT /api/settings` |
| Holdings / Watchlist | CRUD |
| Portfolio | `GET` + `POST /api/portfolio/refresh` |
| Market | popular/searchable crypto and VN stocks, cache-first price + explicit refresh |
| FX | stored rates, server-side conversion test, admin refresh (502 shows previous rates) |
| News | `GET /api/news` |
| History | `GET /api/assets/{id}/history` |
| DynamoDB | local-only table metadata and read-only item scans (max 100) |
| Admin | settings, RSS, job-runs |

Env: `VITE_API_URL` (default `http://127.0.0.1:8000`).
