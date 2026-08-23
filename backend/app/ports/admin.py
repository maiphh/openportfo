"""Admin settings, RSS sources, job runs ports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Optional, Protocol


JobStatus = Literal["success", "partial", "error", "skipped"]


@dataclass
class SystemSettings:
    """Singleton SETTINGS/GLOBAL."""

    email_time: str = "08:00"  # HH:MM
    timezone: str = "Asia/Ho_Chi_Minh"
    email_enabled: bool = False
    price_cache_ttl_minutes: int = 10
    jobs_news: bool = True
    jobs_snapshot: bool = True
    jobs_email: bool = False
    jobs_price: bool = True
    default_display_currency: str = "USD"
    version: int = 0
    chat_model: Optional[str] = None
    chat_fallback_models: Optional[list[str]] = None
    chat_temperature: Optional[float] = None
    chat_top_p: Optional[float] = None
    chat_max_tokens: Optional[int] = None
    chat_system_prompt_extra: Optional[str] = None


class SettingsConflictError(Exception):
    """Raised when an optimistic SystemSettings version is stale."""

    def __init__(self, detail: str = "Settings changed; reload before saving") -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass
class RssSource:
    source_id: str
    name: str
    url: str
    enabled: bool = True


@dataclass
class JobRun:
    run_id: str
    job_type: str
    # ``partial`` is used when independent work units mixed success and
    # failure.  ``error`` means every attempted unit failed; ``skipped`` is
    # reserved for a disabled job.
    status: JobStatus | str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    message: Optional[str] = None
    counts: dict[str, Any] = field(default_factory=dict)


class AdminValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminNotFoundError(Exception):
    def __init__(self, detail: str = "Not found") -> None:
        self.detail = detail
        super().__init__(detail)


class SettingsRepo(Protocol):
    def get(self) -> SystemSettings:
        ...

    def save(
        self,
        settings: SystemSettings,
        *,
        expected_version: Optional[int] = None,
    ) -> SystemSettings:
        ...


class RssSourcesRepo(Protocol):
    def list(self) -> list[RssSource]:
        ...

    def get(self, source_id: str) -> Optional[RssSource]:
        ...

    def create(self, source: RssSource) -> RssSource:
        ...

    def update(self, source: RssSource) -> RssSource:
        ...

    def delete(self, source_id: str) -> None:
        ...


class JobRunsRepo(Protocol):
    def list_recent(self, job_type: Optional[str] = None, limit: int = 50) -> list[JobRun]:
        ...

    def put(self, run: JobRun) -> None:
        ...


__all__ = [
    "SystemSettings",
    "JobStatus",
    "RssSource",
    "JobRun",
    "AdminValidationError",
    "AdminNotFoundError",
    "SettingsConflictError",
    "SettingsRepo",
    "RssSourcesRepo",
    "JobRunsRepo",
]
