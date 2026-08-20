"""In-memory price cache adapter for local development and tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from app.domain.models import PriceQuote
from app.ports.price_cache import CachedPrice


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _key(asset_type: str, symbol: str) -> tuple[str, str]:
    return (asset_type.strip().lower(), symbol.strip().upper())


class InMemoryPriceCacheRepo:
    """Dict-backed price cache keyed by ``(asset_type, symbol)``."""

    def __init__(
        self,
        *,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._items: dict[tuple[str, str], CachedPrice] = {}
        self._clock = clock or _utc_now
        self.put_calls = 0
        self.get_calls = 0

    def get(
        self,
        asset_type: str,
        symbol: str,
        *,
        allow_expired: bool = False,
    ) -> Optional[CachedPrice]:
        self.get_calls += 1
        item = self._items.get(_key(asset_type, symbol))
        if item is None:
            return None
        if not allow_expired and not item.is_fresh(self._clock()):
            return None
        return deepcopy(item)

    def put(self, quote: PriceQuote, ttl_seconds: int) -> CachedPrice:
        self.put_calls += 1
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must be >= 0")
        now = self._clock()
        at = quote.asset_type.strip().lower()  # type: ignore[union-attr]
        sym = quote.symbol.strip().upper()
        cached = CachedPrice(
            asset_type=at,  # type: ignore[arg-type]
            symbol=sym,
            price=quote.price,
            currency=quote.currency,
            as_of=quote.as_of if quote.as_of.tzinfo else quote.as_of.replace(tzinfo=timezone.utc),
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self._items[_key(at, sym)] = cached
        return deepcopy(cached)

    def clear(self) -> None:
        """Test helper: wipe cache."""
        self._items.clear()

    def seed(
        self,
        quote: PriceQuote,
        *,
        ttl_seconds: int = 600,
        expires_at: Optional[datetime] = None,
    ) -> CachedPrice:
        """Test helper: put with optional fixed expiry (for stale tests)."""
        if expires_at is not None:
            at = quote.asset_type.strip().lower()
            sym = quote.symbol.strip().upper()
            cached = CachedPrice(
                asset_type=at,  # type: ignore[arg-type]
                symbol=sym,
                price=quote.price,
                currency=quote.currency,
                as_of=quote.as_of,
                expires_at=expires_at,
            )
            self._items[_key(at, sym)] = cached
            return deepcopy(cached)
        return self.put(quote, ttl_seconds)

