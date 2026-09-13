"""FX rates: read stored rates; admin on-demand refresh via ExchangeRateClient.

Never clears last-good rates on provider failure.
Portfolio GET must not call this refresh path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Callable

from app.ports.fx import (
    ExchangeRateClient,
    ExchangeRateRepo,
    ProviderError,
    RateSnapshot,
    StoredRates,
)
from app.domain.fx_math import get_rate
from app.domain.models import FxRates
from app.services.currency_service import FxContext, fx_context_from_stored, normalize_currency


class ConversionError(Exception):
    """An amount or currency pair cannot be converted with stored rates."""


@dataclass
class FxRefreshResult:
    """Outcome of an admin FX refresh."""

    ok: bool
    stored: Optional[StoredRates]
    error: Optional[str] = None


def ensure_pair_rates(rates: dict[str, Decimal], base: str = "USD") -> dict[str, Decimal]:
    """Ensure flat SRC_DST keys include inverse pairs when one side exists."""
    out = {k.upper(): Decimal(str(v)) for k, v in rates.items()}
    base_u = (base or "USD").upper()
    # Common pair: USD_VND / VND_USD
    direct = f"{base_u}_VND"
    inverse = f"VND_{base_u}"
    if direct in out and inverse not in out and out[direct] != 0:
        out[inverse] = Decimal("1") / out[direct]
    elif inverse in out and direct not in out and out[inverse] != 0:
        out[direct] = Decimal("1") / out[inverse]
    return out


def stored_to_api(stored: Optional[StoredRates]) -> dict[str, Any]:
    """CamelCase JSON for GET /api/fx/rates and error payloads."""
    if stored is None:
        return {
            "base": None,
            "rates": {},
            "asOf": None,
            "provider": None,
            "status": "missing",
            "lastRefreshStatus": None,
            "lastRefreshError": None,
            "updatedBy": None,
        }

    def _iso(dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.isoformat() + "Z"
        return dt.isoformat()

    return {
        "base": stored.base,
        "rates": {k: format(Decimal(v), "f") for k, v in stored.rates.items()},
        "asOf": _iso(stored.as_of),
        "provider": stored.provider,
        "status": stored.status,
        "lastRefreshStatus": stored.last_refresh_status,
        "lastRefreshError": stored.last_refresh_error,
        "updatedBy": stored.updated_by,
    }


class FxService:
    """Read FX store; refresh via provider only on explicit admin action."""

    def __init__(
        self,
        repo: ExchangeRateRepo,
        client: Optional[ExchangeRateClient] = None,
        stale_after_seconds: int = 30 * 86400,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._repo = repo
        self._client = client
        self._stale_after_seconds = stale_after_seconds
        self._clock = clock

    def get_rates(self) -> Optional[StoredRates]:
        """Stored rates only — never calls ExchangeRateClient."""
        return self._repo.get_latest()

    def get_context(self) -> FxContext:
        """Capture one immutable request/job FX snapshot from the store."""
        return fx_context_from_stored(self._repo.get_latest(), stale_after_seconds=self._stale_after_seconds, now=self._clock() if self._clock else None)

    def convert(self, amount: object, source: str, target: str) -> tuple[Decimal, Decimal]:
        """Convert an amount using stored rates only; never calls the provider."""
        try:
            value = Decimal(str(amount))
        except Exception as exc:
            raise ConversionError("amount must be a valid number") from exc
        if not value.is_finite() or value < 0:
            raise ConversionError("amount must be a non-negative finite number")
        try:
            src = normalize_currency(source, field="sourceCurrency")
            dst = normalize_currency(target, field="targetCurrency")
        except ValueError as exc:
            raise ConversionError(str(exc)) from exc
        # Identity conversion is valid even when the FX store is unavailable.
        if src == dst:
            return value, Decimal("1")
        stored = self._repo.get_latest()
        if stored is None or stored.status == "missing":
            raise ConversionError("exchange rates are not available")
        rate = get_rate(
            FxRates(base=stored.base, rates=stored.rates, status=stored.status, as_of=stored.as_of),
            src,
            dst,
        )
        if rate is None:
            raise ConversionError(f"rate is not available for {src}_{dst}")
        return value * rate, rate

    def refresh(self, *, admin_user_id: str, base: str = "USD") -> FxRefreshResult:
        """Fetch provider once; save on success; keep previous on failure."""
        if self._client is None:
            error = "Exchange rate client not configured"
            stored = self._repo.mark_refresh_failure(error)
            return FxRefreshResult(ok=False, stored=stored, error=error)
        try:
            snapshot = self._client.fetch_latest(base=base)
        except ProviderError as exc:
            stored = self._repo.mark_refresh_failure(exc.detail)
            return FxRefreshResult(ok=False, stored=stored, error=exc.detail)
        except Exception as exc:  # noqa: BLE001 — surface as provider failure
            error = str(exc) or "Provider error"
            stored = self._repo.mark_refresh_failure(error)
            return FxRefreshResult(ok=False, stored=stored, error=error)

        rates = ensure_pair_rates(snapshot.rates, base=snapshot.base or base)
        normalized = RateSnapshot(
            base=(snapshot.base or base).upper(),
            rates=rates,
            provider=snapshot.provider or "exchangerate-api",
            fetched_at=snapshot.fetched_at,
            raw=snapshot.raw,
        )
        stored = self._repo.save(normalized, updated_by=admin_user_id)
        return FxRefreshResult(ok=True, stored=stored, error=None)


__all__ = [
    "FxRefreshResult",
    "FxService",
    "ensure_pair_rates",
    "stored_to_api",
    "ConversionError",
]
