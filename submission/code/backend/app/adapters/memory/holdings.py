"""In-memory holdings adapter for local development and tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from collections.abc import Iterator
from typing import Optional

from app.ports.holdings import (
    DuplicateHoldingError,
    HoldingNotFoundError,
    HoldingRecord,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _key(user_id: str, asset_type: str, symbol: str) -> tuple[str, str, str]:
    return (user_id, asset_type, symbol.upper())


class InMemoryHoldingsRepo:
    """Dict-backed holdings store keyed by (user_id, asset_type, symbol)."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str, str], HoldingRecord] = {}

    def list(self, user_id: str) -> list[HoldingRecord]:
        return [
            deepcopy(h)
            for (uid, _, _), h in sorted(self._items.items())
            if uid == user_id
        ]

    def iter_user_pages(
        self,
        *,
        page_size: Optional[int] = None,
    ) -> Iterator[list[str]]:
        """Yield bounded pages of distinct user ids with holdings."""
        cap = max(1, int(page_size)) if page_size is not None else 100
        page: list[str] = []
        previous_user: Optional[str] = None
        # Tuple-key sorting groups all holdings for a user together, so a
        # single previous value is enough to provide distinctness without
        # materializing a second set of every user id.
        for user_id, _, _ in sorted(self._items.keys()):
            if user_id == previous_user:
                continue
            previous_user = user_id
            page.append(user_id)
            if len(page) >= cap:
                yield page
                page = []
        if page:
            yield page

    def iter_all_users(self, *, page_size: Optional[int] = None) -> Iterator[str]:
        """Lazily yield distinct user ids with any holdings."""
        for page in self.iter_user_pages(page_size=page_size):
            yield from page

    def list_all_users(self) -> list[str]:
        """Compatibility materializing helper for non-job callers."""
        return list(self.iter_all_users())

    def get(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
    ) -> Optional[HoldingRecord]:
        item = self._items.get(_key(user_id, asset_type, symbol))
        return deepcopy(item) if item is not None else None

    def create(self, holding: HoldingRecord) -> HoldingRecord:
        k = _key(holding.user_id, holding.asset_type, holding.symbol)
        if k in self._items:
            raise DuplicateHoldingError(
                f"Holding already exists: {holding.asset_type}/{holding.symbol}"
            )
        stored = HoldingRecord(
            user_id=holding.user_id,
            asset_type=holding.asset_type,
            symbol=holding.symbol.upper(),
            qty=holding.qty,
            avg_cost=holding.avg_cost,
            currency=holding.currency,
            asset_id=holding.asset_id,
            note=holding.note,
            created_at=holding.created_at,
            updated_at=holding.updated_at,
        )
        self._items[k] = stored
        return deepcopy(stored)

    def update(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
        *,
        qty: Optional[Decimal] = None,
        avg_cost: Optional[Decimal] = None,
        currency: Optional[str] = None,
        asset_id: Optional[str] = None,
        note: Optional[str] = None,
        clear_note: bool = False,
    ) -> HoldingRecord:
        k = _key(user_id, asset_type, symbol)
        item = self._items.get(k)
        if item is None:
            raise HoldingNotFoundError(
                f"Holding not found: {asset_type}/{symbol}"
            )
        if qty is not None:
            item.qty = qty
        if avg_cost is not None:
            item.avg_cost = avg_cost
        if currency is not None:
            item.currency = currency
        if asset_id is not None:
            item.asset_id = asset_id
        if clear_note:
            item.note = None
        elif note is not None:
            item.note = note
        item.updated_at = _utc_now()
        return deepcopy(item)

    def delete(self, user_id: str, asset_type: str, symbol: str) -> None:
        k = _key(user_id, asset_type, symbol)
        if k not in self._items:
            raise HoldingNotFoundError(
                f"Holding not found: {asset_type}/{symbol}"
            )
        del self._items[k]

    def clear(self) -> None:
        """Test helper: wipe all holdings."""
        self._items.clear()
