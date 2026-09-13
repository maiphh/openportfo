#!/usr/bin/env bash
# Runs inside public.ecr.aws/sam/build-python3.12 (linux/amd64).
# Repo is mounted at /opt/src.
set -euo pipefail
rm -rf /tmp/openportfo-lambda
mkdir -p /tmp/openportfo-lambda
pip install --no-cache-dir -r /opt/src/infra/lambda/requirements-lambda.txt -t /tmp/openportfo-lambda
cp -a /opt/src/backend/app /tmp/openportfo-lambda/app
cp /opt/src/backend/lambda_handler.py /tmp/openportfo-lambda/
find /tmp/openportfo-lambda -type d -name __pycache__ -prune -exec rm -rf {} +
find /tmp/openportfo-lambda -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
rm -f /opt/src/openportfo-jobs.zip
cd /tmp/openportfo-lambda && zip -qr /opt/src/openportfo-jobs.zip .
ls -lh /opt/src/openportfo-jobs.zip
