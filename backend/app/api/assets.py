"""Asset search routes (market data; auth required)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import get_asset_detail_service, get_current_user, get_market_service
from app.ports.market import MarketDataError
from app.ports.users import UserProfile
from app.services.asset_detail_service import AssetDetailService, AssetNotFoundError
from app.services.history_service import HistoryValidationError
from app.services.market_service import QuoteKey
from app.services.market_service import (
    MarketService,
    ValidationError,
    quote_to_dict,
    search_result_to_dict,
)

router = APIRouter(tags=["assets"])


def _quote_response(asset_type: str, symbol: str, asset_id: str, svc: MarketService, force: bool):
    try:
        quotes = svc.get_quotes(
            [QuoteKey(asset_type=asset_type, symbol=symbol, asset_id=asset_id or None)],
            force=force,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=getattr(exc, "detail", None) or str(exc),
        ) from exc
    if not quotes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price not found")
    quote = quotes[0]
    return quote_to_dict(
        quote,
        asset_id=asset_id or None,
        source="refreshed" if force else "cache-first",
    )


class QuoteRequestItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    asset_type: str = Field(alias="assetType")
    symbol: str
    asset_id: Optional[str] = Field(default=None, alias="assetId")


class QuoteBatchRequest(BaseModel):
    items: list[QuoteRequestItem]


@router.post("/api/quotes")
def batch_quotes(
    body: QuoteBatchRequest,
    user: UserProfile = Depends(get_current_user),
    svc: MarketService = Depends(get_market_service),
) -> dict[str, Any]:
    """Cache-first batch quotes. Missing symbols are omitted from ``quotes``."""
    _ = user
    if not body.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="items must not be empty")
    if len(body.items) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="items must have at most 50 entries")
    keys: list[QuoteKey] = []
    id_by_key: dict[tuple[str, str], Optional[str]] = {}
    for item in body.items:
        keys.append(
            QuoteKey(asset_type=item.asset_type, symbol=item.symbol, asset_id=item.asset_id)
        )
        id_by_key[(item.asset_type.strip().lower(), item.symbol.strip().upper())] = item.asset_id
    try:
        quotes = svc.get_quotes(keys, force=False)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=getattr(exc, "detail", None) or str(exc),
        ) from exc
    return {
        "quotes": [
            quote_to_dict(
                q,
                asset_id=id_by_key.get((q.asset_type, q.symbol.upper())),
                source="cache-first",
            )
            for q in quotes
        ]
    }


@router.get("/api/assets")
def list_assets(
    type: str = Query(default=""),  # noqa: A002 — API query name
    limit: int = Query(default=500, ge=1, le=2000),
    user: UserProfile = Depends(get_current_user),
    svc: MarketService = Depends(get_market_service),
) -> list[dict[str, Any]]:
    """List crypto or VN stocks for browse / later search. Auth required."""
    _ = user
    try:
        results = svc.list_assets(type, limit=limit)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    return [search_result_to_dict(r) for r in results]


@router.get("/api/assets/search")
def search_assets(
    q: str = Query(default=""),
    type: str = Query(default=""),  # noqa: A002 — API query name per PRD
    user: UserProfile = Depends(get_current_user),
    svc: MarketService = Depends(get_market_service),
) -> list[dict[str, Any]]:
    """Search crypto or stock symbols. Auth required; 400 on empty q / bad type."""
    _ = user  # ownership not needed for global market search; auth still required
    try:
        results = svc.search(q, type)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    return [search_result_to_dict(r) for r in results]


@router.get("/api/assets/{asset_type}/{slug}/history")
def get_asset_detail_history(
    asset_type: str,
    slug: str,
    range: str = Query(default="30d"),  # noqa: A002
    currency: Optional[str] = Query(default=None),
    user: UserProfile = Depends(get_current_user),
    svc: AssetDetailService = Depends(get_asset_detail_service),
) -> dict[str, Any]:
    """Chart series for /crypto/btc or /stock/VNM. Native prices + stored FX display."""
    try:
        return svc.get_history(
            asset_type=asset_type,
            slug=slug,
            range_=range,
            currency=currency,
            preferred_currency=user.preferred_currency,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    except HistoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=getattr(exc, "detail", None) or str(exc),
        ) from exc


@router.get("/api/assets/{asset_type}/{slug}")
def get_asset_detail(
    asset_type: str,
    slug: str,
    currency: Optional[str] = Query(default=None),
    range: Optional[str] = Query(default=None),  # noqa: A002
    user: UserProfile = Depends(get_current_user),
    svc: AssetDetailService = Depends(get_asset_detail_service),
) -> dict[str, Any]:
    """Profile + quote (+ optional history) for the asset detail page."""
    try:
        return svc.get_detail(
            asset_type=asset_type,
            slug=slug,
            currency=currency,
            range_=range,
            preferred_currency=user.preferred_currency,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    except HistoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=getattr(exc, "detail", None) or str(exc),
        ) from exc


@router.get("/api/assets/{asset_type}/{symbol}/quote")
def get_asset_quote(
    asset_type: str,
    symbol: str,
    assetId: str = Query(default=""),  # noqa: N803
    user: UserProfile = Depends(get_current_user),
    svc: MarketService = Depends(get_market_service),
) -> dict[str, Any]:
    _ = user
    return _quote_response(asset_type, symbol, assetId, svc, False)


@router.post("/api/assets/{asset_type}/{symbol}/quote/refresh")
def refresh_asset_quote(
    asset_type: str,
    symbol: str,
    assetId: str = Query(default=""),  # noqa: N803
    user: UserProfile = Depends(get_current_user),
    svc: MarketService = Depends(get_market_service),
) -> dict[str, Any]:
    _ = user
    return _quote_response(asset_type, symbol, assetId, svc, True)
