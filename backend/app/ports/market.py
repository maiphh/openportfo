"""Market data client ports (CoinGecko / vnstock in prod, fixtures in local/test).

Browser must never call external market APIs — only FastAPI via these ports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class AssetProfile:
    """Provider profile for the asset detail page (crypto or VN stock)."""

    asset_type: AssetType
    symbol: str
    asset_id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    homepage: Optional[str] = None
    categories: list[str] = field(default_factory=list)
    market_cap_rank: Optional[int] = None
    genesis_date: Optional[str] = None
    hashing_algorithm: Optional[str] = None
    circulating_supply: Optional[Decimal] = None
    total_supply: Optional[Decimal] = None
    max_supply: Optional[Decimal] = None
    exchange: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    links: dict[str, str] = field(default_factory=dict)
    change_percent_24h: Optional[Decimal] = None
    change_percent_7d: Optional[Decimal] = None
    change_percent_30d: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    volume_24h: Optional[Decimal] = None
    high_24h: Optional[Decimal] = None
    low_24h: Optional[Decimal] = None
    ath: Optional[Decimal] = None
    atl: Optional[Decimal] = None
    market_currency: Optional[str] = None
    # "live" | "catalog" (cacheable) | "fixture-fallback" (do not persist)
    source: str = "live"


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

    def get_profile(self, id: str) -> Optional[AssetProfile]:
        """Coin profile/description. ``None`` if the id is unknown."""
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

    def get_profile(self, symbol: str) -> Optional[AssetProfile]:
        """Company profile/description. ``None`` if the ticker is unknown."""
        ...


__all__ = [
    "AssetType",
    "AssetSearchResult",
    "AssetProfile",
    "CryptoMarketClient",
    "StockMarketClient",
    "MarketDataError",
    "PriceQuote",
]
