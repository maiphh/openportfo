"""News repository port (Dynamo in prod; in-memory for tests)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol, Sequence


@dataclass
class NewsItem:
    """One news article (ingested by jobs; read by API)."""

    id: str
    title: str
    url: str
    source: str
    published_at: Optional[datetime] = None
    symbols: list[str] = field(default_factory=list)
    date: Optional[str] = None  # YYYY-MM-DD


class NewsRepo(Protocol):
    def list_recent(self, limit: int = 50) -> list[NewsItem]:
        ...

    def put(self, item: NewsItem) -> None:
        ...


__all__ = ["NewsItem", "NewsRepo"]
