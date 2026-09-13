"""Exchange-rate ports: store + provider client.

Portfolio may call ``get_latest`` only. Provider HTTP lives behind
``ExchangeRateClient`` and is invoked only by admin refresh (S06).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional, Protocol

FxRefreshStatus = Literal["success", "error"]
# Domain-compatible status when mapping to app.domain.models.FxRates
FxStoreStatus = Literal["missing", "stale_ok", "fresh"]


class ProviderError(Exception):
    """Raised when the external exchange-rate provider fails."""

    def __init__(self, detail: str = "Exchange rate provider unavailable") -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass
class RateSnapshot:
    """Fresh rates from the provider (not yet persisted)."""

    base: str
    rates: dict[str, Decimal] = field(default_factory=dict)
    provider: str = "exchangerate-api"
    fetched_at: Optional[datetime] = None
    raw: Optional[dict] = None


@dataclass
class StoredRates:
    """Last good rates in Dynamo (logical). Flat keys e.g. USD_VND, VND_USD."""

    base: str
    rates: dict[str, Decimal] = field(default_factory=dict)
    as_of: Optional[datetime] = None
    provider: Optional[str] = None
    # Domain FxRates.status when converting; default fresh when rates present
    status: FxStoreStatus = "fresh"
    last_refresh_status: Optional[FxRefreshStatus] = None
    last_refresh_error: Optional[str] = None
    updated_by: Optional[str] = None


class ExchangeRateRepo(Protocol):
    """Port: read/write stored FX rates. No HTTP. Never clear rates on failure."""

    def get_latest(self) -> Optional[StoredRates]:
        """Return last good rates or ``None`` if never stored."""
        ...

    def save(
        self,
        snapshot: RateSnapshot,
        *,
        updated_by: Optional[str] = None,
    ) -> StoredRates:
        """Persist a successful snapshot; return stored row."""
        ...

    def mark_refresh_failure(self, error: str) -> Optional[StoredRates]:
        """Keep previous rates; persist lastRefreshStatus=error. Create missing row if none."""
        ...


class ExchangeRateClient(Protocol):
    """Port: fetch latest rates from external provider."""

    def fetch_latest(self, base: str = "USD") -> RateSnapshot:
        """Fetch latest rates for ``base``. Raises ``ProviderError`` on failure."""
        ...


__all__ = [
    "FxRefreshStatus",
    "FxStoreStatus",
    "ProviderError",
    "RateSnapshot",
    "StoredRates",
    "ExchangeRateRepo",
    "ExchangeRateClient",
]
