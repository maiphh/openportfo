"""Historical price series with cache-aside ObjectStorage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, DecimalException
from typing import Any, Callable, Literal, Optional, Sequence

from app.ports.market import CryptoMarketClient, MarketDataError, StockMarketClient
from app.ports.storage import ObjectStorage

HistoryRange = Literal["7d", "30d", "90d", "1y"]
VALID_RANGES: frozenset[str] = frozenset({"7d", "30d", "90d", "1y"})
VALID_TYPES: frozenset[str] = frozenset({"crypto", "stock"})
DEFAULT_HISTORY_CACHE_TTL_SECONDS = 3600


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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalize injected/provider timestamps for reliable expiry comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse cache timestamps without making malformed legacy data fresh."""
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        # datetime.fromisoformat accepts offsets but not the common JSON ``Z``.
        return _as_utc(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        return None


def _iso_timestamp(value: datetime) -> str:
    return _as_utc(value).isoformat()


def _synthetic_series(
    *,
    asset_type: str,
    asset_id: str,
    range_: str,
    base_price: Decimal = Decimal("100"),
    now: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Generate deterministic fixture history points (adapters/fakes)."""
    days = _range_days(range_)
    series_now = _as_utc(now or _utc_now()).replace(hour=0, minute=0, second=0, microsecond=0)
    points: list[dict[str, Any]] = []
    # sparse daily points
    step = max(1, days // 7)
    for i in range(0, days + 1, step):
        t = series_now - timedelta(days=days - i)
        # slight drift by day index for visual demos
        price = base_price + Decimal(i)
        points.append({"t": t.isoformat(), "price": format(price, "f")})
    return points


def normalize_series(raw: Sequence[Any]) -> list[dict[str, Any]]:
    """Normalize client series to ``[{t, price}, ...]`` string/iso form."""
    out: list[dict[str, Any]] = []
    for item in raw:
        try:
            if isinstance(item, dict):
                t = item.get("t") or item.get("time") or item.get("timestamp")
                price = item.get("price") or item.get("close")
                if t is None or price is None:
                    continue
                if isinstance(t, datetime):
                    t_s = t.isoformat()
                else:
                    t_s = str(t)
                normalized_price = format(Decimal(str(price)), "f")
                out.append({"t": t_s, "price": normalized_price})
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
                normalized_price = format(Decimal(str(price)), "f")
                out.append({"t": t_s, "price": normalized_price})
        except (DecimalException, OverflowError, OSError, TypeError, ValueError):
            # A malformed point must not make an otherwise usable series fail.
            continue
    return out


class HistoryService:
    """Cache-aside history: ObjectStorage then market client."""

    def __init__(
        self,
        storage: ObjectStorage,
        crypto: CryptoMarketClient,
        stock: StockMarketClient,
        *,
        ttl_seconds: int = DEFAULT_HISTORY_CACHE_TTL_SECONDS,
        cache_ttl_seconds: Optional[int] = None,
        history_ttl_seconds: Optional[int] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._storage = storage
        self._crypto = crypto
        self._stock = stock
        requested_ttl = (
            history_ttl_seconds
            if history_ttl_seconds is not None
            else cache_ttl_seconds
            if cache_ttl_seconds is not None
            else ttl_seconds
        )
        self._ttl_seconds = max(0, int(requested_ttl))
        self._clock = clock or _utc_now

    @property
    def ttl_seconds(self) -> int:
        """Logical history freshness window used for newly fetched series."""
        return self._ttl_seconds

    def _now(self) -> datetime:
        return _as_utc(self._clock())

    def _is_fresh(self, payload: dict[str, Any], now: datetime) -> bool:
        """Return whether a cache payload has explicit, unexpired metadata.

        Older S07 objects contain only ``assetId``, ``range``, ``type`` and
        ``points``. They deliberately do not get an inferred age: legacy data
        is treated as expired so the next request revalidates it.
        """
        expires_raw = payload.get("expiresAt")
        if expires_raw is None:
            # Accept internal snake_case objects while keeping the public
            # storage format camelCase. Entries without any expiry remain
            # legacy/expired by design.
            expires_raw = payload.get("expires_at")
        expires_at = _parse_timestamp(expires_raw)
        return expires_at is not None and now < expires_at

    @staticmethod
    def _usable_cached_payload(value: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if not isinstance(value, dict):
            return None
        points = value.get("points")
        if not isinstance(points, list):
            return None
        return dict(value)

    def _with_state(
        self,
        payload: dict[str, Any],
        *,
        source: str,
        stale: bool,
    ) -> dict[str, Any]:
        """Return a response DTO without leaking response state into storage."""
        out = dict(payload)
        out["source"] = source
        out["stale"] = bool(stale)
        return out

    def _cache_payload(
        self,
        *,
        asset_id: str,
        asset_type: str,
        range_: str,
        points: list[dict[str, Any]],
        now: datetime,
    ) -> dict[str, Any]:
        cached_at = _iso_timestamp(now)
        expires_at = _iso_timestamp(now + timedelta(seconds=self._ttl_seconds))
        return {
            "assetId": asset_id,
            "range": range_,
            "type": asset_type,
            "points": points,
            "cachedAt": cached_at,
            "expiresAt": expires_at,
        }

    def get_history(
        self,
        *,
        asset_id: str,
        asset_type: str,
        range_: str,
        force: bool = False,
        refresh: bool = False,
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
        cached = self._usable_cached_payload(self._storage.get_json(key))
        now = self._now()
        if cached is not None and not (force or refresh) and self._is_fresh(cached, now):
            return self._with_state(cached, source="cache", stale=False)

        # Keep expired/legacy data as last-good while revalidating. Force
        # refresh follows this same fallback path.
        try:
            if at == "crypto":
                raw = self._crypto.get_market_chart(aid, rng)
            else:
                raw = self._stock.get_history(aid, rng)
        except Exception as exc:
            if cached is not None:
                return self._with_state(cached, source="cache", stale=True)
            detail = getattr(exc, "detail", None) or str(exc) or "Market data unavailable"
            raise MarketDataError(detail) from exc

        series = normalize_series(raw) if raw else []
        if not series:
            if cached is not None:
                return self._with_state(cached, source="cache", stale=True)
            # Demo fallback only — never persist synthetic series as live cache.
            synthetic = _synthetic_series(asset_type=at, asset_id=aid, range_=rng, now=now)
            return self._with_state(
                {
                    "assetId": aid,
                    "range": rng,
                    "type": at,
                    "points": synthetic,
                },
                source="synthetic",
                stale=False,
            )

        payload = self._cache_payload(
            asset_id=aid,
            asset_type=at,
            range_=rng,
            points=series,
            now=now,
        )
        self._storage.put_json(key, payload)
        return self._with_state(payload, source="live", stale=False)


__all__ = [
    "HistoryService",
    "HistoryValidationError",
    "DEFAULT_HISTORY_CACHE_TTL_SECONDS",
    "VALID_RANGES",
    "build_history_key",
    "normalize_series",
]
