# Live deploy status (AWS Academy Learner Lab)

**Account:** `059358625850`  
**Region:** `us-east-1`  
**Date:** 2026-08-09  
**Identity:** `voclabs` (Learner Lab)

## Deployed now

| Resource | Status | Name / ID |
|----------|--------|-----------|
| CloudFormation stack | CREATE complete | `openportfo-data` (lab template: `infra/cloudformation-lab.yml`) |
| DynamoDB tables | live | `openportfo-users`, `holdings`, `watchlist`, `price-cache`, `news`, `settings`, `fx`, `rss`, `job-runs`, `snapshots` |
| S3 data bucket | live | `openportfo-data-databucket-bnfamm6trgmo` |
| Cognito User Pool | live | `us-east-1_YRFHh9x1r` |
| Cognito App Client | live | `5vgnrnd9qp8ae0msbh4q6774gh` |
| Cognito Hosted UI | live | `https://openportfo-11f1.auth.us-east-1.amazoncognito.com` |
| Lambda jobs | live + invoked | `openportfo-jobs` (role: `LabRole`) |
| **Elastic Beanstalk API** | **live** | `openportfo-api` / `openportfo-api-env` |
| EB URL | **200 /health** | http://openportfo-api-env.eba-yrwmppgu.us-east-1.elasticbeanstalk.com |
| Local adapter smoke | OK | profile + holding write + S3 put/get |
| EB smoke | OK | `GET /health` → `{"status":"ok"}`; `GET /api/auth/me` with `fake:eb-smoke` → 200 Dynamo profile |

## Not deployed yet

| Resource | Reason |
|----------|--------|
| EventBridge schedules | Optional; manual Lambda invoke works |
| CloudFront / Next.js frontend | Out of scope S12 |
| Custom IAM roles | Lab blocks `iam:CreateRole` — use `LabRole` / `LabInstanceProfile` |

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
MARKET_CLIENT_MODE=fixture
```

## Lab notes

1. Full CFN (`infra/cloudformation.yml`) **fails** on IAM role create — use **`cloudformation-lab.yml`**.
2. Lambda package must use **manylinux** wheels (not Windows).
3. Do not set `AWS_REGION` as a Lambda env var (reserved).
4. Learner Lab tears down when session ends — re-deploy stack after **Start Lab**.

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
