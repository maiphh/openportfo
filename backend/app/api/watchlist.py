"""Watchlist CRUD routes (user-scoped; auth required)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import get_current_user, get_watchlist_repo
from app.ports.users import UserProfile
from app.ports.watchlist import (
    DuplicateWatchlistError,
    WatchlistItem,
    WatchlistNotFoundError,
    WatchlistRepo,
)
from app.services.watchlist_service import ValidationError, WatchlistService

router = APIRouter(tags=["watchlist"])


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def item_to_response(item: WatchlistItem) -> dict[str, Any]:
    """Serialize watchlist item to API JSON (camelCase)."""
    return {
        "userId": item.user_id,
        "assetType": item.asset_type,
        "symbol": item.symbol,
        "assetId": item.asset_id,
        "addedAt": _iso(item.added_at),
    }


class WatchlistAdd(BaseModel):
    """POST /api/watchlist body."""

    model_config = ConfigDict(populate_by_name=True)

    asset_type: str = Field(alias="assetType")
    symbol: str
    asset_id: Optional[str] = Field(default=None, alias="assetId")


def _service(repo: WatchlistRepo = Depends(get_watchlist_repo)) -> WatchlistService:
    return WatchlistService(repo)


@router.get("/api/watchlist")
def list_watchlist(
    user: UserProfile = Depends(get_current_user),
    svc: WatchlistService = Depends(_service),
) -> list[dict[str, Any]]:
    """List current user's watchlist items."""
    return [item_to_response(i) for i in svc.list_items(user.user_id)]


@router.post("/api/watchlist", status_code=status.HTTP_201_CREATED)
def add_watchlist(
    body: WatchlistAdd,
    user: UserProfile = Depends(get_current_user),
    svc: WatchlistService = Depends(_service),
) -> dict[str, Any]:
    """Add an item to the current user's watchlist. 409 if duplicate."""
    try:
        created = svc.add_item(
            user.user_id,
            asset_type=body.asset_type,
            symbol=body.symbol,
            asset_id=body.asset_id,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    except DuplicateWatchlistError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.detail,
        ) from exc
    return item_to_response(created)


@router.delete(
    "/api/watchlist/{asset_type}/{symbol}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_watchlist(
    asset_type: str,
    symbol: str,
    user: UserProfile = Depends(get_current_user),
    svc: WatchlistService = Depends(_service),
) -> None:
    """Remove a watchlist item owned by the current user."""
    try:
        svc.remove_item(user.user_id, asset_type, symbol)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    except WatchlistNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.detail,
        ) from exc
