"""In-memory storage adapter for local development and tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional


class InMemoryObjectStorage:
    """Dict-backed object storage with call counters."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self.get_calls = 0
        self.put_calls = 0
        self.last_get_key: Optional[str] = None
        self.last_put_key: Optional[str] = None
        self.fail_ping = False

    def get_json(self, key: str) -> Optional[dict[str, Any]]:
        self.get_calls += 1
        self.last_get_key = key
        item = self._data.get(key)
        return deepcopy(item) if item is not None else None

    def put_json(self, key: str, data: dict[str, Any]) -> None:
        self.put_calls += 1
        self.last_put_key = key
        self._data[key] = deepcopy(data)

    def ping(self) -> None:
        if getattr(self, "fail_ping", False):
            raise RuntimeError("object storage unavailable")

    def list_keys(self, prefix: str = "", *, limit: int = 100) -> list[str]:
        cap = max(1, min(int(limit), 500))
        keys = sorted(k for k in self._data if k.startswith(prefix or ""))
        return keys[:cap]

    def seed(self, key: str, data: dict[str, Any]) -> None:
        self._data[key] = deepcopy(data)

    def clear(self) -> None:
        self._data.clear()
        self.get_calls = 0
        self.put_calls = 0


__all__ = ["InMemoryObjectStorage"]

