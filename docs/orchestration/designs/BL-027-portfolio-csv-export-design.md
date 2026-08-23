# SA Design — BL-027: Portfolio CSV export (authenticated, FX-aware)

| Field | Value |
|-------|-------|
| **ID** | `BL-027` |
| **Title** | Export portfolio → CSV (display-currency, presigned vs inline decision) |
| **Status** | `ready_for_implementation` |
| **Author (SA)** | Solution Architect (Muse Spark) |
| **Date** | 2026-08-23 |
| **Revised** | 2026-08-23 (after Research) |
| **Complexity** | `complex` (Research complete) |
| **Research** | `docs/orchestration/research/BL-027-portfolio-csv-export-research.md` — **Recommendation adopted: inline `text/csv` locked as canonical; S3 presigned as opt-in extension** |
| **Related PRD** | `docs/prd/OpenPortfo_PRD.md#6.2` (S3 Export holdings CSV), `docs/prd/OpenPortfo_PRD.md#8.5` (Portfolio & pricing), `docs/prd/OpenPortfo_PRD.md#8.8.1` + `#10.1` (ExchangeRates entity) |
| **Related Arch** | `docs/architecture-design.md#3.0` (Full system diagram), `docs/architecture-design.md#4.1` (Feature→API map), `docs/architecture-design.md#4.3` (Data model), `docs/architecture-design.md#12` (Locked stack: no API GW / no SSR / Beanstalk FastAPI / S3+CloudFront) |
| **Feature file** | `docs/backlog/features/BL-027-portfolio-csv-export.md` |

---

## 1. Context & constraints

- Problem / user value (1 paragraph, from feature file): Users track holdings in OpenPortfo but have no portable export. They need one-click CSV of current portfolio (`symbol, assetType, qty, avgCost, price, marketValue, costBasis, pnl, pnlPercent, allocation, currency, fxRateUsed, asOf`) in their **display currency** (FX-aware, same stored rates as `GET /portfolio`) for spreadsheets/tax, and the feature proves the S3 + presigned vs inline delivery tradeoff for the demo rubric (Storage category).

- Locked stack constraints:
  - No API Gateway for user APIs (Beanstalk FastAPI only) — `docs/architecture-design.md#12`, `backend/app/main.py:41-60`
  - No Next.js SSR (CSR/static export → S3+CloudFront) — `docs/prd/OpenPortfo_PRD.md#8.11`, `frontend/app/portfolio/page.tsx:1-5`
  - No browser-direct market APIs (server-side only: CoinGecko/vnstock via `MarketService`) — `docs/prd/OpenPortfo_PRD.md#5.4`
  - Cache-first pricing, on-demand FX only (admin `POST /admin/fx/refresh`; portfolio reads stored rates only) — `backend/app/api/portfolio.py:128-166` (`get_portfolio` uses `FxService.get_context()` + `PortfolioService` reads `ExchangeRateRepo.get_latest` only, never `ExchangeRateClient`), `backend/app/services/fx_service.py:86-107`, `docs/prd/OpenPortfo_PRD.md#8.5 FR-P9/P10`
  - Cognito JWT verification via JWKS (`Authorization: Bearer <Cognito ID token>`; `fake:<user>` in dev) — `backend/app/core/deps.py:214-254` (`get_current_user`), `backend/app/ports/auth.py`
  - Thin wrappers: no `boto3`/`httpx` outside `adapters/` — `docs/prd/OpenPortfo_PRD.md#8.11` / `docs/architecture-design.md#15.1`

- Current portfolio routes to extend (not replace): `backend/app/api/portfolio.py:128` `GET /api/portfolio`, `:169` `POST /api/portfolio/refresh`, `:213` `GET /api/portfolio/performance` — all auth-required, query `currency`/`displayCurrency` resolved via `backend/app/services/currency_service.py:75-95` (`resolve_currency`, `SUPPORTED_CURRENCIES={"VND","USD","EUR"}:21-25`).

---

## 2. Affected surfaces

| Layer | Paths / components | Change type |
|-------|--------------------|-------------|
| Frontend | `frontend/app/portfolio/page.tsx:1-5` (page shell) | **no direct edit** — hosts dashboard |
| Frontend | `frontend/components/portfolio/PortfolioDashboard.tsx:1-344` (add Export CSV button near Refresh `~274-288`, loading spinner, toast) | **modify** |
| Frontend | `frontend/lib/portfolio.ts:1-339` (add `exportPortfolioCsv()` client, reuse `apiBase():frontend/lib/api.ts:10-13`, `bearerHeader:frontend/lib/auth.ts`) | **modify** |
| Frontend | `frontend/lib/api.ts:1-80` | **no change** (keep `apiBase`/`displayCurrencyQuery` only) |
| Frontend | `frontend/components/portfolio/PortfolioDashboard.test.tsx` (new or extend) + `frontend/lib/portfolio.test.ts` | **new/modify tests** |
| Backend API | `backend/app/api/portfolio.py:1-227` (new `GET /api/portfolio/export` handler) | **modify** — single route, same file as `get_portfolio`/`refresh_portfolio` |
| Backend API | `backend/app/main.py:20,50` (`portfolio_router` already included, no new router registration) | **no change** |
| Domain / services | `backend/app/services/portfolio_service.py:100-201` (`PortfolioService.get_portfolio`, `PortfolioView`, `holding_record_to_domain:48-59`) | **reuse** (no edit) |
| Domain / services | `backend/app/domain/portfolio_math.py:43-150` (`compute_native_portfolio`, `pnl_percent:27-31`), `backend/app/domain/fx_math.py:47-188` (`get_rate`, `apply_fx`), `backend/app/domain/models.py:68-111` (`PortfolioLine`, `PortfolioSummary`) | **reuse** |
| Domain / services | `backend/app/services/currency_service.py:23-95` (`SUPPORTED_CURRENCIES`, `resolve_currency`, `FxContext`, `fx_context_from_stored:170`), `backend/app/services/fx_service.py:86-107` (`FxService.get_context`) | **reuse** |
| Domain / services | `backend/app/services/export_service.py` (**NEW** — pure CSV renderer, FX-aware, 2-decimal formatting per BL-012) | **new** |
| Ports | `backend/app/ports/holdings.py:58-116` (`HoldingsRepo`), `backend/app/ports/price_cache.py:52-73` (`PriceCacheRepo`, `CachedPrice`), `backend/app/ports/fx.py:53-72` (`ExchangeRateRepo.get_latest`), `backend/app/ports/storage.py:8-25` (`ObjectStorage`) | **reuse**; `ObjectStorage` evaluated for presigned branch, new method only if Research mandates S3 path (see D1) |
| Adapters | `backend/app/adapters/memory/holdings.py:26-145`, `backend/app/adapters/memory/price_cache.py:24-93`, `backend/app/adapters/memory/fx.py:17-85`, `backend/app/adapters/memory/storage.py:9-50` | **reuse fakes for tests** |
| Adapters | `backend/app/adapters/s3/storage.py:12-72` (`S3ObjectStorage` — `put_json`/`get_json`; presigned via `generate_presigned_url` if Research picks S3) | **conditional extend** (only inside adapter, see D1) |
| Adapters | `backend/app/adapters/dynamodb/holdings.py`, `backend/app/adapters/dynamodb/price_cache.py`, `backend/app/adapters/dynamodb/fx.py` | **no new table, no change** |
| Core wiring | `backend/app/core/deps.py:272-524` (`get_portfolio_service`, `get_fx_service`, `get_holdings_repo`, `get_market_service`, `get_exchange_rate_repo`, `get_object_storage:533-554`) + add `get_export_service()` | **modify** (DI factory for export service) |
| Infra / jobs | `infra/*`, `backend/app/jobs/*` | **none** |
| Docs / tests | `backend/tests/unit/api/test_portfolio_export.py` (**NEW**), `backend/tests/unit/services/test_export_service.py` (**NEW**), `backend/tests/conftest.py`, `backend/tests/fakes/*` (reuse `InMemoryHoldingsRepo`, `InMemoryPriceCacheRepo`, `InMemoryExchangeRateRepo`) | **new tests** |
| Docs | `docs/orchestration/research/BL-027-research.md` (Researcher output) | **new** |

---

## 3. API & data model deltas

### 3.1 API

| Method & path | Auth | Request | Response | Notes |
|---------------|------|---------|----------|-------|
| `GET /api/portfolio/export?format=csv&displayCurrency=USD\|VND\|EUR` (canonical `currency` alias also accepted via `resolve_currency:backend/app/services/currency_service.py:75`) | Cognito JWT (`get_current_user:backend/app/core/deps.py:214`) — `fake:<user>` in dev | Query: `format` **required** = `csv` (else 400), `currency`/`displayCurrency` optional (validated `SUPPORTED_CURRENCIES`, `CurrencyValidationError:backend/app/services/currency_service.py:29`), `assetType` optional `crypto\|stock` (reuse `_normalize_asset_type_filter:backend/app/services/portfolio_service.py:85`) | **Inline (locked default pending Research):** `200 text/csv; charset=utf-8`, headers `Content-Disposition: attachment; filename="openportfo-portfolio-YYYYMMDD.csv"` and `X-FX-Status: fresh\|missing\|stale_ok` + `X-FX-As-Of` (ISO), body CSV rows (see §3.2). **Presigned alternative (Research evaluates):** `200 application/json` `{ url, filename, expiresAt, fxStatus }` or `302` to presigned URL; SA default is **inline** unless Research justifies Storage rubric gain | Scoped to caller `user.user_id` (AC5). No live FX call — reuses `FxService.get_context():backend/app/services/fx_service.py:105`. Errors: `401` unauthenticated, `400` invalid `format`/`currency`/`assetType` (maps `ValidationError`/`CurrencyValidationError` → 400 like `backend/app/api/portfolio.py:154`), `502` only if MarketService refresh path fails (not for export cache path). Existing routes `GET /api/portfolio:128`, `POST /api/portfolio/refresh:169` unchanged |
| `GET /api/portfolio` | Cognito JWT | `currency`/`displayCurrency` | JSON `PortfolioView` | Reference for CSV row math parity (AC1) |
| `POST /api/portfolio/refresh` | Cognito JWT | same | JSON | Not called by export; export is cache-only (same PriceCache TTL as `MarketService:backend/app/core/deps.py:405`) |

CSV contract (header row, exact order): `symbol,assetType,assetId,qty,avgCost,currency,avgCostDisplay,price,priceDisplay,marketValue,costBasis,marketValueDisplay,costBasisDisplay,pnl,pnlDisplay,pnlPercent,allocation,currency_display,fxRateUsed,fxStatus,asOf` — first 13 columns map 1:1 to `PortfolioLine` fields in `backend/app/domain/models.py:68-94` + `backend/app/api/portfolio.py:58-82` (`_line_to_dict`); `allocation` from `apply_fx:backend/app/domain/fx_math.py:178-186`; `fxRateUsed` per-line `FxContext.rate(src,target):backend/app/services/currency_service.py:133`; `fxStatus` = `summary.fx_status` (`missing`/`fresh`/`stale_ok`); `asOf` = `PortfolioView.as_of:backend/app/services/portfolio_service.py:40-45`. Formatting: `Decimal` → `format(d,"f")` with **2-decimal** display via BL-012 policy (`frontend/lib/number-format.ts` precedent; BE uses same `quantize` or `format` with 2dp for monetary columns — see D2). Empty portfolio → header only `200` (AC6).

Presigned S3 variant (if Research selects): `PUT` temp object `exports/{userId}/openportfo-portfolio-YYYYMMDD-HHmmss.csv` via `ObjectStorage` port, then presigned GET `expires_in=300s` with `ResponseContentDisposition: attachment; filename=...` — IAM via Beanstalk instance profile (`s3:PutObject`, `s3:GetObject` scoped to `exports/*`).

### 3.2 Data model

```
Entity: PK / SK / attrs — NO NEW ENTITY
Holdings:      PK userId, SK HOLD#{assetType}#{symbol} — qty, avgCost, currency, assetId, note — via HoldingsRepo.list(userId):backend/app/ports/holdings.py:61
PriceCache:    PK {assetType}#{symbol} — price, currency, asOf, expiresAt — via PriceCacheRepo.get/put through MarketService.get_quotes(force=False) — cache-first, same TTL as GET /portfolio
ExchangeRates: PK FX, SK LATEST (or embedded) — base, rates map (USD_VND,…), provider, asOf, status — via ExchangeRateRepo.get_latest():backend/app/ports/fx.py:56; never cleared on failed refresh (mark_refresh_failure)
```

- DynamoDB: **no new table / no new entity** — reuse `openportfo-holdings`, `openportfo-price-cache`, `openportfo-fx` (table names `backend/app/core/config.py:190-197`). Export reads only.
- S3 layout: **inline path = $0 extra, no S3 object**. Presigned path (if Research picks) = ephemeral `s3://{DATA_BUCKET}/exports/{userId}/openportfo-portfolio-YYYYMMDD.csv` (TTL via presigned expiry, lifecycle delete after 7d). No Athena partition.
- Schemas (`backend/app/api/portfolio.py`): no Pydantic body; query params validated via `resolve_currency` + `ValidationError`. Response is `StreamingResponse`/`Response(media_type="text/csv")` with `Content-Disposition`.

---

## 4. Sequence (happy path)

```
User → Frontend → FastAPI (Beanstalk) → Ports → Adapters → DynamoDB/S3 → External (none on this path)
```

ASCII sequence:

```
1. User picks displayCurrency (USD/VND/EUR) on PortfolioDashboard → clicks [Export CSV]
       Frontend: frontend/components/portfolio/PortfolioDashboard.tsx:274-288
2. Frontend calls GET /api/portfolio/export?format=csv&currency=VND
       frontend/lib/portfolio.ts:exportPortfolioCsv() → fetch(apiBase()+path, {Authorization: Bearer <Cognito>})
       with Accept: text/csv, cache:no-store
3. FastAPI auth: get_current_user() verifies JWT (Cognito JWKS / FakeTokenVerifier)
       backend/app/core/deps.py:214-254 → UserProfile(user_id, role)
4. Handler: GET /api/portfolio/export validates format==csv else 400
       backend/app/api/portfolio.py:NEW (~128-style) → resolve_currency(currency, displayCurrency, preferred)
       (preferred = normalize_stored_currency(user.preferred_currency) || admin default — same as get_portfolio:138)
5. Route obtains request FX snapshot once: FxService.get_context()
       backend/app/services/fx_service.py:105 → fx_context_from_stored(repo.get_latest())
6. PortfolioService.get_portfolio(user_id, display_currency, fx_context, force_refresh=False, asset_type?)
       backend/app/services/portfolio_service.py:113-201 → holdings.list(userId), market.get_quotes(keys, force=False)
       → compute_native_portfolio() → apply_fx(display) → PortfolioView(summary, fx_rates, asOf)
       [No ExchangeRateClient call — stored rates only; same branch as GET /portfolio]
7a. Inline path (default): ExportService.renderCsv(view)
       backend/app/services/export_service.py:NEW → stdlib csv.writer(StringIO, lineterminator="\r\n")
       rows: sorted by assetType,symbol; money as Decimal strings 2dp; fxRateUsed = FxContext.rate(line.currency, display)
       missing FX pair → converted columns blank, header X-FX-Status=missing (AC3)
8a. FastAPI returns Response(content=csv, media_type="text/csv; charset=utf-8",
       headers={Content-Disposition: attachment; filename="openportfo-portfolio-20260823.csv", X-FX-Status})
       Browser downloads file without reload.

7b./8b. Presigned path (if Research selects, alternative):
       7b. Service renders CSV then ObjectStorage.put_object(key, csv) via adapter
            backend/app/ports/storage.py:8 + backend/app/adapters/s3/storage.py:12 (new generate_presigned_url)
       8b. Return JSON {url: presigned, expiresAt, filename, fxStatus} (or 302)
            Frontend follows URL → S3 direct download
```

Edge branches (same response codes as §3.1):
- Empty holdings → Csv header only `200` (compute_native_portfolio → empty lines, header from ExportService).
- `fx.status=missing` and native≠display → converted columns empty, `X-FX-Status: missing`, no provider HTTP call.
- `format≠csv` → `400 {detail:"format must be csv"}`; `currency` unsupported → `400` via `CurrencyValidationError`.
- `Authorization` missing/invalid → `401` via `get_current_user`.
- Other user's holdings never included — `HoldingsRepo.list(user_id)` scoping (AC5).

---

## 5. Decisions (ADR style)

| # | Context | Decision | Consequence | Alternatives rejected |
|---|---------|----------|-------------|-----------------------|
| D1 | PRD S3 stretch requires proof of S3 usage; FE needs one-click CSV for ≤100 holdings. Inline `text/csv` is $0 extra, simpler, no IAM, testable with `TestClient` + `InMemory*` fakes. S3 presigned gives stronger Storage rubric narrative (bucket, IAM, lifecycle) but adds S3 PUT + presigned GET latency, bucket/credentials, and a new `ObjectStorage.generate_presigned_url` port method (currently port is `get_json/put_json/list_keys/ping:backend/app/ports/storage.py:8-25` only). Need research to weigh marks vs cost/complexity under $50 budget (`docs/prd/OpenPortfo_PRD.md#5.6`, `docs/architecture-design.md#8`). | **Default inline `text/csv` streaming; evaluate S3 presigned as opt-in via Research Q1/Q2. SA locks inline unless Research shows presigned materially improves rubric without breaking locked decisions.** Adapter change isolated to `backend/app/adapters/s3/storage.py` + port extension, never in `services/api` (thin-wrapper rule). | Fast path: zero infra change, no `DATA_BUCKET` required, unit tests deterministic (no S3). Presigned path, if later adopted, is additive (return JSON vs CSV) behind same route/query flag. | A: Always S3 presigned — rejected as default because it violates YAGNI for MVP, adds IAM + eventual-consistency risk, slower for ≤100 rows. B: Dual mode switch at runtime — deferred; Research to define flag only if presigned wins. |
| D2 | CSV generation must be deterministic, 2-decimal formatting (BL-012), handle commas/quotes/newlines in notes, UTF-8, cross-platform line endings, and not introduce extra deps. | **Python stdlib `csv` + `io.StringIO` (liner `"\r\n"`, `quoting=QUOTE_MINIMAL`, `utf-8` without BOM), money formatted via `format(d,"f")` quantized to 2dp (same as `backend/app/api/portfolio.py:42-45` `_dec_str` → extend to 2dp for display).** No `pandas`/`openpyxl`. | Zero dep, testable offline, escaping correct, aligns with existing `Decimal` money style. Streaming via `StringIO.getvalue()` for ≤100 rows; for larger would switch to generator without API change. | A: Manual string join — rejected (quote/escape bugs, CSV injection). B: `pandas.to_csv` — rejected (heavy dep, cost, not needed for P1/P2 stretch S3). |
| D3 | FX must reuse stored rates, never call `ExchangeRateClient` on export, and signal missing conversion cleanly. `GET /portfolio` already does this via `FxService.get_context:backend/app/services/fx_service.py:105` + `PortfolioService.apply_fx:backend/app/domain/fx_math.py:82-188` with `fx_status` (`missing`/`fresh`/`stale_ok`). | **Reuse `FxService.get_context()` + `PortfolioService.get_portfolio(... fx_context ...)` path; CSV leaves converted columns blank when `FxContext.rate(src,dst) is None:backend/app/services/currency_service.py:133`, and sets `X-FX-Status: missing` header + `fxStatus` column value. No `ExchangeRateClient` import in portfolio/export code (verify like `backend/tests/unit/api/test_portfolio.py:268-282`).** | Parity with `GET /portfolio` math (AC1/AC2), zero external HTTP, fallback identical (`native columns filled, converted blank`). | A: Re-fetch FX live on export — rejected (violates FR-P10, D3 locked). B: Omit native columns when FX missing — rejected (loses data; PRD says native kept). |
| D4 | Auth isolation + filename UX. | **Auth via existing `get_current_user` (Cognito JWKS), filename `openportfo-portfolio-YYYYMMDD.csv` with `Content-Disposition: attachment` (RFC 6266, ascii fallback).** Date UTC, padded. | Isolation guaranteed by `HoldingsRepo.list(user_id)`; filename matches spec `docs/backlog/features/BL-027-portfolio-csv-export.md:71`. | A: Custom token param — rejected (insecure). B: User-supplied filename — rejected (path injection). |

---

## 6. Complexity assessment

- [x] Requires choosing between ≥2 libs/patterns → Researcher needed (inline `text/csv` vs S3 presigned URL; stdlib `csv` vs pandas; `StreamingResponse` vs `Response`)
- [x] Security / auth / cost-critical AWS path (S3 presigned IAM, `DATA_BUCKET` scope, `s3:PutObject`/`s3:GetObject` least-privilege, `Content-Disposition` presigned signing, cost ≤$50)
- [x] No prior port/adapter pattern to reuse (`ObjectStorage` port today has `get_json/put_json/list_keys/ping` only — `generate_presigned_url`/`put_bytes` not present; need research to extend port without leaking `boto3` to services)
- [x] Risk to locked decisions (if presigned chosen must still keep cache-first pricing, stored-FX-only, no browser market FX, no API GW, no SSR)

**Verdict:** `complex`

**If complex, research questions:**

1. **Inline `text/csv` vs S3 presigned URL for OpenPortfo export (≤100 holdings):** latency/TTFB, memory vs S3 cost (PUT+GET, storage), BE lifetimes (Beanstalk `t3.micro`), CloudFront/S3 CORS, presigned expiry (`expires_in` 60–900s), testability with `TestClient` vs mocked `boto3`, and rubric tradeoff (Storage evidence: inline=$0 vs presigned proves Storage category). Which default maximizes demo marks under $50?
2. **S3 presigned generation pattern behind `ObjectStorage` port:** required port method signature (`generate_presigned_url(key, expires_in, content_disposition, content_type)` vs `put_bytes`+`presign`), `boto3.client('s3').generate_presigned_url('get_object', Params={Bucket,Key,ResponseContentDisposition})` usage, least-privilege IAM for Beanstalk role (`s3:PutObject` scoped to `exports/{userId}/*`), adapter test fake (`InMemoryObjectStorage` presigned stub), and error handling (bucket missing → 502 vs 200 inline).
3. **Python CSV generation idioms for FastAPI:** `csv.writer` + `io.StringIO` vs streaming `StreamingResponse` generator with `yield`, `lineterminator="\r\n"` vs `"\n"`, `quoting=QUOTE_MINIMAL`, UTF-8 vs UTF-8-sig (BOM) for Excel, 2-decimal `Decimal` quantize consistency with BL-012, header `fxStatus` vs `X-FX-Status` signaling, and CSV injection (`=HYPERLINK`) mitigation — what pattern keeps `services/` pure and testable?

---

## 7. Handoff to Implementor

### File ownership

- Allowed to edit:
  - `backend/app/api/portfolio.py` (add `GET /api/portfolio/export` only — follow `get_portfolio:128` pattern for auth/query/FxContext)
  - `backend/app/services/export_service.py` (**new** — owns `render_portfolio_csv(view: PortfolioView) -> str`, helpers `_csv_row`, `csv_filename()`)
  - `backend/app/core/deps.py` (add `get_export_service()` factory; if Research picks presigned, add `generate_presigned_url` to `ObjectStorage` port wiring)
  - `backend/app/ports/storage.py` (only if Research mandates presigned — add `generate_presigned_url`/`put_bytes` abstract methods, keep `boto3` out of callers)
  - `backend/app/adapters/s3/storage.py` (only if presigned — implement new port method via `boto3` confined here)
  - `backend/app/adapters/memory/storage.py` (add presigned stub for tests if needed)
  - `frontend/lib/portfolio.ts` (add `exportPortfolioCsv(displayCurrency, assetType?) => Promise<Blob>` using `apiBase():frontend/lib/api.ts:10` + `bearerHeader:frontend/lib/auth.ts`)
  - `frontend/components/portfolio/PortfolioDashboard.tsx` (add Export button, loading state `exporting`, disabled while `loading||exporting`, spinner, toast on 400/500, `URL.createObjectURL(blob)` + `a[download]` trigger without reload)
  - Tests: `backend/tests/unit/api/test_portfolio_export.py`, `backend/tests/unit/services/test_export_service.py`, `frontend/lib/portfolio.test.ts` (extend), `frontend/components/portfolio/PortfolioDashboard.test.tsx` (optional)

- Must NOT edit (owned by other active sprint/BL / locked):
  - `backend/app/services/portfolio_service.py` (reuse as-is; no formula duplication — call `get_portfolio` only)
  - `backend/app/domain/portfolio_math.py`, `backend/app/domain/fx_math.py`, `backend/app/domain/models.py` (pure, already correct)
  - `backend/app/adapters/dynamodb/*` (no new table)
  - `backend/app/core/config.py` (no new env unless Research mandates `EXPORT_S3_BUCKET` — reuse `DATA_BUCKET` if presigned)
  - `frontend/app/layout.tsx`, `frontend/components/AppShell.tsx`, `frontend/lib/api.ts` (keep `apiBase` stable)
  - `infra/*`, `backend/app/jobs/*` (no scheduled export)
  - No `boto3`/`httpx` outside `adapters/` — enforced in review via `grep -R "boto3\|httpx" backend/app/services backend/app/api backend/app/domain`

### TDD order

1. **Test: `backend/tests/unit/services/test_export_service.py` — pure CSV shape (AC1, unit, no HTTP)**
   - Empty portfolio → header only.
   - One holding (BTC `qty=1`, `avgCost=30000 USD`, `price=40000 USD` via `PriceQuote`) → row math: `marketValue=40000`, `costBasis=30000`, `pnl=10000`, `pnlPercent=0.333...`, `allocation=1.0`. Compare `PortfolioService.get_portfolio` TotalsDisplay parity.
   - `marketValueDisplay`/`avgCostDisplay` 2dp formatting; commas/quotes escaped; `\r\n` lines.

2. **Test: `backend/tests/unit/services/test_export_service.py` — FX conversion (AC2)**
   - Seed `InMemoryExchangeRateRepo` with `StoredRates(base=USD, rates={USD_VND=25000}, asOf=..., status=fresh)` then `export_service.render_csv(view with display=VND)` — asserts `marketValueDisplay=1000000000` etc., uses `fx_math.get_rate:backend/app/domain/fx_math.py:47` same path.

3. **Test: `backend/tests/unit/services/test_export_service.py` — missing FX (AC3)**
   - `StoredRates=None` or `status=missing`, `displayCurrency=VND` with native USD holding → native columns filled, converted columns empty string, `fxStatus=missing` column, no provider call.

4. **Implement: `backend/app/services/export_service.py`**
   - `def render_portfolio_csv(view: PortfolioView) -> str` using `csv.writer(StringIO, quoting=QUOTE_MINIMAL, lineterminator="\r\n")`, `Decimal` 2dp via `quantize(Decimal("0.01"))` or `format(d,"f")`, `FxContext.rate` for `fxRateUsed`. Pass steps 1-3.

5. **Test: `backend/tests/unit/api/test_portfolio_export.py` — auth & isolation (AC4/AC5)**
   - `401` when no `Authorization`.
   - Setup via `tests/fakes/holdings.py`/`price_cache.py`/`fx.py` + `set_*_repo` pattern like `backend/tests/unit/api/test_portfolio.py:69-121` (`_make_client`), then `GET /api/portfolio/export?format=csv` → `200 text/csv`, `Content-Disposition` regex `openportfo-portfolio-\d{8}.csv`, `X-FX-Status` present.
   - Two users A/B, holdings for each → A export contains only A's symbols.

6. **Test: `backend/tests/unit/api/test_portfolio_export.py` — empty (AC6), bad format (400), currency validation (400)**
   - Empty holdings → header only.
   - `?format=json` → `400`.
   - `?format=csv&currency=JPY` → `400` ( JPY not in `SUPPORTED_CURRENCIES`).

7. **Implement: `backend/app/api/portfolio.py` — `GET /api/portfolio/export` + `backend/app/core/deps.py: get_export_service` wiring**
   - Follow `get_portfolio:128-166` structure: `get_current_user`, `get_portfolio_service`, `get_fx_service`, `resolve_currency`, `svc.get_portfolio(..., fx_context=fx.get_context())`, then `ExportService(view)` → `Response` with `media_type="text/csv; charset=utf-8"` and headers. Map `ValidationError`/`CurrencyValidationError` → `400`, `UnauthorizedError` already `401`.

8. **Test: `frontend/lib/portfolio.test.ts` + `frontend/components/portfolio/PortfolioDashboard.test.tsx` (AC7)**
   - Mock `fetch` → `exportPortfolioCsv` returns `Blob` with `text/csv`.
   - Dashboard: Export button exists near Refresh (`getByRole("button", {name:/export/i})`), click → `fetch` called with `format=csv`, loading spinner shows, blob URL created, `a.click` triggered without reload, toast on 400.

9. **Implement: `frontend/lib/portfolio.ts` + `frontend/components/portfolio/PortfolioDashboard.tsx`**
   - `exportPortfolioCsv`: `fetch(apiBase()+"/api/portfolio/export?"+portfolioQuery(...)+ "&format=csv", {headers:{...bearerHeader(token), Accept:"text/csv"}})`, on `!ok` throw `PortfolioApiError`, on ok `await res.blob()` then `return blob`. Keep `cache:no-store`.
   - Dashboard: `const [exporting,setExporting]=useState(false)`, handler `onExport = async ()=>{setExporting(true); try{blob=await exportPortfolioCsv(...); url=URL.createObjectURL(blob); a.download=filenameFromContentDisposition||...; a.href=url; a.click(); URL.revokeObjectURL(url); toast.success}`.

10. **Verification: run `cd backend; pytest -q` (must include new `test_portfolio_export.py` + `test_export_service.py`), `cd frontend; npm run lint; npm run test -- lib/portfolio Dashboard`; manual curl `curl -H "Authorization: Bearer fake:alice" "http://localhost:8000/api/portfolio/export?format=csv&displayCurrency=VND" -i` → `text/csv` + header; confirm no `boto3` bleed `grep -R boto3 backend/app/services backend/app/api`. Write `docs/orchestration/walkthroughs/BL-027-walkthrough.md` per template.

### Out-of-scope guardrails

- Do **not** call `ExchangeRateClient` / ExchangeRate-API on export path — stored rates only (mirror `backend/tests/unit/api/test_portfolio.py:268-282` wiring check).
- Do **not** add new DynamoDB entity/table — reuse `HoldingsRepo`/`PriceCacheRepo`/`ExchangeRateRepo`.
- Do **not** implement scheduled export, email attachment, Athena query, multi-sheet Excel/PDF, admin/global export (user-scoped only), intraday PnL history — feature file §Out of scope.
- Do **not** introduce new deps (`pandas`, `openpyxl`) — stdlib `csv` only.
- Do **not** change `backend/app/main.py` router registration beyond existing `portfolio_router`.
- Do **not** use Next.js SSR or browser-direct market APIs.
- Do **not** store large CSV durably in DynamoDB; if presigned, S3 ephemeral only with lifecycle.
- Keep CSV columns additive — do not rename existing `GET /portfolio` JSON fields.

---

## 8. Acceptance criteria checklist (copy from feature file)

- [ ] **AC1** Given an authenticated user with holdings, When they `GET /portfolio/export?format=csv&displayCurrency=USD`, Then response is `text/csv` (or JSON presigned wrapper — one locked choice) with correct headers and rows match `GET /portfolio` math (qty*price, allocation, etc.) — file:line `backend/tests/unit/api/test_portfolio_export.py`.
- [ ] **AC2** Given displayCurrency differs from native, When FX stored rate exists, Then converted `marketValue_D`/`costBasis_D` equals native * rate (same `fx_math` as portfolio service) — unit test `test_portfolio_export_fx_conversion`.
- [ ] **AC3** Given no stored FX rate, When displayCurrency != native, Then CSV includes native values, converted columns empty/`null`, and response header or CSV comment indicates `fxStatus=missing` without live FX call.
- [ ] **AC4** Given unauthenticated request, Then 401.
- [ ] **AC5** Given another user's holdings exist, When user A exports, Then only A's holdings appear (isolation).
- [ ] **AC6** Given empty portfolio, Then 200 with header only.
- [ ] **AC7** Frontend: Export button triggers download without page reload; shows loading → success/error toast.
- [ ] **AC8** No `boto3` outside `adapters/`; if S3 path chosen, presigned via `ObjectStorage` port adapter.

---

## 9. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Inline CSV memory for 100 holdings negligible but presigned tempting for rubric Storage marks | Lock inline default; Research quantifies marks vs cost — presigned additive only if justified |
| FX missing trips `apply_fx` returning native-only summary → display totals None (`backend/app/domain/fx_math.py:108-114`) | ExportService tolerates `marketValueDisplay is None` → blank converted cols, `X-FX-Status: missing` |
| `boto3` leak outside adapters breaks thin-wrapper rule | Review gate: `grep -R "boto3\|botocore" backend/app/services backend/app/api backend/app/domain` must be empty; confine to `backend/app/adapters/s3/storage.py` |
| `Content-Disposition` filename injection or non-ascii | Sanitize via hardcoded `openportfo-portfolio-YYYYMMDD.csv`, UTC date, `quote` filename only ascii digits/hyphens |
| Cache staleness: export uses stale `PriceCache` | Documented: same TTL as `GET /portfolio` via `MarketService`; export is snapshot, not `force` refresh (separate `POST /portfolio/refresh` if need fresh) |
| Excel CSV quirks (comma, newline, `=cmd`) | `csv.QUOTE_MINIMAL` + sanitize `note` leading `=+-@` by prefixing `'` or quoting (injection mitigation) |

---

## 10. Research linkage

- Research doc: `docs/orchestration/research/BL-027-portfolio-csv-export-research.md` — **verified 2026-08-23, 8 sources fetched, no hallucinated links**.
- **Recommendation adopted:** **Option A inline `text/csv` via `csv.writer` + `io.StringIO` + `Response`** locked as canonical `GET /api/portfolio/export?format=csv` (200 `text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="openportfo-portfolio-YYYYMMDD.csv"`, `X-FX-Status`/`X-FX-As-Of`). S3 presigned (Option C) retained as documented **opt-in** (`?delivery=presigned`, 300s expiry, per-user prefix) — not default — because Storage 3-pt mark already satisfied by S3 frontend + snapshots/history (`docs/architecture-design.md#3.3`), and inline is $0 vs ~$0.02/mo extra for demo scale. See Research §5 rationale + citations: [Python csv](https://docs.python.org/3/library/csv.html), [boto3 presigned](https://docs.aws.amazon.com/boto3/latest/guide/s3-presigned-urls.html), [FastAPI custom response](https://fastapi.tiangolo.com/advanced/custom-response/), [S3 pricing](https://aws.amazon.com/s3/pricing/), [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection), [WSTG INPV-21](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/21-Testing_for_CSV_Injection), [S3 presigned docs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html), [securing presigned blog](https://aws.amazon.com/blogs/compute/securing-amazon-s3-presigned-urls-for-serverless-applications/).
- **D1 revised per Research §6:** Lock inline `text/csv` as canonical; document S3 presigned as future `?delivery=presigned` behind `ObjectStorage.generate_presigned_url` (confined to `backend/app/adapters/s3/storage.py`, `s3v4`+`virtual`, 300s). No `ObjectStorage` port extension in MVP (keep `get_json`/`put_json`/`list_keys`/`ping` only). Update §3.1 to state rubric tradeoff explicitly.
- **D2/D3/D4 unchanged** — stdlib `csv`, `FxService.get_context()` reuse, `get_current_user` auth all validated by Research Q3.

---

**SA sign-off:** `ready_for_implementation` — Research incorporated, TDD order §7 unchanged. Implementor may proceed in worktree `D:\rmit\cloud\a3-wt-bl027` branch `feat/BL-027-portfolio-csv-export`. No backend code edited by SA per rule.
