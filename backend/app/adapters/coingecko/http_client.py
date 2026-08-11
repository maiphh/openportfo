"""Live CoinGecko HTTP client (optional; MARKET_CLIENT_MODE=http).

Fixture client remains the unit-test default.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Sequence

import httpx

from app.domain.models import PriceQuote
from app.ports.market import AssetSearchResult, MarketDataError


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


__all__ = ["HttpCoinGeckoClient"]
