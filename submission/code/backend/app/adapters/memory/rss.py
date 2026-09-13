"""In-memory rss adapter for local development and tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Optional

from app.ports.rss import RssItem


class FakeRssFetcher:
    def __init__(self, feeds: Optional[dict[str, list[RssItem]]] = None) -> None:
        self._feeds: dict[str, list[RssItem]] = {
            k: list(v) for k, v in (feeds or {}).items()
        }
        self.fetch_calls = 0
        self.last_url: Optional[str] = None

    def fetch(self, url: str) -> list[RssItem]:
        self.fetch_calls += 1
        self.last_url = url
        return [deepcopy(i) for i in self._feeds.get(url, [])]

    def set_feed(self, url: str, items: list[RssItem]) -> None:
        self._feeds[url] = list(items)


__all__ = ["FakeRssFetcher"]

