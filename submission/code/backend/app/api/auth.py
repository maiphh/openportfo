"""Auth and settings routes (Cognito JWT; no password register/login)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import get_current_user, get_user_profile_repo
from app.core.config import Settings, get_settings
from app.ports.users import UserProfile, UserProfileRepo
from app.services.currency_service import CurrencyValidationError, normalize_currency, normalize_stored_currency
from app.services.user_settings import UserSettingsValidationError, normalize_user_settings_patch

router = APIRouter(tags=["auth"])


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def profile_to_response(profile: UserProfile) -> dict[str, Any]:
    """Serialize profile to API JSON (camelCase per PRD)."""
    return {
        "userId": profile.user_id,
        "email": profile.email,
        "name": profile.name,
        "role": profile.role,
        "newsKeywords": list(profile.news_keywords),
        "emailOptIn": profile.email_opt_in,
        "preferredCurrency": normalize_stored_currency(profile.preferred_currency),
        "avatarStyle": profile.avatar_style,
        "avatarSeed": profile.avatar_seed,
        "avatarColor": profile.avatar_color,
        "createdAt": _iso(profile.created_at),
        "updatedAt": _iso(profile.updated_at),
    }


class SettingsUpdate(BaseModel):
    """PUT /api/settings body (partial)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    news_keywords: Any = Field(default=None, alias="newsKeywords")
    email_opt_in: Any = Field(default=None, alias="emailOptIn")
    preferred_currency: Any = Field(default=None, alias="preferredCurrency")
    avatar_style: Any = Field(default=None, alias="avatarStyle")
    avatar_seed: Any = Field(default=None, alias="avatarSeed")
    avatar_color: Any = Field(default=None, alias="avatarColor")


@router.get("/api/auth/me")
def get_me(user: UserProfile = Depends(get_current_user)) -> dict[str, Any]:
    """Return current user profile; bootstrap on first call."""
    return profile_to_response(user)


@router.post("/api/debug/auth/make-admin")
def debug_make_current_user_admin(
    user: UserProfile = Depends(get_current_user),
    repo: UserProfileRepo = Depends(get_user_profile_repo),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Promote the authenticated profile for local UI testing only."""
    if settings.app_env.strip().lower() not in {"local", "test"}:
        # Hide the debug capability entirely in deployed environments.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    updated = repo.set_role(user.user_id, "admin")
    return profile_to_response(updated)


@router.get("/api/settings")
def get_user_settings(user: UserProfile = Depends(get_current_user)) -> dict[str, Any]:
    """Settings slice of the current profile (alias of /auth/me fields)."""
    return {
        "newsKeywords": list(user.news_keywords),
        "emailOptIn": user.email_opt_in,
        "preferredCurrency": normalize_stored_currency(user.preferred_currency),
        "avatarStyle": user.avatar_style,
        "avatarSeed": user.avatar_seed,
        "avatarColor": user.avatar_color,
    }


@router.put("/api/settings")
def put_settings(
    body: SettingsUpdate,
    user: UserProfile = Depends(get_current_user),
    repo: UserProfileRepo = Depends(get_user_profile_repo),
) -> dict[str, Any]:
    """Update newsKeywords, emailOptIn, preferredCurrency."""
    payload = body.model_dump(by_alias=True, exclude_unset=True)
    try:
        patch = normalize_user_settings_patch(payload)
    except UserSettingsValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    updated = repo.update_settings(user.user_id, patch=patch)
    return profile_to_response(updated)
