#!/usr/bin/env bash
# Package openportfo-jobs.zip with Linux (manylinux) wheels for Lambda.
# Requires Docker. Output: <repo>/openportfo-jobs.zip
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_ZIP="${1:-$REPO_ROOT/openportfo-jobs.zip}"

command -v docker >/dev/null || { echo "Docker is required to build a Linux Lambda zip" >&2; exit 1; }
test -f "$REPO_ROOT/infra/lambda/requirements-lambda.txt"
test -f "$REPO_ROOT/backend/lambda_handler.py"
test -d "$REPO_ROOT/backend/app"
test -f "$REPO_ROOT/infra/lambda/package-in-container.sh"

echo "[package-lambda] docker linux/amd64 pip + app -> $OUTPUT_ZIP"
docker run --rm --platform linux/amd64 \
  -v "$REPO_ROOT:/opt/src" -w /opt/src \
  public.ecr.aws/sam/build-python3.12:latest \
  bash /opt/src/infra/lambda/package-in-container.sh

BUILT="$REPO_ROOT/openportfo-jobs.zip"
test -f "$BUILT"
if [ "$OUTPUT_ZIP" != "$BUILT" ]; then
  cp "$BUILT" "$OUTPUT_ZIP"
fi
echo "[package-lambda] wrote $OUTPUT_ZIP"
