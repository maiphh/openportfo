"""In-memory NewsRepo."""

from __future__ import annotations

from copy import deepcopy
from typing import Optional

from app.ports.news import NewsItem


class InMemoryNewsRepo:
    def __init__(self, items: Optional[list[NewsItem]] = None) -> None:
        self._items: list[NewsItem] = list(items or [])
        self.put_calls = 0

    def list_recent(self, limit: int = 50) -> list[NewsItem]:
        # newest first; normalize sort key to string
        def _key(x: NewsItem) -> str:
            if x.published_at is not None:
                return x.published_at.isoformat()
            return x.date or ""

        items = sorted(self._items, key=_key, reverse=True)
        return [deepcopy(i) for i in items[: max(0, limit)]]

    def put(self, item: NewsItem) -> None:
        self.put_calls += 1
        # replace by id
        self._items = [i for i in self._items if i.id != item.id]
        self._items.append(deepcopy(item))

    def seed(self, items: list[NewsItem]) -> None:
        self._items = [deepcopy(i) for i in items]

    def clear(self) -> None:
        self._items.clear()
        self.put_calls = 0


__all__ = ["InMemoryNewsRepo"]
