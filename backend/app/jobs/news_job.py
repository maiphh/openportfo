"""Daily news ingest job: RSS → keyword match → NewsRepo."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
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
from app.ports.news import NewsItem


def _item_id(url: str, title: str) -> str:
    raw = f"{url}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def _matches(title: str, keywords: list[str]) -> bool:
    t = (title or "").lower()
    for kw in keywords:
        if kw and kw.lower() in t:
            return True
    return False


def _iter_profiles(ctx: JobContext):
    """Use the lazy repository traversal, with legacy-repo compatibility."""
    iterator = getattr(ctx.user_profile_repo, "iter_all", None)
    if callable(iterator):
        yield from iterator()
        return
    yield from ctx.user_profile_repo.list_all()


def _iter_holding_users(ctx: JobContext):
    """Use distinct lazy holding-user traversal when the adapter supports it."""
    iterator = getattr(ctx.holdings_repo, "iter_all_users", None)
    if callable(iterator):
        yield from iterator()
        return
    yield from ctx.holdings_repo.list_all_users()


def _collect_needles(ctx: JobContext) -> list[str]:
    """Collect matching needles while profiles/users are traversed lazily.

    The feed must be fetched once per source, so the unique needle set is
    retained, but complete profile/user/holding collections are not.
    """
    seen: set[str] = set()
    needles: list[str] = []

    def add(raw: str | None) -> None:
        text = (raw or "").strip()
        if not text:
            return
        key = text.lower()
        if key in seen:
            return
        seen.add(key)
        needles.append(text)

    profile_user_ids: set[str] = set()

    def add_user_assets(user_id: str) -> None:
        for holding in ctx.holdings_repo.list(user_id):
            add(holding.symbol)
        for item in ctx.watchlist_repo.list(user_id):
            add(item.symbol)

    for profile in _iter_profiles(ctx):
        profile_user_ids.add(profile.user_id)
        for kw in profile.news_keywords or []:
            add(kw)
        add_user_assets(profile.user_id)

    # A holding may exist before a profile is created.  The distinct-user
    # adapter traversal covers those records without re-reading profile users.
    for user_id in _iter_holding_users(ctx):
        if user_id not in profile_user_ids:
            add_user_assets(user_id)
    return needles


def run_news_job(ctx: JobContext) -> JobRun:
    """Fetch enabled feeds independently and persist one aggregate run.

    A source is the isolation boundary: a fetch or write failure marks that
    source failed, but does not prevent later sources from being processed.
    The single JobRun written at the end therefore describes the whole
    invocation instead of whichever source happened to fail first.
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
            job_type="news",
            status=status,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            message=message,
            counts=counts,
        )
        # Exactly one aggregate result is persisted for this invocation.
        ctx.job_runs_repo.put(run)
        return run

    try:
        settings = ctx.settings_repo.get()

        if not settings.jobs_news:
            return persist(
                status="skipped",
                message="jobs.news disabled",
                counts={
                    "written": 0,
                    "fetched": 0,
                    "sources": 0,
                    "sources_attempted": 0,
                    "sources_succeeded": 0,
                    "sources_failed": 0,
                    "attempted": 0,
                    "succeeded": 0,
                    "failed": 0,
                },
            )

        needles = _collect_needles(ctx)
        sources = [s for s in ctx.rss_sources_repo.list() if s.enabled]
        fetched = 0
        written = 0
        sources_attempted = 0
        sources_succeeded = 0
        sources_failed = 0
        failures: list[str] = []

        # Empty needles intentionally means no feed request.  This avoids
        # ingesting every item in every feed and is a successful no-op.
        if needles:
            for src in sources:
                sources_attempted += 1
                label = sanitize_error(src.source_id or src.name or src.url, limit=80)
                try:
                    items = ctx.rss_fetcher.fetch(src.url)
                    fetched += len(items)
                    for it in items:
                        if not _matches(it.title, needles):
                            continue
                        date_s = None
                        if it.published_at is not None:
                            date_s = it.published_at.date().isoformat()
                        news = NewsItem(
                            id=_item_id(it.url, it.title),
                            title=it.title,
                            url=it.url,
                            source=src.name or it.source_name or src.url,
                            published_at=it.published_at,
                            symbols=[],
                            date=date_s,
                        )
                        ctx.news_repo.put(news)
                        written += 1
                except Exception as exc:  # noqa: BLE001 - isolate this source
                    sources_failed += 1
                    if len(failures) < MAX_ERROR_DETAILS:
                        failures.append(f"{label}: {sanitize_error(exc)}")
                else:
                    sources_succeeded += 1

        status = aggregate_status(sources_attempted, sources_failed)
        message = None
        if failures:
            message = sanitize_error(
                f"{sources_failed} of {sources_attempted} RSS sources failed: "
                f"{error_summary(failures)}",
                limit=MAX_ERROR_SUMMARY_LENGTH,
            )
        return persist(
            status=status,
            message=message,
            counts={
                "written": written,
                "fetched": fetched,
                "sources": len(sources),
                "sources_attempted": sources_attempted,
                "sources_succeeded": sources_succeeded,
                "sources_failed": sources_failed,
                "attempted": sources_attempted,
                "succeeded": sources_succeeded,
                "failed": sources_failed,
            },
        )
    except Exception as exc:
        return persist(
            status="error",
            message=sanitize_error(exc),
            counts={
                "written": 0,
                "fetched": 0,
                "sources": 0,
                "sources_attempted": 0,
                "sources_succeeded": 0,
                "sources_failed": 0,
                "attempted": 0,
                "succeeded": 0,
                "failed": 1,
            },
        )


__all__ = ["run_news_job"]
