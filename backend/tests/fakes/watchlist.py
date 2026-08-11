"""In-memory WatchlistRepo for local/test."""

from __future__ import annotations

from copy import deepcopy
from typing import Optional

from app.ports.watchlist import (
    DuplicateWatchlistError,
    WatchlistItem,
    WatchlistNotFoundError,
)


def _key(user_id: str, asset_type: str, symbol: str) -> tuple[str, str, str]:
    return (user_id, asset_type, symbol.upper())


class InMemoryWatchlistRepo:
    """Dict-backed watchlist store keyed by (user_id, asset_type, symbol)."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str, str], WatchlistItem] = {}

    def list(self, user_id: str) -> list[WatchlistItem]:
        return [
            deepcopy(item)
            for (uid, _, _), item in sorted(self._items.items())
            if uid == user_id
        ]

    def get(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
    ) -> Optional[WatchlistItem]:
        item = self._items.get(_key(user_id, asset_type, symbol))
        return deepcopy(item) if item is not None else None

    def add(self, item: WatchlistItem) -> WatchlistItem:
        k = _key(item.user_id, item.asset_type, item.symbol)
        if k in self._items:
            raise DuplicateWatchlistError(
                f"Watchlist item already exists: {item.asset_type}/{item.symbol}"
            )
        stored = WatchlistItem(
            user_id=item.user_id,
            asset_type=item.asset_type,
            symbol=item.symbol.upper(),
            asset_id=item.asset_id,
            added_at=item.added_at,
        )
        self._items[k] = stored
        return deepcopy(stored)

    def remove(self, user_id: str, asset_type: str, symbol: str) -> None:
        k = _key(user_id, asset_type, symbol)
        if k not in self._items:
            raise WatchlistNotFoundError(
                f"Watchlist item not found: {asset_type}/{symbol}"
            )
        del self._items[k]

    def clear(self) -> None:
        """Test helper: wipe all watchlist items."""
        self._items.clear()
