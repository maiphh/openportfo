"""Price warm job: collect symbols → market force fetch → PriceCache."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.jobs.context import JobContext
from app.ports.admin import JobRun
from app.services.market_service import QuoteKey


def run_price_job(ctx: JobContext) -> JobRun:
    started = datetime.now(timezone.utc)
    settings = ctx.settings_repo.get()
    run_id = str(uuid4())

    if not getattr(settings, "jobs_snapshot", True) and False:
        # price job uses dedicated flag if present; default always on unless we add jobs_price
        pass

    # Use jobs_snapshot as related price-warm companion is not separate in settings;
    # Prefer always-on unless we treat missing as enabled. S09 has jobs_news/snapshot/email only.
    # Document: price job runs unless we introduce jobs.price; for now always enabled.
    enabled = True

    if not enabled:
        run = JobRun(
            run_id=run_id,
            job_type="price",
            status="skipped",
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            message="jobs.price disabled",
            counts={},
        )
        ctx.job_runs_repo.put(run)
        return run

    keys_map: dict[tuple[str, str], QuoteKey] = {}
    list_users = getattr(ctx.holdings_repo, "list_all_users", None)
    if callable(list_users):
        user_ids = list_users()
    else:
        # Fallback: list_all on profiles
        list_all = getattr(ctx.user_profile_repo, "list_all", None)
        user_ids = [p.user_id for p in list_all()] if callable(list_all) else []

    for uid in user_ids:
        for h in ctx.holdings_repo.list(uid):
            keys_map[(h.asset_type, h.symbol.upper())] = QuoteKey(
                asset_type=h.asset_type,
                symbol=h.symbol,
                asset_id=h.asset_id,
            )
        for w in ctx.watchlist_repo.list(uid):
            k = (w.asset_type, w.symbol.upper())
            if k not in keys_map:
                keys_map[k] = QuoteKey(
                    asset_type=w.asset_type,
                    symbol=w.symbol,
                    asset_id=getattr(w, "asset_id", None),
                )

    keys = list(keys_map.values())
    quotes = ctx.market_service.get_quotes(keys, force=True) if keys else []

    run = JobRun(
        run_id=run_id,
        job_type="price",
        status="success",
        started_at=started,
        finished_at=datetime.now(timezone.utc),
        message=None,
        counts={"symbols": len(keys), "quotes": len(quotes)},
    )
    ctx.job_runs_repo.put(run)
    return run


__all__ = ["run_price_job"]
