"""Asset search routes (market data; auth required)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user, get_market_service
from app.ports.market import MarketDataError
from app.ports.users import UserProfile
from app.services.market_service import QuoteKey
from app.services.market_service import MarketService, ValidationError, search_result_to_dict

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
    return {
        "assetType": quote.asset_type,
        "symbol": quote.symbol,
        "assetId": asset_id or None,
        "price": format(quote.price, "f"),
        "currency": quote.currency,
        "asOf": quote.as_of.isoformat(),
        "source": "refreshed" if force else "cache-first",
    }


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
