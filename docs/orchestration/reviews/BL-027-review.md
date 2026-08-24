# SA Review — BL-027: Portfolio CSV export (authenticated, FX-aware)

| Field | Value |
|-------|-------|
| **ID** | `BL-027` |
| **Reviewer (SA)** | Solution Architect (review mode) |
| **Date** | 2026-08-24 |
| **Walkthrough** | `docs/orchestration/walkthroughs/BL-027-walkthrough.md` |
| **Verdict** | `approve` |

---

## 1. AC verification

| AC | Satisfied? | Evidence (file:line or test) | Note |
|----|------------|------------------------------|------|
| AC1 | yes | `test_export_200_text_csv_headers_and_math` `backend/tests/unit/api/test_portfolio_export.py:182-209`; math parity `test_one_btc_holding_math_matches_portfolio_service` `backend/tests/unit/services/test_export_service.py:86-116`; handler `backend/app/api/portfolio.py:130-177` | Inline `text/csv` locked. `200`, `charset=utf-8`, `Content-Disposition` `openportfo-portfolio-\d{8}.csv`, `X-FX-Status`, qty×price / pnl match `PortfolioService`. |
| AC2 | yes | `test_portfolio_export_fx_conversion` `backend/tests/unit/services/test_export_service.py:222-253`; API `test_export_fx_conversion_when_stored_rate_exists` `backend/tests/unit/api/test_portfolio_export.py:297-321` | Stored `USD_VND=25000` → `marketValueDisplay=1000000000`, `costBasisDisplay=750000000`, `fxRateUsed=25000`. Conversion via `PortfolioService.get_portfolio` + stored `FxService.get_context()`, not a live client. |
| AC3 | yes | `test_missing_fx_native_filled_converted_blank` `backend/tests/unit/services/test_export_service.py:256-279`; `test_export_never_calls_exchange_rate_client` `backend/tests/unit/api/test_portfolio_export.py:274-294` | Native filled, display cols `""`, `fxStatus=missing`, `X-FX-Status: missing`. Source scan: no `ExchangeRateClient` in `portfolio.py` / `export_service.py` / `get_export_service`. |
| AC4 | yes | `test_export_unauthorized_401` `backend/tests/unit/api/test_portfolio_export.py:176-179`; `get_current_user` `backend/app/core/deps.py:223-226` (`detail="Missing authorization header"`) | `401` + `{detail: ...}`. |
| AC5 | yes | `test_export_isolation_user_a_vs_b` `backend/tests/unit/api/test_portfolio_export.py:212-235` | Alice CSV symbols `{"BTC"}`, Bob `{"VNM"}`. Scoped via `svc.get_portfolio(user.user_id, ...)` `backend/app/api/portfolio.py:155-156`. |
| AC6 | yes | `test_export_empty_header_only` `backend/tests/unit/api/test_portfolio_export.py:238-250`; `test_empty_portfolio_header_only` `backend/tests/unit/services/test_export_service.py:71-83` | `200` + header row only, CRLF, no BOM. |
| AC7 | yes | `frontend/components/portfolio/PortfolioDashboard.test.tsx:109-185`; client `frontend/lib/portfolio.test.ts:287-347`, `:364-386`; UI `frontend/components/portfolio/PortfolioDashboard.tsx:224-257`, `:326-335`, `:350-365` | Export CSV next to Refresh; `Exporting…`; Blob download without reload; `role="status"` success/error/empty banners. |
| AC8 | yes | Ports grep empty for `boto3`/`botocore`/`httpx`/`requests` imports under `services`/`api`/`domain`/`jobs`; `test_export_service_has_no_http_or_aws_imports` `backend/tests/unit/services/test_export_service.py:282-290`; commit does not touch `backend/app/ports/storage.py` | Inline only. No `ObjectStorage` extension. `GET /api/holdings/export` unchanged. |

---

## 2. Architecture checks

- [x] Ports isolation (`boto3`/`httpx` only in `adapters/`)? **Empty** in `backend/app/services`, `api`, `domain`, `jobs` (imports). Hits remain in `backend/app/adapters/**` only. Jobs comment `backend/app/jobs/context.py:1` is “no boto3”, not an import.
- [x] Locked decisions intact (no API GW, no SSR, cache-first, Cognito JWKS)?
  - No API GW: FastAPI route `backend/app/api/portfolio.py:130`.
  - No SSR: dashboard remains `"use client"` `frontend/components/portfolio/PortfolioDashboard.tsx:1`; `frontend/app/layout.tsx` / `frontend/lib/api.ts` not in diff.
  - Cache-first: `force_refresh=False` `backend/app/api/portfolio.py:160`.
  - No browser market APIs: FE `fetch` to `/api/portfolio/export` `frontend/lib/portfolio.ts:242-250`.
  - Cognito JWKS: `Depends(get_current_user)` `backend/app/api/portfolio.py:136` → `backend/app/core/deps.py:216`.
  - FX stored-only: `fx_context=fx.get_context()` `backend/app/api/portfolio.py:161`; no `ExchangeRateClient` on export path.
- [x] Cost/budget impact ≤$50 narrative respected? Inline `Response(text/csv)` `backend/app/api/portfolio.py:177`; no S3 PUT/presign, no new env/IAM/table. **$0 extra AWS.**
- [x] Security (no secrets in frontend/Git, no presigned leak)? Filename hardcoded UTC pattern `backend/app/services/export_service.py:109-111`; injection sanitize identity fields only `backend/app/services/export_service.py:169-174`; no presigned bearer URL.

---

## 3. Code quality

- [x] Tests green + meaningful (not just `assert True`)? Re-ran: backend **17 passed** (`test_export_service.py` + `test_portfolio_export.py`); frontend **43 passed / 3 files**. Assertions check HTTP codes, CSV math, FX blanks, isolation, Blob download, `{detail: ...}` on 400 (`test_portfolio_export.py:260-261`, `portfolio.test.ts:334-346`).
- [x] File ownership respected (no edit of other BL's files)? `git diff da01d0b..HEAD` = 10 files only (`portfolio.py`, `deps.py`, `export_service.py`, two BE test files, walkthrough, `PortfolioDashboard.tsx` + test, `portfolio.ts` + test). **Not edited:** `portfolio_service.py`, `domain/portfolio_math.py`, `domain/fx_math.py`, `domain/models.py`, `adapters/dynamodb/*`, `infra/*`, `jobs/*`, `frontend/lib/api.ts`, `frontend/app/layout.tsx`, `backend/app/api/holdings.py`.
- [x] Error model `{detail: ...}` + correct HTTP codes? `400` `detail="format must be csv"` `backend/app/api/portfolio.py:142-143`; `ValidationError`/`CurrencyValidationError` → `400` `:163-166`; `401` via `get_current_user`; `200` CSV on success.

---

## 4. Issues (if request_changes)

| # | File:line | Issue | Required fix |
|---|-----------|-------|--------------|
| — | — | none | — |

---

## 5. Decision

- **If approve:** Orchestrator may merge branch `feat/BL-027-portfolio-csv-export` → `integration/*` or `main`, mark backlog `done`.
- **If request_changes:** Implementor to address issues in same worktree, re-run tests, update walkthrough, re-request review. No new worktree.

**Verdict: `approve`.** Orchestrator may mark `docs/backlog/features/BL-027-portfolio-csv-export.md` `done` and merge. Do not implement `?delivery=presigned` as a follow-up on this BL unless a new ticket is opened.

---

## 6. Notes for Orchestrator

Accepted deviations (meet AC + locked stack):

1. `exportPortfolioCsv` returns `{ blob, filename }` (`frontend/lib/portfolio.ts:234-258`) — additive vs `Promise<Blob>`; uses `Content-Disposition`.
2. No toast library; inline `role="status"` banner (`PortfolioDashboard.tsx:350-365`).
3. CSV injection sanitize on identity fields only (`export_service.py:169-174`); leading `-` on PnL preserved (`test_csv_injection_prefix_on_symbol_only` `:191-214`). CSV contract has no `note` column.
4. `?delivery=presigned` **not** implemented — correct (Research Option A / Design D1 lock).
5. `GET /api/holdings/export` left unchanged.

Walkthrough file:line claims **exist** (spot-checked). Minor range drift only: `portfolio.ts` helpers continue through `:259`; `test_export_service.py` last test ends `:290` vs claimed `:287`. Pytest evidence matches this review run (`17 passed` targeted; FE `43 passed`).

Non-blocking nits (do not block `done`): `_dec_2dp` (`export_service.py:65-76`) uses `format(d,"f")` not 2dp — display cols use `_dec_display_2dp` (`:81-88`) which is what AC/BL-012 require; `_fx_rate_for_line` (`:114-136`) reads `view.fx_rates` instead of `FxContext.rate()` but stays on the stored snapshot.
