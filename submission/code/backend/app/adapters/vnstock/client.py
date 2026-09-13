"""vnstock market client — fixture-based (no live HTTP / vnstock dep in S04).

Real library calls can replace fixtures later without changing the port.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence

from app.adapters.vnstock.catalog import (
    fixture_heatmap_rows,
    stock_catalog,
    stock_prices,
    stock_profile_meta,
)
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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _quote_from_value(symbol: str, name: str, value: float, change_pct: float) -> QuoteRow:
    change = value * change_pct / 100.0
    prev = value - change
    open_px = prev
    return QuoteRow(
        symbol=symbol,
        name=name,
        value=value,
        change=change,
        change_pct=change_pct,
        open=open_px,
        high=max(value, open_px, prev),
        low=min(value, open_px, prev),
        prev=prev,
    )


def group_quote_rows(
    items: list[tuple[str, QuoteRow]],
    *,
    limit: int,
    empty_name: str = "Khác",
) -> list[QuoteGroup]:
    """Sort by value, trim to ``limit``, and rebuild industry/category buckets."""
    capped = sorted(items, key=lambda item: item[1].value, reverse=True)[:limit]
    buckets: dict[str, list[QuoteRow]] = {}
    for name, row in capped:
        buckets.setdefault(name or empty_name, []).append(row)
    return [
        QuoteGroup(
            name=name,
            rows=tuple(sorted(rows, key=lambda r: r.value, reverse=True)),
        )
        for name, rows in sorted(
            buckets.items(),
            key=lambda kv: -sum(r.value for r in kv[1]),
        )
        if rows
    ]


class FixtureVnstockClient:
    """In-process stock client with VN-style fixtures."""

    def __init__(
        self,
        *,
        search_index: Optional[list[AssetSearchResult]] = None,
        prices: Optional[dict[str, tuple[Decimal, str]]] = None,
        fail_prices: bool = False,
    ) -> None:
        self.search_calls = 0
        self.price_calls = 0
        self.last_price_symbols: list[str] = []
        self.fail_prices = fail_prices
        self._search_index = list(search_index or stock_catalog())
        self._prices: dict[str, tuple[Decimal, str]] = dict(prices or stock_prices())

    def list_all(self, *, limit: int = 250) -> list[AssetSearchResult]:
        cap = max(1, min(int(limit), 500))
        return list(self._search_index[:cap])

    def search(self, q: str) -> list[AssetSearchResult]:
        self.search_calls += 1
        needle = (q or "").strip().lower()
        if not needle:
            return []
        return [
            r
            for r in self._search_index
            if needle in r.symbol.lower() or needle in r.name.lower()
        ]

    def get_prices(self, symbols: Sequence[str]) -> list[PriceQuote]:
        self.price_calls += 1
        self.last_price_symbols = [str(s).upper() for s in symbols]
        if self.fail_prices:
            raise MarketDataError("Fixture stock prices unavailable")
        now = _utc_now()
        out: list[PriceQuote] = []
        for sym in symbols:
            key = str(sym).upper()
            if key not in self._prices:
                continue
            price, cur = self._prices[key]
            out.append(
                PriceQuote(
                    asset_type="stock",
                    symbol=key,
                    price=price,
                    currency=cur,
                    as_of=now,
                )
            )
        return out

    def get_history(self, symbol: str, range: str) -> list:
        """Fixture history points; set via ``set_history`` or empty → service synthesizes."""
        self.history_calls = getattr(self, "history_calls", 0) + 1
        self.last_history_symbol = symbol
        self.last_history_range = range
        key = f"{str(symbol).upper()}:{str(range).lower()}"
        hist = getattr(self, "_history", {})
        return list(hist.get(key, hist.get(str(symbol).upper(), [])))

    def set_history(self, symbol: str, range: str, points: list) -> None:
        """Test helper: set fixture history series for (symbol, range)."""
        if not hasattr(self, "_history"):
            self._history = {}
        self._history[f"{symbol.upper()}:{range.lower()}"] = list(points)

    def set_price(self, symbol: str, price: Decimal, currency: str = "VND") -> None:
        """Test helper: upsert fixture price."""
        self._prices[symbol.upper()] = (price, currency)

    def get_profile(self, symbol: str) -> Optional[AssetProfile]:
        self.profile_calls = getattr(self, "profile_calls", 0) + 1
        self.last_profile_symbol = symbol
        key = (symbol or "").strip().upper()
        hit = next((r for r in self._search_index if r.symbol.upper() == key), None)
        if hit is None:
            return None
        meta = stock_profile_meta(hit.symbol)
        desc = meta.get("description") or f"{hit.name} is a Vietnam-listed equity ({hit.symbol})."
        links: dict[str, str] = {}
        homepage = meta.get("homepage")
        if homepage:
            links["homepage"] = str(homepage)
        return AssetProfile(
            asset_type="stock",
            symbol=hit.symbol,
            asset_id=hit.asset_id,
            name=hit.name,
            description=desc,
            image_url=stock_logo_url(hit.symbol, homepage=homepage, explicit=meta.get("image_url")),
            homepage=homepage,
            industry=meta.get("industry"),
            exchange=meta.get("exchange") or "HOSE",
            country=meta.get("country") or "VN",
            links=links,
            market_currency="VND",
            source="catalog",
        )

    def get_heatmap(
        self,
        *,
        exchange: str = "HOSE",
        limit: int = 100,
    ) -> list[HeatmapSector]:
        self.heatmap_calls = getattr(self, "heatmap_calls", 0) + 1
        self.last_heatmap_exchange = exchange
        cap = max(1, min(int(limit), 300))
        grouped: dict[str, list[HeatmapStock]] = {}
        for symbol, name, industry, change_pct, weight in fixture_heatmap_rows():
            image_url = stock_logo_url(symbol)
            if image_url:
                get_logo_cache().put("stock", symbol, image_url)
            grouped.setdefault(industry, []).append(
                HeatmapStock(
                    symbol=symbol,
                    name=name,
                    change_pct=change_pct,
                    market_cap=weight,
                    image_url=image_url,
                )
            )
        # Prefer larger tiles first, then trim to ``limit``.
        flat: list[tuple[str, HeatmapStock]] = []
        for industry, stocks in grouped.items():
            for stock in stocks:
                flat.append((industry, stock))
        flat.sort(key=lambda item: item[1].market_cap, reverse=True)
        flat = flat[:cap]
        out_map: dict[str, list[HeatmapStock]] = {}
        for industry, stock in flat:
            out_map.setdefault(industry, []).append(stock)
        sectors = [
            HeatmapSector(
                name=name,
                stocks=tuple(sorted(stocks, key=lambda s: s.market_cap, reverse=True)),
            )
            for name, stocks in sorted(out_map.items(), key=lambda kv: -sum(s.market_cap for s in kv[1]))
        ]
        return sectors

    def get_quotes(
        self,
        *,
        exchange: str = "HOSE",
        limit: int = 80,
    ) -> list[QuoteGroup]:
        self.quotes_calls = getattr(self, "quotes_calls", 0) + 1
        self.last_quotes_exchange = exchange
        cap = max(1, min(int(limit), 300))
        paired: list[tuple[str, QuoteRow]] = []
        for symbol, name, industry, change_pct, _weight in fixture_heatmap_rows():
            if symbol not in self._prices:
                continue
            value = float(self._prices[symbol][0])
            paired.append((industry, _quote_from_value(symbol, name, value, change_pct)))
        return group_quote_rows(paired, limit=cap)


__all__ = ["FixtureVnstockClient"]
