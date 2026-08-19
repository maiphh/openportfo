"""Holdings CRUD routes (user-scoped; auth required)."""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from io import StringIO
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import (
    get_current_user,
    get_fx_service,
    get_holdings_repo,
    get_market_service,
)
from app.ports.holdings import (
    DuplicateHoldingError,
    HoldingNotFoundError,
    HoldingRecord,
    HoldingsRepo,
)
from app.ports.users import UserProfile
from app.services.fx_service import FxService
from app.services.holdings_service import HoldingsService, ValidationError
from app.services.market_service import MarketService

router = APIRouter(tags=["holdings"])


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def _dec_str(d: Decimal) -> str:
    """Serialize Decimal without scientific notation where practical."""
    return format(d, "f")


def holding_to_response(h: HoldingRecord) -> dict[str, Any]:
    """Serialize holding to API JSON (camelCase per PRD)."""
    return {
        "userId": h.user_id,
        "assetType": h.asset_type,
        "symbol": h.symbol,
        "assetId": h.asset_id,
        "qty": _dec_str(h.qty),
        "avgCost": _dec_str(h.avg_cost),
        "currency": h.currency,
        "note": h.note,
        "createdAt": _iso(h.created_at),
        "updatedAt": _iso(h.updated_at),
    }


class HoldingCreate(BaseModel):
    """POST /api/holdings body."""

    model_config = ConfigDict(populate_by_name=True)

    asset_type: str = Field(alias="assetType")
    symbol: str
    asset_id: Optional[str] = Field(default=None, alias="assetId")
    qty: str
    avg_cost: str = Field(alias="avgCost")
    currency: str
    note: Optional[str] = None


class HoldingUpdate(BaseModel):
    """PUT /api/holdings/{assetType}/{symbol} body (partial)."""

    model_config = ConfigDict(populate_by_name=True)

    qty: Optional[str] = None
    avg_cost: Optional[str] = Field(default=None, alias="avgCost")
    currency: Optional[str] = None
    asset_id: Optional[str] = Field(default=None, alias="assetId")
    note: Optional[str] = None


def _service(
    repo: HoldingsRepo = Depends(get_holdings_repo),
    market: MarketService = Depends(get_market_service),
    fx: FxService = Depends(get_fx_service),
) -> HoldingsService:
    """Wire catalog validation + stored FX cost conversion on write."""
    return HoldingsService(repo, market=market, fx=fx)


@router.get("/api/holdings/export")
def export_holdings_csv(
    user: UserProfile = Depends(get_current_user),
    svc: HoldingsService = Depends(_service),
) -> Response:
    """CSV download of the current user's holdings."""
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["assetType", "symbol", "assetId", "qty", "avgCost", "currency", "note"]
    )
    for h in svc.list_holdings(user.user_id):
        writer.writerow(
            [
                h.asset_type,
                h.symbol,
                h.asset_id or "",
                _dec_str(h.qty),
                _dec_str(h.avg_cost),
                h.currency,
                h.note or "",
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="holdings.csv"'},
    )


@router.get("/api/holdings")
def list_holdings(
    user: UserProfile = Depends(get_current_user),
    svc: HoldingsService = Depends(_service),
) -> list[dict[str, Any]]:
    """List current user's holdings."""
    return [holding_to_response(h) for h in svc.list_holdings(user.user_id)]


@router.post("/api/holdings", status_code=status.HTTP_201_CREATED)
def create_holding(
    body: HoldingCreate,
    user: UserProfile = Depends(get_current_user),
    svc: HoldingsService = Depends(_service),
) -> dict[str, Any]:
    """Create a holding for the current user. 409 if duplicate key."""
    try:
        created = svc.create_holding(
            user.user_id,
            asset_type=body.asset_type,
            symbol=body.symbol,
            qty=body.qty,
            avg_cost=body.avg_cost,
            currency=body.currency,
            asset_id=body.asset_id,
            note=body.note,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    except DuplicateHoldingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.detail,
        ) from exc
    return holding_to_response(created)


@router.put("/api/holdings/{asset_type}/{symbol}")
def update_holding(
    asset_type: str,
    symbol: str,
    body: HoldingUpdate,
    user: UserProfile = Depends(get_current_user),
    svc: HoldingsService = Depends(_service),
) -> dict[str, Any]:
    """Update qty / avgCost / note (etc.) for a holding owned by current user."""
    # Detect explicit null note only if "note" was in the request body.
    raw = body.model_dump(by_alias=False, exclude_unset=True)
    note_provided = "note" in raw
    try:
        updated = svc.update_holding(
            user.user_id,
            asset_type,
            symbol,
            qty=body.qty,
            avg_cost=body.avg_cost,
            currency=body.currency,
            asset_id=body.asset_id,
            note=body.note,
            note_provided=note_provided,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    except HoldingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.detail,
        ) from exc
    return holding_to_response(updated)


@router.delete(
    "/api/holdings/{asset_type}/{symbol}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_holding(
    asset_type: str,
    symbol: str,
    user: UserProfile = Depends(get_current_user),
    svc: HoldingsService = Depends(_service),
) -> None:
    """Delete a holding owned by the current user."""
    try:
        svc.delete_holding(user.user_id, asset_type, symbol)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    except HoldingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.detail,
        ) from exc
