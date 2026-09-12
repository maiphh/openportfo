# OpenPortfo jobs Lambda package

## Handler

- Module: `lambda_handler.handler` (file `backend/lambda_handler.py`)
- Or: `app.jobs.lambda_entry.handler`
- Event: `{"job":"news"}` | `{"job":"price"}` | `{"job":"snapshot"}` | `{"job":"email"}`
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
    MARKET_CLIENT_MODE=fixture,
    SES_FROM_EMAIL=verified-from@example.com
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

Omitted `date` writes **Asia/Ho_Chi_Minh today** (not UTC); invalid `date` fails fast with
`event.date must be YYYY-MM-DD` and writes nothing.

Snapshot always force-refreshes prices before computing PnL.

Daily email (opt-in users; admin `jobs.email` + `emailEnabled`):

```bash
aws lambda invoke \
  --region us-east-1 \
  --function-name openportfo-jobs \
  --payload '{"job":"email"}' \
  out-email.json && cat out-email.json
```

SES sandbox: verify `SES_FROM_EMAIL` and each recipient. Set that env on the jobs Lambda.

**AWS Academy Learner Lab:** SES is not available. `voclabs` / `LabRole` cannot call `ses:*` (`AllowedByOrganizations: false` plus identity deny). `iam:PutRolePolicy` on `LabRole` is also denied, so you cannot attach `ses:SendEmail` yourself. LocalStack does not deliver to Gmail.

**Demo fallback (Gmail SMTP):** set `SMTP_USERNAME` + `SMTP_PASSWORD` (Google App Password). Defaults are `smtp.gmail.com:587`. The email job uses SMTP instead of SES. Do not commit the App Password.

1. Turn on [2-Step Verification](https://myaccount.google.com/signinoptions/two-step-verification).
2. Create an App Password at [App passwords](https://myaccount.google.com/apppasswords) (app: Mail).
3. Put the 16-character password in `backend/.env` as `SMTP_PASSWORD` (spaces optional). `SMTP_USERNAME` is your Gmail address.

## EventBridge

Enable schedules by updating CFN with `CreateEventBridgeRules=true` and `JobsLambdaArn`,  
or create rules manually:

| Job | ICT | UTC cron | Input |
|-----|-----|----------|-------|
| news, price, snapshot | 00:00 | `cron(0 17 * * ? *)` | `{"job":"..."}` |
| email | 00:15 | `cron(15 17 * * ? *)` | `{"job":"email"}` |

**Do not create an FX rule.**
