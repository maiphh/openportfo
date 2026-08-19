"""Watchlist CRUD routes (user-scoped; auth required)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import get_current_user, get_market_service, get_watchlist_repo
from app.ports.market import MarketDataError
from app.ports.users import UserProfile
from app.ports.watchlist import (
    DuplicateWatchlistError,
    WatchlistItem,
    WatchlistNotFoundError,
    WatchlistRepo,
)
from app.services.market_service import MarketService, QuoteKey
from app.services.watchlist_service import ValidationError, WatchlistService

router = APIRouter(tags=["watchlist"])


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def item_to_response(
    item: WatchlistItem,
    *,
    quote: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Serialize watchlist item to API JSON (camelCase)."""
    body: dict[str, Any] = {
        "userId": item.user_id,
        "assetType": item.asset_type,
        "symbol": item.symbol,
        "assetId": item.asset_id,
        "addedAt": _iso(item.added_at),
        "price": None,
        "currency": None,
        "asOf": None,
        "stale": False,
    }
    if quote is not None:
        body["price"] = quote.get("price")
        body["currency"] = quote.get("currency")
        body["asOf"] = quote.get("asOf")
        body["stale"] = bool(quote.get("stale"))
    return body


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
    market: MarketService = Depends(get_market_service),
) -> list[dict[str, Any]]:
    """List current user's watchlist items with cache-first quotes."""
    items = svc.list_items(user.user_id)
    quotes_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    keys = [
        QuoteKey(asset_type=i.asset_type, symbol=i.symbol, asset_id=i.asset_id)
        for i in items
    ]
    if keys:
        quotes = []
        by_type: dict[str, list[QuoteKey]] = {"crypto": [], "stock": []}
        for key in keys:
            by_type.setdefault(key.asset_type, []).append(key)
        for group in by_type.values():
            if not group:
                continue
            try:
                quotes.extend(market.get_quotes(group, force=False))
            except MarketDataError:
                continue
        for q in quotes:
            quotes_by_key[(q.asset_type, q.symbol.upper())] = {
                "price": format(q.price, "f"),
                "currency": q.currency,
                "asOf": q.as_of.isoformat() if q.as_of.tzinfo else q.as_of.isoformat() + "Z",
                "stale": bool(q.stale),
            }
    return [
        item_to_response(
            i,
            quote=quotes_by_key.get((i.asset_type, i.symbol.upper())),
        )
        for i in items
    ]


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
