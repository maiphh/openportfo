# Elastic Beanstalk deploy (FastAPI)

## Prerequisites

1. Learner Lab running; region **us-east-1**
2. CloudFormation stack `openportfo-data` deployed (`infra/README.md`)
3. EB CLI optional; Console works fine for demo

## Package source

From repo, zip the **backend** app contents (not the whole monorepo):

```powershell
cd D:\rmit\cloud\a3\backend
# include app/, Procfile, requirements.txt, .ebextensions/
Compress-Archive -Path app,Procfile,requirements.txt,.ebextensions -DestinationPath ..\openportfo-api.zip -Force
```

Or use EB CLI:

```bash
cd backend
eb init -p python-3.12 openportfo-api --region us-east-1
eb create openportfo-api-env \
  --instance_profile openportfo-eb-instance-profile \
  --single
```

## Environment properties (no secrets in git)

| Key | Example |
|-----|---------|
| `APP_ENV` | `prod` |
| `AUTH_MODE` | `cognito` (or `fake` for lab smoke without Hosted UI) |
| `STORAGE_BACKEND` | `aws` |
| `USE_AWS_ADAPTERS` | `true` |
| `AWS_REGION` | `us-east-1` |
| `DATA_BUCKET` | *(CFN output DataBucketName)* |
| `COGNITO_REGION` | `us-east-1` |
| `COGNITO_USER_POOL_ID` | *(CFN)* |
| `COGNITO_APP_CLIENT_ID` | *(CFN)* |
| `ADMIN_EMAILS` | Comma-separated grant-only bootstrap emails (optional; set in EB console) |
| `LLM_TEMPERATURE` / `LLM_TOP_P` | *(optional runtime defaults)* |
| `LLM_SYSTEM_PROMPT_EXTRA` | *(optional bounded prompt suffix; no secrets)* |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173,https://YOUR_EB_URL` |
| `MARKET_CLIENT_MODE` | `fixture` or `http` |
| `EXCHANGE_RATE_API_KEY` | *(optional; admin FX only — set in EB console, never commit)* |

Table names default to `openportfo-*` matching CFN.

## Health

- Process health check path: `/health`
- After deploy: `curl https://YOUR_EB_ENV.elasticbeanstalk.com/health`

## Instance profile

Attach CFN output `EBInstanceProfileName` (`openportfo-eb-instance-profile`) so the instance can call DynamoDB + S3 without access keys in env.
The attached profile must include `dynamodb:TransactWriteItems` on the Users and Settings table ARNs for last-admin role changes. Never grant or log the `ADMIN_EMAILS` value to browser clients.
