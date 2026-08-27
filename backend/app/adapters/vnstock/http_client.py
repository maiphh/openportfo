"""Live vnstock client (MARKET_CLIENT_MODE=http).

Fixture fallback is opt-in for tests. Production http mode must not serve
catalog boards on heatmap/quotes — those paths raise MarketDataError (API 502).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional, Sequence

from app.adapters.vnstock.catalog import stock_catalog
from app.adapters.vnstock.client import FixtureVnstockClient, group_quote_rows
from app.adapters.vnstock.logos import stock_logo_url
from app.domain.models import PriceQuote
from app.ports.market import (
    AssetProfile,
    AssetSearchResult,
    HeatmapSector,
    HeatmapStock,
    MarketDataError,
    QuoteGroup,
    QuoteRow,
)
from app.services.logo_cache import get_logo_cache

logger = logging.getLogger(__name__)

_LISTING_TTL_SECONDS = 3600
_HEATMAP_TTL_SECONDS = 120
_HEATMAP_QUOTE_CHUNK = 40
# Default heatmap (100) and quotes (80) both need ≤200 batch quotes; first widget warms both.
_SHARED_QUOTE_FLOOR = 200
# vnstock Quote.history close is in thousands of VND (61.6 → 61_600).
_VNSTOCK_PRICE_SCALE = Decimal("1000")

_SYM_KEYS = ("symbol", "ticker", "ticker_cd", "organ_code", "code")
_NAME_KEYS = (
    "organ_name",
    "company_name",
    "name",
    "company_short_name",
    "organ_short_name",
    "en_organ_name",
)
_CLOSE_KEYS = ("close", "close_price", "c")
_TIME_KEYS = ("time", "date", "trading_date", "t")
_RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
_HOSE_ALIASES = {"HOSE", "HSX", "HOSEBOARD", "HSXBOARD"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stock_heatmap_logo(symbol: str) -> Optional[str]:
    cache = get_logo_cache()
    cached = cache.get("stock", symbol)
    if cached:
        return cached
    url = stock_logo_url(symbol)
    if url:
        cache.put("stock", symbol, url)
    return url


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


def _industry_label(rec: dict[str, Any]) -> str:
    """Industry name from VCI ICB columns or older listing aliases."""
    return str(
        rec.get("icb_name3")
        or rec.get("icb_name4")
        or rec.get("icb_name")
        or rec.get("industry_name")
        or rec.get("industry")
        or ""
    ).strip()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class _QuoteBoardSnapshot:
    """One TTL window of industry + listing + Market.quote work."""

    exchange: str
    quote_cap: int
    complete: bool
    industry_map: dict[str, str]
    name_map: dict[str, str]
    quotes: dict[str, dict[str, float]]
    cached_at: datetime


def _group_heatmap(
    stocks: list[tuple[str, HeatmapStock]],
    *,
    limit: int,
) -> list[HeatmapSector]:
    """Sort by size, trim to ``limit``, and rebuild sector buckets."""
    capped = sorted(stocks, key=lambda item: item[1].market_cap, reverse=True)[:limit]
    buckets: dict[str, list[HeatmapStock]] = {}
    for sector, stock in capped:
        if stock.market_cap <= 0:
            continue
        buckets.setdefault(sector or "Khác", []).append(stock)
    return [
        HeatmapSector(
            name=name,
            stocks=tuple(sorted(items, key=lambda s: s.market_cap, reverse=True)),
        )
        for name, items in sorted(
            buckets.items(),
            key=lambda kv: -sum(s.market_cap for s in kv[1]),
        )
        if items
    ]


class HttpVnstockClient:
    """vnstock wrapper. Catalog fallback is off unless tests opt in."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        use_fixture_fallback: bool = False,
    ) -> None:
        self._fallback = FixtureVnstockClient() if use_fixture_fallback else None
        self._listing_cache: Optional[list[AssetSearchResult]] = None
        self._listing_cached_at: Optional[datetime] = None
        self._heatmap_cache: Optional[tuple[str, int, list[HeatmapSector]]] = None
        self._heatmap_cached_at: Optional[datetime] = None
        self._quotes_cache: Optional[tuple[str, int, list[QuoteGroup]]] = None
        self._quotes_cached_at: Optional[datetime] = None
        self._industry_map_cache: Optional[dict[str, str]] = None
        self._industry_map_cached_at: Optional[datetime] = None
        self._exchange_symbols_cache: Optional[tuple[str, set[str]]] = None
        self._exchange_symbols_cached_at: Optional[datetime] = None
        self._quote_board_cache: Optional[_QuoteBoardSnapshot] = None
        self._live = False
        try:
            import vnstock  # type: ignore  # noqa: F401

            self._apply_api_key(api_key)
            self._live = True
        except Exception:
            if self._fallback is not None:
                logger.warning("vnstock is not importable; stock quotes use catalog fixtures")
            else:
                logger.warning("vnstock is not importable; live stock quotes are unavailable")
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

    def get_profile(self, symbol: str) -> Optional[AssetProfile]:
        key = (symbol or "").strip().upper()
        if not key:
            return None
        if self._live:
            try:
                live = self._live_profile(key)
                if live is not None:
                    live.source = "live"
                    return live
            except Exception:
                pass
        if self._fallback is not None:
            fallback = self._fallback.get_profile(key)
            if fallback is not None:
                fallback.source = "fixture-fallback"
            return fallback
        return None

    def get_heatmap(
        self,
        *,
        exchange: str = "HOSE",
        limit: int = 100,
    ) -> list[HeatmapSector]:
        board = (exchange or "HOSE").strip().upper() or "HOSE"
        cap = max(1, min(int(limit), 300))
        now = _utc_now()
        if (
            self._heatmap_cache is not None
            and self._heatmap_cached_at is not None
            and self._heatmap_cache[0] == board
            and self._heatmap_cache[1] == cap
            and (now - self._heatmap_cached_at).total_seconds() < _HEATMAP_TTL_SECONDS
        ):
            return list(self._heatmap_cache[2])

        sectors: list[HeatmapSector] = []
        if self._live:
            try:
                sectors = self._live_heatmap(board, cap)
            except Exception as exc:
                logger.warning("vnstock heatmap failed: %s", exc)
                if self._fallback is None:
                    if isinstance(exc, MarketDataError):
                        raise
                    raise MarketDataError(f"vnstock heatmap failed: {exc}") from exc
                sectors = []

        if not sectors:
            if self._fallback is not None:
                logger.warning("vnstock heatmap unavailable; using catalog fixture")
                sectors = self._fallback.get_heatmap(exchange=board, limit=cap)
            else:
                raise MarketDataError("vnstock heatmap unavailable")

        self._heatmap_cache = (board, cap, list(sectors))
        self._heatmap_cached_at = now
        return sectors

    def get_quotes(
        self,
        *,
        exchange: str = "HOSE",
        limit: int = 80,
    ) -> list[QuoteGroup]:
        board = (exchange or "HOSE").strip().upper() or "HOSE"
        cap = max(1, min(int(limit), 300))
        now = _utc_now()
        if (
            self._quotes_cache is not None
            and self._quotes_cached_at is not None
            and self._quotes_cache[0] == board
            and self._quotes_cache[1] == cap
            and (now - self._quotes_cached_at).total_seconds() < _HEATMAP_TTL_SECONDS
        ):
            return list(self._quotes_cache[2])

        groups: list[QuoteGroup] = []
        if self._live:
            try:
                groups = self._live_quotes(board, cap)
            except Exception as exc:
                logger.warning("vnstock quotes failed: %s", exc)
                if self._fallback is None:
                    if isinstance(exc, MarketDataError):
                        raise
                    raise MarketDataError(f"vnstock quotes failed: {exc}") from exc
                groups = []

        if not groups:
            if self._fallback is not None:
                logger.warning("vnstock quotes unavailable; using catalog fixture")
                groups = self._fallback.get_quotes(exchange=board, limit=cap)
            else:
                raise MarketDataError("vnstock quotes unavailable")

        self._quotes_cache = (board, cap, list(groups))
        self._quotes_cached_at = now
        return groups

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

    def _live_profile(self, symbol: str) -> Optional[AssetProfile]:
        rec: dict[str, Any] = {}
        rec.update(self._company_rows(symbol))
        if not rec:
            return None
        name = _pick(rec, _NAME_KEYS) or symbol
        description = _pick(
            rec,
            # VN company "about" is usually a dated history timeline (`history`).
            ("history", "history_dev", "company_profile", "description", "overview", "business_model"),
        ) or None
        industry = _pick(rec, ("industry", "icb_name3", "icb_name2", "icb_name", "sector"))
        exchange = _pick(rec, ("exchange", "exchange_name")) or "HOSE"
        homepage = _pick(rec, ("website", "url", "homepage"))
        if homepage and not homepage.startswith("http"):
            homepage = f"https://{homepage}"
        links = {"homepage": homepage} if homepage else {}
        image_url = stock_logo_url(symbol, homepage=homepage or None, provider_row=rec)
        return AssetProfile(
            asset_type="stock",
            symbol=symbol,
            asset_id=symbol,
            name=name,
            description=description,
            image_url=image_url,
            homepage=homepage or None,
            industry=industry or None,
            exchange=exchange,
            country="VN",
            links=links,
            market_currency="VND",
        )

    def _company_rows(self, symbol: str) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        frames: list[Any] = []
        try:
            from vnstock import Company  # type: ignore

            company = Company(symbol=symbol)
            for method in ("overview", "profile"):
                if hasattr(company, method):
                    try:
                        frames.append(getattr(company, method)())
                    except Exception:
                        continue
        except Exception:
            pass
        if not frames:
            try:
                from vnstock import Vnstock  # type: ignore

                company = Vnstock().stock(symbol=symbol, source="VCI").company
                for method in ("overview", "profile"):
                    if hasattr(company, method):
                        try:
                            frames.append(getattr(company, method)())
                        except Exception:
                            continue
            except Exception:
                pass
        for frame in frames:
            rows = _records(frame)
            if rows:
                merged.update(rows[0])
        return merged

    def _live_history(self, symbol: str, range: str) -> list:
        days = _RANGE_DAYS.get((range or "7d").lower(), 7)
        now = _utc_now()
        start = (now.date() - timedelta(days=days)).isoformat()
        end = now.date().isoformat()
        df = self._quote_history(str(symbol).upper(), start, end)
        if df is None or len(df) == 0:
            return []
        return _history_points(df)

    def _live_heatmap(self, exchange: str, limit: int) -> list[HeatmapSector]:
        insights = self._insights_heatmap(exchange, limit)
        if insights:
            return insights
        return self._quote_board_heatmap(exchange, limit)

    def _insights_heatmap(self, exchange: str, limit: int) -> list[HeatmapSector]:
        """Sponsor Insights().sentiment.heatmap when vnstock_data is installed."""
        try:
            from vnstock_data import Insights  # type: ignore
        except Exception:
            return []
        try:
            df = Insights().sentiment.heatmap(exchange=exchange)
        except Exception as exc:
            logger.info("Insights heatmap unavailable: %s", exc)
            return []
        rows = _records(df)
        if not rows:
            return []
        industry_map = self._industry_map()
        name_map = self._symbol_name_map()
        paired: list[tuple[str, HeatmapStock]] = []
        for rec in rows:
            symbol = _pick(rec, _SYM_KEYS).upper()
            if not symbol:
                continue
            change = _to_float(
                rec.get("price_change_percent")
                or rec.get("percent_change")
                or rec.get("price_change")
            )
            size = _to_float(rec.get("market_cap") or rec.get("value_1d") or rec.get("total_value"))
            if size <= 0:
                continue
            sector = (
                industry_map.get(symbol)
                or str(rec.get("industry_name") or rec.get("icb_name") or "").strip()
                or "Khác"
            )
            name = name_map.get(symbol) or _pick(rec, _NAME_KEYS) or symbol
            paired.append(
                (
                    sector,
                    HeatmapStock(
                        symbol=symbol,
                        name=name,
                        change_pct=round(change, 4),
                        market_cap=size,
                        image_url=_stock_heatmap_logo(symbol),
                    ),
                )
            )
        return _group_heatmap(paired, limit=limit)

    def _quote_board(self, exchange: str, limit: int) -> Optional[_QuoteBoardSnapshot]:
        """Shared industry + listing + batch-quote snapshot for heatmap and quotes."""
        board = (exchange or "HOSE").strip().upper() or "HOSE"
        cap = max(1, min(int(limit), 300))
        want = max(cap * 2, cap + 40, _SHARED_QUOTE_FLOOR)
        now = _utc_now()
        cached = self._quote_board_cache
        if (
            cached is not None
            and cached.exchange == board
            and (now - cached.cached_at).total_seconds() < _HEATMAP_TTL_SECONDS
            and (cached.quote_cap >= want or cached.complete)
        ):
            return cached

        industry_map = self._industry_map()
        if not industry_map:
            return None
        allowed = self._exchange_symbols(board)
        name_map = self._symbol_name_map()
        candidates = [
            sym
            for sym in industry_map
            if not allowed or sym in allowed
        ]
        if not candidates:
            candidates = list(industry_map.keys())
        # Quote more than ``limit`` so low-activity names can be dropped later.
        quote_cap = min(len(candidates), want)
        preferred = [
            item.symbol
            for item in stock_catalog()
            if item.symbol in industry_map and (not allowed or item.symbol in allowed)
        ]
        preferred_set = set(preferred)
        rest = [s for s in candidates if s not in preferred_set]
        symbols = (preferred + rest)[:quote_cap]
        quotes = self._batch_quote_rows(symbols)
        snapshot = _QuoteBoardSnapshot(
            exchange=board,
            quote_cap=len(symbols),
            complete=len(symbols) >= len(candidates),
            industry_map=industry_map,
            name_map=name_map,
            quotes=quotes,
            cached_at=now,
        )
        self._quote_board_cache = snapshot
        return snapshot

    def _quote_board_heatmap(self, exchange: str, limit: int) -> list[HeatmapSector]:
        """Build heatmap from the shared quote-board snapshot (free vnstock)."""
        snap = self._quote_board(exchange, limit)
        if snap is None:
            return []
        paired: list[tuple[str, HeatmapStock]] = []
        for symbol, q in snap.quotes.items():
            size = q["size"]
            if size <= 0:
                continue
            paired.append(
                (
                    snap.industry_map.get(symbol, "Khác"),
                    HeatmapStock(
                        symbol=symbol,
                        name=snap.name_map.get(symbol) or symbol,
                        change_pct=round(q["change_pct"], 4),
                        market_cap=size,
                        image_url=_stock_heatmap_logo(symbol),
                    ),
                )
            )
        return _group_heatmap(paired, limit=limit)

    def _live_quotes(self, exchange: str, limit: int) -> list[QuoteGroup]:
        snap = self._quote_board(exchange, limit)
        if snap is None:
            return []
        paired: list[tuple[str, QuoteRow]] = []
        for symbol, q in snap.quotes.items():
            value = q["value"]
            if value <= 0:
                continue
            paired.append(
                (
                    snap.industry_map.get(symbol, "Khác"),
                    QuoteRow(
                        symbol=symbol,
                        name=snap.name_map.get(symbol) or symbol,
                        value=value,
                        change=q["change"],
                        change_pct=round(q["change_pct"], 4),
                        open=q["open"],
                        high=q["high"],
                        low=q["low"],
                        prev=q["prev"],
                    ),
                )
            )
        return group_quote_rows(paired, limit=limit)

    def _industry_map(self) -> dict[str, str]:
        now = _utc_now()
        if (
            self._industry_map_cache is not None
            and self._industry_map_cached_at is not None
            and (now - self._industry_map_cached_at).total_seconds() < _HEATMAP_TTL_SECONDS
        ):
            return self._industry_map_cache
        try:
            from vnstock import Listing  # type: ignore

            df = Listing().symbols_by_industries()
        except Exception:
            try:
                from vnstock import Reference  # type: ignore

                df = Reference().industry.sectors()
            except Exception:
                return {}
        out: dict[str, str] = {}
        for rec in _records(df):
            symbol = _pick(rec, _SYM_KEYS).upper()
            industry = _industry_label(rec)
            if symbol and industry:
                out[symbol] = industry
        if out:
            self._industry_map_cache = out
            self._industry_map_cached_at = now
        return out

    def _symbol_name_map(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for item in self._live_catalog():
            out[item.symbol.upper()] = item.name
        if out:
            return out
        try:
            from vnstock import Listing  # type: ignore

            df = Listing().symbols_by_exchange()
        except Exception:
            return out
        for rec in _records(df):
            symbol = _pick(rec, _SYM_KEYS).upper()
            name = _pick(rec, _NAME_KEYS)
            if symbol and name:
                out[symbol] = name
        return out

    def _exchange_symbols(self, exchange: str) -> set[str]:
        board = (exchange or "HOSE").strip().upper()
        now = _utc_now()
        if (
            self._exchange_symbols_cache is not None
            and self._exchange_symbols_cached_at is not None
            and self._exchange_symbols_cache[0] == board
            and (now - self._exchange_symbols_cached_at).total_seconds() < _HEATMAP_TTL_SECONDS
        ):
            return set(self._exchange_symbols_cache[1])
        try:
            from vnstock import Listing  # type: ignore

            df = Listing().symbols_by_exchange()
        except Exception:
            return set()
        aliases = {board}
        if board in _HOSE_ALIASES:
            aliases |= _HOSE_ALIASES
        if board in {"ALL", "*"}:
            aliases = set()
        out: set[str] = set()
        for rec in _records(df):
            ex = str(rec.get("exchange") or "").strip().upper()
            if aliases and ex and ex not in aliases:
                continue
            symbol = _pick(rec, _SYM_KEYS).upper()
            if symbol:
                out.add(symbol)
        self._exchange_symbols_cache = (board, out)
        self._exchange_symbols_cached_at = now
        return out

    def _batch_quotes(self, symbols: Sequence[str]) -> dict[str, dict[str, float]]:
        rows = self._batch_quote_rows(symbols)
        return {sym: {"change_pct": q["change_pct"], "size": q["size"]} for sym, q in rows.items()}

    def _batch_quote_rows(self, symbols: Sequence[str]) -> dict[str, dict[str, float]]:
        from vnstock import Market  # type: ignore

        market = Market()
        out: dict[str, dict[str, float]] = {}
        chunk = max(1, _HEATMAP_QUOTE_CHUNK)
        for i in range(0, len(symbols), chunk):
            batch = [str(s).upper() for s in symbols[i : i + chunk]]
            try:
                df = market.quote(symbol=batch)
            except Exception as exc:
                logger.warning("heatmap quote batch failed (%s): %s", len(batch), exc)
                continue
            for rec in _records(df):
                symbol = _pick(rec, _SYM_KEYS).upper()
                if not symbol:
                    continue
                last = _to_float(
                    rec.get("close_price")
                    or rec.get("match_price")
                    or rec.get("last_price")
                    or rec.get("close")
                    or rec.get("price")
                )
                change = _to_float(rec.get("price_change") or rec.get("change"))
                pct = _to_float(
                    rec.get("percent_change")
                    or rec.get("price_change_percent")
                    or rec.get("change_percent")
                )
                open_px = _to_float(rec.get("open_price") or rec.get("open"))
                high = _to_float(
                    rec.get("high_price") or rec.get("high") or rec.get("highest")
                )
                low = _to_float(rec.get("low_price") or rec.get("low") or rec.get("lowest"))
                prev = _to_float(
                    rec.get("reference_price")
                    or rec.get("ref_price")
                    or rec.get("reference")
                    or rec.get("prior_close")
                    or rec.get("previous_close")
                )
                size = _to_float(
                    rec.get("market_cap")
                    or rec.get("total_value")
                    or rec.get("value_1d")
                    or rec.get("volume_accumulated")
                )
                if last and pct and not change:
                    change = last * pct / 100.0
                if last and change and not pct:
                    pct = (change / last) * 100.0
                if last and change and not prev:
                    prev = last - change
                elif last and prev and not change:
                    change = last - prev
                    if last and not pct:
                        pct = (change / last) * 100.0
                if not open_px:
                    open_px = prev or last
                if not high:
                    high = max(last, open_px, prev)
                if not low:
                    candidates = [x for x in (last, open_px, prev) if x]
                    low = min(candidates) if candidates else last
                out[symbol] = {
                    "value": last,
                    "change": change,
                    "change_pct": pct,
                    "open": open_px,
                    "high": high,
                    "low": low,
                    "prev": prev,
                    "size": size,
                }
        return out


__all__ = ["HttpVnstockClient", "_industry_label"]
