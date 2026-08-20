"""AWS Lambda entrypoint for scheduled jobs.

Event schema (locked S10/S12):
  {"job": "news"} | {"job": "price"} | {"job": "snapshot"}

Wire AWS adapters via env (set on Lambda configuration):
  STORAGE_BACKEND=aws
  USE_AWS_ADAPTERS=true
  APP_ENV=prod
  AUTH_MODE=fake   # jobs do not verify user JWTs
  DATA_BUCKET=...
  AWS_REGION=us-east-1
  table name overrides if needed

No FX schedule — never invoke with job=fx.
"""

from __future__ import annotations

from typing import Any

from app.core.config import clear_settings_cache, get_settings
from app.core.deps import build_job_context
from app.jobs.handler import handler as job_handler


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """Lambda handler: build AWS JobContext and dispatch."""
    # Ensure settings re-read env on cold/warm with config updates
    clear_settings_cache()
    settings = get_settings()
    # Fail fast before constructing any repository or making an AWS call. Local
    # Lambda-shaped tests remain supported because non-production settings are
    # intentionally outside the production job validation contract.
    settings.validate_job_runtime()
    ctx = build_job_context(settings)
    result = job_handler(event or {}, ctx)
    return result


# Alias used by some package layouts
lambda_handler = handler

__all__ = ["handler", "lambda_handler"]
