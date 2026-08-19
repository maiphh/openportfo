"""User snapshot history (read path for the daily snapshot job)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user, get_snapshot_service
from app.ports.users import UserProfile
from app.services.snapshot_service import (
    SnapshotService,
    SnapshotValidationError,
    record_to_dict,
)

router = APIRouter(tags=["snapshots"])


@router.get("/api/snapshots")
def list_snapshots(
    date_from: Optional[str] = Query(default=None, alias="from"),
    date_to: Optional[str] = Query(default=None, alias="to"),
    user: UserProfile = Depends(get_current_user),
    svc: SnapshotService = Depends(get_snapshot_service),
) -> list[dict[str, Any]]:
    try:
        records = svc.list(user.user_id, date_from=date_from, date_to=date_to)
    except SnapshotValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    return [record_to_dict(r) for r in records]


@router.get("/api/snapshots/{date}")
def get_snapshot(
    date: str,
    user: UserProfile = Depends(get_current_user),
    svc: SnapshotService = Depends(get_snapshot_service),
) -> dict[str, Any]:
    try:
        record = svc.get(user.user_id, date)
    except SnapshotValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")
    return record_to_dict(record)
