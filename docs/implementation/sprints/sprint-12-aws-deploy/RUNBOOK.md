# Sprint 12 — Deploy runbook (AWS Academy Learner Lab)

Region default: **us-east-1**. No secrets in git.

## 0. Cost guardrails

Before heavy deploy:

1. Billing → Budgets (if lab allows) or personal alert notes: **$10** and **$30** thresholds.
2. Prefer **single-instance** EB, **PAY_PER_REQUEST** DynamoDB (CFN default), Lambda short timeout.
3. **Stop Lab** when done — Learner Lab tears down resources on session end in many cohorts; still delete stack if reusable account.

## 1. Start Lab → credentials

1. Open AWS Academy → **Learner Lab** → **Start Lab**.
2. **AWS Details** → copy CLI credentials (or open Console).
3. Configure CLI:

```bash
aws configure set region us-east-1
# paste access key / secret / session token from lab
aws sts get-caller-identity
```

## 2. Deploy data plane (CloudFormation)

```bash
cd /path/to/a3   # repo root
aws cloudformation deploy \
  --region us-east-1 \
  --stack-name openportfo-data \
  --template-file infra/cloudformation.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides ProjectPrefix=openportfo
```

Capture outputs (`DataBucketName`, Cognito ids, `EBInstanceProfileName`, `LambdaExecutionRoleArn`).

See also: [`infra/README.md`](../../../../infra/README.md).

## 3. Deploy Elastic Beanstalk (API)

Follow [`deploy/eb-deploy.md`](../../../../deploy/eb-deploy.md).

Minimum env on EB:

```text
APP_ENV=prod
STORAGE_BACKEND=aws
USE_AWS_ADAPTERS=true
AUTH_MODE=cognito   # or fake for first smoke
AWS_REGION=us-east-1
DATA_BUCKET=<DataBucketName>
COGNITO_USER_POOL_ID=...
COGNITO_APP_CLIENT_ID=...
COGNITO_REGION=us-east-1
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://<eb-url>
```

Smoke:

```bash
curl -sS https://<eb-url>/health
```

## 4. Deploy Lambda jobs + EventBridge

1. Package per [`infra/lambda/README.md`](../../../../infra/lambda/README.md).
2. Create function with **LambdaExecutionRoleArn**.
3. Set same table/bucket env vars as API (`STORAGE_BACKEND=aws`, `DATA_BUCKET`, …).
4. Manual invoke:

```bash
aws lambda invoke --function-name openportfo-jobs \
  --payload '{"job":"news"}' out.json
```

5. Optional: update CFN with `CreateEventBridgeRules=true` and `JobsLambdaArn`.

**Schedules only:** `news`, `price`, `snapshot`. **No FX cron.**

## 5. Smoke checklist (demo)

| Step | Expect |
|------|--------|
| `GET /health` | 200 `{"status":"ok"}` or similar |
| Auth | Cognito Hosted UI → ID token → `GET /api/auth/me` **or** `AUTH_MODE=fake` + `Authorization: Bearer fake:<sub>` |
| One write | `POST` holding or watchlist → 200/201 |
| One job | Lambda invoke `{"job":"snapshot"}` → success in payload + CloudWatch log |
| Athena | Run query in `athena-sample.sql` after snapshot wrote S3 |

## 6. Cognito notes

- JWT verify uses **public JWKS** — EB role needs **no** `cognito-idp:*` for verify.
- Callbacks: localhost:3000 / 5173 + CloudFront placeholder (CFN parameters).
- Google IdP optional (console); not required for MVP.

## 7. Offline vs live

| Artifact | Offline-ready |
|----------|----------------|
| Unit tests (fakes) | Yes — default |
| Dynamo/S3 adapters + mappers | Yes (code) |
| CFN / IAM / Procfile / Lambda entry | Yes (templates) |
| Live EB / Lambda / Cognito / Athena | Needs Lab credentials |

## 8. Teardown

```bash
aws cloudformation delete-stack --stack-name openportfo-data --region us-east-1
# terminate EB env + Lambda function if created outside CFN
```
