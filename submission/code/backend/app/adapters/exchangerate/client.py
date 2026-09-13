"""HTTP adapter for ExchangeRate-API (v6 latest endpoint).

Server-side only. Services depend on ExchangeRateClient port, not this class.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

import httpx

from app.ports.fx import ProviderError, RateSnapshot


class HttpExchangeRateClient:
    """Fetch latest rates from ExchangeRate-API.

    GET https://v6.exchangerate-api.com/v6/{KEY}/latest/{BASE}
    """

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = 10.0,
        base_url: str = "https://v6.exchangerate-api.com/v6",
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._timeout = timeout_seconds
        self._base_url = base_url.rstrip("/")
        self._transport = transport

    def fetch_latest(self, base: str = "USD") -> RateSnapshot:
        if not self._api_key:
            raise ProviderError("EXCHANGE_RATE_API_KEY is not configured")

        base_u = (base or "USD").upper()
        url = f"{self._base_url}/{self._api_key}/latest/{base_u}"
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                resp = client.get(url)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Exchange rate request failed: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderError(
                f"Exchange rate provider HTTP {resp.status_code}"
            )

        try:
            data: dict[str, Any] = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderError("Invalid JSON from exchange rate provider") from exc

        result = (data.get("result") or "").lower()
        if result and result != "success":
            raise ProviderError(
                data.get("error-type") or data.get("error") or "Provider reported failure"
            )

        conversion = data.get("conversion_rates") or data.get("rates") or {}
        if not isinstance(conversion, dict) or not conversion:
            raise ProviderError("Provider response missing conversion_rates")

        rates: dict[str, Decimal] = {}
        for currency, value in conversion.items():
            cur = str(currency).upper()
            if cur == base_u:
                continue
            try:
                rates[f"{base_u}_{cur}"] = Decimal(str(value))
            except Exception:  # noqa: BLE001
                continue

        # Prefer explicit VND pair + inverse for portfolio display
        vnd_key = f"{base_u}_VND"
        if vnd_key in rates and rates[vnd_key] != 0:
            rates[f"VND_{base_u}"] = Decimal("1") / rates[vnd_key]

        if not rates:
            raise ProviderError("No usable rates in provider response")

        return RateSnapshot(
            base=base_u,
            rates=rates,
            provider="exchangerate-api",
            fetched_at=datetime.now(timezone.utc),
            raw=data,
        )


__all__ = ["HttpExchangeRateClient"]
