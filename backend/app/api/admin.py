"""Admin-only settings, RSS sources, job runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import (
    get_job_runs_repo,
    get_rss_sources_repo,
    get_settings_repo,
    require_admin,
    set_market_service,
)
from app.ports.admin import (
    AdminNotFoundError,
    AdminValidationError,
    RssSource,
    SystemSettings,
)
from app.ports.users import UserProfile

router = APIRouter(tags=["admin"])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def settings_to_dict(s: SystemSettings) -> dict[str, Any]:
    return {
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
        "defaultDisplayCurrency": s.default_display_currency,
    }


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email_time: Optional[str] = Field(default=None, alias="emailTime")
    timezone: Optional[str] = None
    email_enabled: Optional[bool] = Field(default=None, alias="emailEnabled")
    price_cache_ttl_minutes: Optional[int] = Field(
        default=None, alias="priceCacheTtlMinutes"
    )
    jobs_news: Optional[bool] = Field(default=None, alias="jobsNews")
    jobs_snapshot: Optional[bool] = Field(default=None, alias="jobsSnapshot")
    jobs_email: Optional[bool] = Field(default=None, alias="jobsEmail")
    jobs_price: Optional[bool] = Field(default=None, alias="jobsPrice")
    default_display_currency: Optional[str] = Field(
        default=None, alias="defaultDisplayCurrency"
    )
    # Nested jobs object optional
    jobs: Optional[dict[str, bool]] = None


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
    data = body.model_dump(exclude_unset=True)
    jobs = data.pop("jobs", None)
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
        current.default_display_currency = data["default_display_currency"]
    saved = repo.save(current)
    set_market_service(None)
    return settings_to_dict(saved)


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
