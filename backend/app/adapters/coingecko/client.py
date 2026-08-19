"""CoinGecko market client — fixture-based (no live HTTP in S04).

Real REST calls can replace fixtures later without changing the port.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence

from app.adapters.coingecko.catalog import (
    crypto_catalog,
    crypto_prices,
    crypto_profile_meta,
    fixture_crypto_heatmap_rows,
)
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


def _group_quote_rows(
    items: list[tuple[str, QuoteRow]],
    *,
    limit: int,
    empty_name: str = "Others",
) -> list[QuoteGroup]:
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


class FixtureCoinGeckoClient:
    """In-process crypto client with searchable fixtures and price map by coin id."""

    def __init__(
        self,
        *,
        search_index: Optional[list[AssetSearchResult]] = None,
        prices: Optional[dict[str, tuple[Decimal, str]]] = None,
        fail_prices: bool = False,
    ) -> None:
        self.search_calls = 0
        self.price_calls = 0
        self.last_price_ids: list[str] = []
        self.fail_prices = fail_prices
        self._search_index = list(search_index or crypto_catalog())
        self._prices: dict[str, tuple[Decimal, str]] = dict(prices or crypto_prices())
        self._id_to_symbol: dict[str, str] = {
            r.asset_id: r.symbol for r in self._search_index
        }

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
            if needle in r.symbol.lower()
            or needle in r.name.lower()
            or needle in r.asset_id.lower()
        ]

    def get_simple_prices(
        self,
        ids: Sequence[str],
        vs: str = "usd",
    ) -> list[PriceQuote]:
        self.price_calls += 1
        self.last_price_ids = [str(i) for i in ids]
        if self.fail_prices:
            raise MarketDataError("Fixture crypto prices unavailable")
        now = _utc_now()
        currency = (vs or "usd").upper()
        out: list[PriceQuote] = []
        for coin_id in ids:
            key = str(coin_id).lower()
            if key not in self._prices:
                continue
            price, cur = self._prices[key]
            quote_cur = cur if currency == "USD" else currency
            symbol = self._id_to_symbol.get(key, key.upper())
            out.append(
                PriceQuote(
                    asset_type="crypto",
                    symbol=symbol.upper(),
                    price=price,
                    currency=quote_cur,
                    as_of=now,
                )
            )
        return out

    def get_market_chart(self, id: str, range: str) -> list:
        """Fixture history points; set via ``set_chart`` or empty → service synthesizes."""
        self.chart_calls = getattr(self, "chart_calls", 0) + 1
        self.last_chart_id = id
        self.last_chart_range = range
        key = f"{str(id).lower()}:{str(range).lower()}"
        charts = getattr(self, "_charts", {})
        return list(charts.get(key, charts.get(str(id).lower(), [])))

    def set_chart(self, coin_id: str, range: str, points: list) -> None:
        """Test helper: set fixture chart series for (id, range)."""
        if not hasattr(self, "_charts"):
            self._charts = {}
        self._charts[f"{coin_id.lower()}:{range.lower()}"] = list(points)

    def set_price(self, coin_id: str, price: Decimal, currency: str = "USD") -> None:
        """Test helper: upsert fixture price."""
        self._prices[coin_id.lower()] = (price, currency)

    def get_profile(self, id: str) -> Optional[AssetProfile]:
        self.profile_calls = getattr(self, "profile_calls", 0) + 1
        self.last_profile_id = id
        coin_id = (id or "").strip().lower()
        hit = next((r for r in self._search_index if r.asset_id.lower() == coin_id), None)
        if hit is None:
            hit = next((r for r in self._search_index if r.symbol.lower() == coin_id), None)
        if hit is None:
            return None
        meta = crypto_profile_meta(hit.asset_id)
        desc = meta.get("description") or f"{hit.name} is a cryptocurrency ({hit.symbol})."
        links: dict[str, str] = {}
        if meta.get("homepage"):
            links["homepage"] = str(meta["homepage"])
        max_supply = meta.get("max_supply")
        return AssetProfile(
            asset_type="crypto",
            symbol=hit.symbol,
            asset_id=hit.asset_id,
            name=hit.name,
            description=desc,
            image_url=meta.get("image_url"),
            homepage=meta.get("homepage"),
            categories=list(meta.get("categories") or []),
            market_cap_rank=meta.get("market_cap_rank"),
            genesis_date=meta.get("genesis_date"),
            hashing_algorithm=meta.get("hashing_algorithm"),
            max_supply=Decimal(str(max_supply)) if max_supply else None,
            links=links,
            market_currency="USD",
            source="catalog",
        )

    def get_heatmap(self, *, limit: int = 100) -> list[HeatmapSector]:
        self.heatmap_calls = getattr(self, "heatmap_calls", 0) + 1
        cap = max(1, min(int(limit), 300))
        grouped: dict[str, list[HeatmapStock]] = {}
        for _coin_id, symbol, name, category, change_pct, market_cap in fixture_crypto_heatmap_rows():
            grouped.setdefault(category, []).append(
                HeatmapStock(
                    symbol=symbol,
                    name=name,
                    change_pct=change_pct,
                    market_cap=market_cap,
                )
            )
        flat: list[tuple[str, HeatmapStock]] = []
        for category, stocks in grouped.items():
            for stock in stocks:
                flat.append((category, stock))
        flat.sort(key=lambda item: item[1].market_cap, reverse=True)
        flat = flat[:cap]
        out_map: dict[str, list[HeatmapStock]] = {}
        for category, stock in flat:
            out_map.setdefault(category, []).append(stock)
        return [
            HeatmapSector(
                name=name,
                stocks=tuple(sorted(stocks, key=lambda s: s.market_cap, reverse=True)),
            )
            for name, stocks in sorted(
                out_map.items(),
                key=lambda kv: -sum(s.market_cap for s in kv[1]),
            )
        ]

    def get_quotes(self, *, limit: int = 80) -> list[QuoteGroup]:
        self.quotes_calls = getattr(self, "quotes_calls", 0) + 1
        cap = max(1, min(int(limit), 300))
        paired = []
        for coin_id, symbol, name, category, change_pct, _mcap in fixture_crypto_heatmap_rows():
            if coin_id not in self._prices:
                continue
            value = float(self._prices[coin_id][0])
            paired.append((category, _quote_from_value(symbol, name, value, change_pct)))
        return _group_quote_rows(paired, limit=cap)


__all__ = ["FixtureCoinGeckoClient"]
