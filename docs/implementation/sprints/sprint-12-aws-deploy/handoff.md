# Handoff — Sprint 12 — AWS deploy & real adapters

## Status
- [x] Done (offline artifacts + wiring; live Lab deploy optional)

## Ports / modules added

### DynamoDB adapters (`backend/app/adapters/dynamodb/`)
| Module | Port | Table default |
|--------|------|---------------|
| `users.py` | UserProfileRepo | `openportfo-users` |
| `holdings.py` | HoldingsRepo | `openportfo-holdings` |
| `watchlist.py` | WatchlistRepo | `openportfo-watchlist` |
| `price_cache.py` | PriceCacheRepo | `openportfo-price-cache` |
| `news.py` | NewsRepo | `openportfo-news` |
| `settings.py` | SettingsRepo | `openportfo-settings` |
| `rss.py` | RssSourcesRepo | `openportfo-rss` |
| `fx.py` | ExchangeRateRepo | `openportfo-fx` |
| `job_runs.py` | JobRunsRepo | `openportfo-job-runs` |
| `snapshots.py` | SnapshotRepo | `openportfo-snapshots` |
| `base.py` | shared helpers | — |

### Other adapters
- `adapters/s3/storage.py` — ObjectStorage
- `adapters/rss/fetcher.py` — HttpRssFetcher (httpx + feedparser)
- `adapters/coingecko/http_client.py` — optional live CoinGecko
- `adapters/vnstock/http_client.py` — optional vnstock + fixture fallback
- Existing: `cognito/jwt_verifier.py`, `exchangerate/client.py`

### Jobs / deploy
- `app/jobs/lambda_entry.py` + `backend/lambda_handler.py`
- `backend/Procfile`, `.ebextensions/`
- `infra/cloudformation.yml`, `infra/iam/*.json`, `infra/lambda/`
- `deploy/eb-deploy.md`
- Athena: `athena-sample.sql`
- Runbook: `RUNBOOK.md`

## Table key schemes (locked)

| Entity | PK | SK | Notes |
|--------|----|----|-------|
| Users | `userId` | — | Cognito `sub` |
| Holdings | `userId` | `HOLD#{assetType}#{symbol}` | symbol upper |
| Watchlist | `userId` | `WATCH#{assetType}#{symbol}` | |
| PriceCache | `pk` = `{assetType}#{symbol}` | — | Dynamo TTL attr `ttl` optional |
| News | `date` YYYY-MM-DD | `{source}#{id}` | scan for list_recent |
| Settings | `SETTINGS` | `GLOBAL` | singleton |
| FX | `FX` | `LATEST` | admin only; **no cron** |
| RSS | `RSS` | `sourceId` | |
| JobRuns | `JOB#{type}` | `{startedAt}#{runId}` | |
| Snapshots | `userId` | `SNAP#YYYY-MM-DD` | + S3 JSON |

### S3 keys
```
history/{assetType}/{assetId}/{range}.json
snapshots/userId={id}/dt={YYYY-MM-DD}/part.json
```

## Env vars (see `backend/.env.example`)

| Var | Default | Purpose |
|-----|---------|---------|
| `APP_ENV` | `local` | local/test/prod |
| `AUTH_MODE` | `fake` | fake \| cognito |
| `STORAGE_BACKEND` | `memory` | memory \| aws |
| `USE_AWS_ADAPTERS` | `false` | force AWS adapters |
| `AWS_REGION` | `us-east-1` | |
| `DATA_BUCKET` | empty | required when AWS adapters |
| `COGNITO_*` | empty | pool/client for AUTH_MODE=cognito |
| `*_TABLE` | openportfo-* | all entity tables incl. RSS/JOB_RUNS/SNAPSHOTS |
| `MARKET_CLIENT_MODE` | `fixture` | fixture \| http |
| `EXCHANGE_RATE_API_KEY` | empty | admin FX only — never commit |
| `COINGECKO_API_KEY` | empty | optional |
| `DYNAMODB_ENDPOINT_URL` / `S3_ENDPOINT_URL` | empty | LocalStack optional |
| `RUN_AWS_TESTS` | unset | integration smoke only |
| `EB_HEALTH_URL` | unset | optional health smoke |

**AWS adapters on when:** `USE_AWS_ADAPTERS=true` **or** `STORAGE_BACKEND=aws`.  
Default remains fakes for unit tests.

## Shared files touched
- `backend/app/core/config.py` — new fields + `aws_adapters_enabled()`
- `backend/app/core/deps.py` — wire Dynamo/S3/RSS; `build_job_context()`
- `backend/requirements.txt` — boto3, feedparser

## API routes added
- None (infra/adapters only)

## Deploy paths
| Path | Role |
|------|------|
| `infra/cloudformation.yml` | Dynamo + S3 + Cognito + IAM + optional EventBridge |
| `infra/README.md` | CFN steps |
| `infra/iam/*.json` | least-privilege snippets |
| `infra/lambda/` | package notes + requirements-lambda |
| `deploy/eb-deploy.md` | Beanstalk |
| `docs/.../RUNBOOK.md` | end-to-end lab steps |
| `docs/.../athena-sample.sql` | Athena demo |

## Event schema (jobs)
```json
{"job": "news"}
{"job": "price"}
{"job": "snapshot"}
```
**No FX schedule.**

## Tests
```
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```
- Unit suite offline with fakes — **must stay green**
- Mapper tests: `tests/unit/adapters/test_dynamo_mappers.py`
- Config flag tests: `tests/unit/adapters/test_config_aws_flag.py`
- Optional: `tests/integration/test_aws_smoke.py` marked `@pytest.mark.aws`, skipped unless `RUN_AWS_TESTS=1`

### Result
```
cd backend && .\.venv\Scripts\python.exe -m pytest -q
159 passed, 2 skipped, 2 warnings
```
- 2 skipped = `@pytest.mark.aws` integration tests (require `RUN_AWS_TESTS=1`)
- Full suite green offline with default fakes

## Offline-ready vs live AWS

| Ready offline | Needs Lab credentials |
|---------------|----------------------|
| All adapters + mappers | CFN deploy |
| deps wiring + defaults | EB deploy |
| Procfile / Lambda entry | Lambda + EventBridge |
| CFN/IAM templates | Cognito Hosted UI login |
| Athena SQL + runbook | Athena query over real S3 |
| Unit tests | `@pytest.mark.aws` smoke |

## Known gaps / deferred
- Live Lab deploy not executed in this agent environment (no credentials)
- Google Cognito IdP: document-only / console optional
- Next.js + CloudFront frontend: out of scope (S11 temp UI remains)
- SES email job: stretch S13
- Real vnstock live path is best-effort with fixture fallback
- News `list_recent` uses Scan (acceptable demo scale)

## Next sprint needs (S13 stretch)
- SES optional daily email
- Optional CloudFront + real frontend
- Hardening / cost report screenshots from live deploy
