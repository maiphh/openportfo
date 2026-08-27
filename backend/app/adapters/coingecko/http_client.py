"""Live CoinGecko HTTP client (MARKET_CLIENT_MODE=http).

Fixture fallback is opt-in for tests. Production http mode must not serve
catalog boards on heatmap/quotes — those paths raise MarketDataError (API 502).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Sequence

import httpx

from app.adapters.coingecko.catalog import crypto_category
from app.adapters.coingecko.client import FixtureCoinGeckoClient
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
_MARKETS_TTL_SECONDS = 120


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _group_heatmap(
    stocks: list[tuple[str, HeatmapStock]],
    *,
    limit: int,
) -> list[HeatmapSector]:
    capped = sorted(stocks, key=lambda item: item[1].market_cap, reverse=True)[:limit]
    buckets: dict[str, list[HeatmapStock]] = {}
    for sector, stock in capped:
        if stock.market_cap <= 0:
            continue
        buckets.setdefault(sector or "Others", []).append(stock)
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


def _group_quotes(
    items: list[tuple[str, QuoteRow]],
    *,
    limit: int,
) -> list[QuoteGroup]:
    capped = sorted(items, key=lambda item: item[1].value, reverse=True)[:limit]
    buckets: dict[str, list[QuoteRow]] = {}
    for name, row in capped:
        buckets.setdefault(name or "Others", []).append(row)
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


class HttpCoinGeckoClient:
    """CoinGecko REST client. Catalog fallback is off unless tests opt in."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = "https://api.coingecko.com/api/v3",
        timeout_seconds: float = 15.0,
        transport: Optional[httpx.BaseTransport] = None,
        use_fixture_fallback: bool = False,
    ) -> None:
        self._api_key = (api_key or "").strip() or None
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._transport = transport
        self._fallback = FixtureCoinGeckoClient() if use_fixture_fallback else None
        self._markets_cache: Optional[tuple[int, list[dict[str, Any]]]] = None
        self._markets_cached_at: Optional[datetime] = None

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._api_key:
            # Demo key header (Pro uses x-cg-pro-api-key)
            headers["x-cg-demo-api-key"] = self._api_key
        return headers

    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(
                timeout=self._timeout,
                transport=self._transport,
                headers=self._headers(),
            ) as client:
                resp = client.get(url, params=params or {})
        except httpx.HTTPError as exc:
            raise MarketDataError(f"CoinGecko request failed: {exc}") from exc
        if resp.status_code != 200:
            raise MarketDataError(f"CoinGecko HTTP {resp.status_code}")
        return resp.json()

    def list_all(self, *, limit: int = 250) -> list[AssetSearchResult]:
        cap = max(1, min(int(limit), 250))
        data = self._get(
            "/coins/markets",
            {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": cap,
                "page": 1,
                "sparkline": "false",
            },
        )
        out: list[AssetSearchResult] = []
        for c in data or []:
            if not isinstance(c, dict):
                continue
            coin_id = str(c.get("id") or "").strip()
            if not coin_id:
                continue
            out.append(
                AssetSearchResult(
                    symbol=str(c.get("symbol") or "").upper(),
                    name=str(c.get("name") or coin_id),
                    asset_id=coin_id,
                    asset_type="crypto",
                    currency="USD",
                )
            )
        return out

    def search(self, q: str) -> list[AssetSearchResult]:
        needle = (q or "").strip()
        if not needle:
            return []
        data = self._get("/search", {"query": needle})
        coins = (data or {}).get("coins") or []
        out: list[AssetSearchResult] = []
        for c in coins[:20]:
            out.append(
                AssetSearchResult(
                    symbol=str(c.get("symbol") or "").upper(),
                    name=str(c.get("name") or ""),
                    asset_id=str(c.get("id") or ""),
                    asset_type="crypto",
                    currency="USD",
                )
            )
        return out

    def get_simple_prices(
        self,
        ids: Sequence[str],
        vs: str = "usd",
    ) -> list[PriceQuote]:
        if not ids:
            return []
        id_list = ",".join(str(i).lower() for i in ids)
        vs_c = (vs or "usd").lower()
        data = self._get(
            "/simple/price",
            {"ids": id_list, "vs_currencies": vs_c},
        )
        now = _utc_now()
        currency = vs_c.upper()
        out: list[PriceQuote] = []
        for coin_id in ids:
            key = str(coin_id).lower()
            row = (data or {}).get(key) or {}
            price = row.get(vs_c)
            if price is None:
                continue
            out.append(
                PriceQuote(
                    asset_type="crypto",
                    # simple/price has no ticker; leave coin id (MarketService matches asset_id)
                    symbol=key.upper(),
                    price=Decimal(str(price)),
                    currency=currency,
                    as_of=now,
                )
            )
        return out

    def get_market_chart(self, id: str, range: str) -> list:
        days_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = days_map.get((range or "7d").lower(), 7)
        data = self._get(
            f"/coins/{id}/market_chart",
            {"vs_currency": "usd", "days": days},
        )
        prices = (data or {}).get("prices") or []
        return [[p[0], p[1]] for p in prices if isinstance(p, (list, tuple)) and len(p) >= 2]

    def get_profile(self, id: str) -> Optional[AssetProfile]:
        coin_id = (id or "").strip()
        if not coin_id:
            return None
        data = self._get(
            f"/coins/{coin_id}",
            {
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false",
            },
        )
        if not isinstance(data, dict) or not data.get("id"):
            return None
        return profile_from_coingecko(data)

    def get_heatmap(self, *, limit: int = 100) -> list[HeatmapSector]:
        cap = max(1, min(int(limit), 300))
        try:
            coins = self._live_markets(cap)
            sectors = self._heatmap_from_markets(coins, cap)
            if sectors:
                return sectors
        except Exception as exc:
            logger.warning("CoinGecko heatmap failed: %s", exc)
            if self._fallback is None:
                if isinstance(exc, MarketDataError):
                    raise
                raise MarketDataError(f"CoinGecko heatmap failed: {exc}") from exc
        if self._fallback is not None:
            logger.warning("CoinGecko heatmap unavailable; using catalog fixture")
            return self._fallback.get_heatmap(limit=cap)
        raise MarketDataError("CoinGecko heatmap unavailable")

    def get_quotes(self, *, limit: int = 80) -> list[QuoteGroup]:
        cap = max(1, min(int(limit), 300))
        try:
            coins = self._live_markets(cap)
            groups = self._quotes_from_markets(coins, cap)
            if groups:
                return groups
        except Exception as exc:
            logger.warning("CoinGecko quotes failed: %s", exc)
            if self._fallback is None:
                if isinstance(exc, MarketDataError):
                    raise
                raise MarketDataError(f"CoinGecko quotes failed: {exc}") from exc
        if self._fallback is not None:
            logger.warning("CoinGecko quotes unavailable; using catalog fixture")
            return self._fallback.get_quotes(limit=cap)
        raise MarketDataError("CoinGecko quotes unavailable")

    def _live_markets(self, limit: int) -> list[dict[str, Any]]:
        now = _utc_now()
        per_page = min(max(1, int(limit)), 250)
        if (
            self._markets_cache is not None
            and self._markets_cached_at is not None
            and self._markets_cache[0] >= per_page
            and (now - self._markets_cached_at).total_seconds() < _MARKETS_TTL_SECONDS
        ):
            return self._markets_cache[1][:per_page]
        data = self._get(
            "/coins/markets",
            {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": 1,
                "sparkline": "false",
            },
        )
        coins = [c for c in (data or []) if isinstance(c, dict)]
        self._markets_cache = (per_page, coins)
        self._markets_cached_at = now
        return coins

    def _heatmap_from_markets(
        self,
        coins: list[dict[str, Any]],
        limit: int,
    ) -> list[HeatmapSector]:
        paired: list[tuple[str, HeatmapStock]] = []
        for rec in coins:
            coin_id = str(rec.get("id") or "").strip()
            symbol = str(rec.get("symbol") or "").upper()
            if not symbol:
                continue
            market_cap = _to_float(rec.get("market_cap"))
            if market_cap <= 0:
                continue
            image_url = str(rec.get("image") or "").strip() or None
            if image_url:
                cache = get_logo_cache()
                cache.put("crypto", symbol, image_url)
                if coin_id:
                    cache.put("crypto", coin_id, image_url)
            paired.append(
                (
                    crypto_category(coin_id, symbol),
                    HeatmapStock(
                        symbol=symbol,
                        name=str(rec.get("name") or symbol),
                        change_pct=round(_to_float(rec.get("price_change_percentage_24h")), 4),
                        market_cap=market_cap,
                        image_url=image_url,
                    ),
                )
            )
        return _group_heatmap(paired, limit=limit)

    def _quotes_from_markets(
        self,
        coins: list[dict[str, Any]],
        limit: int,
    ) -> list[QuoteGroup]:
        paired: list[tuple[str, QuoteRow]] = []
        for rec in coins:
            coin_id = str(rec.get("id") or "").strip()
            symbol = str(rec.get("symbol") or "").upper()
            if not symbol:
                continue
            value = _to_float(rec.get("current_price"))
            if value <= 0:
                continue
            change = _to_float(rec.get("price_change_24h"))
            pct = _to_float(rec.get("price_change_percentage_24h"))
            high = _to_float(rec.get("high_24h"))
            low = _to_float(rec.get("low_24h"))
            prev = value - change
            open_px = prev
            if not high:
                high = max(value, open_px, prev)
            if not low:
                candidates = [x for x in (value, open_px, prev) if x]
                low = min(candidates) if candidates else value
            paired.append(
                (
                    crypto_category(coin_id, symbol),
                    QuoteRow(
                        symbol=symbol,
                        name=str(rec.get("name") or symbol),
                        value=value,
                        change=change,
                        change_pct=round(pct, 4),
                        open=open_px,
                        high=high,
                        low=low,
                        prev=prev,
                    ),
                )
            )
        return _group_quotes(paired, limit=limit)


def _first_url(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, (list, tuple)):
        for item in value:
            if item and str(item).strip():
                return str(item).strip()
    return None


def _as_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _currency_map_value(data: Any, key: str = "usd") -> Optional[Decimal]:
    if not isinstance(data, dict):
        return None
    return _as_decimal(data.get(key))


def profile_from_coingecko(data: dict[str, Any]) -> AssetProfile:
    """Map CoinGecko /coins/{id} JSON to AssetProfile (native USD stats)."""
    description = None
    desc = data.get("description")
    if isinstance(desc, dict):
        description = (desc.get("en") or "").strip() or None
    elif isinstance(desc, str):
        description = desc.strip() or None
    image = data.get("image") if isinstance(data.get("image"), dict) else {}
    links_raw = data.get("links") if isinstance(data.get("links"), dict) else {}
    homepage = _first_url(links_raw.get("homepage"))
    twitter = (links_raw.get("twitter_screen_name") or "").strip()
    reddit = _first_url(links_raw.get("subreddit_url"))
    github = None
    repos = links_raw.get("repos_url") if isinstance(links_raw.get("repos_url"), dict) else {}
    if isinstance(repos.get("github"), list) and repos["github"]:
        github = _first_url(repos["github"])
    whitepaper = _first_url(links_raw.get("whitepaper"))
    links: dict[str, str] = {}
    if homepage:
        links["homepage"] = homepage
    if twitter:
        links["twitter"] = f"https://twitter.com/{twitter.lstrip('@')}"
    if reddit:
        links["reddit"] = reddit
    if github:
        links["github"] = github
    if whitepaper:
        links["whitepaper"] = whitepaper
    md = data.get("market_data") if isinstance(data.get("market_data"), dict) else {}
    categories = [str(c) for c in (data.get("categories") or []) if c]
    return AssetProfile(
        asset_type="crypto",
        symbol=str(data.get("symbol") or "").upper(),
        asset_id=str(data.get("id") or ""),
        name=str(data.get("name") or data.get("id") or ""),
        description=description,
        image_url=_first_url((image or {}).get("large") or (image or {}).get("small")),
        homepage=homepage,
        categories=categories,
        market_cap_rank=int(data["market_cap_rank"]) if data.get("market_cap_rank") is not None else None,
        genesis_date=(str(data.get("genesis_date") or "").strip() or None),
        hashing_algorithm=(str(data.get("hashing_algorithm") or "").strip() or None),
        circulating_supply=_as_decimal(md.get("circulating_supply")),
        total_supply=_as_decimal(md.get("total_supply")),
        max_supply=_as_decimal(md.get("max_supply")),
        links=links,
        change_percent_24h=_as_decimal(md.get("price_change_percentage_24h")),
        change_percent_7d=_as_decimal(md.get("price_change_percentage_7d")),
        change_percent_30d=_as_decimal(md.get("price_change_percentage_30d")),
        market_cap=_currency_map_value(md.get("market_cap")),
        volume_24h=_currency_map_value(md.get("total_volume")),
        high_24h=_currency_map_value(md.get("high_24h")),
        low_24h=_currency_map_value(md.get("low_24h")),
        ath=_currency_map_value(md.get("ath")),
        atl=_currency_map_value(md.get("atl")),
        market_currency="USD",
    )


__all__ = ["HttpCoinGeckoClient", "profile_from_coingecko"]
