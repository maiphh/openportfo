# BL-027 — Portfolio CSV export (authenticated, FX-aware)

| Field | Value |
|-------|--------|
| **ID** | `BL-027` |
| **Title** | Export portfolio → CSV (display-currency, presigned vs inline decision) |
| **Priority** | `P1` |
| **Status** | `ready` |
| **Owner (BA)** | Orchestrator demo |
| **Owner (Eng)** | TBD |
| **Requested by** | Demo examiner / user (stretch S3 in PRD) |
| **Related PRD / sprint** | PRD S3 Export holdings CSV (`S3`), sprint-05-portfolio, docs/orchestration demo |
| **Created** | 2026-08-23 |
| **Ready date** | 2026-08-23 |
| **Done date** | |

---

## 1. Problem / user value

Users track holdings in OpenPortfo but have no portable export. They need a one-click CSV of their portfolio (symbol, type, qty, avgCost, price, marketValue, pnl, allocation) in their **display currency** (FX-aware), for spreadsheets/tax. This also proves **S3 + presigned URL** vs inline generation — a good cloud-native story for the demo.

---

## 2. User story

As a **portfolio owner**, I want **to download my current portfolio as CSV in my display currency**, so that **I can analyse it offline without copy-pasting**.

---

## 3. Scope

### In scope

- `GET /portfolio/export?format=csv&displayCurrency=USD|VND` (auth required, scoped to caller `userId`)
- FX-aware: same stored FX rates as `GET /portfolio` (no live FX call)
- CSV columns: symbol, assetType, qty, avgCost (native + converted), price, marketValue, costBasis, pnl, pnlPercent, allocation, currency, fxRateUsed, asOf
- Two delivery modes to be decided by SA+Research: **inline `text/csv`** vs **S3 presigned URL** (compare)
- Frontend: button on Portfolio dashboard → downloads CSV (or follows presigned URL)
- Tests: unit for CSV shape, FX conversion, auth isolation, empty portfolio

### Out of scope

- Scheduled export, email attachment, Athena query
- Multi-sheet Excel, PDF
- Admin/global export (user-scoped only)
- Intraday PnL history in CSV (current snapshot only)

---

## 4. Behaviour

### Happy path

1. User on Dashboard picks display currency (USD/VND) → clicks **Export CSV**.
2. Frontend calls `GET /api/portfolio/export?format=csv&displayCurrency=VND` with `Authorization: Bearer <Cognito>` (or `fake:<user>` in dev).
3. Backend: load holdings → resolve prices (PriceCache, no fresh external call unless TTL logic already in portfolio service) → FX convert using stored rates → render CSV → return `text/csv` with `Content-Disposition: attachment; filename="openportfo-portfolio-YYYYMMDD.csv"` (or 302/JSON with presigned URL — SA decides).
4. Browser downloads file; CSV opens in spreadsheet with correct numbers (2-decimal formatting per BL-012).

### Edge cases / errors

- Empty portfolio → CSV with header only (200).
- No stored FX rate for conversion pair → include native columns, leave converted columns blank, header `fxStatus=missing` (same semantics as `GET /portfolio` `fx.status`).
- Unauthenticated → 401.
- Unsupported format → 400.
- Very large portfolio (100 holdings) → still inline feasible; presigned path would stream via S3.

### UX notes

- Screens / routes: Dashboard header near Refresh button; loading spinner while fetching; error toast on 400/500.
- Empty / loading / error states: button disabled while loading; empty portfolio toast "No holdings to export".
- Filename includes date: `openportfo-portfolio-2026-08-23.csv`.

---

## 5. Acceptance criteria

- [ ] **AC1** Given an authenticated user with holdings, When they `GET /portfolio/export?format=csv&displayCurrency=USD`, Then response is `text/csv` (or JSON presigned wrapper — one locked choice) with correct headers and rows match `GET /portfolio` math (qty*price, allocation, etc.) — file:line `backend/tests/unit/api/test_portfolio_export.py`.
- [ ] **AC2** Given displayCurrency differs from native, When FX stored rate exists, Then converted `marketValue_D`/`costBasis_D` equals native * rate (same `fx_math` as portfolio service) — unit test `test_portfolio_export_fx_conversion`.
- [ ] **AC3** Given no stored FX rate, When displayCurrency != native, Then CSV includes native values, converted columns empty/`null`, and response header or CSV comment indicates `fxStatus=missing` without live FX call.
- [ ] **AC4** Given unauthenticated request, Then 401.
- [ ] **AC5** Given another user's holdings exist, When user A exports, Then only A's holdings appear (isolation).
- [ ] **AC6** Given empty portfolio, Then 200 with header only.
- [ ] **AC7** Frontend: Export button triggers download without page reload; shows loading → success/error toast.
- [ ] **AC8** No `boto3` outside `adapters/`; if S3 path chosen, presigned via `ObjectStorage` port adapter.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | HoldingsRepo, PriceCacheRepo, ExchangeRateRepo (stored rates only) |
| New / changed APIs | `GET /portfolio/export` (preferred) or `POST /portfolio/export` if presigned async; SA to lock |
| Auth required? | yes (Cognito JWT) |
| Caching / freshness | Reuse same PriceCache TTL / stale logic as `GET /portfolio`; no new external calls |
| Jobs / schedules | none |
| External calls | none on this path (no CoinGecko/vnstock/ExchangeRate-API) |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `frontend/src/components/PortfolioDashboard.tsx` or `frontend/src/app/portfolio/page.tsx`, `frontend/src/lib/api.ts` |
| Backend API | `backend/app/api/portfolio.py` (new route), `backend/app/api/schemas.py` |
| Domain / services | `backend/app/services/portfolio_service.py` (reuse), new `backend/app/services/export_service.py` (if needed) |
| Adapters | `backend/app/adapters/memory/*`, `backend/app/adapters/s3/storage.py` (if presigned), `backend/app/adapters/dynamodb/*` already |
| Infra / jobs | none |
| Docs / tests | `backend/tests/unit/api/test_portfolio_export.py`, `backend/tests/unit/services/test_export_service.py` |

---

## 8. Dependencies & risks

- Depends on: BL-013 (portfolio unit FX) done, BL-012 (number format) done
- Risks / unknowns: Choice inline vs presigned S3 — presigned adds S3 bucket + IAM + latency but demonstrates Storage category more fully; inline is simpler under $50. Research needed.
- Cost: Inline = $0 extra; presigned = S3 PUT + presigned GET (~$0). Either under budget.

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Inline vs presigned S3? | open | SA + Researcher to decide (default inline unless research shows S3 presigned is stronger for rubric) |
| 2 | CSV generation lib? Stdlib `csv` vs custom | resolved | Use Python stdlib `csv` + `io.StringIO` (no extra dep) |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-23 | Demo BL-027 for orchestration cycle | Created from PRD S3 stretch |

---

## 11. Implementation notes (Eng fills after `ready`)

- Approach:
- PR / branch: `feat/BL-027-portfolio-csv-export` → worktree `D:\rmit\cloud\a3-wt-bl027`
- Verification:
