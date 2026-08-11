# OpenPortfo — Solution Architecture Design

**Working title:** OpenPortfo (Crypto + VN Stock Portfolio Tracker)  
**Course:** Cloud Computing — Assessment 3  
**Budget target:** ≤ $50 AWS (monthly / project period)  
**Style:** On-demand data (no real-time websockets)

---

## Agreed stack (locked)

| Layer | Choice | Host |
|---|---|---|
| **Frontend** | Next.js **without SSR** (CSR / static export) | **S3 + CloudFront** |
| **Backend API** | **FastAPI** | **Elastic Beanstalk** |
| **Scheduled jobs** | Daily RSS, portfolio snapshot, optional email | **EventBridge → Lambda only** (not user-facing API) |
| **API Gateway** | — | **Not required** (main API is Beanstalk FastAPI) |
| **Database** | Users, holdings, watchlist, price cache, news | **DynamoDB** |
| **Object storage** | Price history, daily snapshots (Athena) | **S3** |
| **Analytics** | Query portfolio history | **Athena** |
| **Email (optional)** | Daily summary | **SES** (feature only; low/no rubric marks) |
| **External data** | Crypto + VN stocks + news + FX | **CoinGecko**, **vnstock**, **RSS**, **ExchangeRate-API** (admin on-demand only) |

**Not used:** Next SSR; Next + FastAPI both as live servers on one Beanstalk.

```
Browser (Next.js CSR)
  │
  ├─ GET UI  ──► CloudFront ──► S3 (static export)
  │
  └─ API     ──► Elastic Beanstalk (FastAPI)
                      │
                      ├─ DynamoDB (users, holdings, watchlist, settings, news, price cache)
                      ├─ S3 data (history / snapshots) ──► Athena
                      │
                      └─ On demand / Refresh:
                            ├─► CoinGecko API  (crypto quotes + history)
                            └─► vnstock        (VN stock quotes + history)

EventBridge Scheduler (cron; reads Admin settings: email time, RSS list)
       │
       ▼
    Lambda (scheduled only)
       ├─► RSS sources (from Admin config) → keyword match → DynamoDB News
       ├─► CoinGecko + vnstock → PriceCache + portfolio snapshots → DynamoDB / S3
       └─► SES daily email (time from Admin config)
```

---

## 1. Requirement check (proposal vs assignment)

### 1.1 Assignment hard requirements

| Requirement | Your proposal | Fit |
|---|---|---|
| End-to-end cloud app on AWS | Web app + APIs + scheduled jobs | ✅ |
| Services across **Compute, Storage, Networking/CDN, Database, Analytics** | Designed below | ✅ |
| Fully **implemented & automated** (not console-only) | UI/API/cron invoke services | ✅ |
| High-value services (6 pts each): Beanstalk / Lambda / API GW / ECS / EMR | Beanstalk + Lambda + API GW | ✅ |
| Other AWS services (3 pts each) | DynamoDB, S3, CloudFront, Athena | ✅ |
| Third-party APIs (2 pts each, **max 2 graded**) | CoinGecko + vnstock (or RSS) | ✅ |
| Client UI with tables/charts | Portfolio + history charts | ✅ |
| Deployed live for demo | Yes | ✅ |
| Solution architecture document | This design feeds the doc | ✅ |
| **Do not reuse Assessment 2** | New domain | ✅ |

Official example ideas even include: *“light-weight crypto exchange / portfolio of crypto assets … monitor trends”* — your idea is on-theme.

### 1.2 Proposal feature review

| Feature | Verdict | Notes |
|---|---|---|
| Watchlist + holdings → portfolio | **Core — keep** | Best cloud-data story |
| Charts, filters, historical | **Core — keep** | Satisfies “interpret results graphically” |
| Login | **Core — keep** | Required for multi-user data |
| On-view / on-refresh API fetch | **Correct** | Avoids real-time cost & complexity |
| Daily RSS news + keyword match | **Keep, scope carefully** | Good Lambda schedule demo; simple keyword match only |
| Daily email portfolio summary | **Keep as stretch** | SES is useful but **assignment notes SES as “no marks”** in the sample idea — still a strong demo feature |
| Real trading / exchange | **Out of scope** | Not needed; tracking only |

### 1.3 Scope for a high mark under $50 (recommended MVP)

**Must-have (demo script):**
1. Register / login  
2. Search assets (crypto + VN stock)  
3. Add to **watchlist** and **holdings** (qty + cost basis)  
4. Portfolio dashboard (value, PnL, allocation pie, table filters)  
5. Asset detail + historical price chart  
6. News feed filtered by user’s symbols/keywords  
7. Manual **Refresh** button (on-demand external API)  
8. Daily job: snapshot portfolio + (optional) email summary  

**Nice-to-have if time left:**
- Allocation by asset class (crypto vs VN stock)  
- Export CSV of holdings  
- Multi-currency display (USD + VND)

**Cut if behind schedule:**
- Fancy NLP news ranking (keyword match is enough)  
- Intraday charts  
- Social login  

---

## 2. Data sources (free / stable)

### 2.1 Crypto — recommendation: **CoinGecko (primary)**

| Source | Free tier (approx.) | Historical | Stability | Verdict |
|---|---|---|---|---|
| **CoinGecko** | ~10k calls/mo, ~30–100 RPM (Demo) | Daily/hourly OHLC | High, widely used | **Use this** |
| CoinMarketCap | Free key, credit limits | Limited on free | High | Backup only |
| CoinCap / CoinPaprika | Free-ish | Varies | Medium | Optional fallback |
| Binance public | Free | Yes | High | Only if you accept CEX-only symbols |

**Why CoinGecko wins for this project**
- Free, no key required for Demo (still better to use a free API key if available)  
- `/simple/price`, `/coins/markets`, `/coins/{id}/market_chart` cover portfolio + charts  
- Stable enough for student demo; cache aggressively so you never burn the quota  

**Quota strategy (critical)**
- Cache market quotes in DynamoDB/S3 for **5–15 minutes**  
- Batch: one `simple/price?ids=btc,eth,...` for all holdings  
- Historical: fetch once per asset/range, store in S3, serve from cache  
- Never call external APIs on every table row render  

### 2.2 Vietnam stocks — **vnstock (Python library → public broker APIs)**

- Open-source toolkit wrapping TCBS / SSI public endpoints  
- Free, no official paid key for basic use  
- Good for: listing search, current price, historical OHLCV  

**Caveats to document in architecture report**
- Unofficial / best-effort public APIs → can break if broker changes endpoints  
- Prefer **server-side only** (Lambda/Beanstalk), never browser → broker  
- Cache quotes (market hours vs after-hours)  
- Fallback: store last good price so UI never blanks  

### 2.3 News — RSS (free)

Examples (pick 3–5):
- Cointelegraph / CoinDesk RSS (crypto)  
- CafeF / VnExpress Kinh doanh / Vietstock RSS (VN market)  

Pipeline: EventBridge → Lambda → parse RSS → keyword match (user symbols + custom keywords) → store in DynamoDB `News` table → UI list.

---

## 3. High-level architecture (agreed)

### Diagram files (draw.io + SVG)

| File | Use |
|---|---|
| [`docs/diagrams/OpenPortfo_Architecture.drawio`](diagrams/OpenPortfo_Architecture.drawio) | **Editable** in [diagrams.net](https://app.diagrams.net) — 3 pages: High-Level, Path A, Path B |
| [`docs/diagrams/OpenPortfo_Architecture.svg`](diagrams/OpenPortfo_Architecture.svg) | Preview / embed in docs |

**How to open:** double-click the `.drawio` file, or File → Open in https://app.diagrams.net → Export as PNG/PDF for the architecture document.

### 3.0 Full system diagram (request path + schedule path + external data)

```
                         ┌──────────────────────────────────────┐
                         │  EXTERNAL DATA SOURCES                 │
                         │  ┌────────────┐  ┌─────────┐  ┌─────┐ │
                         │  │ CoinGecko  │  │ vnstock │  │ RSS │ │
                         │  │ (crypto)   │  │ (VN)    │  │feeds│ │
                         │  └─────▲──────┘  └────▲────┘  └──▲──┘ │
                         └────────┼──────────────┼──────────┼────┘
                                  │              │          │
        ┌─────────────────────────┼──────────────┼──────────┼──────────────┐
        │                         │ on-demand    │          │ schedule     │
        │                         │ / refresh    │          │ only         │
        │  ┌──────────────────────┴──────────────┴──┐       │              │
        │  │                                         │       │              │
┌───────┴──┴─────────────────────────────────────────┴───────┼──────────────┴──┐
│ AWS                                                         │                 │
│                                                             │                 │
│  Browser (Next.js CSR, no SSR)                              │                 │
│    │                                                        │                 │
│    ├─ UI ──► CloudFront ──► S3 (frontend static)            │                 │
│    │                                                        │                 │
│    └─ API ──► Elastic Beanstalk (FastAPI)  ◄────────────────┤                 │
│                  │  auth, holdings, watchlist, portfolio,    │                 │
│                  │  news read, admin settings                │                 │
│                  │                                           │                 │
│                  ├─► DynamoDB (users, holdings, watchlist,   │                 │
│                  │            price cache, news,             │                 │
│                  │            SystemSettings / Admin)        │                 │
│                  │                                           │                 │
│                  └─► S3 data (OHLC history, snapshots)       │                 │
│                              │                               │                 │
│                              └─► Athena (SQL analytics)      │                 │
│                                                              │                 │
│  ┌─ SCHEDULED PATH ──────────────────────────────────────────┘                 │
│  │                                                                             │
│  │  EventBridge Scheduler                                                      │
│  │    (cron; email time + job flags from Admin/SystemSettings)                 │
│  │         │                                                                   │
│  │         ▼                                                                   │
│  │      Lambda (no browser traffic; no API Gateway)                            │
│  │         ├─ read RSS URL list from SystemSettings ──► RSS feeds              │
│  │         │     keyword match ──► DynamoDB News                               │
│  │         ├─ CoinGecko + vnstock batch ──► PriceCache + snapshots             │
│  │         │     ──► DynamoDB + S3                                             │
│  │         └─ SES daily portfolio email (if enabled)                           │
│  └─────────────────────────────────────────────────────────────────────────────┘
└────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Two paths (draw these separately in the architecture PDF)

**Path A — User request (portfolio render / refresh)**

```
User → CloudFront/S3 (UI)
User → FastAPI (Beanstalk)
         → DynamoDB holdings
         → PriceCache; if miss or Refresh:
              → CoinGecko (crypto)
              → vnstock (VN stocks)
         → compute PnL → JSON → charts/tables
```

**Path B — EventBridge scheduled jobs**

```
EventBridge (cron from Admin: e.g. 08:00 ICT)
    → Lambda
         1) RSS: fetch configured sources → match keywords → News table
         2) Prices: CoinGecko + vnstock → update cache
         3) Portfolio: snapshot each user → DynamoDB (+ S3 for Athena)
         4) Email: SES summary using Admin email time / opt-in
```

### 3.2 Hosting map

| Request | Served by |
|---|---|
| `/`, dashboard, admin UI, JS/CSS | **CloudFront → S3** |
| `/api/*` (auth, holdings, portfolio, news, admin) | **Beanstalk → FastAPI** |
| Daily RSS / snapshot / email | **EventBridge → Lambda** (not browser) |

CORS: FastAPI allows CloudFront origin only.  
**Locked:** Lambda = schedule only; no API Gateway for user APIs.

### 3.3 Why this shape (marks + $50)

| Service | Category | Marks | Role | Cost control |
|---|---|---|---|---|
| **Elastic Beanstalk** | Compute | **6** | FastAPI (user APIs + admin) | 1× `t3.micro` |
| **Lambda** | Compute | **6** | Scheduled RSS / prices / snapshot / email | Free tier |
| **DynamoDB** | Database | **3** | Users, holdings, settings, cache, news | On-demand |
| **S3** | Storage | **3** | Frontend + history/snapshots | Few GB |
| **CloudFront** | Networking & CDN | **3** | Frontend delivery | Low traffic |
| **Athena** | Analytics | **3** | SQL on snapshot files | Scan MBs |
| **EventBridge** | Orchestration | — | Cron for Lambda | Free tier |
| **SES** | Email | **0 marks** | Daily summary | Sandbox OK |

Avoid: API Gateway (not needed), RDS, EMR, dual Next+FastAPI servers.

---

## 4. Application modules & APIs

### 4.1 Feature → API map (all user APIs = FastAPI on Beanstalk)

| UI action | API | Backend | External |
|---|---|---|---|
| Register / login / Google | Cognito Hosted UI or client SDK | **Amazon Cognito** User Pool (+ Google IdP) | Google OAuth |
| Current user / bootstrap profile | `GET /auth/me` | FastAPI verifies Cognito JWT → DynamoDB profile | — |
| Search assets | `GET /assets/search?q=&type=crypto\|stock` | FastAPI | CoinGecko / vnstock |
| Watchlist CRUD | `GET/POST/DELETE /watchlist` | FastAPI → DynamoDB | — |
| Holdings CRUD | `GET/POST/PUT/DELETE /holdings` | FastAPI → DynamoDB | — |
| Portfolio view | `GET /portfolio` | FastAPI: holdings + cache → PnL | CoinGecko/vnstock if cache miss |
| Refresh prices | `POST /portfolio/refresh` | FastAPI force-refresh cache | CoinGecko + vnstock |
| History chart | `GET /assets/{id}/history?range=30d` | FastAPI → S3 cache else fetch | CoinGecko / vnstock |
| News (read) | `GET /news` | FastAPI → DynamoDB | — (filled by Lambda) |
| **Admin settings** | `GET/PUT /admin/settings` | FastAPI → DynamoDB SystemSettings | — |
| **Admin RSS sources** | `GET/POST/PUT/DELETE /admin/rss-sources` | FastAPI → DynamoDB | — |
| **FX rates (read)** | `GET /fx/rates` | FastAPI → DynamoDB stored rates only | — |
| **FX refresh (admin)** | `POST /admin/fx/refresh` | FastAPI → ExchangeRate-API → DynamoDB on success; keep old on fail | ExchangeRate-API |
| Daily summary job | EventBridge cron | **Lambda** → snapshot + SES | CoinGecko/vnstock/RSS as needed |

### 4.2 Admin page (system configuration)

**Who:** role `admin` (seed one admin user for demo).  
**UI route:** `/admin` (Next.js) → protected admin APIs.

| Setting | Purpose | Used by |
|---|---|---|
| RSS source list (name, URL, enabled) | Which feeds Lambda pulls | EventBridge → Lambda news job |
| Global default keywords | Fallback relevance matching | Lambda news job |
| Daily email time (timezone, cron) | When SES summaries send | EventBridge schedule (or Lambda checks window) |
| Email enabled (global kill-switch) | Turn off all daily emails | Lambda |
| Price cache TTL (minutes) | How stale quotes may be | FastAPI portfolio/refresh |
| Feature flags (news job, snapshot job) | Enable/disable scheduled tasks | Lambda |
| Supported quote currencies display | USD / VND labels | UI |
| Exchange rates (stored) | Last good USD↔VND from ExchangeRate-API | Portfolio conversion |
| Refresh exchange rates | Admin button → one API call; fallback keep old | Admin + FastAPI |

**Admin UX (MVP):**
1. List / add / disable RSS URLs  
2. Set daily email time (e.g. 08:00 Asia/Ho_Chi_Minh)  
3. Toggle jobs on/off  
4. View last job run status (from DynamoDB `JobRun` or CloudWatch)  

**Note:** Changing email time in MVP can mean (a) update EventBridge schedule via backend/IAM role, or (b) Lambda runs hourly and only sends when local time matches setting — (b) is simpler for a student demo.

### 4.3 Data model (DynamoDB)

```
Users (app profile; auth is Cognito)
  PK: userId   (= Cognito sub)
  email, name, role (user|admin), createdAt
  newsKeywords[], emailOptIn, preferredCurrency
  # passwords live in Cognito only — no passwordHash here

Holdings
  PK: userId   SK: HOLD#assetType#symbol
  qty, avgCost, currency, note, updatedAt

Watchlist
  PK: userId   SK: WATCH#assetType#symbol
  addedAt

PriceCache
  PK: assetType#symbol
  price, currency, asOf, rawJson, ttl

News
  PK: date (YYYY-MM-DD)   SK: source#hash
  title, url, publishedAt, symbols[], keywords[]

PortfolioSnapshot (also written as JSON to S3 for Athena)
  PK: userId   SK: SNAP#YYYY-MM-DD
  totalValue, totalCost, pnl, breakdown[]

SystemSettings (Admin)
  PK: SETTINGS   SK: GLOBAL
  emailTime, timezone, emailEnabled
  priceCacheTtlMinutes
  jobs: { news: bool, snapshot: bool, email: bool }
  defaultDisplayCurrency
  updatedAt, updatedBy

ExchangeRates (Admin-maintained; no scheduled fetch)
  PK: FX   SK: LATEST
  base, rates (e.g. USD_VND, VND_USD)
  provider: exchangerate-api
  asOf, lastRefreshStatus, lastRefreshError
  updatedAt, updatedBy

RssSources (Admin)
  PK: RSS   SK: sourceId
  name, url, enabled, createdAt

JobRuns (optional audit)
  PK: JOB#news|snapshot|email   SK: runAt
  status, message, counts
```

**S3 layout for Athena**
```
s3://OpenPortfo-data/
  snapshots/userId=u123/dt=2026-08-07/part.json
  history/crypto/bitcoin/30d.json
  history/stock/VNM/1y.json
```

### 4.3 Portfolio calculation (server-side)

```
marketValue = Σ (qty_i * price_i)
costBasis   = Σ (qty_i * avgCost_i)
pnl         = marketValue - costBasis
pnl%        = pnl / costBasis
allocation  = marketValue_i / marketValue
```

Normalize currency for display using **stored FX rates** from [ExchangeRate-API](https://www.exchangerate-api.com/docs/overview). Crypto lines primarily USD; VN stocks VND. **Admin-only on-demand refresh** (no auto/cron FX calls). Portfolio conversion reads last good rates in DynamoDB; if refresh fails, keep previous rates.

---

## 5. Scheduled pipelines (cloud-native story)

```
EventBridge Scheduler (cron)
   │  07:30 ICT  price warm-cache (top symbols)
   │  08:00 ICT  portfolio snapshot + email
   │  09:00 ICT  RSS news ingest
   ▼
Lambda
   ├─ fetch CoinGecko batch + vnstock batch
   ├─ update PriceCache (DynamoDB) + S3 history
   ├─ for each user: compute snapshot → DynamoDB + S3
   ├─ match news keywords → News table
   └─ SES send daily summary (opt-in users)
```

This proves: **event-driven compute**, **not only request/response**.

---

## 6. Auth design (**locked: Amazon Cognito**)

| Approach | Status |
|---|---|
| **A. Cognito User Pool** (+ optional Google federated IdP) | **Selected** |
| B. Custom DynamoDB + app-issued JWT | Superseded |

**Flow**
1. Browser authenticates with **Cognito** (email/password and/or **Sign in with Google**).  
2. Client receives Cognito tokens; sends **ID token** as `Authorization: Bearer …` to FastAPI.  
3. Beanstalk validates JWT via Cognito **JWKS** (`iss`, `aud`/`client_id`, `exp`, signature).  
4. `userId` = Cognito `sub`. DynamoDB holds **profile only** (role, keywords, emailOptIn) — not passwords.  
5. Admin = DynamoDB `role=admin` (or Cognito group), enforced in FastAPI.

**Threat model (brief):** HTTPS; public app client (no secret in SPA); never trust unverified tokens; least-privilege IAM for Beanstalk; no secrets in Git. Details: `docs/prd/auth-cognito.md`.

---

## 7. Frontend pages (demo flow)

1. **Login / Register**  
2. **Dashboard** — total value, 24h change, PnL, allocation pie, holdings table (filter crypto/stock)  
3. **Watchlist** — prices + sparkline if time  
4. **Add holding** modal — symbol search, qty, cost  
5. **Asset detail** — history chart (Chart.js / Recharts)  
6. **News** — cards filtered to user keywords  
7. **User settings** — email opt-in, personal keywords  
8. **Admin** (role=admin) — RSS sources, email time, job toggles, cache TTL, **FX rates + Refresh**, last job status  

Charts: Chart.js or Recharts (client-side after FastAPI JSON).

---

## 8. Cost estimate (student demo scale)

Assumptions: ≤ 20 users, demo traffic, 1× t3.micro Beanstalk, on-demand DynamoDB, < 5 GB S3, < 50k API calls/mo.

| Service | Est. monthly |
|---|---|
| Elastic Beanstalk + EC2 t3.micro | $0–12 (free tier / credits first; else ~$7–10) |
| Lambda | $0 (within free) |
| API Gateway | $0 (within free) |
| DynamoDB on-demand | $0–2 |
| S3 + CloudFront | $0–2 |
| Athena | $0–1 (scan MBs, not TBs) |
| SES | $0 (sandbox, few emails) |
| EventBridge | $0 |
| **Total** | **~$0–15 typical; hard cap well under $50** |

**Cost guardrails**
- AWS Budgets alert at $10 and $30  
- Beanstalk min=max=1, smallest instance  
- No NAT Gateway, no ALB multi-AZ extras if avoidable  
- Athena: always `SELECT` with partition `dt=`  
- Never store large binary in DynamoDB  

---

## 9. Implementation plan (weeks 5–12 aligned to brief)

| Phase | Work |
|---|---|
| Week 5–6 | Finalize idea with tutor; lock architecture diagram |
| Week 7 | Beanstalk skeleton + DynamoDB tables + auth |
| Week 8 | Holdings/watchlist CRUD + CoinGecko integration + cache |
| Week 9 | vnstock adapter + portfolio math + charts |
| Week 10 | API Gateway expose REST; Lambda split; CloudFront |
| Week 11 | News RSS job + snapshot → S3 + Athena query UI |
| Week 12 | Email job polish, architecture doc, demo script |

---

## 10. Architecture diagram narrative (for the PDF)

Your solution architecture document **must** show:

1. Client action → which component is invoked  
2. Detailed interactions among AWS services  
3. Function of each component  

Suggested figures:
- **Fig 1:** High-level system context (user, AWS, external APIs)  
- **Fig 2:** Request path for “View portfolio” (refresh on demand)  
- **Fig 3:** Daily scheduled pipeline (news + email + snapshot)  
- **Fig 4:** DynamoDB entity diagram  
- **Fig 5:** Sequence diagram “Add holding → recompute portfolio”

Use draw.io / Lucidchart with AWS icons (same style as sample LoL Buddy).

---

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| CoinGecko rate limit | Batch + cache TTL; circuit breaker return last price |
| vnstock/public API break | Adapter interface; fixture mode for demo day |
| SES sandbox | Pre-verify tutor email; show sent message in console logs too |
| Beanstalk cost | Single instance; stop env when not developing |
| Scope creep | Freeze MVP list in week 6 |

---

## 12. Suggested tech stack (agreed)

| Layer | Choice |
|---|---|
| Frontend | **Next.js** (static export / CSR, **no SSR**) → **S3 + CloudFront** |
| Backend | **Python 3.11 + FastAPI** → **Elastic Beanstalk** |
| Charts | Chart.js or Recharts (client-side) |
| AWS SDK | boto3 (FastAPI + Lambda) |
| Crypto data | CoinGecko REST |
| VN stocks | vnstock (server-side only) |
| FX | ExchangeRate-API (admin on-demand only; store last good rate) |
| News | feedparser + RSS (Lambda) |
| Auth | **Amazon Cognito** (email + Google IdP) + DynamoDB user **profiles**; FastAPI JWKS verify |
| Jobs | EventBridge Scheduler → Lambda |
| Infra as code (optional) | AWS SAM for Lambda; shell/CI for S3 sync + EB deploy |

---

## 13. Third-party APIs to claim for marks

1. **CoinGecko API** — prices, markets, historical charts  
2. **vnstock / underlying public stock APIs** — VN equities  

Also integrated (document as data source; marks cap may still be “max 2” graded APIs):

3. **ExchangeRate-API** — USD↔VND (and stored rate map); **admin on-demand refresh only**; portfolio uses last good rate; no auto poll  
   Docs: https://www.exchangerate-api.com/docs/overview  

(RSS is free and good for features; if examiner counts only “APIs”, still document it under data sources.)

---

## 14. Demo script (30 minutes)

1. Open live URL → register/login  
2. Search BTC + VNM → add watchlist  
3. Add holdings with cost basis  
4. Show portfolio table + pie + PnL  
5. Click **Refresh** → explain API + cache  
6. Open asset chart (historical from S3/cache)  
7. Show news matched to “BTC”, “VNM”  
8. Trigger or show evidence of daily Lambda (CloudWatch log / last snapshot)  
9. Walk architecture diagram: Beanstalk → API GW → Lambda → DynamoDB/S3/Athena  
10. Cost slide: why under $50  

---

## 15. Final recommendation

**Green light the idea** with this scoping:

> A personal **crypto + Vietnam stock portfolio tracker** on AWS: users log in, manage watchlists and holdings, view on-demand valued portfolio with charts, read keyword-matched market news, and receive optional daily email summaries — powered by CoinGecko, vnstock, and a serverless + Beanstalk architecture kept under $50.

Discuss with tutor by Week 5/6; lock MVP features above before coding.
