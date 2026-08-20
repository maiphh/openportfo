"""Asset detail page: resolve slug, profile, quote, history + stored FX."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from app.domain.fx_math import get_rate
from app.domain.models import FxRates
from app.ports.fx import ExchangeRateRepo, StoredRates
from app.ports.market import (
    AssetProfile,
    AssetSearchResult,
    CryptoMarketClient,
    MarketDataError,
    StockMarketClient,
)
from app.ports.storage import ObjectStorage
from app.services.history_service import HistoryService, HistoryValidationError
from app.services.market_service import MarketService, QuoteKey, ValidationError

VALID_TYPES = frozenset({"crypto", "stock"})
VALID_RANGES = frozenset({"7d", "30d", "90d", "1y"})
DIRECT_CRYPTO_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class AssetNotFoundError(Exception):
    def __init__(self, detail: str = "Asset not found") -> None:
        self.detail = detail
        super().__init__(detail)


def native_currency(asset_type: str) -> str:
    return "USD" if asset_type == "crypto" else "VND"


def profile_cache_key(asset_type: str, asset_id: str) -> str:
    return f"profile/{asset_type.lower()}/{asset_id}.json"


def resolve_cache_key(asset_type: str, slug: str) -> str:
    return f"resolve/{asset_type.lower()}/{slug.strip().lower()}.json"


def _dec_str(value: Optional[Decimal]) -> Optional[str]:
    if value is None:
        return None
    return format(value, "f")


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def stored_to_fx(stored: Optional[StoredRates]) -> Optional[FxRates]:
    if stored is None or not stored.rates:
        return None
    status = stored.status if stored.status in {"missing", "stale_ok", "fresh"} else "fresh"
    if not stored.rates:
        status = "missing"
    return FxRates(
        base=stored.base,
        rates=dict(stored.rates),
        status=status,  # type: ignore[arg-type]
        as_of=stored.as_of,
    )


def convert_amount(amount: Optional[Decimal], rate: Optional[Decimal]) -> Optional[Decimal]:
    if amount is None or rate is None:
        return None
    return amount * rate


class AssetDetailService:
    """Compose profile + quote + history for /crypto/btc and /stock/VNM pages."""

    def __init__(
        self,
        market: MarketService,
        history: HistoryService,
        crypto: CryptoMarketClient,
        stock: StockMarketClient,
        storage: ObjectStorage,
        fx_repo: Optional[ExchangeRateRepo] = None,
    ) -> None:
        self._market = market
        self._history = history
        self._crypto = crypto
        self._stock = stock
        self._storage = storage
        self._fx = fx_repo

    def resolve(self, asset_type: str, slug: str) -> AssetSearchResult:
        at = (asset_type or "").strip().lower()
        needle = (slug or "").strip()
        if at not in VALID_TYPES:
            raise ValidationError("type must be 'crypto' or 'stock'")
        if not needle:
            raise ValidationError("asset slug is required")
        cached = self._storage.get_json(resolve_cache_key(at, needle))
        if isinstance(cached, dict) and cached.get("assetId") and cached.get("symbol"):
            return AssetSearchResult(
                symbol=str(cached["symbol"]),
                name=str(cached.get("name") or cached["symbol"]),
                asset_id=str(cached["assetId"]),
                asset_type=at,  # type: ignore[arg-type]
                currency=cached.get("currency"),
            )

        # Canonical crypto links carry the provider's coin id (for example
        # ``book-of-meme``), so resolve that id directly before searching by
        # text. CoinGecko's search endpoint is optimized for names/symbols and
        # does not reliably return an exact hit when queried with an id. The
        # browse fallback is also capped, which made valid lower-ranked coins
        # impossible to open from a search result.
        if at == "crypto" and DIRECT_CRYPTO_ID_RE.fullmatch(needle):
            try:
                direct_profile = self._crypto.get_profile(needle)
            except MarketDataError:
                direct_profile = None
            if (
                direct_profile is not None
                and direct_profile.asset_id.strip()
                and direct_profile.symbol.strip()
            ):
                hit = AssetSearchResult(
                    symbol=direct_profile.symbol,
                    name=direct_profile.name or direct_profile.symbol,
                    asset_id=direct_profile.asset_id,
                    asset_type="crypto",
                    currency=direct_profile.market_currency or "USD",
                )
                self._cache_resolution(hit, needle)
                if (direct_profile.source or "live") != "fixture-fallback":
                    self._storage.put_json(
                        profile_cache_key(hit.asset_type, hit.asset_id),
                        self._profile_to_cache(direct_profile),
                    )
                return hit

        try:
            hits = self._market.search(needle, at)
        except ValidationError:
            hits = []
        hit: Optional[AssetSearchResult] = None
        for candidate in hits:
            if candidate.symbol.upper() == needle.upper():
                hit = candidate
                break
        if hit is None:
            for candidate in hits:
                if candidate.asset_id.lower() == needle.lower():
                    hit = candidate
                    break
        if hit is None:
            for candidate in self._market.list_assets(at, limit=500):
                if (
                    candidate.symbol.upper() == needle.upper()
                    or candidate.asset_id.lower() == needle.lower()
                ):
                    hit = candidate
                    break
        if hit is None:
            raise AssetNotFoundError(f"Asset not found: {at}/{needle}")
        self._cache_resolution(hit, needle)
        return hit

    def _cache_resolution(self, hit: AssetSearchResult, requested_slug: str) -> None:
        payload = {
            "assetType": hit.asset_type,
            "symbol": hit.symbol,
            "assetId": hit.asset_id,
            "name": hit.name,
            "currency": hit.currency,
        }
        aliases = {requested_slug.lower(), hit.symbol.lower(), hit.asset_id.lower()}
        for alias in aliases:
            self._storage.put_json(resolve_cache_key(hit.asset_type, alias), payload)

    def get_detail(
        self,
        *,
        asset_type: str,
        slug: str,
        currency: Optional[str] = None,
        range_: Optional[str] = None,
        force: bool = False,
        refresh: bool = False,
        preferred_currency: Optional[str] = None,
    ) -> dict[str, Any]:
        resolved = self.resolve(asset_type, slug)
        display = (currency or preferred_currency or "").strip().upper() or native_currency(
            resolved.asset_type
        )
        profile = self._load_profile(resolved)
        quote = self._load_quote(resolved)
        fx_meta, rate = self._fx_meta(native_currency(resolved.asset_type), display)
        history = None
        if range_:
            history = self.get_history(
                asset_type=resolved.asset_type,
                slug=resolved.symbol,
                range_=range_,
                currency=display,
                force=bool(force or refresh),
                resolved=resolved,
            )
        return {
            "assetType": resolved.asset_type,
            "symbol": resolved.symbol,
            "assetId": resolved.asset_id,
            "name": profile.name if profile else resolved.name,
            "nativeCurrency": native_currency(resolved.asset_type),
            "displayCurrency": display,
            "profile": self._profile_to_dict(profile, resolved),
            "quote": self._quote_to_dict(quote, profile, resolved, rate),
            "fx": fx_meta,
            "history": history,
        }

    def get_history(
        self,
        *,
        asset_type: str,
        slug: str,
        range_: str,
        currency: Optional[str] = None,
        force: bool = False,
        refresh: bool = False,
        preferred_currency: Optional[str] = None,
        resolved: Optional[AssetSearchResult] = None,
    ) -> dict[str, Any]:
        hit = resolved or self.resolve(asset_type, slug)
        rng = (range_ or "").strip().lower()
        if rng not in VALID_RANGES:
            raise HistoryValidationError("range must be one of 7d, 30d, 90d, 1y")
        native = native_currency(hit.asset_type)
        display = (currency or preferred_currency or "").strip().upper() or native
        raw = self._history.get_history(
            asset_id=hit.asset_id,
            asset_type=hit.asset_type,
            range_=rng,
            force=bool(force or refresh),
        )
        fx_meta, rate = self._fx_meta(native, display)
        points = []
        for point in raw.get("points") or []:
            if not isinstance(point, dict):
                continue
            price = point.get("price")
            display_price = None
            if price is not None and rate is not None:
                display_price = format(Decimal(str(price)) * rate, "f")
            points.append(
                {
                    "t": point.get("t"),
                    "price": price,
                    "priceDisplay": display_price,
                }
            )
        return {
            "assetType": hit.asset_type,
            "symbol": hit.symbol,
            "assetId": hit.asset_id,
            "range": rng,
            "nativeCurrency": native,
            "displayCurrency": display,
            "source": raw.get("source"),
            "stale": bool(raw.get("stale")),
            "cachedAt": raw.get("cachedAt"),
            "expiresAt": raw.get("expiresAt"),
            "points": points,
            "fx": fx_meta,
        }

    def _load_profile(self, hit: AssetSearchResult) -> Optional[AssetProfile]:
        key = profile_cache_key(hit.asset_type, hit.asset_id)
        cached = self._storage.get_json(key)
        if isinstance(cached, dict) and cached.get("assetId"):
            return self._profile_from_cache(cached)
        try:
            if hit.asset_type == "crypto":
                profile = self._crypto.get_profile(hit.asset_id)
            else:
                profile = self._stock.get_profile(hit.symbol)
        except MarketDataError:
            profile = None
        if profile is None:
            return None
        if (profile.source or "live") != "fixture-fallback":
            self._storage.put_json(key, self._profile_to_cache(profile))
        return profile

    def _load_quote(self, hit: AssetSearchResult):
        quotes = self._market.get_quotes(
            [
                QuoteKey(
                    asset_type=hit.asset_type,
                    symbol=hit.symbol,
                    asset_id=hit.asset_id,
                )
            ],
            force=False,
        )
        return quotes[0] if quotes else None

    def _fx_meta(self, native: str, display: str) -> tuple[dict[str, Any], Optional[Decimal]]:
        stored = self._fx.get_latest() if self._fx is not None else None
        fx_domain = stored_to_fx(stored)
        rate = None
        status = "missing"
        as_of = stored.as_of if stored is not None else None
        if native == display:
            rate = Decimal("1")
            status = (stored.status if stored is not None else "fresh") or "fresh"
            if stored is not None and stored.rates:
                status = stored.status
        elif fx_domain is not None:
            rate = get_rate(fx_domain, native, display)
            status = fx_domain.status if rate is not None else "missing"
            if rate is None:
                status = "missing"
        return (
            {
                "status": status if rate is not None or native == display else "missing",
                "asOf": _iso(as_of),
                "rate": _dec_str(rate),
            },
            rate,
        )

    def _profile_to_dict(
        self,
        profile: Optional[AssetProfile],
        hit: AssetSearchResult,
    ) -> dict[str, Any]:
        if profile is None:
            return {
                "description": f"{hit.name} ({hit.symbol}).",
                "imageUrl": None,
                "homepage": None,
                "categories": [],
                "marketCapRank": None,
                "genesisDate": None,
                "hashingAlgorithm": None,
                "circulatingSupply": None,
                "totalSupply": None,
                "maxSupply": None,
                "exchange": "HOSE" if hit.asset_type == "stock" else None,
                "industry": None,
                "country": "VN" if hit.asset_type == "stock" else None,
                "links": {},
            }
        return {
            "description": profile.description,
            "imageUrl": profile.image_url,
            "homepage": profile.homepage,
            "categories": list(profile.categories or []),
            "marketCapRank": profile.market_cap_rank,
            "genesisDate": profile.genesis_date,
            "hashingAlgorithm": profile.hashing_algorithm,
            "circulatingSupply": _dec_str(profile.circulating_supply),
            "totalSupply": _dec_str(profile.total_supply),
            "maxSupply": _dec_str(profile.max_supply),
            "exchange": profile.exchange,
            "industry": profile.industry,
            "country": profile.country,
            "links": dict(profile.links or {}),
        }

    def _quote_to_dict(
        self,
        quote,
        profile: Optional[AssetProfile],
        hit: AssetSearchResult,
        rate: Optional[Decimal],
    ) -> Optional[dict[str, Any]]:
        if quote is None:
            return None
        price = quote.price
        return {
            "price": format(price, "f"),
            "currency": quote.currency,
            "asOf": _iso(quote.as_of),
            "stale": bool(quote.stale),
            "source": "cache-first",
            "changePercent24h": _dec_str(profile.change_percent_24h) if profile else None,
            "changePercent7d": _dec_str(profile.change_percent_7d) if profile else None,
            "changePercent30d": _dec_str(profile.change_percent_30d) if profile else None,
            "marketCap": _dec_str(profile.market_cap) if profile else None,
            "volume24h": _dec_str(profile.volume_24h) if profile else None,
            "high24h": _dec_str(profile.high_24h) if profile else None,
            "low24h": _dec_str(profile.low_24h) if profile else None,
            "ath": _dec_str(profile.ath) if profile else None,
            "atl": _dec_str(profile.atl) if profile else None,
            "priceDisplay": _dec_str(convert_amount(price, rate)),
            "marketCapDisplay": _dec_str(
                convert_amount(profile.market_cap, rate) if profile else None
            ),
            "volume24hDisplay": _dec_str(
                convert_amount(profile.volume_24h, rate) if profile else None
            ),
            "high24hDisplay": _dec_str(
                convert_amount(profile.high_24h, rate) if profile else None
            ),
            "low24hDisplay": _dec_str(
                convert_amount(profile.low_24h, rate) if profile else None
            ),
            "assetId": hit.asset_id,
            "symbol": hit.symbol,
            "assetType": hit.asset_type,
        }

    def _profile_to_cache(self, profile: AssetProfile) -> dict[str, Any]:
        return {
            "assetType": profile.asset_type,
            "symbol": profile.symbol,
            "assetId": profile.asset_id,
            "name": profile.name,
            "description": profile.description,
            "imageUrl": profile.image_url,
            "homepage": profile.homepage,
            "categories": list(profile.categories or []),
            "marketCapRank": profile.market_cap_rank,
            "genesisDate": profile.genesis_date,
            "hashingAlgorithm": profile.hashing_algorithm,
            "circulatingSupply": _dec_str(profile.circulating_supply),
            "totalSupply": _dec_str(profile.total_supply),
            "maxSupply": _dec_str(profile.max_supply),
            "exchange": profile.exchange,
            "industry": profile.industry,
            "country": profile.country,
            "links": dict(profile.links or {}),
            "changePercent24h": _dec_str(profile.change_percent_24h),
            "changePercent7d": _dec_str(profile.change_percent_7d),
            "changePercent30d": _dec_str(profile.change_percent_30d),
            "marketCap": _dec_str(profile.market_cap),
            "volume24h": _dec_str(profile.volume_24h),
            "high24h": _dec_str(profile.high_24h),
            "low24h": _dec_str(profile.low_24h),
            "ath": _dec_str(profile.ath),
            "atl": _dec_str(profile.atl),
            "marketCurrency": profile.market_currency,
        }

    def _profile_from_cache(self, data: dict[str, Any]) -> AssetProfile:
        def _d(key: str) -> Optional[Decimal]:
            raw = data.get(key)
            if raw is None or raw == "":
                return None
            return Decimal(str(raw))

        return AssetProfile(
            asset_type=data.get("assetType") or "crypto",  # type: ignore[arg-type]
            symbol=str(data.get("symbol") or ""),
            asset_id=str(data.get("assetId") or ""),
            name=str(data.get("name") or ""),
            description=data.get("description"),
            image_url=data.get("imageUrl"),
            homepage=data.get("homepage"),
            categories=list(data.get("categories") or []),
            market_cap_rank=data.get("marketCapRank"),
            genesis_date=data.get("genesisDate"),
            hashing_algorithm=data.get("hashingAlgorithm"),
            circulating_supply=_d("circulatingSupply"),
            total_supply=_d("totalSupply"),
            max_supply=_d("maxSupply"),
            exchange=data.get("exchange"),
            industry=data.get("industry"),
            country=data.get("country"),
            links=dict(data.get("links") or {}),
            change_percent_24h=_d("changePercent24h"),
            change_percent_7d=_d("changePercent7d"),
            change_percent_30d=_d("changePercent30d"),
            market_cap=_d("marketCap"),
            volume_24h=_d("volume24h"),
            high_24h=_d("high24h"),
            low_24h=_d("low24h"),
            ath=_d("ath"),
            atl=_d("atl"),
            market_currency=data.get("marketCurrency"),
        )


__all__ = [
    "AssetDetailService",
    "AssetNotFoundError",
    "native_currency",
    "profile_cache_key",
    "resolve_cache_key",
]
