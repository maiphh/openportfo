"""Watchlist application service: validation + repository orchestration."""

from __future__ import annotations

from typing import Optional

from app.ports.watchlist import (
    AssetType,
    DuplicateWatchlistError,
    WatchlistItem,
    WatchlistNotFoundError,
    WatchlistRepo,
    utc_now,
)


class ValidationError(Exception):
    """Client input failed business validation (maps to HTTP 400)."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


_ALLOWED_ASSET_TYPES = frozenset({"crypto", "stock"})


def _normalize_symbol(symbol: str) -> str:
    s = (symbol or "").strip().upper()
    if not s:
        raise ValidationError("symbol is required")
    return s


def _normalize_asset_type(asset_type: str) -> AssetType:
    t = (asset_type or "").strip().lower()
    if t not in _ALLOWED_ASSET_TYPES:
        raise ValidationError("assetType must be 'crypto' or 'stock'")
    return t  # type: ignore[return-value]


class WatchlistService:
    """Orchestrates WatchlistRepo (no prices, no AWS SDK)."""

    def __init__(self, repo: WatchlistRepo) -> None:
        self._repo = repo

    def list_items(self, user_id: str) -> list[WatchlistItem]:
        return self._repo.list(user_id)

    def add_item(
        self,
        user_id: str,
        *,
        asset_type: str,
        symbol: str,
        asset_id: Optional[str] = None,
    ) -> WatchlistItem:
        at = _normalize_asset_type(asset_type)
        sym = _normalize_symbol(symbol)
        item = WatchlistItem(
            user_id=user_id,
            asset_type=at,
            symbol=sym,
            asset_id=asset_id,
            added_at=utc_now(),
        )
        return self._repo.add(item)

    def remove_item(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
    ) -> None:
        at = _normalize_asset_type(asset_type)
        sym = _normalize_symbol(symbol)
        self._repo.remove(user_id, at, sym)


__all__ = [
    "WatchlistService",
    "ValidationError",
    "DuplicateWatchlistError",
    "WatchlistNotFoundError",
]
