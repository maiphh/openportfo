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


def run_news_job(ctx: JobContext) -> JobRun:
    started = datetime.now(timezone.utc)
    settings = ctx.settings_repo.get()
    run_id = str(uuid4())

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

    # Global keywords: collect from all user profiles if available; fallback empty
    keywords: list[str] = []
    list_all = getattr(ctx.user_profile_repo, "list_all", None)
    if callable(list_all):
        for profile in list_all():
            keywords.extend(profile.news_keywords or [])
    # Also use source names as weak fallback keywords when empty — match any title
    match_all = not any(k.strip() for k in keywords)

    sources = [s for s in ctx.rss_sources_repo.list() if s.enabled]
    fetched = 0
    written = 0
    for src in sources:
        items = ctx.rss_fetcher.fetch(src.url)
        fetched += len(items)
        for it in items:
            if not match_all and not _matches(it.title, keywords):
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
                keywords=[k for k in keywords if k and k.lower() in (it.title or "").lower()],
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


__all__ = ["run_news_job"]
