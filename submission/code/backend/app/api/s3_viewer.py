"""Read-only object-storage inspector for the local temporary UI."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import Settings, get_settings
from app.core.deps import get_object_storage, require_admin
from app.ports.storage import ObjectStorage
from app.ports.users import UserProfile

router = APIRouter(prefix="/api/dev/s3", tags=["dev"])

_ALLOWED_PREFIXES = ("profile/", "resolve/", "history/", "snapshots/")


def _require_local(settings: Settings) -> None:
    if settings.app_env.strip().lower() not in {"local", "test"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="S3 viewer is available only in local/test environments",
        )


def _safe_prefix(raw: str) -> str:
    prefix = (raw or "").strip().lstrip("/")
    if not prefix:
        return ""
    if not prefix.endswith("/"):
        prefix = prefix + "/"
    if not any(prefix == allowed or prefix.startswith(allowed) for allowed in _ALLOWED_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prefix must be profile/, resolve/, history/, or snapshots/",
        )
    return prefix


def _safe_key(raw: str) -> str:
    key = (raw or "").strip().lstrip("/")
    if not key or ".." in key or key.endswith("/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object key")
    if not any(key.startswith(allowed) for allowed in _ALLOWED_PREFIXES):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Key is outside allowed prefixes")
    return key


@router.get("")
def list_objects(
    prefix: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=500),
    _user: UserProfile = Depends(require_admin),
    settings: Settings = Depends(get_settings),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict[str, Any]:
    _require_local(settings)
    safe = _safe_prefix(prefix)
    try:
        keys = storage.list_keys(safe, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not list object storage: {exc}",
        ) from exc
    backend = "s3" if settings.aws_adapters_enabled() else "memory"
    return {
        "backend": backend,
        "bucket": (settings.data_bucket or "").strip() or None,
        "endpoint": (settings.s3_endpoint_url or "").strip() or None,
        "prefix": safe,
        "keys": keys,
        "count": len(keys),
    }


@router.get("/object")
def get_object(
    key: str = Query(...),
    _user: UserProfile = Depends(require_admin),
    settings: Settings = Depends(get_settings),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict[str, Any]:
    _require_local(settings)
    safe = _safe_key(key)
    try:
        body = storage.get_json(safe)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not read object: {exc}",
        ) from exc
    if body is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    return {"key": safe, "body": body}
