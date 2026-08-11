"""In-memory ExchangeRateRepo + fake ExchangeRateClient for local/test."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from app.ports.fx import ProviderError, RateSnapshot, StoredRates


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryExchangeRateRepo:
    """Dict-backed FX store with get_latest + save (never wipes on failed refresh)."""

    def __init__(self, initial: Optional[StoredRates] = None) -> None:
        self._latest: Optional[StoredRates] = (
            deepcopy(initial) if initial is not None else None
        )
        self.get_latest_calls = 0
        self.save_calls = 0

    def get_latest(self) -> Optional[StoredRates]:
        self.get_latest_calls += 1
        return deepcopy(self._latest) if self._latest is not None else None

    def save(
        self,
        snapshot: RateSnapshot,
        *,
        updated_by: Optional[str] = None,
    ) -> StoredRates:
        self.save_calls += 1
        as_of = snapshot.fetched_at or _utc_now()
        stored = StoredRates(
            base=snapshot.base,
            rates=dict(snapshot.rates),
            as_of=as_of,
            provider=snapshot.provider,
            status="fresh" if snapshot.rates else "missing",
            last_refresh_status="success",
            last_refresh_error=None,
            updated_by=updated_by,
        )
        self._latest = deepcopy(stored)
        return deepcopy(stored)

    def seed(self, rates: Optional[StoredRates]) -> None:
        """Test helper: set or clear stored rates without HTTP."""
        self._latest = deepcopy(rates) if rates is not None else None

    def clear(self) -> None:
        self._latest = None
        self.get_latest_calls = 0
        self.save_calls = 0


class FakeExchangeRateClient:
    """Configurable FX provider fake: success snapshot or ProviderError."""

    def __init__(
        self,
        *,
        snapshot: Optional[RateSnapshot] = None,
        fail: bool = False,
        fail_message: str = "Simulated provider failure",
    ) -> None:
        self.fetch_calls = 0
        self.last_base: Optional[str] = None
        self.fail = fail
        self.fail_message = fail_message
        self._snapshot = snapshot or RateSnapshot(
            base="USD",
            rates={
                "USD_VND": Decimal("25000"),
                "VND_USD": Decimal("1") / Decimal("25000"),
            },
            provider="exchangerate-api",
            fetched_at=datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc),
        )

    def fetch_latest(self, base: str = "USD") -> RateSnapshot:
        self.fetch_calls += 1
        self.last_base = base
        if self.fail:
            raise ProviderError(self.fail_message)
        snap = deepcopy(self._snapshot)
        # Honour requested base when returning success
        snap.base = (base or "USD").upper()
        return snap

    def set_snapshot(self, snapshot: RateSnapshot) -> None:
        """Test helper: replace success payload."""
        self._snapshot = deepcopy(snapshot)

    def set_fail(self, fail: bool = True, message: Optional[str] = None) -> None:
        """Test helper: toggle failure mode."""
        self.fail = fail
        if message is not None:
            self.fail_message = message


__all__ = [
    "InMemoryExchangeRateRepo",
    "FakeExchangeRateClient",
]
