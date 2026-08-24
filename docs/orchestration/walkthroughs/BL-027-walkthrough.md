# Walkthrough — BL-027: Portfolio CSV export (authenticated, FX-aware)

| Field | Value |
|-------|-------|
| **ID** | `BL-027` |
| **Branch** | `feat/BL-027-portfolio-csv-export` |
| **Worktree** | `D:\rmit\cloud\a3-wt-bl027` |
| **Implementor** | Implementor |
| **Date** | 2026-08-24 |
| **SA design** | `docs/orchestration/designs/BL-027-portfolio-csv-export-design.md` |
| **Research** | `docs/orchestration/research/BL-027-portfolio-csv-export-research.md` |

---

## 1. Summary (what was built)

Authenticated `GET /api/portfolio/export?format=csv` returns an inline UTF-8 `text/csv` snapshot of the caller's FX-aware portfolio (same `PortfolioService.get_portfolio` + `FxService.get_context()` path as `GET /api/portfolio`; stored rates only). `ExportService` renders stdlib CSV (`QUOTE_MINIMAL`, `\r\n`, 2dp display columns, injection-safe identity fields). The Portfolio dashboard adds an **Export CSV** button next to Refresh that downloads a Blob without page reload and shows a status toast. Pre-existing `GET /api/holdings/export` is unchanged. S3 presigned delivery was **not** implemented (Research Option A locked).

## 2. Files changed (path:line)

| File | Change | Lines |
|------|--------|-------|
| `backend/app/services/export_service.py:17-39` | CSV header (exact SA order) | NEW |
| `backend/app/services/export_service.py:54-62` | OWASP CSV injection sanitize (`'` prefix) | NEW |
| `backend/app/services/export_service.py:81-88` | Display money 2dp via `quantize(Decimal("0.01"))` | NEW |
| `backend/app/services/export_service.py:109-111` | `csv_filename()` → `openportfo-portfolio-YYYYMMDD.csv` UTC | NEW |
| `backend/app/services/export_service.py:149-195` | `render_portfolio_csv(view)` stdlib `csv.writer` + CRLF | NEW |
| `backend/app/services/export_service.py:169-174` | Sanitize **identity text only** (symbol/assetType/assetId); native Decimals keep leading `-` | NEW |
| `backend/app/api/portfolio.py:130-177` | `GET /api/portfolio/export` inline `Response(text/csv)` + `Content-Disposition` + `X-FX-Status`/`X-FX-As-Of` | |
| `backend/app/core/deps.py:42` | Import `ExportService` | |
| `backend/app/core/deps.py:529-530` | `get_export_service()` factory | |
| `backend/tests/unit/services/test_export_service.py:71-287` | Empty header; BTC math vs PortfolioService; 2dp; quoting; injection; FX; missing FX | NEW |
| `backend/tests/unit/api/test_portfolio_export.py:176-321` | 401; 200 CSV headers; isolation A vs B; empty; `format=json` 400; `currency=JPY` 400 | NEW |
| `frontend/lib/portfolio.ts:187-256` | `exportPortfolioCsv`, `triggerBlobDownload`, Content-Disposition filename helpers | |
| `frontend/lib/portfolio.test.ts` | Client + helper tests for CSV fetch / Blob download | |
| `frontend/components/portfolio/PortfolioDashboard.tsx:55-58` | `exporting` + inline toast state | |
| `frontend/components/portfolio/PortfolioDashboard.tsx:139` | `lines` wrapped in `useMemo` (eslint) | |
| `frontend/components/portfolio/PortfolioDashboard.tsx:224-257` | `handleExport` Blob download + toast | |
| `frontend/components/portfolio/PortfolioDashboard.tsx:326-335` | Export CSV button next to Refresh | |
| `frontend/components/portfolio/PortfolioDashboard.tsx:350-365` | `role="status"` toast banner | |
| `frontend/components/portfolio/PortfolioDashboard.test.tsx` | Button, loading, blob download, error/empty toasts | NEW |
| `docs/orchestration/walkthroughs/BL-027-walkthrough.md` | This file | NEW |

**Not edited (locked / out of scope):** `portfolio_service.py`, `domain/portfolio_math.py`, `domain/fx_math.py`, `domain/models.py`, `adapters/dynamodb/*`, `infra/*`, `jobs/*`, `frontend/lib/api.ts`, `frontend/app/layout.tsx`, `backend/app/api/holdings.py` (`GET /api/holdings/export` left as the simpler holdings dump).

## 3. Decisions & deviations from SA design

| # | SA said | Did | Reason |
|---|---------|-----|--------|
| 1 | Inline `text/csv` via `csv.writer` + `StringIO` + `Response` (Research Option A) | Same | Locked; no `?delivery=presigned`, no `ObjectStorage` port extension |
| 2 | `exportPortfolioCsv` → `Promise<Blob>` | Returns `{ blob, filename }` | Additive: uses `Content-Disposition` filename for the `<a download>` attribute without extra round-trip |
| 3 | Toast library (`toast.success`) | Inline `role="status"` banner | No toast dependency in `frontend/package.json`; same UX (success / error / empty) without new deps |
| 4 | Sanitize user-controlled `note`/`symbol` | Sanitize `symbol`/`assetType`/`assetId` only; **not** numeric columns | CSV contract has no `note` column; prefixing `'` on `-5000` PnL would corrupt native money. OWASP injection applies to formula-leading **text** |
| 5 | Default `disabled={loading \|\| exporting}` | Same on Export; Refresh still uses `loading \|\| refreshing` | Matches SA; Export does not wait on refresh |
| 6 | Leave holdings export alone | `GET /api/holdings/export` untouched | Different, simpler dump; BL-027 is portfolio FX-aware export |

## 4. How to verify

```powershell
# backend (worktree)
cd D:\rmit\cloud\a3-wt-bl027\backend
D:\rmit\cloud\a3\backend\.venv\Scripts\python.exe -m pytest -q
D:\rmit\cloud\a3\backend\.venv\Scripts\python.exe -m pytest -q tests/unit/services/test_export_service.py tests/unit/api/test_portfolio_export.py

# frontend
cd D:\rmit\cloud\a3-wt-bl027\frontend
npm run lint
npm run test -- lib/portfolio components/portfolio/PortfolioDashboard

# ports isolation (must be empty)
Get-ChildItem -Path "D:\rmit\cloud\a3-wt-bl027\backend\app\services","D:\rmit\cloud\a3-wt-bl027\backend\app\api","D:\rmit\cloud\a3-wt-bl027\backend\app\domain","D:\rmit\cloud\a3-wt-bl027\backend\app\jobs" -Recurse -Filter *.py |
  Select-String -Pattern "import boto3|import botocore|from boto3|import httpx|from httpx|import requests|from requests"
```

Expected output:

```
# full pytest
529 passed, 4 skipped, 4 warnings in ~20s

# targeted BL-027
17 passed

# frontend lint
(no errors; eslint exit 0)

# frontend tests
Test Files  3 passed (3)
Tests  43 passed (43)

# ports
(no matches)
```

Manual (optional, local API):

```powershell
curl.exe -H "Authorization: Bearer fake:alice" "http://localhost:8000/api/portfolio/export?format=csv&displayCurrency=VND" -i
```

Expect `200`, `Content-Type: text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="openportfo-portfolio-YYYYMMDD.csv"`, `X-FX-Status`, CSV header row.

## 5. Test evidence (paste)

```
# D:\rmit\cloud\a3-wt-bl027\backend
529 passed, 4 skipped, 4 warnings in 19.54s

# targeted
tests/unit/services/test_export_service.py tests/unit/api/test_portfolio_export.py
.................                                                        [100%]
17 passed, 2 warnings in 1.17s

# frontend
npm run lint  → exit 0 (0 errors)
npm run test -- lib/portfolio components/portfolio/PortfolioDashboard
Test Files  3 passed (3)
Tests  43 passed (43)
```

- Unit tests added: `test_export_service.py` (9), `test_portfolio_export.py` (8), `portfolio.test.ts` export/helpers, `PortfolioDashboard.test.tsx` (5).
- Coverage of AC: AC1 math+CSV headers; AC2 FX conversion; AC3 missing FX + no live client; AC4 401; AC5 isolation; AC6 empty header-only; AC7 FE button/download/toast; AC8 ports grep empty.

## 6. API / UX verification

- Curl / browser steps:
  1. Sign in (Bearer `fake:<user>` in dev).
  2. Open `/portfolio/`, pick display currency, click **Export CSV** (beside Refresh).
  3. Browser downloads `openportfo-portfolio-YYYYMMDD.csv` without reload; button shows **Exporting…** then success banner.
  4. Empty portfolio: still 200 header-only from API; UI shows “No holdings to export”.
  5. Unauthenticated `GET /api/portfolio/export` → 401; `format=json` / `currency=JPY` → 400.
- Screenshots / curl output: not captured in this worktree run (unit/API tests cover contract).

## 7. Ports isolation check

```powershell
Get-ChildItem -Path "backend/app/services","backend/app/api","backend/app/domain","backend/app/jobs" -Recurse -Filter *.py |
  Select-String -Pattern "import boto3|import botocore|from boto3|import httpx|from httpx|import requests|from requests"
```

Result: **empty** (no matches in services/api/domain/jobs). `boto3` remains confined to adapters. Export path does not import `ExchangeRateClient`.

## 8. Known limitations / follow-ons

- No `?delivery=presigned` / `ObjectStorage.generate_presigned_url` (documented opt-in in Research §5–6; not MVP).
- UTF-8 **without BOM** (Excel Windows double-click may mangle; Research open question `?bom=1`).
- Export is cache-first (`force_refresh=False`); use **Refresh** first if prices must be refetched.
- No toast library; status is an in-page banner (`role="status"`).
- Portfolio cap assumed ≤100 rows; `Response` (not `StreamingResponse`) as locked.

## 9. Handoff to SA Review

- Walkthrough ready for SA review: **yes**
- AC checklist self-assessed:

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | pass | `test_export_200_text_csv_headers_and_math` + service BTC math |
| AC2 | pass | `test_portfolio_export_fx_conversion` / `test_export_fx_conversion_when_stored_rate_exists` |
| AC3 | pass | `test_missing_fx_native_filled_converted_blank` + `test_export_never_calls_exchange_rate_client` |
| AC4 | pass | `test_export_unauthorized_401` |
| AC5 | pass | `test_export_isolation_user_a_vs_b` |
| AC6 | pass | `test_export_empty_header_only` / `test_empty_portfolio_header_only` |
| AC7 | pass | `PortfolioDashboard.test.tsx` + `exportPortfolioCsv` client tests |
| AC8 | pass | ports grep empty; no ObjectStorage change |
