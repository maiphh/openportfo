"""In-memory users adapter for local development and tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from collections.abc import Iterator
from threading import RLock
from typing import Optional, Sequence

from app.ports.users import UNSET, Role, UserProfile, UserSettingsPatch
from app.services.currency_service import normalize_stored_currency


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryUserProfileRepo:
    """Dict-backed profile store. Role always lives here, never on the token."""

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}
        self._lock = RLock()

    def get(self, user_id: str) -> Optional[UserProfile]:
        with self._lock:
            profile = self._profiles.get(user_id)
            return deepcopy(profile) if profile is not None else None

    def get_or_create(
        self,
        user_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> UserProfile:
        with self._lock:
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
                preferred_currency=None,
                avatar_style=None,
                avatar_seed=None,
                avatar_color=None,
                created_at=now,
                updated_at=now,
            )
            self._profiles[user_id] = profile
            return deepcopy(profile)

    def update_settings(
        self,
        user_id: str,
        patch: Optional[UserSettingsPatch] = None,
        *,
        news_keywords: object = UNSET,
        email_opt_in: object = UNSET,
        preferred_currency: object = UNSET,
        avatar_style: object = UNSET,
        avatar_seed: object = UNSET,
        avatar_color: object = UNSET,
    ) -> UserProfile:
        patch = patch or UserSettingsPatch(
            news_keywords=news_keywords,
            email_opt_in=email_opt_in,
            preferred_currency=preferred_currency,
            avatar_style=avatar_style,
            avatar_seed=avatar_seed,
            avatar_color=avatar_color,
        )
        with self._lock:
            profile = self._profiles.get(user_id)
            if profile is None:
                raise KeyError(f"User not found: {user_id}")
            if patch.news_keywords is not UNSET:
                profile.news_keywords = list(patch.news_keywords or [])
            if patch.email_opt_in is not UNSET:
                profile.email_opt_in = bool(patch.email_opt_in)
            if patch.preferred_currency is not UNSET:
                profile.preferred_currency = normalize_stored_currency(patch.preferred_currency)
            if patch.avatar_style is not UNSET:
                profile.avatar_style = patch.avatar_style
            if patch.avatar_seed is not UNSET:
                profile.avatar_seed = patch.avatar_seed
            if patch.avatar_color is not UNSET:
                profile.avatar_color = patch.avatar_color
            profile.updated_at = _utc_now()
            return deepcopy(profile)

    def update_identity(
        self,
        user_id: str,
        *,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> UserProfile:
        with self._lock:
            profile = self._profiles.get(user_id)
            if profile is None:
                raise KeyError(f"User not found: {user_id}")
            changed = False
            if email and profile.email != email:
                profile.email = email
                changed = True
            if name and profile.name != name:
                profile.name = name
                changed = True
            if changed:
                profile.updated_at = _utc_now()
            return deepcopy(profile)

    def iter_pages(
        self,
        *,
        page_size: Optional[int] = None,
    ) -> Iterator[list[UserProfile]]:
        """Yield bounded profile pages to mirror the Dynamo adapter."""
        cap = max(1, int(page_size)) if page_size is not None else 100
        page: list[UserProfile] = []
        with self._lock:
            profiles = [deepcopy(profile) for profile in self._profiles.values()]
        for profile in profiles:
            page.append(deepcopy(profile))
            if len(page) >= cap:
                yield page
                page = []
        if page:
            yield page

    def iter_all(self, *, page_size: Optional[int] = None) -> Iterator[UserProfile]:
        """Lazily yield all profiles."""
        for page in self.iter_pages(page_size=page_size):
            yield from page

    def list_all(self) -> list[UserProfile]:
        """Compatibility materializing helper for non-job callers."""
        return list(self.iter_all())

    def set_role(self, user_id: str, role: Role) -> UserProfile:
        with self._lock:
            profile = self._profiles.get(user_id)
            if profile is None:
                raise KeyError(f"User not found: {user_id}")
            profile.role = role
            profile.updated_at = _utc_now()
            return deepcopy(profile)

    def change_role_guarded(self, user_id: str, role: Role) -> UserProfile:
        """Atomically apply a role change with the last-admin invariant."""
        with self._lock:
            profile = self._profiles.get(user_id)
            if profile is None:
                raise KeyError(f"User not found: {user_id}")
            if role == "user" and profile.role == "admin":
                admin_count = sum(1 for item in self._profiles.values() if item.role == "admin")
                if admin_count <= 1:
                    from app.services.admin_user_service import LastAdminError

                    raise LastAdminError("At least one admin is required")
            profile.role = role
            profile.updated_at = _utc_now()
            return deepcopy(profile)

    def list_page(
        self,
        *,
        limit: int,
        start_after: Optional[str] = None,
    ) -> tuple[list[UserProfile], Optional[str]]:
        """Mirror Dynamo's forward continuation in deterministic insertion order."""
        cap = max(1, int(limit))
        with self._lock:
            ids = list(self._profiles)
            offset = 0
            if start_after is not None:
                try:
                    offset = ids.index(start_after) + 1
                except ValueError as exc:
                    raise KeyError(f"User not found: {start_after}") from exc
            selected = ids[offset : offset + cap]
            profiles = [deepcopy(self._profiles[user_id]) for user_id in selected]
            has_more = offset + len(selected) < len(ids)
        return profiles, (selected[-1] if selected and has_more else None)

    def clear(self) -> None:
        """Test helper: wipe all profiles."""
        with self._lock:
            self._profiles.clear()
