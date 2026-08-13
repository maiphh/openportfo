"""Market data client ports (CoinGecko / vnstock in prod, fixtures in local/test).

Browser must never call external market APIs — only FastAPI via these ports.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Optional, Protocol, Sequence

from app.domain.models import PriceQuote

AssetType = Literal["crypto", "stock"]


class MarketDataError(Exception):
    """Raised when external market data fails and no usable cache is available."""

    def __init__(self, detail: str = "Market data unavailable") -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class AssetSearchResult:
    """One hit from crypto/stock search (mapped to API DTO by MarketService)."""

    symbol: str
    name: str
    asset_id: str
    asset_type: AssetType
    # Optional extras from providers (ignored by API if unused)
    currency: Optional[str] = None


class CryptoMarketClient(Protocol):
    """Port: CoinGecko (or fixture). Prices keyed by provider coin id."""

    def list_all(self, *, limit: int = 250) -> list[AssetSearchResult]:
        """Return a catalog of coins for browse/search (cap with ``limit``)."""
        ...

    def search(self, q: str) -> list[AssetSearchResult]:
        """Search coins by name/symbol; ``asset_type`` is always ``crypto``."""
        ...

    def get_simple_prices(
        self,
        ids: Sequence[str],
        vs: str = "usd",
    ) -> list[PriceQuote]:
        """Batch current prices for coin ids (e.g. ``bitcoin``).

        Returned quotes should set ``asset_type="crypto"`` and ``symbol`` to
        the canonical ticker when known (else uppercased id).
        """
        ...

    def get_market_chart(self, id: str, range: str) -> list:
        """Historical series for coin ``id`` and range (e.g. ``7d``). Stub OK until S07."""
        ...


class StockMarketClient(Protocol):
    """Port: vnstock (or fixture). Prices keyed by ticker symbol."""

    def list_all(self, *, limit: int = 250) -> list[AssetSearchResult]:
        """Return a catalog of VN stocks for browse/search (cap with ``limit``)."""
        ...

    def search(self, q: str) -> list[AssetSearchResult]:
        """Search VN stocks by ticker/name; ``asset_type`` is always ``stock``."""
        ...

    def get_prices(self, symbols: Sequence[str]) -> list[PriceQuote]:
        """Batch current prices for stock symbols (e.g. ``VNM``)."""
        ...

    def get_history(self, symbol: str, range: str) -> list:
        """Historical series for stock ``symbol``. Stub OK until S07."""
        ...


__all__ = [
    "AssetType",
    "AssetSearchResult",
    "CryptoMarketClient",
    "StockMarketClient",
    "MarketDataError",
    "PriceQuote",
]
