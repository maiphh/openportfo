# Sprint 10 — Detailed Plan: Scheduled jobs (Lambda-shaped)

| | |
|--|--|
| **ID** | S10 |
| **Depends on** | S06–S09 (ports, flags, market, news, storage) |
| **Unblocks** | S12 Lambda deploy, architecture Path B demo |
| **PRD** | M11, M12, FR-J*, FR-AD9 (no FX in jobs) |

---

## 1. Objective

Testable job functions that later run on Lambda:

1. **News ingest** — RSS → keyword match → NewsRepo  
2. **Price warm** — market batch → PriceCache  
3. **Snapshot** — per-user portfolio → SnapshotRepo + ObjectStorage  

Thin `handler(event)` for Lambda. **No ExchangeRateClient.**

---

## 2. Module layout

```
app/jobs/context.py       # JobContext: ports dataclass
app/jobs/news_job.py
app/jobs/price_job.py
app/jobs/snapshot_job.py
app/jobs/handler.py       # dispatch event["job"]
app/ports/rss.py
app/adapters/rss/fetcher.py
app/ports/snapshots.py
```

Jobs orchestrate **ports only**; reuse domain + portfolio logic where possible.

---

## 3. Job specifications

### run_news_job(ctx)
1. If `settings.jobs.news` is false → JobRun `skipped`  
2. List enabled RSS sources  
3. `RssFetcher.fetch(url)` per source  
4. Keyword match (global settings keywords + title substring, case-insensitive)  
5. `NewsRepo.put`  
6. JobRun success + counts  

### run_price_job(ctx)
1. If disabled → skip  
2. Collect unique symbols from all holdings (and watchlists)  
3. Force market quotes  
4. PriceCache put  
5. JobRun  

### run_snapshot_job(ctx)
1. If disabled → skip  
2. For each user with holdings: compute portfolio (native; FX store **get only** optional)  
3. SnapshotRepo `SNAP#YYYY-MM-DD`  
4. ObjectStorage `snapshots/userId={id}/dt={date}/part.json`  
5. JobRun  

### Email
No-op / stretch only (`EmailSender` port)

---

## 4. RssFetcher port

`fetch(url) -> list[RssItem(title, url, published_at)]`  
Adapter: httpx + feedparser **inside adapter only**.

---

## 5. Event schema (for S12)

```json
{"job": "news"}
{"job": "price"}
{"job": "snapshot"}
```

---

## 6. TDD sequence

1. News job writes matched items (fake RSS)  
2. News disabled → skip JobRun  
3. Price job updates cache  
4. Snapshot writes storage key format  
5. Assert no ExchangeRateClient on context / not called  

---

## 7. Exit criteria

- [ ] Three jobs unit-tested with fakes  
- [ ] handler dispatches by event  
- [ ] handoff: event schema + JobRun fields  

---

## 8. Agent prompt

```
Sprint 10 ONLY. Lambda-shaped jobs using ports only.
No FX provider calls. No Beanstalk/Lambda deploy. TDD with fakes.
Event schema in handoff for S12.
```
