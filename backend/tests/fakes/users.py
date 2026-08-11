"""In-memory UserProfileRepo for local/test."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional, Sequence

from app.ports.users import Role, UserProfile


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryUserProfileRepo:
    """Dict-backed profile store. Role always lives here, never on the token."""

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}

    def get(self, user_id: str) -> Optional[UserProfile]:
        profile = self._profiles.get(user_id)
        return deepcopy(profile) if profile is not None else None

    def get_or_create(
        self,
        user_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> UserProfile:
        existing = self._profiles.get(user_id)
        if existing is not None:
            # Optionally fill missing email/name from latest claims
            changed = False
            if email and not existing.email:
                existing.email = email
                changed = True
            if name and not existing.name:
                existing.name = name
                changed = True
            if changed:
                existing.updated_at = _utc_now()
            return deepcopy(existing)

        now = _utc_now()
        profile = UserProfile(
            user_id=user_id,
            email=email,
            name=name,
            role="user",
            news_keywords=[],
            email_opt_in=False,
            preferred_currency="USD",
            created_at=now,
            updated_at=now,
        )
        self._profiles[user_id] = profile
        return deepcopy(profile)

    def update_settings(
        self,
        user_id: str,
        *,
        news_keywords: Optional[Sequence[str]] = None,
        email_opt_in: Optional[bool] = None,
        preferred_currency: Optional[str] = None,
    ) -> UserProfile:
        profile = self._profiles.get(user_id)
        if profile is None:
            raise KeyError(f"User not found: {user_id}")
        if news_keywords is not None:
            profile.news_keywords = list(news_keywords)
        if email_opt_in is not None:
            profile.email_opt_in = email_opt_in
        if preferred_currency is not None:
            profile.preferred_currency = preferred_currency
        profile.updated_at = _utc_now()
        return deepcopy(profile)

    def list_all(self) -> list[UserProfile]:
        """Test/job helper: all profiles (not on Protocol; used by jobs via getattr)."""
        return [deepcopy(p) for p in self._profiles.values()]

    def set_role(self, user_id: str, role: Role) -> UserProfile:
        profile = self._profiles.get(user_id)
        if profile is None:
            raise KeyError(f"User not found: {user_id}")
        profile.role = role
        profile.updated_at = _utc_now()
        return deepcopy(profile)

    def clear(self) -> None:
        """Test helper: wipe all profiles."""
        self._profiles.clear()
