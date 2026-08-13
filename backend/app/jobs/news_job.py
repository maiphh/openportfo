"""Daily news ingest job: RSS → keyword match → NewsRepo."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from app.jobs.context import JobContext
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


def _collect_needles(ctx: JobContext) -> list[str]:
    """Keywords from all profiles plus symbols from holdings and watchlist."""
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

    profiles = ctx.user_profile_repo.list_all()
    user_ids = {p.user_id for p in profiles}
    for profile in profiles:
        for kw in profile.news_keywords or []:
            add(kw)
    user_ids.update(ctx.holdings_repo.list_all_users())
    for uid in user_ids:
        for holding in ctx.holdings_repo.list(uid):
            add(holding.symbol)
        for item in ctx.watchlist_repo.list(uid):
            add(item.symbol)
    return needles


def run_news_job(ctx: JobContext) -> JobRun:
    started = datetime.now(timezone.utc)
    run_id = str(uuid4())
    try:
        settings = ctx.settings_repo.get()

        if not settings.jobs_news:
            run = JobRun(
                run_id=run_id,
                job_type="news",
                status="skipped",
                started_at=started,
                finished_at=datetime.now(timezone.utc),
                message="jobs.news disabled",
                counts={"written": 0, "fetched": 0},
            )
            ctx.job_runs_repo.put(run)
            return run

        needles = _collect_needles(ctx)
        sources = [s for s in ctx.rss_sources_repo.list() if s.enabled]
        fetched = 0
        written = 0
        # Empty needles: do not ingest the whole feed.
        if needles:
            for src in sources:
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
                        keywords=[
                            k
                            for k in needles
                            if k and k.lower() in (it.title or "").lower()
                        ],
                        date=date_s,
                    )
                    ctx.news_repo.put(news)
                    written += 1

        run = JobRun(
            run_id=run_id,
            job_type="news",
            status="success",
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            message=None,
            counts={"written": written, "fetched": fetched, "sources": len(sources)},
        )
        ctx.job_runs_repo.put(run)
        return run
    except Exception as exc:
        run = JobRun(
            run_id=run_id,
            job_type="news",
            status="error",
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            message=str(exc),
            counts={},
        )
        ctx.job_runs_repo.put(run)
        return run


__all__ = ["run_news_job"]
