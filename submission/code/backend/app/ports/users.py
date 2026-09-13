"""User profile port (DynamoDB in prod, in-memory fake in local/test)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections.abc import Iterator
from typing import Any, Literal, Optional, Protocol, Sequence

Role = Literal["user", "admin"]


class _Unset:
    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET"


UNSET = _Unset()


@dataclass(frozen=True)
class UserSettingsPatch:
    """Explicit field patch; ``UNSET`` means leave a field unchanged."""

    news_keywords: Any = UNSET
    email_opt_in: Any = UNSET
    preferred_currency: Any = UNSET
    avatar_style: Any = UNSET
    avatar_seed: Any = UNSET
    avatar_color: Any = UNSET


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserProfile:
    """App profile keyed by Cognito ``sub`` (user_id)."""

    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: Role = "user"
    news_keywords: list[str] = field(default_factory=list)
    email_opt_in: bool = False
    preferred_currency: Optional[str] = None
    avatar_style: Optional[str] = None
    avatar_seed: Optional[str] = None
    avatar_color: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


class UserProfileRepo(Protocol):
    """Port: persist and load app user profiles."""

    def get(self, user_id: str) -> Optional[UserProfile]:
        """Return profile or ``None`` if missing."""
        ...

    def get_or_create(
        self,
        user_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> UserProfile:
        """Return existing profile or create one with default role=user."""
        ...

    def update_identity(
        self,
        user_id: str,
        *,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> UserProfile:
        """Refresh verified identity claims without changing role/settings."""
        ...

    def update_settings(
        self,
        user_id: str,
        patch: Optional[UserSettingsPatch] = None,
        *,
        news_keywords: Any = UNSET,
        email_opt_in: Any = UNSET,
        preferred_currency: Any = UNSET,
        avatar_style: Any = UNSET,
        avatar_seed: Any = UNSET,
        avatar_color: Any = UNSET,
    ) -> UserProfile:
        """Patch settings fields; raises KeyError if profile missing."""
        ...

    def set_role(self, user_id: str, role: Role) -> UserProfile:
        """Set role (admin bootstrap in tests/ops). Raises KeyError if missing."""
        ...

    def list_page(
        self,
        *,
        limit: int,
        start_after: Optional[str] = None,
    ) -> tuple[list[UserProfile], Optional[str]]:
        """Return one forward page and the last user id evaluated."""
        ...

    def iter_pages(
        self,
        *,
        page_size: Optional[int] = None,
    ) -> Iterator[list[UserProfile]]:
        """Lazily yield profile pages for scheduled jobs.

        ``page_size`` is a storage-adapter hint.  ``None`` leaves the
        provider's natural page size unchanged.  Pages are intentionally
        short-lived so a job does not need to hold the complete user table in
        memory.
        """
        ...

    def iter_all(self, *, page_size: Optional[int] = None) -> Iterator[UserProfile]:
        """Lazily yield all profiles (jobs: news keywords / snapshots)."""
        ...

    def list_all(self) -> list[UserProfile]:
        """Compatibility materializing helper for non-job callers."""
        ...
