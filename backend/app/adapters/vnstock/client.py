"""vnstock market client — fixture-based (no live HTTP / vnstock dep in S04).

Real library calls can replace fixtures later without changing the port.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence

from app.adapters.vnstock.catalog import stock_catalog, stock_prices, stock_profile_meta
from app.domain.models import PriceQuote
from app.ports.market import AssetProfile, AssetSearchResult, MarketDataError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
        if meta.get("homepage"):
            links["homepage"] = str(meta["homepage"])
        return AssetProfile(
            asset_type="stock",
            symbol=hit.symbol,
            asset_id=hit.asset_id,
            name=hit.name,
            description=desc,
            homepage=meta.get("homepage"),
            industry=meta.get("industry"),
            exchange=meta.get("exchange") or "HOSE",
            country=meta.get("country") or "VN",
            links=links,
            market_currency="VND",
            source="catalog",
        )


__all__ = ["FixtureVnstockClient"]
