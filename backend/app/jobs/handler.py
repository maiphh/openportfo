"""Thin Lambda-shaped dispatcher for scheduled jobs.

Event schema (for S12):
  {"job": "news"} | {"job": "price"} | {"job": "snapshot"}
"""

from __future__ import annotations

from typing import Any

from app.jobs.context import JobContext
from app.jobs.news_job import run_news_job
from app.jobs.price_job import run_price_job
from app.jobs.snapshot_job import run_snapshot_job
from app.ports.admin import JobRun


def handler(event: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    """Dispatch by event['job']; returns JobRun as dict."""
    job = (event or {}).get("job") or (event or {}).get("job_type")
    if not job:
        raise ValueError("event.job is required (news|price|snapshot)")

    job = str(job).lower().strip()
    if job == "news":
        run = run_news_job(ctx)
    elif job == "price":
        run = run_price_job(ctx)
    elif job == "snapshot":
        run = run_snapshot_job(ctx)
    else:
        raise ValueError(f"Unknown job: {job}")

    return _run_to_dict(run)


def _run_to_dict(run: JobRun) -> dict[str, Any]:
    return {
        "runId": run.run_id,
        "jobType": run.job_type,
        "status": run.status,
        "message": run.message,
        "counts": run.counts or {},
        "startedAt": run.started_at.isoformat() if run.started_at else None,
        "finishedAt": run.finished_at.isoformat() if run.finished_at else None,
    }


__all__ = ["handler"]
