# OpenPortfo — Product Requirements Document (PRD)

| Field | Value |
|--------|--------|
| **Product** | OpenPortfo |
| **Type** | Cloud-based crypto + Vietnam stock portfolio tracker |
| **Course** | RMIT Cloud Computing — Assessment 3 |
| **Document version** | 1.3 |
| **Status** | Cognito auth (D1); FX via ExchangeRate-API on-demand admin refresh (D3 revised) |
| **Related docs** | `docs/architecture-design.md`, `docs/prd/auth-cognito.md`, `docs/proposal/OpenPortfo_Project_Proposal.md` |
| **Budget** | AWS spend ≤ **USD $50** (project period) |
| **Data style** | **On-demand** prices (no WebSocket / real-time streaming) |

---

## 1. Executive summary

OpenPortfo is a web application that gives individual investors a **single view** of cryptocurrency and Vietnam-listed stock holdings: watchlist, positions with cost basis, portfolio value and PnL, historical charts, keyword-matched market news, and an optional daily email summary.

It is built on AWS to satisfy Assessment 3 (compute, storage, CDN, database, analytics, scheduled jobs, third-party APIs) while staying under a **$50** cloud budget.

**Primary user value:** one dashboard instead of separate crypto apps, VN broker portals, and spreadsheets.

**Primary academic value:** end-to-end cloud architecture with a clear split between:

- **Request path:** Browser → CloudFront/S3 (UI) + Elastic Beanstalk/FastAPI (APIs) → DynamoDB/S3/external APIs  
- **Schedule path:** EventBridge → Lambda → DynamoDB/S3/SES (no browser traffic)

---

## 2. Goals and non-goals

### 2.1 Goals

| ID | Goal | Success signal |
|----|------|----------------|
| G1 | Unified multi-asset portfolio (crypto + VN stocks) | User can hold BTC and VNM in one portfolio view |
| G2 | On-demand valuation with caching | Portfolio loads without calling external APIs every row; Refresh forces update |
| G3 | Graphical interpretation of results | Dashboard tables + pie/allocation + history chart |
| G4 | Multi-user with auth | **Amazon Cognito** sign-up/sign-in (email + optional Google); data scoped by Cognito `sub` |
| G5 | Scheduled cloud jobs | Daily (or cron) news ingest + portfolio snapshot (+ optional email) via Lambda |
| G6 | Admin-configurable system | Admin can manage RSS sources, job flags, cache TTL, email time |
| G7 | Live deploy under budget | Public demo URL; estimated AWS ≤ $50 |
| G8 | Maintainable code | Thin repository/storage wrappers over AWS so domain logic is not full of raw `boto3` |

### 2.2 Non-goals (explicitly out of scope)

| ID | Non-goal | Reason |
|----|----------|--------|
| NG1 | Real trading / order execution | Tracker only |
| NG2 | Real-time WebSocket prices | Cost + complexity; on-demand is required style |
| NG3 | Custom password hashing in DynamoDB | Replaced by **Cognito** (passwords managed by Cognito, not app bcrypt) |
| NG4 | Fancy NLP / LLM news ranking | Keyword match only for MVP |
| NG5 | Mobile native apps | Responsive web is enough |
| NG6 | Multi-region HA / multi-AZ production | Single-region student demo |
| NG7 | Reusing Assessment 2 domain | New product domain required |
| NG8 | Multi-cloud portability day-one | AWS-first; wrappers only ease *future* migration |

---

## 3. Personas and roles

### 3.1 Personas

| Persona | Needs |
|---------|--------|
| **Individual investor (primary)** | Track crypto + VN stocks, see PnL, skim relevant news, optional daily email |
| **Demo examiner / tutor** | Live URL, clear AWS usage, charts, scheduled job evidence, architecture story |
| **System admin (demo)** | Configure RSS, jobs, email time, cache TTL without redeploying code |

### 3.2 Roles

| Role | Capabilities |
|------|----------------|
| **`user`** | Own profile, watchlist, holdings, portfolio, news (read), personal settings (keywords, email opt-in, currency preference) |
| **`admin`** | All user capabilities + `/admin` system settings, RSS source CRUD, job flags, view last job status |

**MVP assumption:** one **seeded admin** account for demo (created at deploy or via one-time script). Promoting arbitrary users to admin may be deferred.

---

## 4. Problem statement

Crypto and VN equity positions live in different apps and spreadsheets. Individuals lack a low-cost, unified view of **total value, allocation, and PnL**, plus light **news** and a simple **daily summary**, without building a full brokerage or paying for multi-product SaaS.

---

## 5. Product principles

1. **On-demand over real-time** — prices update on view/refresh or schedule, not streaming.  
2. **Cache-first** — never call CoinGecko/vnstock per table row.  
3. **Clear cloud split** — user APIs on Beanstalk; background only on Lambda.  
4. **Server-side market data** — browser never calls CoinGecko/vnstock/broker APIs directly.  
5. **Budget-aware** — smallest Beanstalk footprint; DynamoDB on-demand; Athena scans small partitions only.  
6. **Thin AWS adapters** — repositories/storage wrappers; domain code does not scatter raw `boto3`.  
7. **Demo-first** — every MVP feature appears in a 30-minute demo script.

---

## 6. Users, scope, and MVP definition

### 6.1 MVP (must ship for high mark)

| # | Feature | Priority |
|---|---------|----------|
| M1 | Cognito register / login / logout (email+password); optional Google IdP | P0 |
| M2 | Search assets (crypto + VN stock) | P0 |
| M3 | Watchlist CRUD | P0 |
| M4 | Holdings CRUD (qty + cost basis) | P0 |
| M5 | Portfolio dashboard (value, cost, PnL, PnL%, allocation pie, holdings table + filter crypto/stock) | P0 |
| M6 | Manual **Refresh** prices | P0 |
| M7 | Asset detail + historical price chart | P0 |
| M8 | News feed (keyword / symbol matched; data filled by Lambda) | P0 |
| M9 | User settings: email opt-in, personal news keywords, preferred display currency | P0 |
| M10 | Admin: RSS sources, email time, job toggles, cache TTL, **FX rates (view + Refresh)**, last job status | P0 |
| M10b | Exchange rates (ExchangeRate-API) — **admin on-demand only**; portfolio conversion uses stored rates | P0 |
| M11 | Scheduled jobs: price warm-cache and/or snapshot; news ingest | P0 |
| M12 | Snapshots to DynamoDB + S3; **Athena** used at least once (query or documented demo) | P0 |
| M13 | Live deploy: S3+CloudFront UI, Beanstalk API, Lambda jobs | P0 |

### 6.2 Stretch (nice-to-have)

| # | Feature | Priority |
|---|---------|----------|
| S1 | Daily SES portfolio email | P1 (demo-strong; low rubric marks) |
| S2 | Allocation breakdown by asset class (crypto vs VN) | P2 |
| S3 | Export holdings CSV | P2 |
| S4 | Extra base currencies / historical FX | P2 |
| S5 | Sparklines on watchlist | P3 |
| S6 | Password reset email | P3 — default **out** of MVP |

### 6.3 Explicit cuts if behind schedule

- NLP news ranking  
- Intraday charts  
- Social login  
- Dynamic EventBridge schedule updates from admin UI (prefer simpler Lambda time-window)  

---

## 7. User journeys

### 7.1 First-time investor

1. Open CloudFront URL → Sign up / Sign in via **Cognito** (email+password or Google).  
2. Search `bitcoin` (crypto) and `VNM` (stock).  
3. Add both to watchlist; add holdings with quantity and average cost.  
4. Open Dashboard → see total value, PnL, pie, table.  
5. Click **Refresh** → prices update; UI shows new `asOf`.  
6. Open asset detail → history chart.  
7. Open News → items mentioning BTC / VNM / keywords.  
8. Settings → enable email opt-in + keywords (if SES in scope).

### 7.2 Daily return visit

1. Login → Dashboard uses **PriceCache** (no external call if TTL valid).  
2. Optional Refresh.  
3. Skim News.  

### 7.3 Admin

1. Login as admin → `/admin`.  
2. Add/disable RSS URLs.  
3. Set email time + timezone; toggle news/snapshot/email jobs.  
4. Set price cache TTL (minutes).  
5. **Exchange rates panel:** view last stored rates (e.g. USD↔VND), `asOf`, source; click **Refresh rates** to call ExchangeRate-API once.  
6. If refresh fails, UI shows error and **keeps displaying previous rates** (no wipe).  
7. View last job run status / counts.  

### 7.4 Scheduled system (no user)

1. EventBridge fires cron.  
2. Lambda reads `SystemSettings` + `RssSources`.  
3. If enabled: fetch RSS → keyword match → `News`; batch prices → `PriceCache` + S3 history; snapshot users → DynamoDB + S3; optional SES.  
4. Write `JobRuns` audit row.

---

## 8. Functional requirements

### 8.1 Authentication & users (Amazon Cognito)

| ID | Requirement | Acceptance criteria |
|----|-------------|---------------------|
| FR-A1 | Cognito User Pool | App uses one User Pool + App Client (public SPA); no client secret in frontend |
| FR-A2 | Email + password auth | Sign-up / sign-in via Cognito (Hosted UI **or** Amplify/amazon-cognito-identity-js in Next.js) |
| FR-A3 | Google sign-in | Google configured as **Cognito federated IdP**; same User Pool users as email users |
| FR-A4 | Tokens | After login, client holds Cognito **ID token** (and access/refresh as needed); API calls send `Authorization: Bearer <Cognito ID token>` |
| FR-A5 | FastAPI verification | Beanstalk validates JWT against Cognito **JWKS** (iss, aud/client_id, exp, signature); invalid → `401` |
| FR-A6 | App profile | DynamoDB profile keyed by Cognito `sub` (`userId`); created on first authenticated request if missing |
| FR-A7 | Roles | `user` \| `admin` stored in **DynamoDB profile** (or Cognito custom attribute `custom:role`); admin routes → `403` if not admin |
| FR-A8 | Logout | Client signs out via Cognito (clear tokens / Hosted UI logout); subsequent API calls fail auth |
| FR-A9 | User settings | Profile fields: `newsKeywords[]`, `emailOptIn`, `preferredCurrency` (DynamoDB, not Cognito password store) |

**Passwords:** managed only by Cognito — **no** `passwordHash` in DynamoDB.  
**Password reset / email verification:** Cognito built-in (enable in User Pool).

### 8.2 Asset search

| ID | Requirement | Acceptance criteria |
|----|-------------|---------------------|
| FR-S1 | Search crypto | `GET /assets/search?q=&type=crypto` returns id/symbol/name from CoinGecko (server-side) |
| FR-S2 | Search VN stock | `type=stock` uses vnstock (or underlying public API) server-side |
| FR-S3 | Empty / short query | Clear validation error or empty list; no crash |
| FR-S4 | External failure | Graceful error message; no stack trace to client |

### 8.3 Watchlist

| ID | Requirement | Acceptance criteria |
|----|-------------|---------------------|
| FR-W1 | List watchlist | Only current user’s items |
| FR-W2 | Add item | `assetType` + `symbol` (and stable id if needed); idempotent or clear conflict |
| FR-W3 | Remove item | Item gone from list |
| FR-W4 | Prices on list | Show last known price from PriceCache when available |

### 8.4 Holdings

| ID | Requirement | Acceptance criteria |
|----|-------------|---------------------|
| FR-H1 | List holdings | Scoped by `userId` |
| FR-H2 | Create holding | Requires `assetType`, `symbol`, `qty` > 0, `avgCost` ≥ 0, `currency` |
| FR-H3 | Update holding | Can change qty, avgCost, note |
| FR-H4 | Delete holding | Removed; portfolio no longer includes it |
| FR-H5 | Validation | Reject invalid numbers / missing fields with `400` |

### 8.5 Portfolio & pricing

| ID | Requirement | Acceptance criteria |
|----|-------------|---------------------|
| FR-P1 | Portfolio aggregate | `marketValue`, `costBasis`, `pnl`, `pnlPercent`, `asOf`, per-line breakdown |
| FR-P2 | Line fields | symbol, assetType, qty, avgCost, price, marketValue, pnl, allocation % |
| FR-P3 | Cache-first | If PriceCache fresh within TTL → no external call |
| FR-P4 | Cache miss | Backend fetches CoinGecko and/or vnstock in **batch** where possible; writes PriceCache |
| FR-P5 | Manual refresh | `POST /portfolio/refresh` forces external fetch for user’s symbols (respect rate limits) |
| FR-P6 | Stale / API failure | Return last good price if present; flag `stale: true` or warning in response |
| FR-P7 | Filters | Client or API can filter holdings by `crypto` \| `stock` |
| FR-P8 | Allocation pie data | With a display currency and valid stored FX rates, pie uses **converted** market values; if no rate available, fall back to same-currency groups only |
| FR-P9 | Mixed currency + FX | API returns per-line native currency **and** optional converted fields using **stored** rates from DynamoDB (not a live FX call on each portfolio GET) |
| FR-P10 | Portfolio does not auto-call FX API | `GET /portfolio` never hits ExchangeRate-API; it only reads last cached rates |

**Formulas (server-side authoritative):**

```
Native (per line, in line currency C):
  marketValue_i = qty_i * price_i
  costBasis_i   = qty_i * avgCost_i

Converted to display currency D (using stored rates):
  rate(C→D) from ExchangeRate store (or 1 if C == D)
  marketValue_D_i = marketValue_i * rate(C→D)
  costBasis_D_i   = costBasis_i * rate(C→D)

Totals in D:
  marketValue_D = Σ marketValue_D_i
  costBasis_D   = Σ costBasis_D_i
  pnl_D         = marketValue_D - costBasis_D
  pnl%_D        = pnl_D / costBasis_D   (0 or null if costBasis_D = 0)
  allocation_i  = marketValue_D_i / marketValue_D
```

**Currency (locked — D3 revised):**

- Asset quotes remain native: crypto primarily **USD**, VN stocks **VND**.  
- **Exchange rates** come from [ExchangeRate-API](https://www.exchangerate-api.com/docs/overview) (**Standard** or **Pair** endpoint).  
- Rates are fetched **only on admin demand** (Refresh button) — **not** on a schedule, **not** on every portfolio/page load.  
- Portfolio conversion uses the **last successfully stored** rate.  
- If FX refresh fails or no rate has ever been stored: keep previous rate if any; otherwise return native subtotals only and set `fx.status = "missing" | "stale_ok" | "fresh"`.

### 8.6 History & charts

| ID | Requirement | Acceptance criteria |
|----|-------------|---------------------|
| FR-C1 | History API | `GET /assets/{id}/history?range=` e.g. `7d|30d|90d|1y` |
| FR-C2 | Cache in S3 | Prefer `s3://…/history/{assetType}/{id}/{range}.json`; fetch external only on miss |
| FR-C3 | Chart UI | Asset detail page plots series (Chart.js or Recharts) |

### 8.7 News

| ID | Requirement | Acceptance criteria |
|----|-------------|---------------------|
| FR-N1 | List news | `GET /news` returns recent items from DynamoDB |
| FR-N2 | Relevance | Prefer items matching user symbols and/or `newsKeywords` (filter server or client) |
| FR-N3 | Ingest | **Lambda only** (not on every page load): RSS → parse → keyword match → News table |
| FR-N4 | Admin RSS list | Only enabled sources are fetched |

### 8.8 Admin & system settings

| ID | Requirement | Acceptance criteria |
|----|-------------|---------------------|
| FR-AD1 | Get/put global settings | emailTime, timezone, emailEnabled, priceCacheTtlMinutes, job flags, default display currency (optional) |
| FR-AD2 | RSS CRUD | name, url, enabled |
| FR-AD3 | Job flags | `news`, `snapshot`, `email` independently toggleable |
| FR-AD4 | Last job status | Show last run time/status/counts from `JobRuns` or equivalent |
| FR-AD5 | Authorization | Non-admin cannot mutate admin resources |
| FR-AD6 | FX rates panel | Admin UI shows stored rates (minimum **USD → VND** and/or **VND → USD**), `asOf`, `provider`, last refresh status/error |
| FR-AD7 | FX Refresh (on-demand) | Admin clicks **Refresh rates** → backend calls ExchangeRate-API **once** → on success, overwrite stored rates + `asOf` |
| FR-AD8 | FX failure fallback | On API error/timeout/non-2xx: **do not delete** existing rates; return error message; keep serving old rates to portfolio |
| FR-AD9 | No auto FX jobs | EventBridge/Lambda **must not** call ExchangeRate-API on a schedule (unless product later changes this requirement) |

### 8.8.1 Exchange rates (ExchangeRate-API)

| ID | Requirement | Acceptance criteria |
|----|-------------|---------------------|
| FR-FX1 | Provider | [ExchangeRate-API](https://www.exchangerate-api.com/docs/overview) — Free plan **Standard** and/or **Pair Conversion** endpoints |
| FR-FX2 | API key | Stored in Beanstalk env (`EXCHANGE_RATE_API_KEY`), never in frontend or Git |
| FR-FX3 | MVP pairs | At least rates needed to convert between **USD** and **VND** (pair endpoint or standard base USD including VND) |
| FR-FX4 | Persistence | Last good rates in DynamoDB (e.g. `SystemSettings` or `ExchangeRates` entity) |
| FR-FX5 | Who can refresh | **Admin only** (`POST /admin/fx/refresh`) |
| FR-FX6 | Who can read rates | Authenticated users may `GET` current stored rates for UI labels; refresh remains admin-only |
| FR-FX7 | Portfolio use | Conversion uses stored rates only; document `fx.asOf` on portfolio response |
| FR-FX8 | First-run empty | Before any successful refresh: portfolio works in native currencies; conversion fields null/omitted; admin prompted to Refresh once |

### 8.9 Scheduled jobs (Lambda)

| ID | Requirement | Acceptance criteria |
|----|-------------|---------------------|
| FR-J1 | Trigger | EventBridge Scheduler cron (region lab-compatible, default **us-east-1**) |
| FR-J2 | News job | If enabled: fetch RSS → match → DynamoDB News; write JobRun |
| FR-J3 | Price job | If enabled: batch update prices for known symbols (from holdings/watchlists or top set) → PriceCache (+ optional S3 history) |
| FR-J4 | Snapshot job | If enabled: per-user portfolio snapshot → DynamoDB `PortfolioSnapshot` + S3 partition path |
| FR-J5 | Email job | **Stretch (D5):** only if SES is implemented; respect `emailEnabled`, user `emailOptIn`, and **time window** (D4) |
| FR-J6 | No public HTTP | Lambda is **not** user-facing API (no requirement for browser → Lambda) |
| FR-J7 | Email time (D4) | EventBridge runs Lambda on a **fixed frequent schedule** (e.g. hourly). Lambda reads `emailTime` + `timezone` from SystemSettings and sends only when current local time falls in the configured window (and once per user per day) |

### 8.10 Analytics (Athena)

| ID | Requirement | Acceptance criteria |
|----|-------------|---------------------|
| FR-AT1 | Snapshot files queryable | S3 layout supports partition projection or simple path filters (`userId`, `dt`) |
| FR-AT2 | Demo proof | At least one saved Athena query or UI/admin action showing SQL over snapshots (even if “run once” for demo) |

### 8.11 Frontend pages

| Page | Requirements |
|------|----------------|
| Login / Register | Forms, error states, redirect when authenticated |
| Dashboard | Totals, PnL, pie, holdings table, filter, Refresh button |
| Watchlist | List, add via search, remove |
| Add/Edit holding | Modal or page: search, qty, cost, note |
| Asset detail | Meta + history chart |
| News | Card/list with title, source, link, date |
| User settings | Keywords, email opt-in, preferred currency |
| Admin | RSS, settings, job status, **FX rates + Refresh rates button** |

**Hosting:** Next.js **static export / CSR only** (no SSR). Deploy to **S3 + CloudFront**.  
**API base URL:** environment config pointing at Beanstalk (HTTPS preferred).  
**CORS:** FastAPI allows CloudFront origin (and localhost for dev).

---

## 9. API specification (user-facing)

Base path recommendation: `/api` prefix on Beanstalk (e.g. `https://{eb-env}.elasticbeanstalk.com/api/...`).

| Group | Method & path | Auth | Description |
|-------|---------------|------|-------------|
| Auth | *(Cognito Hosted UI / client SDK)* | — | Sign-up, login, Google, logout — **not** custom FastAPI password endpoints |
| Auth | `GET /auth/me` | Cognito JWT | Ensure profile exists; return user + role + settings |
| Auth | `POST /auth/bootstrap` | Cognito JWT | Optional explicit “create profile if missing” (or fold into `/auth/me`) |
| Assets | `GET /assets/search` | Yes | Query `q`, `type=crypto\|stock` |
| Assets | `GET /assets/{id}/history` | Yes | Query `range` |
| Watchlist | `GET /watchlist` | Yes | List |
| Watchlist | `POST /watchlist` | Yes | Add |
| Watchlist | `DELETE /watchlist/{itemId}` | Yes | Remove |
| Holdings | `GET /holdings` | Yes | List |
| Holdings | `POST /holdings` | Yes | Create |
| Holdings | `PUT /holdings/{itemId}` | Yes | Update |
| Holdings | `DELETE /holdings/{itemId}` | Yes | Delete |
| Portfolio | `GET /portfolio` | Yes | Aggregated valuation |
| Portfolio | `POST /portfolio/refresh` | Yes | Force price refresh |
| News | `GET /news` | Yes | List (optional query filters) |
| Settings | `GET /settings` / `PUT /settings` | Yes | User preferences |
| Admin | `GET/PUT /admin/settings` | Admin | Global settings |
| Admin | `GET/POST/PUT/DELETE /admin/rss-sources` | Admin | RSS sources |
| Admin | `GET /admin/job-runs` | Admin | Recent job runs |
| FX | `GET /fx/rates` | Yes | Read **stored** rates + `asOf` + status (no external call) |
| FX | `POST /admin/fx/refresh` | Admin | On-demand call to ExchangeRate-API; update store on success; keep old rates on failure |
| Health | `GET /health` | No | Beanstalk health check |

**Error model (minimum):** JSON `{ "detail": "..." }` with appropriate HTTP status (`400/401/403/404/409/502`).

**Idempotency:** duplicate watchlist/holding keys should return `409` or upsert — **decide in implementation; prefer clear 409 for demo simplicity.**

---

## 10. Data requirements

### 10.1 DynamoDB entities

| Entity | Keys (logical) | Main attributes |
|--------|----------------|-----------------|
| Users (profile) | PK `userId` (= Cognito `sub`) | email, name, role, authProvider hints, newsKeywords[], emailOptIn, preferredCurrency, createdAt — **no passwordHash** |
| Holdings | PK `userId`, SK `HOLD#{assetType}#{symbol}` | qty, avgCost, currency, note, assetId, updatedAt |
| Watchlist | PK `userId`, SK `WATCH#{assetType}#{symbol}` | assetId, addedAt |
| PriceCache | PK `{assetType}#{symbol}` | price, currency, asOf, rawJson, ttl |
| News | PK `date` (YYYY-MM-DD), SK `source#{hash}` | title, url, publishedAt, symbols[], keywords[], sourceName |
| PortfolioSnapshot | PK `userId`, SK `SNAP#YYYY-MM-DD` | totalValue, totalCost, pnl, breakdown[], currencyNote |
| SystemSettings | PK `SETTINGS`, SK `GLOBAL` | emailTime, timezone, emailEnabled, priceCacheTtlMinutes, jobs{}, defaultDisplayCurrency, updatedAt, updatedBy |
| ExchangeRates | PK `FX`, SK `LATEST` (or embed in SystemSettings) | base, rates map (e.g. `USD_VND`, `VND_USD`), provider=`exchangerate-api`, asOf, lastRefreshStatus, lastRefreshError, updatedAt, updatedBy |
| RssSources | PK `RSS`, SK `sourceId` | name, url, enabled, createdAt |
| JobRuns | PK `JOB#{type}`, SK `runAt` | status, message, counts |

*Physical table strategy (single-table vs multi-table) is an implementation choice; multi-table is acceptable for clarity in a student project.*

### 10.2 S3 layout

```
s3://{data-bucket}/
  snapshots/userId={userId}/dt={YYYY-MM-DD}/part.json
  history/{assetType}/{assetId}/{range}.json
s3://{frontend-bucket}/   # Next.js export (index.html, _next/, …)
```

### 10.3 Retention (MVP defaults)

| Data | Retention |
|------|-----------|
| PriceCache | TTL attribute (e.g. 5–15 minutes logical freshness; Dynamo TTL optional) |
| News | Keep ≥ 14 days for demo; no hard delete required |
| Snapshots | Keep for project duration |
| History JSON | Overwrite per range key |

---

## 11. Non-functional requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR1 | Performance | Portfolio `GET` p95 target **&lt; 3s** when cache warm (demo scale) |
| NFR2 | Performance | Refresh may be slower; show loading state |
| NFR3 | Security | HTTPS; Cognito tokens only; JWKS verification on API; no secrets in Git; no Google client secret in SPA |
| NFR4 | Security | IAM least privilege for Beanstalk role and Lambda role |
| NFR5 | Cost | Design for **≤ $50**; alerts at $10 / $30 if available in lab |
| NFR6 | Scale | Demo: ≤ ~20 users, low traffic |
| NFR7 | Availability | Best-effort student lab; single Beanstalk instance OK |
| NFR8 | Observability | CloudWatch logs for Beanstalk + Lambda; JobRuns for job UX |
| NFR9 | Compliance | Educational demo; not financial advice; document data source limitations |
| NFR10 | Maintainability | Repository/storage wrappers for DynamoDB & S3 |

---

## 12. Architecture constraints (locked stack)

| Layer | Choice | Host / service |
|-------|--------|----------------|
| Frontend | Next.js CSR / static export (**no SSR**) | S3 + CloudFront |
| Backend API | FastAPI (Python 3.11+) | Elastic Beanstalk |
| Scheduled jobs | Python handlers | EventBridge → **Lambda only** |
| Database | DynamoDB | Users, holdings, cache, news, settings |
| Object storage | S3 | Frontend + history + snapshots |
| Analytics | Athena | SQL on snapshot files |
| Email (optional) | SES | Daily summary |
| Crypto data | CoinGecko | Server-side only |
| VN stocks | vnstock | Server-side only |
| News | RSS + feedparser (or equivalent) | Lambda ingest |
| AWS SDK | **boto3** behind thin wrappers | FastAPI + Lambda |

**Not used (locked):** Next.js SSR; dual Next+FastAPI processes on one Beanstalk as the primary pattern; browser-direct market APIs.

**API Gateway (locked — D2):** **not used** for user APIs. Browser calls **Elastic Beanstalk (FastAPI)** directly. Document in architecture report that API Gateway is intentionally omitted to reduce cost/complexity; marks narrative emphasizes Beanstalk + Lambda as high-value compute.

### 12.1 Path A — user request

```
User → CloudFront → S3 (UI)
User → Beanstalk FastAPI
         → DynamoDB (auth, holdings, watchlist, settings, news read)
         → PriceCache; on miss or Refresh → CoinGecko / vnstock
         → S3 history cache for charts
         → JSON → browser charts/tables
```

### 12.2 Path B — schedule

```
EventBridge → Lambda
  → SystemSettings / RssSources
  → RSS / CoinGecko / vnstock
  → News, PriceCache, Snapshots (DynamoDB + S3)
  → SES (if enabled)
  → JobRuns
```

---

## 13. External dependencies & SLAs (practical)

| Dependency | Use | Constraint handling |
|------------|-----|---------------------|
| CoinGecko | Quotes + history | Batch requests; cache 5–15 min; last-good fallback |
| vnstock / public VN APIs | Quotes + history | Server-only; adapter; fixture mode for demo day if broken |
| RSS feeds | News | Skip failed feeds; continue others |
| SES | Email | Sandbox: verify recipient emails; document limitation |
| AWS Academy lab | Hosting | Temporary credentials; session limits; service allow-list |

---

## 14. UX requirements (summary)

- Clean, readable dashboard suitable for 1080p demo.  
- Loading and empty states (no holdings, no news).  
- Clear **Refresh** control and last-updated timestamp.  
- Tables filterable by asset class.  
- Mobile: usable but desktop-first for demo.  
- Admin section visually separated; only for `admin`.

**Charts:** Chart.js or Recharts (client-side from API JSON).

---

## 15. Engineering requirements

### 15.1 Repository / wrapper layer (required pattern)

| Wrapper | Responsibility |
|---------|----------------|
| `HoldingsRepo` / `WatchlistRepo` / `UsersRepo` | CRUD against DynamoDB |
| `PriceCacheRepo` | Get/put prices + TTL semantics |
| `NewsRepo` | Query news; Lambda write path |
| `SettingsRepo` / `RssSourcesRepo` / `JobRunsRepo` | Admin + jobs |
| `ObjectStorage` (S3) | `put_json` / `get_json` / history & snapshots |
| `MarketDataClient` | Interface over CoinGecko + vnstock adapters |
| `ExchangeRateClient` | Thin client for ExchangeRate-API (admin refresh only) |
| `ExchangeRateRepo` | Read/write last good rates in DynamoDB; **never clear on failed refresh** |

FastAPI routers and domain services **must not** embed ad-hoc `boto3` calls outside these modules (small shared `aws_session` factory OK).

### 15.2 Configuration

| Config | Source |
|--------|--------|
| Table names, bucket names, region | Environment variables |
| CORS origins | Environment variables |
| Cognito | `COGNITO_REGION`, `COGNITO_USER_POOL_ID`, `COGNITO_APP_CLIENT_ID` (Beanstalk + frontend public client id) |
| ExchangeRate-API | `EXCHANGE_RATE_API_KEY` (server only) |
| CoinGecko API key (optional) | Env |
| Price cache default TTL | SystemSettings (override) + env default |

### 15.3 Local development

1. Run FastAPI with uvicorn.  
2. Use lab AWS credentials in `~/.aws` (refresh after each Start Lab).  
3. Run Next.js dev server with `NEXT_PUBLIC_API_URL=http://localhost:8000`.  
4. Optional: local fixture mode if external APIs fail.

### 15.4 Deployment (target)

| Component | Deploy method |
|-----------|----------------|
| Frontend | `next export` / static build → S3 sync → CloudFront invalidation |
| Backend | Elastic Beanstalk application version (zip / EB CLI) |
| Lambda + EventBridge | AWS SAM or console + documented scripts |
| IAM | Instance profile + Lambda role with least privilege |

---

## 16. Success metrics & acceptance (course-oriented)

| Metric | Target |
|--------|--------|
| Demo script | Completes in ~30 minutes without major failure |
| Live URL | UI + API reachable during assessment window |
| AWS categories | Compute (Beanstalk + Lambda), Storage (S3), CDN (CloudFront), DB (DynamoDB), Analytics (Athena) evidenced |
| Third-party APIs | CoinGecko + vnstock; ExchangeRate-API for FX (admin on-demand refresh) |
| Budget | ≤ $50 with cost narrative |
| Data isolation | User A cannot read User B holdings |
| Jobs | CloudWatch and/or JobRuns prove schedule path |

### 16.1 Demo script (product acceptance)

1. Open live URL → register/login.  
2. Search BTC + VNM → watchlist.  
3. Add holdings with cost basis.  
4. Dashboard: table + pie + PnL.  
5. Refresh → explain cache + external APIs.  
6. Asset history chart.  
7. News matched to symbols/keywords.  
8. Evidence of Lambda job (logs / JobRuns / snapshot object).  
9. Admin: show RSS / settings.  
10. Architecture walkthrough + cost story.

---

## 17. Product decisions

### 17.1 Locked (product owner)

| ID | Decision | Choice |
|----|----------|--------|
| **D1** | Auth | **Amazon Cognito User Pool** — email/password + **Google federated IdP**; API auth via **Cognito JWT** (`Authorization: Bearer <id_token>`); FastAPI verifies JWKS. *(Revised from custom app JWT.)* |
| **D2** | API Gateway | **Not used** — public FastAPI on Elastic Beanstalk |
| **D3** | Multi-currency / FX | **ExchangeRate-API** for USD↔VND (and stored rate map). **Admin on-demand Refresh only** — no auto/scheduled FX requests. Portfolio uses **last good stored rate**; on refresh failure **keep old rate**. Native line currencies remain USD (crypto) / VND (stocks). |
| **D4** | Email time enforcement | **Lambda on fixed schedule** (e.g. hourly) + match admin `emailTime`/`timezone` window |
| **D5** | SES daily email | **Stretch only** — MVP still ships snapshot + news jobs |

### 17.2 Defaults for remaining minor items (change if you disagree)

| ID | Topic | Default applied in this PRD |
|----|-------|-----------------------------|
| **D6** | Athena UX | **Console / documented SQL** for demo proof; optional admin button later |
| **D7** | Admin provisioning | Create Cognito user, then set DynamoDB profile `role=admin` (or Cognito group `admin`) via setup script |
| **D8** | Dashboard “24h change” | **Omit in MVP**; optional later via yesterday’s snapshot vs today |

---

## 18. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| CoinGecko rate limits | Blank/failed prices | Batch + cache + last-good |
| vnstock break | VN lines fail | Adapter + demo fixtures |
| SES sandbox | Email fails | Verify emails; treat as stretch |
| Lab credential expiry | Local dev breaks | Re-copy AWS Details each Start Lab |
| Beanstalk cost | Budget burn | t3.micro, single instance; stop when idle |
| Scope creep | Incomplete demo | Freeze MVP list; cut stretch first |
| API Gateway confusion | Wrong diagrams/marks story | Resolve D2 early |

---

## 19. Milestones (implementation-oriented)

| Phase | Deliverable |
|-------|-------------|
| P0 | Repo layout, wrappers, DynamoDB tables, **Cognito pool + JWT verify**, `/auth/me`, health |
| P1 | Holdings/watchlist CRUD + search (CoinGecko) |
| P2 | vnstock + portfolio math + refresh + cache |
| P3 | Next.js pages dashboard/charts; CORS; env config |
| P4 | Deploy UI to S3/CloudFront; API to Beanstalk |
| P5 | Lambda news + snapshot; EventBridge; JobRuns |
| P6 | Admin UI; S3 history; Athena proof |
| P7 | Stretch email; polish; architecture doc; demo dry-run |

---

## 20. Document control

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | 2026-08-09 | Initial PRD from architecture + proposal |
| 1.1 | 2026-08-09 | Locked D1–D5 (custom JWT, no API GW, mixed currency, Lambda time window, SES stretch) |
| 1.2 | 2026-08-09 | **D1 revised: Amazon Cognito** (+ Google IdP); see `docs/prd/auth-cognito.md` |
| 1.3 | 2026-08-09 | **D3 revised: ExchangeRate-API** — admin on-demand refresh, fallback to last rate; portfolio never auto-fetches FX |

**Approval:** Cognito + on-demand admin FX accepted. Implementation-ready for those areas.

---

## Appendix A — Glossary

| Term | Meaning |
|------|---------|
| PriceCache | DynamoDB (or equivalent) short-lived quote store |
| Snapshot | Point-in-time portfolio valuation for a user/day |
| CSR | Client-side rendering (static export) |
| On-demand (prices) | Fetch market prices when needed / scheduled, not streaming |
| On-demand (FX) | Fetch exchange rates **only** when admin clicks Refresh — not on portfolio load or cron |
| Last good rate | Previously stored FX rates retained when a refresh fails |
| ExchangeRate-API | Third-party FX provider ([docs](https://www.exchangerate-api.com/docs/overview)) |
| Wrapper / repository | App-owned interface isolating AWS SDK / external API details |

## Appendix B — Alignment to assignment categories

| Category | Product mapping |
|----------|-----------------|
| Compute | Elastic Beanstalk (FastAPI), Lambda (jobs) |
| Storage | S3 (UI + data) |
| Networking / CDN | CloudFront |
| Database | DynamoDB |
| Analytics | Athena on snapshots |
| 3rd-party APIs | CoinGecko, vnstock |
| UI | Tables + charts |
| Automation | EventBridge schedules; deploy scripts |
