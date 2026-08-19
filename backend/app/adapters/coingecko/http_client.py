"""Live CoinGecko HTTP client (optional; MARKET_CLIENT_MODE=http).

Fixture client remains the unit-test default.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Sequence

import httpx

from app.domain.models import PriceQuote
from app.ports.market import AssetProfile, AssetSearchResult, MarketDataError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HttpCoinGeckoClient:
    """Minimal CoinGecko Demo/Pro REST client."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = "https://api.coingecko.com/api/v3",
        timeout_seconds: float = 15.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._api_key = (api_key or "").strip() or None
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._transport = transport

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
