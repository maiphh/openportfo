"""Thin Lambda-shaped dispatcher for scheduled jobs.

Event schema (for S12 + BL-030):
  {"job": "news"} | {"job": "price"} | {"job": "snapshot"}
  {"job": "snapshot", "date": "YYYY-MM-DD"}  # manual backfill (also snapshot_date alias)
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.jobs.context import JobContext
from app.jobs.news_job import run_news_job
from app.jobs.price_job import run_price_job
from app.jobs.snapshot_job import run_snapshot_job
from app.ports.admin import JobRun


def _extract_snapshot_date(event: dict[str, Any]) -> str | None:
    """Return validated snapshot date override or None for today.

    Accepts ``date`` (primary) or ``snapshot_date`` alias; empty → None.
    Raises ``ValueError("event.date must be YYYY-MM-DD")`` on invalid.
    """
    raw = event.get("date", None)
    if raw is None:
        raw = event.get("snapshot_date", None)
    if raw is None:
        return None
    text = str(raw).strip() if isinstance(raw, str) else str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except (ValueError, TypeError) as exc:
        raise ValueError("event.date must be YYYY-MM-DD") from exc


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
        run = run_snapshot_job(ctx, date_override=_extract_snapshot_date(event or {}))
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
