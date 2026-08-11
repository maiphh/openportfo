"""Daily portfolio snapshot job → SnapshotRepo + ObjectStorage."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.jobs.context import JobContext
from app.ports.admin import JobRun
from app.ports.snapshots import SnapshotRecord
from app.services.portfolio_service import PortfolioView


def _dec(v: Any) -> Any:
    if isinstance(v, Decimal):
        return format(v, "f")
    return v


def _view_to_payload(view: PortfolioView) -> dict[str, Any]:
    summary = view.summary
    lines = []
    for ln in summary.lines:
        lines.append(
            {
                "symbol": ln.symbol,
                "assetType": ln.asset_type,
                "qty": _dec(ln.qty),
                "currency": ln.currency,
                "marketValue": _dec(ln.market_value),
                "costBasis": _dec(ln.cost_basis),
                "pnl": _dec(ln.pnl),
                "missingPrice": ln.missing_price,
            }
        )
    totals = {
        cur: {
            "marketValue": _dec(t.market_value),
            "costBasis": _dec(t.cost_basis),
            "pnl": _dec(t.pnl),
        }
        for cur, t in summary.totals_by_currency.items()
    }
    return {
        "lines": lines,
        "totalsByCurrency": totals,
        "fxStatus": summary.fx_status,
        "rates": {k: _dec(v) for k, v in (view.fx_rates or {}).items()},
    }


def snapshot_storage_key(user_id: str, date: str) -> str:
    """Locked: snapshots/userId={id}/dt={date}/part.json"""
    return f"snapshots/userId={user_id}/dt={date}/part.json"


def run_snapshot_job(ctx: JobContext) -> JobRun:
    started = datetime.now(timezone.utc)
    settings = ctx.settings_repo.get()
    run_id = str(uuid4())
    date = started.date().isoformat()

    if not settings.jobs_snapshot:
        run = JobRun(
            run_id=run_id,
            job_type="snapshot",
            status="skipped",
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            message="jobs.snapshot disabled",
            counts={"users": 0},
        )
        ctx.job_runs_repo.put(run)
        return run

    list_all = getattr(ctx.user_profile_repo, "list_all", None)
    profiles = list(list_all()) if callable(list_all) else []
    users_snapshotted = 0

    for profile in profiles:
        holdings = ctx.holdings_repo.list(profile.user_id)
        if not holdings:
            continue
        view = ctx.portfolio_service.get_portfolio(
            profile.user_id,
            preferred_currency=profile.preferred_currency,
            force_refresh=False,
        )
        payload = _view_to_payload(view)
        payload["userId"] = profile.user_id
        payload["date"] = date
        record = SnapshotRecord(
            user_id=profile.user_id,
            date=date,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
        ctx.snapshot_repo.put(record)
        key = snapshot_storage_key(profile.user_id, date)
        ctx.object_storage.put_json(key, payload)
        users_snapshotted += 1

    run = JobRun(
        run_id=run_id,
        job_type="snapshot",
        status="success",
        started_at=started,
        finished_at=datetime.now(timezone.utc),
        message=None,
        counts={"users": users_snapshotted, "date": date},
    )
    ctx.job_runs_repo.put(run)
    return run


__all__ = ["run_snapshot_job", "snapshot_storage_key"]
