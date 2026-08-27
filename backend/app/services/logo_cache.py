"""In-process logo URL cache shared by market boards and asset detail.

Avoids repeat CoinGecko/profile work for the same ticker within a process.
URLs are immutable CDN paths; a long TTL is safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional

_DEFAULT_TTL = timedelta(days=7)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _Entry:
    url: str
    expires_at: datetime


class LogoCache:
    """Thread-safe ``(asset_type, key) → image URL`` map."""

    def __init__(self, *, ttl: timedelta = _DEFAULT_TTL) -> None:
        self._ttl = ttl
        self._lock = Lock()
        self._entries: dict[tuple[str, str], _Entry] = {}

    def _norm(self, asset_type: str, key: str) -> Optional[tuple[str, str]]:
        kind = (asset_type or "").strip().lower()
        token = (key or "").strip()
        if kind == "crypto":
            token = token.lower()
        elif kind == "stock":
            token = token.upper()
        else:
            return None
        if not token:
            return None
        return kind, token

    def get(self, asset_type: str, key: str) -> Optional[str]:
        pair = self._norm(asset_type, key)
        if pair is None:
            return None
        with self._lock:
            entry = self._entries.get(pair)
            if entry is None:
                return None
            if entry.expires_at <= _utc_now():
                self._entries.pop(pair, None)
                return None
            return entry.url

    def put(self, asset_type: str, key: str, url: Optional[str]) -> None:
        pair = self._norm(asset_type, key)
        text = (url or "").strip()
        if pair is None or not text:
            return
        with self._lock:
            self._entries[pair] = _Entry(url=text, expires_at=_utc_now() + self._ttl)

    def put_many(self, asset_type: str, mapping: dict[str, Optional[str]]) -> None:
        for key, url in mapping.items():
            self.put(asset_type, key, url)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_logo_cache = LogoCache()


def get_logo_cache() -> LogoCache:
    return _logo_cache


def set_logo_cache(cache: Optional[LogoCache]) -> None:
    global _logo_cache
    _logo_cache = cache or LogoCache()


__all__ = ["LogoCache", "get_logo_cache", "set_logo_cache"]
