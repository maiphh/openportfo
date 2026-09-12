"""Price warm job: collect symbols → market force fetch → PriceCache.

Global refresh for every user's holdings + watchlist (crypto and VN stocks).
Schedule via EventBridge at 10–15 minutes, not 1 minute: CoinGecko demo
quotas and after-hours VN quotes make a 1-minute loop wasteful and brittle.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.jobs.context import JobContext
from app.jobs.job_utils import (
    MAX_ERROR_DETAILS,
    aggregate_status,
    error_summary,
    sanitize_error,
)
from app.ports.admin import JobRun
from app.services.market_service import QuoteKey


# Keep each provider call bounded.  Apart from limiting request size, this is
# the failure isolation boundary: a provider error in one batch does not throw
# away successful batches that have already completed or are still pending.
PRICE_BATCH_SIZE = 50


def _quote_key_tuple(key: QuoteKey) -> tuple[str, str]:
    return (str(key.asset_type).strip().lower(), str(key.symbol).strip().upper())


def _missing_quote_labels(keys: list[QuoteKey], quotes: list[object]) -> list[str]:
    returned: set[tuple[str, str]] = set()
    for quote in quotes:
        asset_type = getattr(quote, "asset_type", None)
        symbol = getattr(quote, "symbol", None)
        if asset_type is None or symbol is None:
            continue
        returned.add((str(asset_type).strip().lower(), str(symbol).strip().upper()))
    return [
        f"{key.asset_type}:{key.symbol}"
        for key in keys
        if _quote_key_tuple(key) not in returned
    ]


def _iter_profiles(ctx: JobContext):
    """Use the lazy repository traversal, with legacy-repo compatibility."""
    iterator = getattr(ctx.user_profile_repo, "iter_all", None)
    if callable(iterator):
        yield from iterator()
        return
    yield from ctx.user_profile_repo.list_all()


def _iter_holding_users(ctx: JobContext):
    """Use distinct lazy holding-user traversal when available."""
    iterator = getattr(ctx.holdings_repo, "iter_all_users", None)
    if callable(iterator):
        yield from iterator()
        return
    yield from ctx.holdings_repo.list_all_users()


def _iter_quote_keys(ctx: JobContext):
    """Yield holding/watchlist quote keys without materializing all users."""
    profile_user_ids: set[str] = set()

    def user_keys(user_id: str):
        for holding in ctx.holdings_repo.list(user_id):
            asset_type = str(holding.asset_type).strip().lower()
            symbol = str(holding.symbol).strip().upper()
            yield QuoteKey(
                asset_type=asset_type,
                symbol=symbol,
                asset_id=holding.asset_id,
            )
        for item in ctx.watchlist_repo.list(user_id):
            asset_type = str(item.asset_type).strip().lower()
            symbol = str(item.symbol).strip().upper()
            yield QuoteKey(
                asset_type=asset_type,
                symbol=symbol,
                asset_id=item.asset_id,
            )

    for profile in _iter_profiles(ctx):
        profile_user_ids.add(profile.user_id)
        yield from user_keys(profile.user_id)

    # A holding can exist without a profile.  Cover those users without
    # re-reading holdings/watchlists for users already seen above.
    for user_id in _iter_holding_users(ctx):
        if user_id not in profile_user_ids:
            yield from user_keys(user_id)


def refresh_price_cache(
    ctx: JobContext, *, batch_size: int = PRICE_BATCH_SIZE
) -> dict[str, object]:
    """Force-refresh PriceCache for holdings + watchlist. Does not write JobRun.

    Snapshot calls this before portfolio math so PnL is not computed from a
    stale same-minute cache. The dedicated price job also uses this helper.
    """

    cap = max(1, int(batch_size))
    quotes_count = 0
    missing_count = 0
    batches_attempted = 0
    batches_succeeded = 0
    batches_failed = 0
    failures: list[str] = []
    degraded_details: list[str] = []
    seen: set[tuple[str, str]] = set()
    pending: dict[str, list[QuoteKey]] = {}

    def process_batch(asset_type: str, batch: list[QuoteKey]) -> None:
        nonlocal quotes_count, missing_count
        nonlocal batches_attempted, batches_succeeded, batches_failed
        batches_attempted += 1
        label = f"batch {batches_attempted} ({asset_type}, {len(batch)} symbols)"
        try:
            quotes = ctx.market_service.get_quotes(batch, force=True)
            quotes_count += len(quotes)
            missing = _missing_quote_labels(batch, list(quotes))
            missing_count += len(missing)
            if missing:
                remaining = MAX_ERROR_DETAILS - len(degraded_details)
                if remaining > 0:
                    degraded_details.extend(
                        f"{label}: missing {symbol}"
                        for symbol in missing[:remaining]
                    )
        except Exception as exc:  # noqa: BLE001 - isolate this batch
            batches_failed += 1
            if len(failures) < MAX_ERROR_DETAILS:
                failures.append(f"{label}: {sanitize_error(exc)}")
        else:
            batches_succeeded += 1

    for key in _iter_quote_keys(ctx):
        asset_type = str(key.asset_type).strip().lower()
        symbol = str(key.symbol).strip().upper()
        identity = (asset_type, symbol)
        if identity in seen:
            continue
        seen.add(identity)
        normalized = QuoteKey(
            asset_type=asset_type,
            symbol=symbol,
            asset_id=key.asset_id,
        )
        batch = pending.setdefault(asset_type, [])
        batch.append(normalized)
        if len(batch) >= cap:
            process_batch(asset_type, batch)
            pending[asset_type] = []

    for asset_type, batch in pending.items():
        if batch:
            process_batch(asset_type, batch)

    details = failures + degraded_details
    return {
        "symbols": len(seen),
        "quotes": quotes_count,
        "quotes_missing": missing_count,
        "batches": batches_attempted,
        "batches_attempted": batches_attempted,
        "batches_succeeded": batches_succeeded,
        "batches_failed": batches_failed,
        "attempted": batches_attempted,
        "succeeded": batches_succeeded,
        "failed": batches_failed,
        "message": error_summary(details),
    }


def run_price_job(ctx: JobContext, *, batch_size: int = PRICE_BATCH_SIZE) -> JobRun:
    """Warm prices in bounded, independently reported work units.

    Status semantics are aggregate: disabled is ``skipped``; an enabled job
    with no symbols is a successful no-op; all failed batches are ``error``;
    and a mix of completed and failed/degraded batches is ``partial``.
    """

    started = datetime.now(timezone.utc)
    run_id = str(uuid4())

    def persist(
        *,
        status: str,
        message: str | None,
        counts: dict[str, object],
    ) -> JobRun:
        run = JobRun(
            run_id=run_id,
            job_type="price",
            status=status,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            message=message,
            counts=counts,
        )
        ctx.job_runs_repo.put(run)
        return run

    try:
        settings = ctx.settings_repo.get()

        if not settings.jobs_price:
            return persist(
                status="skipped",
                message="jobs.price disabled",
                counts={
                    "symbols": 0,
                    "quotes": 0,
                    "quotes_missing": 0,
                    "batches": 0,
                    "batches_attempted": 0,
                    "batches_succeeded": 0,
                    "batches_failed": 0,
                    "attempted": 0,
                    "succeeded": 0,
                    "failed": 0,
                },
            )

        result = refresh_price_cache(ctx, batch_size=batch_size)
        status = aggregate_status(
            int(result["batches_attempted"] or 0),
            int(result["batches_failed"] or 0),
            degraded=int(result["quotes_missing"] or 0) > 0,
        )
        counts = {k: v for k, v in result.items() if k != "message"}
        return persist(
            status=status,
            message=str(result["message"]) if result.get("message") else None,
            counts=counts,
        )

    except Exception as exc:
        return persist(
            status="error",
            message=sanitize_error(exc),
            counts={
                "symbols": 0,
                "quotes": 0,
                "quotes_missing": 0,
                "batches": 0,
                "batches_attempted": 0,
                "batches_succeeded": 0,
                "batches_failed": 0,
                "attempted": 0,
                "succeeded": 0,
                "failed": 1,
            },
        )


__all__ = ["PRICE_BATCH_SIZE", "refresh_price_cache", "run_price_job"]
