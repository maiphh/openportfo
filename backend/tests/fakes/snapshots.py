"""In-memory SnapshotRepo."""

from __future__ import annotations

from copy import deepcopy
from typing import Optional

from app.ports.snapshots import SnapshotRecord


class InMemorySnapshotRepo:
    def __init__(self) -> None:
        self._data: dict[tuple[str, str], SnapshotRecord] = {}
        self.put_calls = 0

    def put(self, record: SnapshotRecord) -> None:
        self.put_calls += 1
        self._data[(record.user_id, record.date)] = deepcopy(record)

    def get(self, user_id: str, date: str) -> Optional[SnapshotRecord]:
        item = self._data.get((user_id, date))
        return deepcopy(item) if item else None


__all__ = ["InMemorySnapshotRepo"]
