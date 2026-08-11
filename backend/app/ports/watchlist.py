"""Watchlist repository port (DynamoDB in prod, in-memory fake in local/test).

Logical key under userId: WATCH#{assetType}#{symbol}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional, Protocol

AssetType = Literal["crypto", "stock"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DuplicateWatchlistError(Exception):
    """Raised when adding a watchlist item that already exists for the user."""

    def __init__(self, detail: str = "Watchlist item already exists") -> None:
        self.detail = detail
        super().__init__(detail)


class WatchlistNotFoundError(Exception):
    """Raised when a watchlist item is missing for the user."""

    def __init__(self, detail: str = "Watchlist item not found") -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass
class WatchlistItem:
    """Persisted watchlist entry (no prices in this sprint)."""

    user_id: str
    asset_type: AssetType
    symbol: str
    asset_id: Optional[str] = None
    added_at: datetime = field(default_factory=utc_now)

    @property
    def sk(self) -> str:
        """Logical sort key: WATCH#{assetType}#{symbol}."""
        return f"WATCH#{self.asset_type}#{self.symbol}"


class WatchlistRepo(Protocol):
    """Port: user-scoped watchlist CRUD."""

    def list(self, user_id: str) -> list[WatchlistItem]:
        """Return all watchlist items for ``user_id``."""
        ...

    def get(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
    ) -> Optional[WatchlistItem]:
        """Return one item or ``None``."""
        ...

    def add(self, item: WatchlistItem) -> WatchlistItem:
        """Insert item. Raises ``DuplicateWatchlistError`` if key exists."""
        ...

    def remove(self, user_id: str, asset_type: str, symbol: str) -> None:
        """Remove item. Raises ``WatchlistNotFoundError`` if missing."""
        ...
