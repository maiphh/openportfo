"""Portfolio snapshot repository port."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Protocol


@dataclass
class SnapshotRecord:
    user_id: str
    date: str  # YYYY-MM-DD
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None


class SnapshotRepo(Protocol):
    def put(self, record: SnapshotRecord) -> None:
        ...

    def get(self, user_id: str, date: str) -> Optional[SnapshotRecord]:
        ...

    def list(
        self,
        user_id: str,
        *,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[SnapshotRecord]:
        """Return snapshots for ``user_id`` in ``[date_from, date_to]`` (inclusive ISO dates)."""
        ...


__all__ = ["SnapshotRecord", "SnapshotRepo"]
