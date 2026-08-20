"""In-memory admin adapter for local development and tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

from app.ports.admin import (
    AdminNotFoundError,
    AdminValidationError,
    JobRun,
    RssSource,
    SystemSettings,
)

# Aliases kept for existing call sites
ValidationError = AdminValidationError
NotFoundError = AdminNotFoundError


class InMemorySettingsRepo:
    def __init__(self, initial: Optional[SystemSettings] = None) -> None:
        self._settings = deepcopy(initial) if initial else SystemSettings()

    def get(self) -> SystemSettings:
        return deepcopy(self._settings)

    def save(self, settings: SystemSettings) -> SystemSettings:
        self._settings = deepcopy(settings)
        return deepcopy(self._settings)


class InMemoryRssSourcesRepo:
    def __init__(self) -> None:
        self._items: dict[str, RssSource] = {}

    def list(self) -> list[RssSource]:
        return [deepcopy(v) for v in self._items.values()]

    def get(self, source_id: str) -> Optional[RssSource]:
        item = self._items.get(source_id)
        return deepcopy(item) if item else None

    def create(self, source: RssSource) -> RssSource:
        _validate_url(source.url)
        sid = source.source_id or str(uuid4())
        stored = RssSource(
            source_id=sid,
            name=source.name,
            url=source.url,
            enabled=source.enabled,
        )
        self._items[sid] = deepcopy(stored)
        return deepcopy(stored)

    def update(self, source: RssSource) -> RssSource:
        if source.source_id not in self._items:
            raise AdminNotFoundError(f"RSS source {source.source_id} not found")
        _validate_url(source.url)
        self._items[source.source_id] = deepcopy(source)
        return deepcopy(source)

    def delete(self, source_id: str) -> None:
        if source_id not in self._items:
            raise AdminNotFoundError(f"RSS source {source_id} not found")
        del self._items[source_id]


class InMemoryJobRunsRepo:
    def __init__(self) -> None:
        self._runs: list[JobRun] = []

    def list_recent(self, job_type: Optional[str] = None, limit: int = 50) -> list[JobRun]:
        runs = self._runs
        if job_type:
            runs = [r for r in runs if r.job_type == job_type]
        # newest first
        ordered = list(reversed(runs))
        return [deepcopy(r) for r in ordered[:limit]]

    def put(self, run: JobRun) -> None:
        self._runs.append(deepcopy(run))

    def seed(self, runs: list[JobRun]) -> None:
        self._runs = [deepcopy(r) for r in runs]


def _validate_url(url: str) -> None:
    parsed = urlparse(url or "")
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise AdminValidationError("URL must be http(s) with a host")


__all__ = [
    "InMemorySettingsRepo",
    "InMemoryRssSourcesRepo",
    "InMemoryJobRunsRepo",
    "ValidationError",
    "NotFoundError",
    "AdminValidationError",
    "AdminNotFoundError",
]

