#!/usr/bin/env bash
# BL-036: roll a new application version onto the EXISTING Elastic Beanstalk env.
#
#   1. Packages via scripts/package-eb.sh
#   2. Uploads the zip to the EB versions bucket
#   3. Creates a new application version
#   4. Updates openportfo-api-env in place
#
# Does not create an environment, stack, Lambda, or HTTP API.
# Does not run CloudFormation.
#
# Usage (repo root, Academy lab session must be started):
#   ./scripts/deploy-eb.sh
set -euo pipefail

APP_URL="${EB_APP_URL:-https://openportfo-api-env.eba-yrwmppgu.us-east-1.elasticbeanstalk.com}"
API_URL="${EB_API_URL:-https://7duvngr98b.execute-api.us-east-1.amazonaws.com}"
APPLICATION_NAME="${EB_APPLICATION:-openportfo-api}"
ENVIRONMENT_NAME="${EB_ENVIRONMENT:-openportfo-api-env}"
REGION="${EB_REGION:-us-east-1}"
S3_BUCKET="${EB_S3_BUCKET:-elasticbeanstalk-us-east-1-059358625850}"
S3_PREFIX="openportfo-api"
SKIP_WAIT="${1:-}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_SCRIPT="$REPO_ROOT/scripts/package-eb.sh"
ZIP_PATH="$REPO_ROOT/eb-bundle.zip"

if [ ! -x "$PACKAGE_SCRIPT" ] && [ ! -f "$PACKAGE_SCRIPT" ]; then
  echo "missing $PACKAGE_SCRIPT" >&2
  exit 1
fi
command -v aws >/dev/null || { echo "aws CLI not found" >&2; exit 1; }

echo "[deploy-eb] application: $APPLICATION_NAME"
echo "[deploy-eb] environment: $ENVIRONMENT_NAME (update existing only)"
echo "[deploy-eb] region:      $REGION"
echo "[deploy-eb] app-url:     $APP_URL"
echo "[deploy-eb] api-url:     $API_URL"

read -r ENV_ID ENV_APP ENV_STATUS ENV_HEALTH ENV_CNAME ENV_VERSION < <(
  aws elasticbeanstalk describe-environments \
    --environment-names "$ENVIRONMENT_NAME" \
    --region "$REGION" \
    --query "Environments[0].[EnvironmentId,ApplicationName,Status,Health,CNAME,VersionLabel]" \
    --output text
)

if [ -z "${ENV_ID:-}" ] || [ "$ENV_ID" = "None" ]; then
  echo "Elastic Beanstalk environment '$ENVIRONMENT_NAME' was not found. This script updates an existing env; it will not create one." >&2
  exit 1
fi
if [ "$ENV_APP" != "$APPLICATION_NAME" ]; then
  echo "Environment '$ENVIRONMENT_NAME' belongs to application '$ENV_APP', expected '$APPLICATION_NAME'." >&2
  exit 1
fi
if [ "$ENV_STATUS" = "Terminated" ]; then
  echo "Environment '$ENVIRONMENT_NAME' is Terminated. This script will not create a replacement." >&2
  exit 1
fi
if [ "$ENV_STATUS" = "Updating" ] || [ "$ENV_STATUS" = "Launching" ]; then
  echo "Environment '$ENVIRONMENT_NAME' is $ENV_STATUS. Wait until Ready, then rerun." >&2
  exit 1
fi

echo "[deploy-eb] current: $ENV_ID status=$ENV_STATUS health=$ENV_HEALTH version=$ENV_VERSION"

echo "[deploy-eb] packaging..."
API_URL="$API_URL" "$PACKAGE_SCRIPT" "$APP_URL" "$ZIP_PATH"
test -f "$ZIP_PATH" || { echo "missing $ZIP_PATH after package" >&2; exit 1; }

LABEL="v-$(date +%Y%m%d-%H%M%S)"
KEY="$S3_PREFIX/eb-bundle-$LABEL.zip"

echo "[deploy-eb] upload s3://$S3_BUCKET/$KEY"
aws s3 cp "$ZIP_PATH" "s3://$S3_BUCKET/$KEY" --region "$REGION"

echo "[deploy-eb] create application version $LABEL"
aws elasticbeanstalk create-application-version \
  --application-name "$APPLICATION_NAME" \
  --version-label "$LABEL" \
  --description "deploy-eb $LABEL" \
  --source-bundle "S3Bucket=$S3_BUCKET,S3Key=$KEY" \
  --region "$REGION" >/dev/null

echo "[deploy-eb] update-environment $ENVIRONMENT_NAME -> $LABEL"
aws elasticbeanstalk update-environment \
  --environment-name "$ENVIRONMENT_NAME" \
  --version-label "$LABEL" \
  --region "$REGION" >/dev/null

if [ "$SKIP_WAIT" = "--skip-wait" ]; then
  echo "[deploy-eb] SkipWait: update accepted. Version $LABEL is rolling out."
  exit 0
fi

echo "[deploy-eb] waiting until Ready..."
DEADLINE=$((SECONDS + 600))
STATUS="Updating"
HEALTH=""
VERSION=""
CNAME="$ENV_CNAME"
while [ "$SECONDS" -lt "$DEADLINE" ]; do
  sleep 15
  read -r STATUS HEALTH CNAME VERSION < <(
    aws elasticbeanstalk describe-environments \
      --environment-names "$ENVIRONMENT_NAME" \
      --region "$REGION" \
      --query "Environments[0].[Status,Health,CNAME,VersionLabel]" \
      --output text
  )
  echo "[deploy-eb] status=$STATUS health=$HEALTH version=$VERSION"
  if [ "$STATUS" != "Updating" ]; then
    break
  fi
done

if [ "$STATUS" != "Ready" ]; then
  echo "Environment did not become Ready (status=$STATUS health=$HEALTH version=$VERSION)" >&2
  exit 1
fi

HEALTH_URL="http://$CNAME/health"
echo "[deploy-eb] smoke $HEALTH_URL"
HEALTH_BODY="$(curl -sS --max-time 20 "$HEALTH_URL")"
echo "$HEALTH_BODY" | grep -q '"status":"ok"' || {
  echo "health check failed: $HEALTH_BODY" >&2
  exit 1
}
echo "[deploy-eb] health OK"

AUTH_ME="${API_URL%/}/api/auth/me"
echo "[deploy-eb] smoke $AUTH_ME"
GW_CODE="$(curl -sS -o /dev/null -w "%{http_code}" --max-time 20 "$AUTH_ME" || true)"
if [ "$GW_CODE" = "401" ] || [ "$GW_CODE" = "200" ]; then
  echo "[deploy-eb] Gateway proxy OK"
else
  echo "[deploy-eb] warning: Gateway /api/auth/me unexpected http_code=$GW_CODE"
fi

echo "[deploy-eb] done. env=$ENVIRONMENT_NAME version=$VERSION health=$HEALTH"
echo "[deploy-eb] UI: $APP_URL  (accept the EB cert warning; REST goes through $API_URL)"
