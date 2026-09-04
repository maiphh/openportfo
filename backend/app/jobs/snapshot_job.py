"""Daily portfolio snapshot job → SnapshotRepo + ObjectStorage."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from app.jobs.context import JobContext
from app.jobs.job_utils import (
    MAX_ERROR_DETAILS,
    MAX_ERROR_SUMMARY_LENGTH,
    aggregate_status,
    error_summary,
    sanitize_error,
)
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
        "fx": {
            "status": summary.fx_status,
            "base": summary.fx_base,
            "asOf": summary.fx_as_of.isoformat() if summary.fx_as_of else None,
            "rates": {k: _dec(v) for k, v in (view.fx_rates or {}).items()},
        },
    }


def snapshot_storage_key(user_id: str, date: str) -> str:
    """Locked: snapshots/userId={id}/dt={date}/part.json"""
    return f"snapshots/userId={user_id}/dt={date}/part.json"


def _resolve_snapshot_date(date_override: Any = None) -> str:
    """Validate manual date override or fall back to UTC today.

    Accepts ``None``/empty (→ today) or a strict ``YYYY-MM-DD`` string.
    Raises ``ValueError`` with a ``YYYY-MM-DD`` message on invalid input.
    """
    if date_override is None:
        return datetime.now(timezone.utc).date().isoformat()
    raw = str(date_override).strip() if isinstance(date_override, str) else str(date_override or "").strip()
    if not raw:
        return datetime.now(timezone.utc).date().isoformat()
    try:
        parsed = date.fromisoformat(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("date_override must be YYYY-MM-DD") from exc
    return parsed.isoformat()


def _iter_profiles(ctx: JobContext):
    """Use the lazy repository traversal, with legacy-repo compatibility."""
    iterator = getattr(ctx.user_profile_repo, "iter_all", None)
    if callable(iterator):
        yield from iterator()
        return
    yield from ctx.user_profile_repo.list_all()


def run_snapshot_job(ctx: JobContext, date_override: Optional[str] = None) -> JobRun:
    """Write snapshots per user and continue after an individual failure.

    A user with no holdings is an intentional no-op and is counted as
    skipped.  Any failure while computing or publishing one user's snapshot
    marks only that user failed; the aggregate JobRun is persisted once after
    all users have been attempted.

    Args:
        ctx: Job ports.
        date_override: Optional manual ``YYYY-MM-DD`` (Lambda console/CLI).
            ``None``/empty → UTC today. Invalid → ``ValueError`` before writes.
    """

    started = datetime.now(timezone.utc)
    run_id = str(uuid4())
    date = _resolve_snapshot_date(date_override)

    def persist(
        *,
        status: str,
        message: str | None,
        counts: dict[str, object],
    ) -> JobRun:
        run = JobRun(
            run_id=run_id,
            job_type="snapshot",
            status=status,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            message=message,
            counts=counts,
        )
        # Exactly one aggregate result is written for this invocation.
        ctx.job_runs_repo.put(run)
        return run

    try:
        settings = ctx.settings_repo.get()

        if not settings.jobs_snapshot:
            return persist(
                status="skipped",
                message="jobs.snapshot disabled",
                counts={
                    "users": 0,
                    "users_total": 0,
                    "users_attempted": 0,
                    "users_succeeded": 0,
                    "users_failed": 0,
                    "users_skipped": 0,
                    "attempted": 0,
                    "succeeded": 0,
                    "failed": 0,
                    "date": date,
                },
            )

        users_total = 0
        users_attempted = 0
        users_snapshotted = 0
        users_failed = 0
        users_skipped = 0
        failures: list[str] = []

        for profile in _iter_profiles(ctx):
            users_total += 1
            user_id = str(profile.user_id)
            label = sanitize_error(user_id, limit=80)
            user_attempted = False
            try:
                holdings = ctx.holdings_repo.list(profile.user_id)
                if not holdings:
                    users_skipped += 1
                    continue

                users_attempted += 1
                user_attempted = True
                preferred = (
                    profile.preferred_currency
                    or settings.default_display_currency
                    or "USD"
                )
                view = ctx.portfolio_service.get_portfolio(
                    profile.user_id,
                    preferred_currency=preferred,
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
                key = snapshot_storage_key(profile.user_id, date)
                # Publish the deterministic S3 object first.  The DynamoDB
                # row is the API-visible reference to this snapshot, so it
                # must not be written when the object upload fails.  Both
                # adapters are idempotent for this user/date pair: a retry
                # overwrites the same object and upserts the same row.
                ctx.object_storage.put_json(key, payload)
                ctx.snapshot_repo.put(record)
                users_snapshotted += 1
            except Exception as exc:  # noqa: BLE001 - isolate this user
                # If loading holdings itself fails, it is still an attempted
                # user unit from the job's perspective.
                if not user_attempted:
                    users_attempted += 1
                users_failed += 1
                if len(failures) < MAX_ERROR_DETAILS:
                    failures.append(f"user {label}: {sanitize_error(exc)}")

        status = aggregate_status(users_attempted, users_failed)
        message = None
        if failures:
            message = sanitize_error(
                f"{users_failed} of {users_attempted} snapshot users failed: "
                f"{error_summary(failures)}",
                limit=MAX_ERROR_SUMMARY_LENGTH,
            )
        return persist(
            status=status,
            message=message,
            counts={
                # Keep ``users`` as the legacy successful snapshot count.
                "users": users_snapshotted,
                "users_total": users_total,
                "users_attempted": users_attempted,
                "users_succeeded": users_snapshotted,
                "users_failed": users_failed,
                "users_skipped": users_skipped,
                "attempted": users_attempted,
                "succeeded": users_snapshotted,
                "failed": users_failed,
                "date": date,
            },
        )
    except Exception as exc:
        return persist(
            status="error",
            message=sanitize_error(exc),
            counts={
                "users": 0,
                "users_total": 0,
                "users_attempted": 0,
                "users_succeeded": 0,
                "users_failed": 0,
                "users_skipped": 0,
                "attempted": 0,
                "succeeded": 0,
                "failed": 1,
                "date": date,
            },
        )


__all__ = ["_resolve_snapshot_date", "run_snapshot_job", "snapshot_storage_key"]
