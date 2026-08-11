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


__all__ = ["SnapshotRecord", "SnapshotRepo"]
