#!/usr/bin/env bash
# Runs inside LocalStack when the container is ready (ready.d hook).
# Creates OpenPortfo DynamoDB tables + S3 data bucket to match infra/cloudformation.yml.
set -euo pipefail

echo "[localstack-init] Creating OpenPortfo resources..."

export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# awslocal is preinstalled in the LocalStack image
AWSCMD="awslocal"

PREFIX="${PROJECT_PREFIX:-openportfo}"
BUCKET="${DATA_BUCKET:-openportfo-data-local}"

create_table() {
  local name="$1"
  shift
  if $AWSCMD dynamodb describe-table --table-name "$name" >/dev/null 2>&1; then
    echo "[localstack-init] Table already exists: $name"
    return 0
  fi
  echo "[localstack-init] Creating table: $name"
  $AWSCMD dynamodb create-table --table-name "$name" "$@" >/dev/null
}

# --- DynamoDB tables (keys match backend adapters + cloudformation.yml) ---

# users: PK userId
create_table "${PREFIX}-users" \
  --attribute-definitions AttributeName=userId,AttributeType=S \
  --key-schema AttributeName=userId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# holdings: PK userId, SK sk
create_table "${PREFIX}-holdings" \
  --attribute-definitions \
    AttributeName=userId,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=userId,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# watchlist: PK userId, SK sk
create_table "${PREFIX}-watchlist" \
  --attribute-definitions \
    AttributeName=userId,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=userId,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# price-cache: PK pk (+ TTL attr name registered separately)
create_table "${PREFIX}-price-cache" \
  --attribute-definitions AttributeName=pk,AttributeType=S \
  --key-schema AttributeName=pk,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Enable TTL on price-cache (attribute: ttl) — ignore if already set
if ! $AWSCMD dynamodb describe-time-to-live --table-name "${PREFIX}-price-cache" 2>/dev/null \
  | grep -q '"TimeToLiveStatus": "ENABLED"'; then
  $AWSCMD dynamodb update-time-to-live \
    --table-name "${PREFIX}-price-cache" \
    --time-to-live-specification "Enabled=true,AttributeName=ttl" >/dev/null || true
fi

# news: PK pk, SK sk
create_table "${PREFIX}-news" \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# settings: PK pk, SK sk
create_table "${PREFIX}-settings" \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# fx: PK pk, SK sk
create_table "${PREFIX}-fx" \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# rss: PK pk, SK sk
create_table "${PREFIX}-rss" \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# job-runs: PK pk, SK sk
create_table "${PREFIX}-job-runs" \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# snapshots: PK userId, SK sk
create_table "${PREFIX}-snapshots" \
  --attribute-definitions \
    AttributeName=userId,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=userId,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# chat-idempotency: PK userId, SK requestId (+ TTL expiresAt)
create_table "${PREFIX}-chat-idempotency" \
  --attribute-definitions \
    AttributeName=userId,AttributeType=S \
    AttributeName=requestId,AttributeType=S \
  --key-schema \
    AttributeName=userId,KeyType=HASH \
    AttributeName=requestId,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

if ! $AWSCMD dynamodb describe-time-to-live --table-name "${PREFIX}-chat-idempotency" 2>/dev/null \
  | grep -q '"TimeToLiveStatus": "ENABLED"'; then
  $AWSCMD dynamodb update-time-to-live \
    --table-name "${PREFIX}-chat-idempotency" \
    --time-to-live-specification "Enabled=true,AttributeName=expiresAt" >/dev/null || true
fi

# --- S3 data bucket ---
if $AWSCMD s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "[localstack-init] Bucket already exists: $BUCKET"
else
  echo "[localstack-init] Creating bucket: $BUCKET"
  $AWSCMD s3 mb "s3://${BUCKET}" >/dev/null
fi

echo "[localstack-init] Done."
echo "[localstack-init] Tables:"
$AWSCMD dynamodb list-tables --output text || true
echo "[localstack-init] Buckets:"
$AWSCMD s3 ls || true
