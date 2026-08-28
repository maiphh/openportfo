"""Daily news ingest job: RSS → keyword/symbol match → NewsRepo."""

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
from app.ports.rss import RssItem

MAX_ITEMS_PER_SOURCE = 25


def _normalize_url(url: str) -> str:
    return (url or "").strip().rstrip("/")


def _normalize_title(title: str) -> str:
    return " ".join((title or "").split()).casefold()


def _item_id(url: str, title: str) -> str:
    raw = f"{_normalize_url(url)}|{_normalize_title(title)}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def _matches(title: str, needles: list[str]) -> bool:
    t = (title or "").casefold()
    for kw in needles:
        if kw and kw.casefold() in t:
            return True
    return False


def _matched_asset_symbols(title: str, asset_symbols: list[str]) -> list[str]:
    t = (title or "").casefold()
    found: list[str] = []
    seen: set[str] = set()
    for symbol in asset_symbols:
        text = (symbol or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        if key in t:
            seen.add(key)
            found.append(text)
    return found


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


def _collect_needles(ctx: JobContext) -> tuple[list[str], list[str]]:
    """Return (asset_symbols, keyword_needles) without retaining full user graphs."""
    asset_seen: set[str] = set()
    asset_symbols: list[str] = []
    keyword_seen: set[str] = set()
    keyword_needles: list[str] = []

    def add_asset(raw: str | None) -> None:
        text = (raw or "").strip()
        if not text:
            return
        key = text.casefold()
        if key in asset_seen:
            return
        asset_seen.add(key)
        asset_symbols.append(text)

    def add_keyword(raw: str | None) -> None:
        text = (raw or "").strip()
        if not text:
            return
        key = text.casefold()
        if key in keyword_seen:
            return
        keyword_seen.add(key)
        keyword_needles.append(text)

    profile_user_ids: set[str] = set()

    def add_user_assets(user_id: str) -> None:
        for holding in ctx.holdings_repo.list(user_id):
            add_asset(holding.symbol)
        for item in ctx.watchlist_repo.list(user_id):
            add_asset(item.symbol)

    for profile in _iter_profiles(ctx):
        profile_user_ids.add(profile.user_id)
        for kw in profile.news_keywords or []:
            add_keyword(kw)
        add_user_assets(profile.user_id)

    for user_id in _iter_holding_users(ctx):
        if user_id not in profile_user_ids:
            add_user_assets(user_id)

    return asset_symbols, keyword_needles


def _bounded_recent(items: list[RssItem]) -> list[RssItem]:
    def sort_key(item: RssItem) -> datetime:
        if item.published_at is not None:
            dt = item.published_at
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        return datetime.min.replace(tzinfo=timezone.utc)

    ordered = sorted(items, key=sort_key, reverse=True)
    return ordered[:MAX_ITEMS_PER_SOURCE]


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

        asset_symbols, keyword_needles = _collect_needles(ctx)
        match_needles = [*asset_symbols, *keyword_needles]
        sources = [s for s in ctx.rss_sources_repo.list() if s.enabled]
        fetched = 0
        written = 0
        sources_attempted = 0
        sources_succeeded = 0
        sources_failed = 0
        failures: list[str] = []

        for src in sources:
            sources_attempted += 1
            label = sanitize_error(src.source_id or src.name or src.url, limit=80)
            try:
                items = _bounded_recent(ctx.rss_fetcher.fetch(src.url))
                fetched += len(items)
                for it in items:
                    if match_needles and not _matches(it.title, match_needles):
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
                        symbols=_matched_asset_symbols(it.title, asset_symbols),
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


__all__ = ["run_news_job", "MAX_ITEMS_PER_SOURCE"]
