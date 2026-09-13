"""DynamoDB PriceCacheRepo.

Table: openportfo-price-cache
PK: pk = {assetType}#{symbol}
Optional Dynamo TTL attribute ``ttl`` (epoch seconds).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from app.adapters.dynamodb.base import (
    dt_to_iso,
    get_table,
    iso_to_dt,
    sanitize_for_dynamo,
    to_decimal,
    utc_now,
)
from app.domain.models import PriceQuote
from app.ports.price_cache import CachedPrice


def cache_pk(asset_type: str, symbol: str) -> str:
    return f"{asset_type.strip().lower()}#{symbol.strip().upper()}"


def cached_to_item(cached: CachedPrice) -> dict[str, Any]:
    exp = cached.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    item = {
        "pk": cache_pk(cached.asset_type, cached.symbol),
        "assetType": cached.asset_type,
        "symbol": cached.symbol.upper(),
        "price": to_decimal(cached.price),
        "currency": cached.currency,
        "asOf": dt_to_iso(cached.as_of),
        "expiresAt": dt_to_iso(cached.expires_at),
        # DynamoDB native TTL (optional cleanup); logical freshness uses expiresAt
        "ttl": int(exp.timestamp()) + 3600,
    }
    return sanitize_for_dynamo(item)


def item_to_cached(item: dict[str, Any]) -> CachedPrice:
    return CachedPrice(
        asset_type=str(item["assetType"]).lower(),  # type: ignore[arg-type]
        symbol=str(item["symbol"]).upper(),
        price=to_decimal(item["price"]),
        currency=str(item["currency"]),
        as_of=iso_to_dt(item.get("asOf")) or utc_now(),
        expires_at=iso_to_dt(item.get("expiresAt")) or utc_now(),
    )


class DynamoPriceCacheRepo:
    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table=None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)
        self._clock = clock or utc_now

    def get(
        self,
        asset_type: str,
        symbol: str,
        *,
        allow_expired: bool = False,
    ) -> Optional[CachedPrice]:
        resp = self._table.get_item(Key={"pk": cache_pk(asset_type, symbol)})
        item = resp.get("Item")
        if not item:
            return None
        cached = item_to_cached(item)
        if not allow_expired and not cached.is_fresh(self._clock()):
            return None
        return cached

    def put(self, quote: PriceQuote, ttl_seconds: int) -> CachedPrice:
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must be >= 0")
        now = self._clock()
        at = str(quote.asset_type).strip().lower()
        sym = quote.symbol.strip().upper()
        as_of = quote.as_of
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)
        cached = CachedPrice(
            asset_type=at,  # type: ignore[arg-type]
            symbol=sym,
            price=quote.price,
            currency=quote.currency,
            as_of=as_of,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self._table.put_item(Item=cached_to_item(cached))
        return cached


__all__ = [
    "DynamoPriceCacheRepo",
    "cache_pk",
    "cached_to_item",
    "item_to_cached",
]
