"""Admin-only settings, RSS sources, job runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import (
    get_admin_user_service,
    get_job_runs_repo,
    get_rss_sources_repo,
    get_settings_repo,
    get_user_profile_repo,
    get_settings,
    require_admin,
    set_market_service,
)
from app.ports.admin import (
    AdminNotFoundError,
    AdminValidationError,
    RssSource,
    SettingsConflictError,
    SystemSettings,
)
from app.ports.users import UserProfile, UserProfileRepo
from app.services.admin_user_service import (
    AdminUserError,
    AdminUserService,
    InvalidCursorError,
)
from app.services.currency_service import CurrencyValidationError, normalize_currency, normalize_stored_currency
from app.services.user_settings import UserSettingsValidationError, normalize_user_settings_patch
from app.services.chat_settings_service import (
    ChatSettingsValidationError,
    chat_settings_view,
    normalize_chat_patch,
)

router = APIRouter(tags=["admin"])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def settings_to_dict(s: SystemSettings, *, runtime_settings=None) -> dict[str, Any]:
    data = {
        "emailTime": s.email_time,
        "timezone": s.timezone,
        "emailEnabled": s.email_enabled,
        "priceCacheTtlMinutes": s.price_cache_ttl_minutes,
        "jobs": {
            "news": s.jobs_news,
            "snapshot": s.jobs_snapshot,
            "email": s.jobs_email,
            "price": s.jobs_price,
        },
        "defaultDisplayCurrency": normalize_stored_currency(s.default_display_currency) or "USD",
    }
    data.update(chat_settings_view(runtime_settings or get_settings(), s))
    return data


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    version: int

    email_time: Any = Field(default=None, alias="emailTime")
    timezone: Any = None
    email_enabled: Any = Field(default=None, alias="emailEnabled")
    price_cache_ttl_minutes: Any = Field(
        default=None, alias="priceCacheTtlMinutes"
    )
    jobs_news: Any = Field(default=None, alias="jobsNews")
    jobs_snapshot: Any = Field(default=None, alias="jobsSnapshot")
    jobs_email: Any = Field(default=None, alias="jobsEmail")
    jobs_price: Any = Field(default=None, alias="jobsPrice")
    default_display_currency: Any = Field(
        default=None, alias="defaultDisplayCurrency"
    )
    # Nested jobs object optional
    jobs: Any = None
    chat: Any = None


class UserRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "admin"]


class UserSettingsUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    news_keywords: Any = Field(default=None, alias="newsKeywords")
    email_opt_in: Any = Field(default=None, alias="emailOptIn")
    preferred_currency: Any = Field(default=None, alias="preferredCurrency")
    avatar_style: Any = Field(default=None, alias="avatarStyle")
    avatar_seed: Any = Field(default=None, alias="avatarSeed")
    avatar_color: Any = Field(default=None, alias="avatarColor")


class RssCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    url: str
    enabled: bool = True
    source_id: Optional[str] = Field(default=None, alias="sourceId")


class RssUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    url: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("/api/admin/settings")
def get_admin_settings(
    admin: UserProfile = Depends(require_admin),
    repo=Depends(get_settings_repo),
) -> dict[str, Any]:
    _ = admin
    return settings_to_dict(repo.get())


@router.put("/api/admin/settings")
def put_admin_settings(
    body: SettingsUpdate,
    admin: UserProfile = Depends(require_admin),
    repo=Depends(get_settings_repo),
) -> dict[str, Any]:
    _ = admin
    current = repo.get()
    if body.version != current.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "settings_conflict"},
        )
    data = body.model_dump(exclude_unset=True)
    jobs = data.pop("jobs", None)
    chat = data.pop("chat", None)
    validation_errors: dict[str, str] = {}
    allowed_fields = {
        "version",
        "email_time",
        "timezone",
        "email_enabled",
        "price_cache_ttl_minutes",
        "jobs_news",
        "jobs_snapshot",
        "jobs_email",
        "jobs_price",
        "default_display_currency",
    }
    for key in data:
        if key not in allowed_fields:
            validation_errors[key] = "is not supported"
    if jobs is not None:
        if not isinstance(jobs, dict):
            validation_errors["jobs"] = "must be an object"
        else:
            for key, value in jobs.items():
                if key not in {"news", "snapshot", "email", "price"}:
                    validation_errors[f"jobs.{key}"] = "is not supported"
                elif not isinstance(value, bool):
                    validation_errors[f"jobs.{key}"] = "must be a boolean"
    for field in ("email_time", "timezone"):
        if field in data and data[field] is not None and not isinstance(data[field], str):
            validation_errors[field] = "must be a string or null"
    for field in ("email_enabled", "jobs_news", "jobs_snapshot", "jobs_email", "jobs_price"):
        if field in data and data[field] is not None and not isinstance(data[field], bool):
            validation_errors[field] = "must be a boolean or null"
    if "price_cache_ttl_minutes" in data and data["price_cache_ttl_minutes"] is not None:
        value = data["price_cache_ttl_minutes"]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            validation_errors["priceCacheTtlMinutes"] = "must be a non-negative integer or null"
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_error", "errors": validation_errors},
        )
    if chat is not None:
        if not isinstance(chat, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "validation_error", "errors": {"chat": "must be an object"}},
            )
        try:
            normalized_chat = normalize_chat_patch(
                chat,
                settings=get_settings(),
                current=current,
            )
        except ChatSettingsValidationError as exc:
            raise HTTPException(status_code=400, detail=exc.detail) from exc
        for key, value in normalized_chat.items():
            setattr(current, f"chat_{key}", value)
    if jobs:
        if "news" in jobs:
            current.jobs_news = bool(jobs["news"])
        if "snapshot" in jobs:
            current.jobs_snapshot = bool(jobs["snapshot"])
        if "email" in jobs:
            current.jobs_email = bool(jobs["email"])
        if "price" in jobs:
            current.jobs_price = bool(jobs["price"])
    if "email_time" in data and data["email_time"] is not None:
        current.email_time = data["email_time"]
    if "timezone" in data and data["timezone"] is not None:
        current.timezone = data["timezone"]
    if "email_enabled" in data and data["email_enabled"] is not None:
        current.email_enabled = data["email_enabled"]
    if "price_cache_ttl_minutes" in data and data["price_cache_ttl_minutes"] is not None:
        current.price_cache_ttl_minutes = int(data["price_cache_ttl_minutes"])
    if "jobs_news" in data and data["jobs_news"] is not None:
        current.jobs_news = data["jobs_news"]
    if "jobs_snapshot" in data and data["jobs_snapshot"] is not None:
        current.jobs_snapshot = data["jobs_snapshot"]
    if "jobs_email" in data and data["jobs_email"] is not None:
        current.jobs_email = data["jobs_email"]
    if "jobs_price" in data and data["jobs_price"] is not None:
        current.jobs_price = data["jobs_price"]
    if "default_display_currency" in data and data["default_display_currency"] is not None:
        try:
            current.default_display_currency = normalize_currency(
                data["default_display_currency"],
                field="defaultDisplayCurrency",
            ) or "USD"
        except CurrencyValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    try:
        saved = repo.save(current, expected_version=body.version)
    except SettingsConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "settings_conflict"},
        ) from exc
    set_market_service(None)
    return settings_to_dict(saved)


def _user_row(
    profile: UserProfile,
    *,
    current_user_id: str,
    whitelist: frozenset[str],
) -> dict[str, Any]:
    return {
        "userId": profile.user_id,
        "email": profile.email,
        "name": profile.name,
        "role": profile.role,
        "createdAt": _iso(profile.created_at),
        "updatedAt": _iso(profile.updated_at),
        "newsKeywords": list(profile.news_keywords or []),
        "emailOptIn": bool(profile.email_opt_in),
        "preferredCurrency": normalize_stored_currency(profile.preferred_currency),
        "avatarStyle": profile.avatar_style,
        "avatarSeed": profile.avatar_seed,
        "avatarColor": profile.avatar_color,
        "roleManagedByEnv": bool(profile.email and profile.email.casefold() in whitelist),
        "isCurrentUser": profile.user_id == current_user_id,
    }


@router.get("/api/admin/users")
def list_admin_users(
    limit: int = Query(default=25, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    admin: UserProfile = Depends(require_admin),
    repo: UserProfileRepo = Depends(get_user_profile_repo),
    service: AdminUserService = Depends(get_admin_user_service),
) -> dict[str, Any]:
    try:
        page = service.list_page(limit, cursor)
    except InvalidCursorError as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_cursor"}) from exc
    whitelist = service.whitelist
    return {
        "items": [
            _user_row(profile, current_user_id=admin.user_id, whitelist=whitelist)
            for profile in page.items
        ],
        "nextCursor": page.next_cursor,
    }


@router.put("/api/admin/users/{user_id}/role")
def update_admin_user_role(
    user_id: str,
    body: UserRoleUpdate,
    admin: UserProfile = Depends(require_admin),
    service: AdminUserService = Depends(get_admin_user_service),
) -> dict[str, Any]:
    try:
        profile = service.change_role(user_id, body.role)
    except AdminUserError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code},
        ) from exc
    return _user_row(
        profile,
        current_user_id=admin.user_id,
        whitelist=service.whitelist,
    )


@router.put("/api/admin/users/{user_id}/settings")
def update_admin_user_settings(
    user_id: str,
    body: UserSettingsUpdate,
    admin: UserProfile = Depends(require_admin),
    repo: UserProfileRepo = Depends(get_user_profile_repo),
    service: AdminUserService = Depends(get_admin_user_service),
) -> dict[str, Any]:
    try:
        patch = normalize_user_settings_patch(body.model_dump(by_alias=True, exclude_unset=True))
        profile = repo.update_settings(user_id, patch=patch)
    except UserSettingsValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from exc
    return _user_row(
        profile,
        current_user_id=admin.user_id,
        whitelist=service.whitelist,
    )


@router.get("/api/admin/rss-sources")
def list_rss(
    admin: UserProfile = Depends(require_admin),
    repo=Depends(get_rss_sources_repo),
) -> list[dict[str, Any]]:
    _ = admin
    return [
        {
            "sourceId": s.source_id,
            "name": s.name,
            "url": s.url,
            "enabled": s.enabled,
        }
        for s in repo.list()
    ]


@router.post("/api/admin/rss-sources", status_code=status.HTTP_201_CREATED)
def create_rss(
    body: RssCreate,
    admin: UserProfile = Depends(require_admin),
    repo=Depends(get_rss_sources_repo),
) -> dict[str, Any]:
    _ = admin
    try:
        created = repo.create(
            RssSource(
                source_id=body.source_id or str(uuid4()),
                name=body.name,
                url=body.url,
                enabled=body.enabled,
            )
        )
    except AdminValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    return {
        "sourceId": created.source_id,
        "name": created.name,
        "url": created.url,
        "enabled": created.enabled,
    }


@router.put("/api/admin/rss-sources/{source_id}")
def update_rss(
    source_id: str,
    body: RssUpdate,
    admin: UserProfile = Depends(require_admin),
    repo=Depends(get_rss_sources_repo),
) -> dict[str, Any]:
    _ = admin
    existing = repo.get(source_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="RSS source not found")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        existing.name = data["name"]
    if "url" in data and data["url"] is not None:
        existing.url = data["url"]
    if "enabled" in data and data["enabled"] is not None:
        existing.enabled = data["enabled"]
    try:
        updated = repo.update(existing)
    except AdminValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    except AdminNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail) from exc
    return {
        "sourceId": updated.source_id,
        "name": updated.name,
        "url": updated.url,
        "enabled": updated.enabled,
    }


@router.delete("/api/admin/rss-sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rss(
    source_id: str,
    admin: UserProfile = Depends(require_admin),
    repo=Depends(get_rss_sources_repo),
) -> None:
    _ = admin
    try:
        repo.delete(source_id)
    except AdminNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail) from exc


@router.get("/api/admin/job-runs")
def list_job_runs(
    jobType: Optional[str] = Query(default=None),  # noqa: N803
    limit: int = Query(default=50, ge=1, le=200),
    admin: UserProfile = Depends(require_admin),
    repo=Depends(get_job_runs_repo),
) -> list[dict[str, Any]]:
    _ = admin
    runs = repo.list_recent(job_type=jobType, limit=limit)
    return [
        {
            "runId": r.run_id,
            "jobType": r.job_type,
            "status": r.status,
            "startedAt": _iso(r.started_at),
            "finishedAt": _iso(r.finished_at),
            "message": r.message,
            "counts": r.counts or {},
        }
        for r in runs
    ]
