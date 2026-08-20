"""Explicit response contracts for the public news and history APIs.

The service layer intentionally works with dictionaries so that it can remain
independent of FastAPI.  These models are the boundary contract: they make the
JSON field names visible in OpenAPI, discard legacy/private fields, and keep
cache state consistent for both history endpoints.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiResponseModel(BaseModel):
    """Shared response settings for camelCase JSON DTOs.

    ``extra='ignore'`` is deliberate.  A response model must not accidentally
    expose newly-added internal fields (notably the legacy per-user news
    ``keywords`` attribute) just because a service dictionary contains them.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        coerce_numbers_to_str=True,
    )


class NewsItemResponse(ApiResponseModel):
    """Public, user-filtered news item.

    Keywords are query input and are intentionally absent from this contract;
    returning them would expose one user's private filter configuration to
    every reader of a shared news row.
    """

    id: str
    title: str
    url: Optional[str] = None
    source: str
    published_at: Optional[str] = Field(default=None, alias="publishedAt")
    symbols: list[str]
    date: Optional[str] = None


class HistoryPointResponse(ApiResponseModel):
    """Normalized historical price point.

    Prices are serialized as strings to preserve decimal precision across the
    JSON boundary.  ``priceDisplay`` is nullable when FX data is unavailable.
    """

    t: Optional[str] = None
    price: Optional[str] = None
    price_display: Optional[str] = Field(default=None, alias="priceDisplay")


class FxResponse(ApiResponseModel):
    status: Optional[str] = None
    as_of: Optional[str] = Field(default=None, alias="asOf")
    rate: Optional[str] = None


class HistoryCacheStateResponse(ApiResponseModel):
    """Cache provenance shared by legacy and asset-detail history responses."""

    source: str
    stale: bool
    cached_at: Optional[str] = Field(default=None, alias="cachedAt")
    expires_at: Optional[str] = Field(default=None, alias="expiresAt")


class HistoryResponse(HistoryCacheStateResponse):
    """Response for the legacy ``/api/assets/{id}/history`` route."""

    asset_id: str = Field(alias="assetId")
    range: str
    type: str
    points: list[HistoryPointResponse]


class AssetHistoryResponse(HistoryCacheStateResponse):
    """Response for the resolved asset-detail history route."""

    asset_type: str = Field(alias="assetType")
    symbol: str
    asset_id: str = Field(alias="assetId")
    range: str
    native_currency: str = Field(alias="nativeCurrency")
    display_currency: str = Field(alias="displayCurrency")
    points: list[HistoryPointResponse]
    fx: Optional[FxResponse] = None


class AssetProfileResponse(ApiResponseModel):
    """Profile fields returned by the asset detail page."""

    description: Optional[str] = None
    image_url: Optional[str] = Field(default=None, alias="imageUrl")
    homepage: Optional[str] = None
    categories: list[str] = Field(default_factory=list)
    market_cap_rank: Optional[int] = Field(default=None, alias="marketCapRank")
    genesis_date: Optional[str] = Field(default=None, alias="genesisDate")
    hashing_algorithm: Optional[str] = Field(default=None, alias="hashingAlgorithm")
    circulating_supply: Optional[str] = Field(default=None, alias="circulatingSupply")
    total_supply: Optional[str] = Field(default=None, alias="totalSupply")
    max_supply: Optional[str] = Field(default=None, alias="maxSupply")
    exchange: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    links: dict[str, Optional[str]] = Field(default_factory=dict)


class AssetQuoteResponse(ApiResponseModel):
    """Quote fields returned by the asset detail page."""

    price: Optional[str] = None
    currency: Optional[str] = None
    as_of: Optional[str] = Field(default=None, alias="asOf")
    stale: bool = False
    source: Optional[str] = None
    change_percent_24h: Optional[str] = Field(default=None, alias="changePercent24h")
    change_percent_7d: Optional[str] = Field(default=None, alias="changePercent7d")
    change_percent_30d: Optional[str] = Field(default=None, alias="changePercent30d")
    market_cap: Optional[str] = Field(default=None, alias="marketCap")
    volume_24h: Optional[str] = Field(default=None, alias="volume24h")
    high_24h: Optional[str] = Field(default=None, alias="high24h")
    low_24h: Optional[str] = Field(default=None, alias="low24h")
    ath: Optional[str] = None
    atl: Optional[str] = None
    price_display: Optional[str] = Field(default=None, alias="priceDisplay")
    market_cap_display: Optional[str] = Field(default=None, alias="marketCapDisplay")
    volume_24h_display: Optional[str] = Field(default=None, alias="volume24hDisplay")
    high_24h_display: Optional[str] = Field(default=None, alias="high24hDisplay")
    low_24h_display: Optional[str] = Field(default=None, alias="low24hDisplay")
    asset_id: Optional[str] = Field(default=None, alias="assetId")
    symbol: Optional[str] = None
    asset_type: Optional[str] = Field(default=None, alias="assetType")


class AssetDetailResponse(ApiResponseModel):
    """Profile, quote, FX, and optional history for an asset detail page."""

    asset_type: str = Field(alias="assetType")
    symbol: str
    asset_id: str = Field(alias="assetId")
    name: str
    native_currency: str = Field(alias="nativeCurrency")
    display_currency: str = Field(alias="displayCurrency")
    profile: AssetProfileResponse
    quote: Optional[AssetQuoteResponse] = None
    fx: Optional[FxResponse] = None
    history: Optional[AssetHistoryResponse] = None


__all__ = [
    "ApiResponseModel",
    "AssetDetailResponse",
    "AssetHistoryResponse",
    "AssetProfileResponse",
    "AssetQuoteResponse",
    "FxResponse",
    "HistoryCacheStateResponse",
    "HistoryPointResponse",
    "HistoryResponse",
    "NewsItemResponse",
]
