"""Auth and settings routes (Cognito JWT; no password register/login)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import get_current_user, get_user_profile_repo
from app.core.config import Settings, get_settings
from app.ports.users import UserProfile, UserProfileRepo

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
        "preferredCurrency": profile.preferred_currency,
        "createdAt": _iso(profile.created_at),
        "updatedAt": _iso(profile.updated_at),
    }


class SettingsUpdate(BaseModel):
    """PUT /api/settings body (partial)."""

    model_config = ConfigDict(populate_by_name=True)

    news_keywords: Optional[list[str]] = Field(default=None, alias="newsKeywords")
    email_opt_in: Optional[bool] = Field(default=None, alias="emailOptIn")
    preferred_currency: Optional[str] = Field(default=None, alias="preferredCurrency")


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


@router.put("/api/settings")
def put_settings(
    body: SettingsUpdate,
    user: UserProfile = Depends(get_current_user),
    repo: UserProfileRepo = Depends(get_user_profile_repo),
) -> dict[str, Any]:
    """Update newsKeywords, emailOptIn, preferredCurrency."""
    updated = repo.update_settings(
        user.user_id,
        news_keywords=body.news_keywords,
        email_opt_in=body.email_opt_in,
        preferred_currency=body.preferred_currency,
    )
    return profile_to_response(updated)
