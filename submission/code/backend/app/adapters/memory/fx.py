"""In-memory exchange-rate repository for local development and tests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from typing import Optional

from app.ports.fx import RateSnapshot, StoredRates


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
        self.mark_refresh_failure_calls = 0

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

    def mark_refresh_failure(self, error: str) -> Optional[StoredRates]:
        self.mark_refresh_failure_calls += 1
        if self._latest is None:
            stored = StoredRates(
                base="USD",
                rates={},
                status="missing",
                last_refresh_status="error",
                last_refresh_error=error,
            )
        else:
            stored = replace(
                self._latest,
                last_refresh_status="error",
                last_refresh_error=error,
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
        self.mark_refresh_failure_calls = 0


__all__ = [
    "InMemoryExchangeRateRepo",
]
