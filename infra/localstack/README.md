# LocalStack — local AWS for OpenPortfo

Emulates **DynamoDB** and **S3** on your machine so you can run the real boto3 adapters without an AWS account or Academy Lab session.

| Service | LocalStack (community) | Notes |
|---------|------------------------|--------|
| DynamoDB | ✅ | All 11 OpenPortfo tables |
| S3 | ✅ | `openportfo-data-local` |
| Cognito | ❌ Pro-only | Keep `AUTH_MODE=fake` |
| Lambda / EB | ❌ | Not needed for adapter testing |

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Compose v2)
- Optional: [AWS CLI](https://aws.amazon.com/cli/) v2 for manual checks
- Optional: `awslocal` (`pip install awscli-local`) — thin wrapper around AWS CLI + LocalStack endpoint

## Quick start

From the **repo root** (`a3/`):

```bash
# Start LocalStack (init script creates tables + bucket automatically)
docker compose up -d

# Wait until healthy
docker compose ps
# or:
curl http://localhost:4566/_localstack/health
```

Init hook: `infra/localstack/init-aws.sh` runs once LocalStack is ready.  
Logs:

```bash
docker compose logs -f localstack
```

Stop / wipe:

```bash
docker compose down          # keep volume (data persists)
docker compose down -v       # also delete LocalStack volume
```

## Point the backend at LocalStack

Copy the example env and enable AWS adapters + endpoints:

```bash
cd backend
copy .env.example .env   # Windows
# or: cp .env.example .env
```

Set (or uncomment) in `backend/.env`:

```env
APP_ENV=local
AUTH_MODE=fake
STORAGE_BACKEND=aws
USE_AWS_ADAPTERS=true
AWS_REGION=us-east-1

# Dummy credentials required by boto3 (LocalStack accepts any non-empty values)
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test

DYNAMODB_ENDPOINT_URL=http://localhost:4566
S3_ENDPOINT_URL=http://localhost:4566
DATA_BUCKET=openportfo-data-local

# Optional: keep market/FX offline while testing storage
MARKET_CLIENT_MODE=fixture
```

Then run the API as usual (from `backend/` with your venv):

```bash
uvicorn app.main:app --reload --port 8000
```

Unit tests still default to **memory/fakes** — do **not** set `USE_AWS_ADAPTERS` when running pytest unless you intend to hit LocalStack.

## Manual AWS CLI checks

```bash
# List tables
aws --endpoint-url=http://localhost:4566 dynamodb list-tables \
  --region us-east-1 \
  --cli-connect-timeout 5

# List buckets
aws --endpoint-url=http://localhost:4566 s3 ls \
  --region us-east-1

# Write a test object
aws --endpoint-url=http://localhost:4566 s3 cp ./README.md \
  s3://openportfo-data-local/test/readme.md \
  --region us-east-1
```

Windows PowerShell (env for one session):

```powershell
$env:AWS_ACCESS_KEY_ID = "test"
$env:AWS_SECRET_ACCESS_KEY = "test"
$env:AWS_DEFAULT_REGION = "us-east-1"
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
```

## Resources created by init

| Resource | Name |
|----------|------|
| DynamoDB | `openportfo-users`, `openportfo-holdings`, `openportfo-watchlist`, `openportfo-price-cache`, `openportfo-news`, `openportfo-settings`, `openportfo-fx`, `openportfo-rss`, `openportfo-job-runs`, `openportfo-snapshots`, `openportfo-chat-idempotency` |
| S3 | `openportfo-data-local` |
| TTL | `openportfo-price-cache` attribute `ttl`; `openportfo-chat-idempotency` attribute `expiresAt` |

Key schemas match `infra/cloudformation.yml` and the Dynamo adapters under `backend/app/adapters/dynamodb/`.

## Re-run init only

If tables were deleted but the container is still up:

```bash
docker compose exec localstack bash /etc/localstack/init/ready.d/01-init-aws.sh
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Could not connect to the endpoint URL` | `docker compose up -d` and wait for healthcheck |
| `Unable to locate credentials` | Set `AWS_ACCESS_KEY_ID=test` and `AWS_SECRET_ACCESS_KEY=test` |
| `ResourceNotFoundException` on table | Check init logs; re-run init script (above) |
| Port 4566 in use | Stop other LocalStack/DynamoDB Local processes or change the host port mapping in `docker-compose.yml` |
| Init script not executable | Linux/mac: `chmod +x infra/localstack/init-aws.sh` (Docker on Windows mounts it and LocalStack runs it with bash) |
| Cognito / Hosted UI | Not available on free LocalStack — use `AUTH_MODE=fake` and fake bearer tokens |

## Architecture note

```
Browser / curl
    → FastAPI (localhost:8000)
        → boto3 DynamoDB/S3 adapters
            → LocalStack gateway :4566
```

Production still uses real AWS (Academy Lab / CloudFormation). LocalStack is for **adapter and integration testing only**.
