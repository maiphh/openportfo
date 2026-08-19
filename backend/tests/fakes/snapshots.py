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

    def list(
        self,
        user_id: str,
        *,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[SnapshotRecord]:
        rows = [
            deepcopy(record)
            for (uid, date), record in self._data.items()
            if uid == user_id
            and (date_from is None or date >= date_from)
            and (date_to is None or date <= date_to)
        ]
        rows.sort(key=lambda r: r.date)
        return rows


__all__ = ["InMemorySnapshotRepo"]
