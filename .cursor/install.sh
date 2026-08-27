#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for OpenPortfo.
# - Backend: Python 3.12 venv + runtime/dev deps + local .env (fake auth, in-memory storage).
# - Frontend: Next.js dependencies (npm ci from lockfile).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Ensuring python3.12-venv is available"
if ! python3.12 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3.12-venv
fi

echo "==> Backend: virtualenv + dependencies"
cd "$REPO_ROOT/backend"
if [ ! -x .venv/bin/python ]; then
  python3.12 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt -r requirements-dev.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created backend/.env from .env.example (fake auth + in-memory storage)"
fi
deactivate

echo "==> Frontend: npm dependencies"
cd "$REPO_ROOT/frontend"
if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi

echo "==> Install complete"
