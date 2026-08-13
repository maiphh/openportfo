"""Live vnstock client with fixture fallback when library/network fails.

MARKET_CLIENT_MODE=http. Unit tests keep FixtureVnstockClient.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional, Sequence

from app.adapters.vnstock.client import FixtureVnstockClient
from app.domain.models import PriceQuote
from app.ports.market import AssetSearchResult, MarketDataError

logger = logging.getLogger(__name__)

_LISTING_TTL_SECONDS = 3600
# vnstock Quote.history close is in thousands of VND (61.6 → 61_600).
_VNSTOCK_PRICE_SCALE = Decimal("1000")

_SYM_KEYS = ("symbol", "ticker", "ticker_cd", "organ_code", "code")
_NAME_KEYS = (
    "organ_name",
    "company_name",
    "name",
    "company_short_name",
    "organ_short_name",
)
_CLOSE_KEYS = ("close", "close_price", "c")
_TIME_KEYS = ("time", "date", "trading_date", "t")
_RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _scale_vnstock_price(raw: Any) -> Decimal:
    return Decimal(str(raw)) * _VNSTOCK_PRICE_SCALE


def _pick(row: dict[str, Any], keys: Sequence[str]) -> str:
    for k in keys:
        val = row.get(k)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _records(df: Any) -> list[dict[str, Any]]:
    if df is None:
        return []
    try:
        if hasattr(df, "to_dict"):
            raw = df.to_dict(orient="records")
            return [{str(k).lower(): rec[k] for k in rec} for rec in raw]
    except Exception:
        pass
    if isinstance(df, list):
        out: list[dict[str, Any]] = []
        for rec in df:
            if isinstance(rec, dict):
                out.append({str(k).lower(): v for k, v in rec.items()})
        return out
    return []


def _history_points(df: Any) -> list:
    if df is None or len(df) == 0:
        return []
    cols = {str(c).lower(): c for c in getattr(df, "columns", [])}
    close_col = next((cols[k] for k in _CLOSE_KEYS if k in cols), None)
    if close_col is None and cols:
        close_col = df.columns[-1]
    time_col = next((cols[k] for k in _TIME_KEYS if k in cols), None)
    out: list = []
    try:
        iterator = df.iterrows()
    except Exception:
        return []
    for idx, row in iterator:
        try:
            t = row[time_col] if time_col is not None else idx
            price = row[close_col] if close_col is not None else None
            if price is None:
                continue
            out.append([t, _scale_vnstock_price(price)])
        except Exception:
            continue
    return out


class HttpVnstockClient:
    """Best-effort vnstock wrapper; falls back to fixtures on import/runtime failure."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        use_fixture_fallback: bool = True,
    ) -> None:
        self._fallback = FixtureVnstockClient() if use_fixture_fallback else None
        self._listing_cache: Optional[list[AssetSearchResult]] = None
        self._listing_cached_at: Optional[datetime] = None
        self._live = False
        try:
            import vnstock  # type: ignore  # noqa: F401

            self._apply_api_key(api_key)
            self._live = True
        except Exception:
            logger.warning("vnstock is not importable; stock quotes use catalog fixtures")
            self._live = False

    def list_all(self, *, limit: int = 250) -> list[AssetSearchResult]:
        cap = max(1, min(int(limit), 2000))
        if self._live:
            try:
                lib = self._live_list(cap)
                if lib:
                    return lib
            except Exception:
                pass
        if self._fallback is not None:
            return self._fallback.list_all(limit=cap)
        return []

    def search(self, q: str) -> list[AssetSearchResult]:
        needle = (q or "").strip().lower()
        if not needle:
            return []
        if self._live:
            try:
                lib = self._live_search(q)
                if lib:
                    return lib
            except Exception:
                pass
        if self._fallback is not None:
            return self._fallback.search(q)
        return []

    def get_prices(self, symbols: Sequence[str]) -> list[PriceQuote]:
        if not symbols:
            return []
        if not self._live:
            if self._fallback is not None:
                logger.warning("vnstock not live; returning catalog fixture prices")
                return self._fallback.get_prices(symbols)
            raise MarketDataError("vnstock not available")

        out: list[PriceQuote] = []
        now = _utc_now()
        start = (now.date().replace(day=1)).isoformat()
        end = now.date().isoformat()
        try:
            for sym in symbols:
                key = str(sym).upper()
                try:
                    df = self._quote_history(key, start, end)
                    if df is None or len(df) == 0:
                        continue
                    close_col = "close" if "close" in df.columns else df.columns[-1]
                    price = _scale_vnstock_price(df.iloc[-1][close_col])
                    out.append(
                        PriceQuote(
                            asset_type="stock",
                            symbol=key,
                            price=price,
                            currency="VND",
                            as_of=now,
                        )
                    )
                except Exception:
                    continue
        except Exception as exc:
            if self._fallback is not None:
                logger.warning("vnstock price fetch failed; returning catalog fixtures: %s", exc)
                return self._fallback.get_prices(symbols)
            raise MarketDataError(f"vnstock prices failed: {exc}") from exc

        if not out and self._fallback is not None:
            logger.warning("vnstock returned no prices; returning catalog fixtures")
            return self._fallback.get_prices(symbols)
        return out

    def get_history(self, symbol: str, range: str) -> list:
        if self._live:
            try:
                live = self._live_history(symbol, range)
                if live:
                    return live
            except Exception:
                pass
        if self._fallback is not None:
            return self._fallback.get_history(symbol, range)
        return []

    def _map_listing(self, rec: dict[str, Any]) -> Optional[AssetSearchResult]:
        symbol = _pick(rec, _SYM_KEYS).upper()
        if not symbol:
            return None
        name = _pick(rec, _NAME_KEYS) or symbol
        return AssetSearchResult(
            symbol=symbol,
            name=name,
            asset_id=symbol,
            asset_type="stock",
            currency="VND",
        )

    def _live_catalog(self) -> list[AssetSearchResult]:
        now = _utc_now()
        if (
            self._listing_cache is not None
            and self._listing_cached_at is not None
            and (now - self._listing_cached_at).total_seconds() < _LISTING_TTL_SECONDS
        ):
            return self._listing_cache
        df = self._listing_frame()
        if df is None or len(df) == 0:
            return []
        out: list[AssetSearchResult] = []
        seen: set[str] = set()
        for rec in _records(df):
            item = self._map_listing(rec)
            if item is None or item.symbol in seen:
                continue
            seen.add(item.symbol)
            out.append(item)
        out.sort(key=lambda r: r.symbol)
        self._listing_cache = out
        self._listing_cached_at = now
        return out

    def _live_list(self, limit: int) -> list[AssetSearchResult]:
        return self._live_catalog()[:limit]

    def _live_search(self, q: str) -> list[AssetSearchResult]:
        needle = (q or "").strip().lower()
        if not needle:
            return []
        out: list[AssetSearchResult] = []
        for item in self._live_catalog():
            if needle not in item.symbol.lower() and needle not in item.name.lower():
                continue
            out.append(item)
            if len(out) >= 50:
                break
        return out

    @staticmethod
    def _apply_api_key(api_key: Optional[str]) -> None:
        key = (api_key or "").strip()
        if not key:
            return
        try:
            from vnstock.core import setup_api_key  # type: ignore

            setup_api_key(key)
        except Exception:
            logger.warning("vnstock API key could not be applied")

    def _listing_frame(self) -> Any:
        from vnstock import Listing  # type: ignore

        listing = Listing()
        df = listing.all_symbols()
        if df is not None and len(df) > 0:
            return df
        return None

    def _quote_history(self, symbol: str, start: str, end: str) -> Any:
        from vnstock import Quote  # type: ignore

        quote = Quote(symbol=symbol)
        return quote.history(start=start, end=end, interval="1D")

    def _live_history(self, symbol: str, range: str) -> list:
        days = _RANGE_DAYS.get((range or "7d").lower(), 7)
        now = _utc_now()
        start = (now.date() - timedelta(days=days)).isoformat()
        end = now.date().isoformat()
        df = self._quote_history(str(symbol).upper(), start, end)
        if df is None or len(df) == 0:
            return []
        return _history_points(df)


__all__ = ["HttpVnstockClient"]
