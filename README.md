# OpenPortfo

Cloud-based crypto + Vietnam stock portfolio tracker (RMIT Cloud Computing, Assessment 3).

FastAPI backend on port **8000**. Optional Vite viewer on **5173**. Local AWS (DynamoDB + S3) via LocalStack on **4566**.

## Prerequisites

- Python **3.12** (`py -3.12` on Windows). Elastic Beanstalk and Lambda use 3.12; **do not use 3.14** — `pydantic_core` will fail to import.
- Node.js **18+** (only if you run the temp frontend)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (only if you use LocalStack)

## 1. Start the API

From the repo root:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

macOS / Linux:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

The default `.env.example` uses in-memory fakes (`AUTH_MODE=fake`, `STORAGE_BACKEND=memory`). For live VN stock quotes set `MARKET_CLIENT_MODE=http` (requires the `vnstock` package, already in `requirements.txt`).

Check it:

- Health: http://127.0.0.1:8000/health → `{"status":"ok"}`
- Docs: http://127.0.0.1:8000/docs

Local auth token: `fake:alice` (or any `fake:<username>`).

## 2. Start the temp frontend (optional)

In a second terminal:

```powershell
cd frontend-temp
npm install
npm run dev
```

Open http://localhost:5173. Paste a token such as `fake:alice` and click **Save**.

The UI talks to `http://127.0.0.1:8000` by default (`VITE_API_URL`).

## 3. LocalStack (optional — real DynamoDB/S3 adapters)

From the **repo root**:

```powershell
docker compose up -d
```

In `backend/.env` set:

```env
APP_ENV=local
AUTH_MODE=fake
STORAGE_BACKEND=aws
USE_AWS_ADAPTERS=true
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
DYNAMODB_ENDPOINT_URL=http://localhost:4566
S3_ENDPOINT_URL=http://localhost:4566
DATA_BUCKET=openportfo-data-local
```

Then start uvicorn as in step 1. Full notes: [infra/localstack/README.md](infra/localstack/README.md).

```powershell
docker compose down      # stop, keep data
docker compose down -v   # stop and wipe LocalStack volume
```

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest
```

Leave `USE_AWS_ADAPTERS` unset (or `false`) so unit tests stay on in-memory fakes.

## More docs

| Topic | Doc |
|-------|-----|
| Temp UI screens and auth | [frontend-temp/README.md](frontend-temp/README.md) |
| LocalStack tables / troubleshooting | [infra/localstack/README.md](infra/localstack/README.md) |
| AWS CloudFormation (Learner Lab) | [infra/README.md](infra/README.md) |
| Elastic Beanstalk deploy | [deploy/eb-deploy.md](deploy/eb-deploy.md) |
| Architecture | [docs/architecture-design.md](docs/architecture-design.md) |
