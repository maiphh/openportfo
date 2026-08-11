"""PriceCache repository port (DynamoDB in prod, in-memory fake in local/test).

Logical key: ``(asset_type, symbol)`` — matches PRD ``{assetType}#{symbol}``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional, Protocol

from app.domain.models import PriceQuote

AssetType = Literal["crypto", "stock"]


@dataclass(frozen=True)
class CachedPrice:
    """Stored quote with expiry for TTL freshness checks."""

    asset_type: AssetType
    symbol: str
    price: Decimal
    currency: str
    as_of: datetime
    expires_at: datetime

    def to_quote(self) -> PriceQuote:
        return PriceQuote(
            asset_type=self.asset_type,
            symbol=self.symbol,
            price=self.price,
            currency=self.currency,
            as_of=self.as_of,
        )

    def is_fresh(self, now: Optional[datetime] = None) -> bool:
        """True when ``now`` is strictly before ``expires_at``."""
        from datetime import timezone

        clock = now if now is not None else datetime.now(timezone.utc)
        exp = self.expires_at
        if clock.tzinfo is None and exp.tzinfo is not None:
            clock = clock.replace(tzinfo=timezone.utc)
        elif clock.tzinfo is not None and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return clock < exp


class PriceCacheRepo(Protocol):
    """Port: short-lived quote store keyed by ``(asset_type, symbol)``."""

    def get(
        self,
        asset_type: str,
        symbol: str,
        *,
        allow_expired: bool = False,
    ) -> Optional[CachedPrice]:
        """Return cached quote or ``None``.

        When ``allow_expired`` is False (default), only fresh (non-expired)
        entries are returned. When True, last-good prices may be returned
        even past TTL (for external-failure fallback).
        """
        ...

    def put(self, quote: PriceQuote, ttl_seconds: int) -> CachedPrice:
        """Upsert quote with ``expires_at = now + ttl_seconds``."""
        ...


__all__ = [
    "AssetType",
    "CachedPrice",
    "PriceCacheRepo",
    "PriceQuote",
]
