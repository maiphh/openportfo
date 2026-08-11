# OpenPortfo: A Cloud-Based Crypto and Vietnam Stock Portfolio Tracking System

**Document type:** Research / Project Proposal  
**Course:** RMIT University — Cloud Computing, Assessment 3  
**Date:** August 2026  
**Budget constraint:** AWS spend ≤ USD $50 (project period)  
**Stack summary:** Next.js (S3 + CloudFront) · FastAPI (Elastic Beanstalk) · DynamoDB · Lambda · EventBridge · Athena · SES  

---

## 1. Problem Statement

It is hard for individual investors to manage holdings across different sources—cryptocurrency exchanges or wallets on one side, and Vietnam stock brokers on the other—because each asset class lives in a separate app or spreadsheet, with no single view of total value, allocation, and profit and loss, and no low-cost way to combine on-demand pricing, relevant news, and a simple daily summary under a tight cloud budget.

---

## 2. Proposed Solution

OpenPortfo is a cloud-based portfolio tracking application designed for individual investors who hold both cryptocurrencies and Vietnam-listed stocks. The system provides a unified watchlist and holdings model, a portfolio dashboard with charts and filters, on-demand price refresh (not WebSocket real-time streaming), RSS news filtered by keyword relevance, a daily portfolio summary email, user login, and an administrator page for system configuration.

### 2.1 Core capabilities

- **Unified multi-asset tracking.** Users can search and add crypto (CoinGecko) and Vietnam stocks (vnstock) to watchlist and holdings; the portfolio view computes value, cost, and PnL.
- **On-demand prices with caching.** Quotes refresh on view/refresh or via scheduled jobs—not continuous real-time.
- **Historical charts and analytics.** Price history and snapshots in S3; Athena for optional SQL.
- **News and email.** Scheduled Lambda fetches RSS, keyword-matches, stores news, optional SES daily summary.
- **Admin configuration.** RSS sources, email time, job toggles, cache TTL.

### 2.2 Design principles

User traffic: Next.js static UI on S3 + CloudFront; FastAPI on Elastic Beanstalk for all REST APIs. Background: EventBridge → Lambda only. External data: CoinGecko + vnstock with caching. Target AWS spend ≤ $50.

---

## 3. Architecture

### 3.1 High-level architecture

Figure 1 shows the simplified end-to-end flow: **User → Frontend (CloudFront + S3 Next.js) → Backend (Elastic Beanstalk FastAPI) → Data (DynamoDB, S3, Athena) and Jobs (EventBridge → Lambda → SES)**. The backend calls external market APIs (CoinGecko and vnstock) on demand or refresh. Main user traffic does not use API Gateway.

**Figure 1. OpenPortfo system architecture** — see `docs/diagrams/architecture.png`.

The architecture is organised into five component groups:

#### Frontend

The client is a Next.js application built as a client-side (CSR) static export—no server-side rendering. Static files are stored in **Amazon S3** and delivered through **Amazon CloudFront** with CDN and HTTPS. The user opens the site in a browser; CloudFront serves the UI and fetches Next.js assets from S3. Charts and tables render in the browser after JSON is returned from the backend.

#### Backend

All interactive application logic runs on **AWS Elastic Beanstalk** hosting **FastAPI** (Python). This tier handles authentication, watchlist and holdings CRUD, portfolio valuation, manual price refresh, news read, and the admin page (RSS sources, email time, job toggles). The browser calls REST endpoints under `/api/*` on Beanstalk. On cache miss or refresh, FastAPI requests live prices from external APIs and writes results back to the database cache.

#### Database and storage

**Amazon DynamoDB** is the primary operational database: users, holdings, watchlist, price cache, news items, and system/admin settings. **Amazon S3** also stores price history and daily portfolio snapshots. **Amazon Athena** runs optional SQL analytics over those snapshot files; it is not used on every portfolio page load. Live dashboard data always comes from DynamoDB (and the price cache) via the backend.

#### Jobs (scheduled)

**Amazon EventBridge** runs a cron schedule (email time and job flags come from Admin settings). It triggers **AWS Lambda** only—Lambda is not a public HTTP API. Lambda jobs include: (1) fetch RSS feeds and keyword-match into DynamoDB News; (2) batch-update prices via CoinGecko and vnstock into the price cache; (3) write portfolio snapshots to DynamoDB and S3; (4) send the daily summary through **Amazon SES**. This keeps background work separate from user request traffic.

#### External APIs

**CoinGecko** supplies cryptocurrency prices and historical data. **vnstock** supplies Vietnam stock quotes and history. The backend calls both on demand when the user views or refreshes the portfolio. Scheduled Lambda jobs may call the same APIs for batch warm-cache and snapshot work. Free-tier rate limits are managed with caching in DynamoDB and S3.

### 3.2 API information

All user-facing REST endpoints are implemented in FastAPI on Elastic Beanstalk. Scheduled jobs are EventBridge → Lambda and are not public HTTP APIs.

**Table 1. Main REST API endpoints**

| Group | Endpoints | Behaviour / backend |
|---|---|---|
| Auth | Cognito sign-up/login/Google + `GET /auth/me` | **Amazon Cognito** tokens; FastAPI JWKS verify; DynamoDB **profile** only |
| Assets search | `GET /assets/search?q=&type=crypto\|stock` | CoinGecko or vnstock |
| Watchlist | `GET/POST/DELETE /watchlist` | DynamoDB |
| Holdings | `GET/POST/PUT/DELETE /holdings` | DynamoDB |
| Portfolio | `GET /portfolio` | Holdings + cache → PnL; external on miss |
| Refresh | `POST /portfolio/refresh` | CoinGecko + vnstock → PriceCache |
| History | `GET /assets/{id}/history?range=` | S3 cache or external |
| News | `GET /news` | DynamoDB (filled by Lambda) |
| Admin settings | `GET/PUT /admin/settings` | Email time, jobs, cache TTL |
| Admin RSS | `GET/POST/PUT/DELETE /admin/rss-sources` | RSS list for Lambda news job |

---

## 4. Similar Products

| Product | Crypto | VN stocks | Unified portfolio | News | Email | Cloud / self-serve |
|---|---|---|---|---|---|---|
| CoinMarketCap Portfolio | Yes | No | Crypto only | Site news | Limited | SaaS web |
| Delta / Blockfolio-style | Yes | No | Crypto only | Alerts | Push | Mobile SaaS |
| Yahoo Finance | Limited | Limited VN | Multi-asset (global) | Yes | Alerts | SaaS |
| CafeF / TCBS tools | No | Yes | VN equities | Market news | Varies | Local portals |
| Google Sheets trackers | Manual | Manual | If user builds it | No | No | DIY |
| **OpenPortfo** | Yes (CoinGecko) | Yes (vnstock) | Yes (crypto + VN) | RSS + keywords | Daily SES | AWS ≤ $50 |

OpenPortfo is a lightweight multi-asset cloud demonstration for Assessment 3: dual external data integrations, Beanstalk user APIs vs Lambda schedules, admin-managed RSS/email, Athena-ready snapshots.

---

## 5. Limitations and Further Improvement

### 5.1 Current limitations

- Free API rate limits (CoinGecko); caching required  
- vnstock / public Vietnam data may change  
- No real-time streaming  
- SES sandbox (verified recipients)  
- Single-region, demo scale  
- Keyword-only news relevance  
- Rough USD/VND conversion  

### 5.2 Further improvement

- **AI Chatbot helper** — portfolio Q&A from holdings/snapshots  
- **RSS RAG Chatbot** — retrieve news chunks + LLM answers with citations  
- **Analyzer** — risk/allocation insights, anomaly alerts  
- Better NLP relevance, multi-currency FX, mobile app, Cognito, more markets  

---

## 6. Conclusion

Fragmented multi-source holdings (crypto + VN stocks) are hard to manage without a single affordable view. OpenPortfo unifies watchlist and holdings, on-demand portfolio dashboard, history charts, keyword RSS news, and optional daily email under a clear AWS split: frontend on S3/CloudFront, FastAPI on Beanstalk, DynamoDB/S3/Athena for data, EventBridge→Lambda for jobs, CoinGecko and vnstock for market data—feasible under a USD $50 budget and ready for Assessment 3 implementation.

---

## 7. References

[1] CoinGecko API — https://www.coingecko.com/en/api/documentation  
[2] AWS Elastic Beanstalk — https://docs.aws.amazon.com/elasticbeanstalk/  
[3] AWS Lambda — https://docs.aws.amazon.com/lambda/  
[4] Amazon DynamoDB — https://docs.aws.amazon.com/dynamodb/  
[5] vnstock — https://github.com/thinh-vu/vnstock  
[6] Next.js — https://nextjs.org/docs  
[7] FastAPI — https://fastapi.tiangolo.com/  
