"""Test-only exchange-rate provider failure double.

The in-memory repository lives in app.adapters.memory; this module keeps
the configurable provider fake available to unit tests.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from app.adapters.memory.fx import InMemoryExchangeRateRepo
from app.ports.fx import ProviderError, RateSnapshot


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
