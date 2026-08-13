"""CoinGecko market client — fixture-based (no live HTTP in S04).

Real REST calls can replace fixtures later without changing the port.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence

from app.adapters.coingecko.catalog import crypto_catalog, crypto_prices
from app.domain.models import PriceQuote
from app.ports.market import AssetSearchResult, MarketDataError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


__all__ = ["FixtureCoinGeckoClient"]
