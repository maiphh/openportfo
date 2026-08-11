"""Holdings repository port (DynamoDB in prod, in-memory fake in local/test).

Logical key under userId: HOLD#{assetType}#{symbol}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional, Protocol

AssetType = Literal["crypto", "stock"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DuplicateHoldingError(Exception):
    """Raised when creating a holding that already exists for the user."""

    def __init__(self, detail: str = "Holding already exists") -> None:
        self.detail = detail
        super().__init__(detail)


class HoldingNotFoundError(Exception):
    """Raised when a holding is missing for the user."""

    def __init__(self, detail: str = "Holding not found") -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass
class HoldingRecord:
    """Persisted user position (qty + cost basis). Money as Decimal."""

    user_id: str
    asset_type: AssetType
    symbol: str
    qty: Decimal
    avg_cost: Decimal
    currency: str
    asset_id: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def sk(self) -> str:
        """Logical sort key: HOLD#{assetType}#{symbol}."""
        return f"HOLD#{self.asset_type}#{self.symbol}"


class HoldingsRepo(Protocol):
    """Port: user-scoped holdings CRUD."""

    def list(self, user_id: str) -> list[HoldingRecord]:
        """Return all holdings for ``user_id`` (empty list if none)."""
        ...

    def get(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
    ) -> Optional[HoldingRecord]:
        """Return one holding or ``None``."""
        ...

    def create(self, holding: HoldingRecord) -> HoldingRecord:
        """Insert holding. Raises ``DuplicateHoldingError`` if key exists."""
        ...

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
        """Patch fields. Raises ``HoldingNotFoundError`` if missing."""
        ...

    def delete(self, user_id: str, asset_type: str, symbol: str) -> None:
        """Remove holding. Raises ``HoldingNotFoundError`` if missing."""
        ...
