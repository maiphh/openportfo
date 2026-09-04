# OpenPortfo jobs Lambda package

## Handler

- Module: `lambda_handler.handler` (file `backend/lambda_handler.py`)
- Or: `app.jobs.lambda_entry.handler`
- Event: `{"job":"news"}` | `{"job":"price"}` | `{"job":"snapshot"}`
- Manual backfill (BL-030): `{"job":"snapshot","date":"YYYY-MM-DD"}` (also `snapshot_date` alias)
- **No FX job / schedule**

## Build zip (from repo root, Linux/WSL preferred for manylinux wheels)

```bash
rm -rf /tmp/openportfo-lambda && mkdir -p /tmp/openportfo-lambda
pip install -r infra/lambda/requirements-lambda.txt -t /tmp/openportfo-lambda
# copy application code
cp -r backend/app /tmp/openportfo-lambda/
cp backend/lambda_handler.py /tmp/openportfo-lambda/
cd /tmp/openportfo-lambda && zip -r9 ../openportfo-jobs.zip . && cd -
```

On Windows PowerShell (simplified):

```powershell
$dest = "$env:TEMP\openportfo-lambda"
Remove-Item -Recurse -Force $dest -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $dest | Out-Null
pip install -r infra\lambda\requirements-lambda.txt -t $dest
Copy-Item -Recurse backend\app $dest\app
Copy-Item backend\lambda_handler.py $dest\
Compress-Archive -Path "$dest\*" -DestinationPath openportfo-jobs.zip -Force
```

## Create function

```bash
aws lambda create-function \
  --region us-east-1 \
  --function-name openportfo-jobs \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT:role/openportfo-lambda-jobs-role \
  --handler lambda_handler.handler \
  --timeout 120 \
  --memory-size 512 \
  --zip-file fileb://openportfo-jobs.zip \
  --environment "Variables={
    APP_ENV=prod,
    STORAGE_BACKEND=aws,
    USE_AWS_ADAPTERS=true,
    AUTH_MODE=fake,
    AWS_REGION=us-east-1,
    DATA_BUCKET=YOUR_BUCKET,
    MARKET_CLIENT_MODE=fixture
  }"
```

Use CFN output `LambdaExecutionRoleArn` for `--role`.

## Manual invoke (smoke)

```bash
aws lambda invoke \
  --region us-east-1 \
  --function-name openportfo-jobs \
  --payload '{"job":"news"}' \
  out.json && cat out.json
```

Manual snapshot backfill (BL-030 — Lambda console Test or CLI):

```bash
aws lambda invoke \
  --region us-east-1 \
  --function-name openportfo-jobs \
  --payload '{"job":"snapshot","date":"2026-09-03"}' \
  out-snap.json && cat out-snap.json
```

Omitted `date` writes UTC today; invalid `date` fails fast with
`event.date must be YYYY-MM-DD` and writes nothing.

## EventBridge

Enable schedules by updating CFN with `CreateEventBridgeRules=true` and `JobsLambdaArn`,  
or create rules manually with constant JSON input `{"job":"news"}` etc.  
**Do not create an FX rule.**
