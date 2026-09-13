# Live deploy status (AWS Academy Learner Lab)

**Account:** `059358625850`  
**Region:** `us-east-1`  
**Date:** 2026-09-13 (live re-verified; prior edition 2026-08-09)  
**Identity:** `voclabs` (Learner Lab)

## Deployed now (verified 2026-09-13, read-only)

| Resource | Status | Name / ID |
|----------|--------|-----------|
| CloudFormation stack | `openportfo-data` present (`UPDATE_ROLLBACK_COMPLETE` — Gateway **not** via CFN; see runbook) | lab template `infra/cloudformation-lab.yml` |
| DynamoDB tables | live | `openportfo-users`, `holdings`, `watchlist`, `price-cache`, `news`, `settings`, `fx`, `rss`, `job-runs`, `snapshots` |
| S3 data bucket | live | `openportfo-data-databucket-bnfamm6trgmo` |
| Cognito User Pool | live | `us-east-1_YRFHh9x1r` |
| Cognito App Client | live | `5vgnrnd9qp8ae0msbh4q6774gh` |
| Cognito Hosted UI | live | `https://openportfo-11f1.auth.us-east-1.amazoncognito.com` |
| Lambda jobs | live `Active`, `LastModified 2026-09-13T10:05:38Z`, `CodeSize 20469631`, `python3.12`, `LabRole` | `openportfo-jobs` (`lambda_handler.handler`) |
| EventBridge rules | 4x `ENABLED` | `openportfo-job-news/price/snapshot @cron(0 17 * * ? *)`, `openportfo-job-email @cron(15 17 * * ? *)`; `openportfo-job-news` target `NewsJob → openportfo-jobs Input {"job":"news"}` |
| HTTP API Gateway | live | `7duvngr98b` (`https://7duvngr98b.execute-api.us-east-1.amazonaws.com`); route `ANY /api/{proxy+}` → `HTTP_PROXY ANY → http://...EB.../api/{proxy}` (`Payload 1.0`, `Timeout 30000`); stage `$default` `AutoDeploy` |
| **Elastic Beanstalk API** | **live Ready/Green** | `openportfo-api` / `openportfo-api-env` (`e-njepgizthf`), `VersionLabel v-20260913-http-api`, `DateUpdated 2026-09-13T09:20:25Z` |
| EB URL | **200 /health** | http://openportfo-api-env.eba-yrwmppgu.us-east-1.elasticbeanstalk.com → `{"status":"ok"}` |
| Gateway smoke | OK (2026-09-13) | `GET https://7duvngr98b.../api/auth/me → 401 {"detail":"Missing authorization header"}` (FastAPI through Gateway) |
| Local adapter smoke | OK | profile + holding write + S3 put/get |
| EB smoke | OK | `GET /health` → `{"status":"ok"}`; `GET /api/auth/me` with `fake:eb-smoke` → 200 Dynamo profile |

## Not deployed / still constrained

| Resource | Reason |
|----------|--------|
| CloudFront / S3-website UI | Lab blocks `CloudFront` — UI served from EB single-hosting (BL-031); S3 remains the **data** bucket (history/snapshots) for Athena story |
| Full-CFN Gateway path | `openportfo-data` is `UPDATE_ROLLBACK_COMPLETE` — live Gateway `7duvngr98b` was created via `apigatewayv2` + EB `-ApiUrl` bundle per `docs/runbooks/http-api-gateway.md`, not via stack update |
| Custom IAM roles | Lab blocks `iam:CreateRole` — use `LabRole` / `LabInstanceProfile` |
| Live CoinGecko/vnstock | Live Lambda + EB still run `MARKET_CLIENT_MODE=fixture` (see env below) — third-party automation beyond FX/RSS needs an `http` switch + verification |

> Lab recycles on session end — after **Start Lab**, re-run `scripts/deploy-eb.ps1` + `scripts/deploy-lambda.ps1` (no `SkipEventBridge`) and re-verify this page's smokes.

## Env for apps (no secrets)

```text
APP_ENV=prod
STORAGE_BACKEND=aws
USE_AWS_ADAPTERS=true
AUTH_MODE=fake          # or cognito
DATA_BUCKET=openportfo-data-databucket-bnfamm6trgmo
COGNITO_USER_POOL_ID=us-east-1_YRFHh9x1r
COGNITO_APP_CLIENT_ID=5vgnrnd9qp8ae0msbh4q6774gh
COGNITO_REGION=us-east-1
MARKET_CLIENT_MODE=fixture   # live 2026-09-13 still fixture; switch to `http` for live CoinGecko/vnstock demo
```

> Env shows keys only — no secrets. Lambda SMTP vars are set live but never committed here.

## Lab notes

1. Full CFN (`infra/cloudformation.yml`) **fails** on IAM role create — use **`cloudformation-lab.yml`**. Do **not** `cloudformation deploy` the full lab template to enable Gateway while `openportfo-data` is `UPDATE_ROLLBACK_COMPLETE` — use `apigatewayv2` per `docs/runbooks/http-api-gateway.md`.
2. Lambda package must use **manylinux** wheels (not Windows).
3. Do not set `AWS_REGION` as a Lambda env var (reserved).
4. Learner Lab tears down when session ends — after **Start Lab**, re-run `.\scripts\deploy-eb.ps1` + `.\scripts\deploy-lambda.ps1` (no `SkipEventBridge`), then re-verify the smokes above.

## Public API smoke

```bash
curl http://openportfo-api-env.eba-yrwmppgu.us-east-1.elasticbeanstalk.com/health
# {"status":"ok"}

curl -H "Authorization: Bearer fake:alice" \
  http://openportfo-api-env.eba-yrwmppgu.us-east-1.elasticbeanstalk.com/api/auth/me
```

Temp UI: set API URL to the EB URL and token `fake:alice`.

## Lambda smoke

```bash
aws lambda invoke --function-name openportfo-jobs --cli-binary-format raw-in-base64-out --payload "{\"job\":\"news\"}" out.json
```

Example success: `{"jobType":"news","status":"success",...}`

## EB packaging notes (Windows)

1. Zip with **forward slashes** (Python `zipfile` / `Path.as_posix()`). .NET `ZipFile` on Windows breaks Linux `unzip`.
2. Include `tests/fakes/auth.py` when `AUTH_MODE=fake`.
3. Instance profile: **`LabInstanceProfile`**.
