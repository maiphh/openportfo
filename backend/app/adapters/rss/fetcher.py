"""HTTP + feedparser RSS fetcher (adapter only; no boto3)."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import mktime
from typing import Any, Optional

import httpx

from app.ports.rss import RssItem

try:
    import feedparser
except ImportError:  # pragma: no cover — optional until installed
    feedparser = None  # type: ignore[assignment]


def _struct_time_to_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(mktime(value), tz=timezone.utc)
    except (TypeError, OverflowError, ValueError, OSError):
        return None


def _parse_published(entry: Any) -> Optional[datetime]:
    if getattr(entry, "published_parsed", None):
        dt = _struct_time_to_dt(entry.published_parsed)
        if dt:
            return dt
    if getattr(entry, "updated_parsed", None):
        dt = _struct_time_to_dt(entry.updated_parsed)
        if dt:
            return dt
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if not raw:
            continue
        try:
            return parsedate_to_datetime(str(raw))
        except (TypeError, ValueError, IndexError):
            try:
                s = str(raw).replace("Z", "+00:00")
                return datetime.fromisoformat(s)
            except ValueError:
                continue
    return None


class HttpRssFetcher:
    """Fetch RSS/Atom via httpx and parse with feedparser."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        transport: Optional[httpx.BaseTransport] = None,
        user_agent: str = "OpenPortfoRSS/1.0",
    ) -> None:
        self._timeout = timeout_seconds
        self._transport = transport
        self._user_agent = user_agent

    def fetch(self, url: str) -> list[RssItem]:
        if feedparser is None:
            raise RuntimeError(
                "feedparser is not installed; add feedparser to requirements for RSS jobs"
            )
        try:
            with httpx.Client(
                timeout=self._timeout,
                transport=self._transport,
                follow_redirects=True,
                headers={"User-Agent": self._user_agent},
            ) as client:
                resp = client.get(url)
                resp.raise_for_status()
                content = resp.text
        except httpx.HTTPError:
            return []

        parsed = feedparser.parse(content)
        source_name = getattr(parsed.feed, "title", None) if getattr(parsed, "feed", None) else None
        items: list[RssItem] = []
        for entry in getattr(parsed, "entries", []) or []:
            title = (getattr(entry, "title", None) or "").strip()
            link = (getattr(entry, "link", None) or "").strip()
            if not title and not link:
                continue
            items.append(
                RssItem(
                    title=title or link,
                    url=link or title,
                    published_at=_parse_published(entry),
                    source_name=source_name,
                )
            )
        return items


__all__ = ["HttpRssFetcher"]
