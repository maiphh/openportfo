"""Object storage port (S3 in prod, in-memory fake in local/test)."""

from __future__ import annotations

from typing import Any, Optional, Protocol


class ObjectStorage(Protocol):
    """JSON blob store for history/snapshots. No boto3 in callers."""

    def get_json(self, key: str) -> Optional[dict[str, Any]]:
        """Return JSON object or ``None`` if missing."""
        ...

    def put_json(self, key: str, data: dict[str, Any]) -> None:
        """Write/overwrite JSON object at ``key``."""
        ...

    def ping(self) -> None:
        """Raise if object storage is unreachable."""
        ...

    def list_keys(self, prefix: str = "", *, limit: int = 100) -> list[str]:
        """Return object keys under ``prefix`` (lexicographic, capped)."""
        ...


__all__ = ["ObjectStorage"]
