"""Historical price series with cache-aside ObjectStorage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Literal, Optional, Sequence

from app.ports.market import CryptoMarketClient, MarketDataError, StockMarketClient
from app.ports.storage import ObjectStorage

HistoryRange = Literal["7d", "30d", "90d", "1y"]
VALID_RANGES: frozenset[str] = frozenset({"7d", "30d", "90d", "1y"})
VALID_TYPES: frozenset[str] = frozenset({"crypto", "stock"})


class HistoryValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass
class HistoryPoint:
    t: datetime
    price: Decimal


def build_history_key(asset_type: str, asset_id: str, range_: str) -> str:
    """Locked key layout: history/{asset_type}/{asset_id}/{range}.json"""
    return f"history/{asset_type.lower()}/{asset_id}/{range_.lower()}.json"


def _range_days(range_: str) -> int:
    return {"7d": 7, "30d": 30, "90d": 90, "1y": 365}[range_]


def _synthetic_series(
    *,
    asset_type: str,
    asset_id: str,
    range_: str,
    base_price: Decimal = Decimal("100"),
) -> list[dict[str, Any]]:
    """Generate deterministic fixture history points (adapters/fakes)."""
    days = _range_days(range_)
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    points: list[dict[str, Any]] = []
    # sparse daily points
    step = max(1, days // 7)
    for i in range(0, days + 1, step):
        t = now - timedelta(days=days - i)
        # slight drift by day index for visual demos
        price = base_price + Decimal(i)
        points.append({"t": t.isoformat(), "price": format(price, "f")})
    return points


def normalize_series(raw: Sequence[Any]) -> list[dict[str, Any]]:
    """Normalize client series to ``[{t, price}, ...]`` string/iso form."""
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            t = item.get("t") or item.get("time") or item.get("timestamp")
            price = item.get("price") or item.get("close")
            if t is None or price is None:
                continue
            if isinstance(t, datetime):
                t_s = t.isoformat()
            else:
                t_s = str(t)
            out.append({"t": t_s, "price": format(Decimal(str(price)), "f")})
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            t, price = item[0], item[1]
            if isinstance(t, datetime):
                t_s = t.isoformat()
            elif isinstance(t, (int, float)):
                # ms or s epoch
                ts = float(t)
                if ts > 1e12:
                    ts = ts / 1000.0
                t_s = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            else:
                t_s = str(t)
            out.append({"t": t_s, "price": format(Decimal(str(price)), "f")})
    return out


class HistoryService:
    """Cache-aside history: ObjectStorage then market client."""

    def __init__(
        self,
        storage: ObjectStorage,
        crypto: CryptoMarketClient,
        stock: StockMarketClient,
    ) -> None:
        self._storage = storage
        self._crypto = crypto
        self._stock = stock

    def get_history(
        self,
        *,
        asset_id: str,
        asset_type: str,
        range_: str,
    ) -> dict[str, Any]:
        at = (asset_type or "").strip().lower()
        rng = (range_ or "").strip().lower()
        aid = (asset_id or "").strip()
        if not aid:
            raise HistoryValidationError("asset_id is required")
        if at not in VALID_TYPES:
            raise HistoryValidationError("type must be crypto or stock")
        if rng not in VALID_RANGES:
            raise HistoryValidationError("range must be one of 7d, 30d, 90d, 1y")

        key = build_history_key(at, aid, rng)
        cached = self._storage.get_json(key)
        if cached is not None:
            payload = dict(cached)
            payload["source"] = "cache"
            return payload

        if at == "crypto":
            raw = self._crypto.get_market_chart(aid, rng)
        else:
            raw = self._stock.get_history(aid, rng)

        if not raw:
            # Demo fallback only — never persist synthetic series as live cache.
            series = _synthetic_series(asset_type=at, asset_id=aid, range_=rng)
            return {
                "assetId": aid,
                "range": rng,
                "type": at,
                "points": series,
                "source": "synthetic",
            }

        series = normalize_series(raw)
        payload = {
            "assetId": aid,
            "range": rng,
            "type": at,
            "points": series,
        }
        self._storage.put_json(key, payload)
        out = dict(payload)
        out["source"] = "live"
        return out


__all__ = [
    "HistoryService",
    "HistoryValidationError",
    "VALID_RANGES",
    "build_history_key",
    "normalize_series",
]
