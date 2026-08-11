"""RSS fetcher port (feedparser/httpx only in adapter)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol


@dataclass
class RssItem:
    title: str
    url: str
    published_at: Optional[datetime] = None
    source_name: Optional[str] = None


class RssFetcher(Protocol):
    def fetch(self, url: str) -> list[RssItem]:
        """Fetch and parse feed at ``url``."""
        ...


__all__ = ["RssItem", "RssFetcher"]
