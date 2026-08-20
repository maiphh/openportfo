"""Currency policy and request-scoped exchange-rate context.

The API accepts a deliberately small, explicit set of display currencies.  A
request gets one immutable FX snapshot and all application services use that
snapshot for the lifetime of the request; they never call a provider while
rendering a response.  Provider/store adapters remain responsible for
fetching and persisting rates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Mapping, Optional

from app.domain.fx_math import get_rate
from app.domain.models import FxRates
from app.ports.fx import StoredRates

# Keep this policy in one place.  It is intentionally shared by query
# parameters, stored preferences, admin defaults, and the UI contract.
SUPPORTED_CURRENCIES: frozenset[str] = frozenset({"VND", "USD", "EUR"})
SUPPORTED_CURRENCY_LIST: tuple[str, ...] = ("VND", "USD", "EUR")
DEFAULT_DISPLAY_CURRENCY = "VND"


class CurrencyValidationError(ValueError):
    """Raised when a currency is not a supported ISO-4217 code."""

    def __init__(self, detail: str = "currency must be one of VND, USD, EUR") -> None:
        self.detail = detail
        super().__init__(detail)


def normalize_currency(
    value: object,
    *,
    field: str = "currency",
    allow_none: bool = False,
) -> Optional[str]:
    """Normalize and validate one supported currency code.

    ``None`` is useful for optional query parameters and means "not supplied";
    an empty string is never treated as a valid preference.
    """
    if value is None:
        if allow_none:
            return None
        raise CurrencyValidationError(f"{field} is required")
    text = str(value).strip().upper()
    if not text:
        if allow_none:
            return None
        raise CurrencyValidationError(f"{field} is required")
    if text not in SUPPORTED_CURRENCIES:
        choices = ", ".join(SUPPORTED_CURRENCY_LIST)
        raise CurrencyValidationError(f"{field} must be one of {choices}")
    return text


def normalize_stored_currency(value: object) -> Optional[str]:
    """Best-effort normalization for persisted preferences.

    Old/invalid rows must not make authentication or every API request fail;
    invalid values are ignored and callers use their configured default.
    """
    try:
        return normalize_currency(value, allow_none=True)
    except CurrencyValidationError:
        return None


def resolve_currency(
    canonical: object = None,
    *,
    legacy: object = None,
    preferred: object = None,
    default: object = DEFAULT_DISPLAY_CURRENCY,
    field: str = "currency",
) -> str:
    """Resolve canonical query → legacy alias → preference → default.

    If both query spellings are supplied they must agree.  This prevents a
    cache key or browser URL from silently describing a different currency
    than the backend calculation.
    """
    canonical_norm = normalize_currency(canonical, field=field, allow_none=True)
    legacy_norm = normalize_currency(legacy, field="displayCurrency", allow_none=True)
    if canonical_norm and legacy_norm and canonical_norm != legacy_norm:
        raise CurrencyValidationError("currency and displayCurrency must match")
    preferred_norm = normalize_stored_currency(preferred)
    default_norm = normalize_stored_currency(default) or DEFAULT_DISPLAY_CURRENCY
    return canonical_norm or legacy_norm or preferred_norm or default_norm


def _decimal_rates(rates: Mapping[str, object] | None) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for raw_key, raw_value in (rates or {}).items():
        key = str(raw_key).strip().upper()
        if not key:
            continue
        try:
            value = raw_value if isinstance(raw_value, Decimal) else Decimal(str(raw_value))
        except (InvalidOperation, ValueError, TypeError):
            continue
        if value.is_finite() and value >= 0:
            out[key] = value
    return out


@dataclass(frozen=True)
class FxContext:
    """Immutable FX state captured once for one request/job operation."""

    base: str = "USD"
    rates: Mapping[str, Decimal] = None  # type: ignore[assignment]
    status: str = "missing"
    as_of: Optional[datetime] = None
    provider: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "base", (self.base or "USD").strip().upper() or "USD")
        object.__setattr__(self, "rates", _decimal_rates(self.rates))
        if not self.rates and self.status != "missing":
            object.__setattr__(self, "status", "missing")

    def rate(self, source: str, target: str) -> Optional[Decimal]:
        """Return source→target multiplier, including same-currency 1."""
        return get_rate(
            FxRates(
                base=self.base,
                rates=dict(self.rates),
                status="missing" if self.status == "missing" else self.status,  # type: ignore[arg-type]
                as_of=self.as_of,
            ),
            source,
            target,
        )

    def convert(self, amount: object, source: str, target: str) -> Optional[Decimal]:
        """Convert a finite Decimal amount or return ``None`` if unavailable."""
        try:
            value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError):
            return None
        if not value.is_finite():
            return None
        rate = self.rate(source, target)
        return value * rate if rate is not None else None

    @property
    def is_available(self) -> bool:
        return self.status != "missing" and bool(self.rates)


def fx_context_from_stored(stored: Optional[StoredRates]) -> FxContext:
    """Map a repository snapshot into a request-safe context."""
    if stored is None:
        return FxContext()
    status = str(stored.status or "missing").strip().lower()
    if status not in {"missing", "stale_ok", "fresh"}:
        status = "fresh" if stored.rates else "missing"
    rates = _decimal_rates(stored.rates)
    return FxContext(
        base=stored.base or "USD",
        rates=rates,
        status="missing" if not rates else status,
        as_of=stored.as_of,
        provider=stored.provider,
    )


__all__ = [
    "SUPPORTED_CURRENCIES",
    "SUPPORTED_CURRENCY_LIST",
    "DEFAULT_DISPLAY_CURRENCY",
    "CurrencyValidationError",
    "FxContext",
    "fx_context_from_stored",
    "normalize_currency",
    "normalize_stored_currency",
    "resolve_currency",
]
