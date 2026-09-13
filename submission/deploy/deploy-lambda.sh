#!/usr/bin/env bash
# BL-037: update the EXISTING openportfo-jobs Lambda and EventBridge rules.
# Does not create a function. Does not run CloudFormation.
set -euo pipefail

FUNCTION_NAME="${JOBS_LAMBDA_NAME:-openportfo-jobs}"
REGION="${EB_REGION:-us-east-1}"
ACCOUNT="059358625850"
FUNCTION_ARN="arn:aws:lambda:${REGION}:${ACCOUNT}:function:${FUNCTION_NAME}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZIP_PATH="$REPO_ROOT/openportfo-jobs.zip"
DOTENV="$REPO_ROOT/backend/.env"

command -v aws >/dev/null || { echo "aws CLI not found" >&2; exit 1; }

echo "[deploy-lambda] function: $FUNCTION_NAME (update existing only)"
echo "[deploy-lambda] region:   $REGION"

if ! aws lambda get-function-configuration --function-name "$FUNCTION_NAME" --region "$REGION" \
    --query "{Name:FunctionName,Runtime:Runtime,Handler:Handler}" --output json >/tmp/openportfo-fn.json; then
  echo "Lambda function '$FUNCTION_NAME' was not found. This script updates an existing function; it will not create one." >&2
  exit 1
fi
echo "[deploy-lambda] current: $(cat /tmp/openportfo-fn.json)"

echo "[deploy-lambda] packaging Linux zip..."
"$REPO_ROOT/scripts/package-lambda.sh" "$ZIP_PATH"
test -f "$ZIP_PATH"

echo "[deploy-lambda] update-function-code"
aws lambda update-function-code --function-name "$FUNCTION_NAME" --zip-file "fileb://$ZIP_PATH" \
  --region "$REGION" --query "{CodeSize:CodeSize,LastModified:LastModified}" --output json

for _ in $(seq 1 40); do
  ST=$(aws lambda get-function-configuration --function-name "$FUNCTION_NAME" --region "$REGION" --query LastUpdateStatus --output text)
  echo "[deploy-lambda] LastUpdateStatus=$ST"
  [ "$ST" = "Successful" ] && break
  [ "$ST" = "Failed" ] && { echo "Lambda update Failed" >&2; exit 1; }
  sleep 3
done
[ "$ST" = "Successful" ] || { echo "Lambda not ready (LastUpdateStatus=$ST)" >&2; exit 1; }

python3 - "$FUNCTION_NAME" "$REGION" "$DOTENV" <<'PY'
import json, os, subprocess, sys, tempfile
fn, region, dotenv = sys.argv[1:]
raw = subprocess.check_output([
    "aws", "lambda", "get-function-configuration",
    "--function-name", fn, "--region", region,
    "--query", "Environment.Variables", "--output", "json",
], text=True)
vars_ = json.loads(raw) or {}
wanted = ("SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_HOST", "SMTP_PORT", "SES_FROM_EMAIL")
if os.path.isfile(dotenv):
    with open(dotenv, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k in wanted and v:
                vars_[k] = v
has_smtp = bool(vars_.get("SMTP_USERNAME") and vars_.get("SMTP_PASSWORD"))
print(f"[deploy-lambda] update-function-configuration (env merge; SMTP present: {has_smtp})", flush=True)
fd, path = tempfile.mkstemp(suffix=".json")
os.close(fd)
try:
    with open(path, "w", encoding="ascii") as f:
        json.dump({"Variables": vars_}, f)
    subprocess.check_call([
        "aws", "lambda", "update-function-configuration",
        "--function-name", fn, "--region", region,
        "--environment", f"file://{path}",
        "--query", "{LastModified:LastModified,Timeout:Timeout}",
        "--output", "json",
    ])
finally:
    try:
        os.remove(path)
    except OSError:
        pass
PY

for _ in $(seq 1 40); do
  ST=$(aws lambda get-function-configuration --function-name "$FUNCTION_NAME" --region "$REGION" --query LastUpdateStatus --output text)
  echo "[deploy-lambda] LastUpdateStatus=$ST"
  [ "$ST" = "Successful" ] && break
  [ "$ST" = "Failed" ] && exit 1
  sleep 3
done

put_job_rule() {
  local name="$1" cron="$2" desc="$3" tid="$4" input="$5" sid="$6"
  echo "[deploy-lambda] put-rule $name $cron"
  aws events put-rule --name "$name" --region "$REGION" --schedule-expression "$cron" --state ENABLED --description "$desc" >/dev/null
  local tgt
  tgt="$(mktemp)"
  python3 -c "import json,sys; json.dump([{'Id':sys.argv[1],'Arn':sys.argv[2],'Input':sys.argv[3]}], open(sys.argv[4],'w'))" \
    "$tid" "$FUNCTION_ARN" "$input" "$tgt"
  aws events put-targets --rule "$name" --region "$REGION" --targets "file://$tgt" >/dev/null
  rm -f "$tgt"
  local src="arn:aws:events:${REGION}:${ACCOUNT}:rule/${name}"
  set +e
  err=$(aws lambda add-permission --function-name "$FUNCTION_NAME" --region "$REGION" \
    --statement-id "$sid" --action lambda:InvokeFunction --principal events.amazonaws.com \
    --source-arn "$src" 2>&1)
  code=$?
  set -e
  if [ "$code" -ne 0 ] && ! echo "$err" | grep -q ResourceConflictException; then
    echo "$err" >&2
    exit 1
  fi
}

put_job_rule "openportfo-job-news" "cron(0 17 * * ? *)" "Daily news ingest at 00:00 ICT (no FX)" "NewsJob" '{"job":"news"}' "AllowEventBridgeNews"
put_job_rule "openportfo-job-price" "cron(0 17 * * ? *)" "Price cache warm at 00:00 ICT (no FX)" "PriceJob" '{"job":"price"}' "AllowEventBridgePrice"
put_job_rule "openportfo-job-snapshot" "cron(0 17 * * ? *)" "Portfolio snapshot at 00:00 ICT (no FX)" "SnapshotJob" '{"job":"snapshot"}' "AllowEventBridgeSnapshot"
put_job_rule "openportfo-job-email" "cron(15 17 * * ? *)" "Daily portfolio email at 00:15 ICT (after snapshot)" "EmailJob" '{"job":"email"}' "AllowEventBridgeEmail"

OUT="$REPO_ROOT/.workflows/runs/lambda-email-invoke.json"
mkdir -p "$(dirname "$OUT")"
PAYLOAD="$(mktemp)"
printf '%s\n' '{"job":"email"}' > "$PAYLOAD"
echo "[deploy-lambda] invoke {\"job\":\"email\"}"
aws lambda invoke --function-name "$FUNCTION_NAME" --region "$REGION" \
  --cli-binary-format raw-in-base64-out --payload "file://$PAYLOAD" "$OUT" \
  --query "{StatusCode:StatusCode,FunctionError:FunctionError}" --output json
rm -f "$PAYLOAD"
echo "[deploy-lambda] invoke result: $OUT"
echo "[deploy-lambda] done. function=$FUNCTION_NAME"
echo "[deploy-lambda] schedules: news/price/snapshot 00:00 ICT; email 00:15 ICT"
