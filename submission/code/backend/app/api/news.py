"""News list API — search shared storage by market / asset keywords + time."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user, get_news_service
from app.ports.news import NewsItem
from app.ports.users import UserProfile
from app.services.news_service import NewsService
from app.api.schemas import NewsItemResponse

router = APIRouter(tags=["news"])

MarketQuery = Literal["stock", "crypto"]


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def news_item_to_dict(item: NewsItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "publishedAt": _iso(item.published_at),
        "symbols": list(item.symbols or []),
        "date": item.date,
    }


@router.get(
    "/api/news",
    response_model=list[NewsItemResponse],
    response_model_by_alias=True,
)
def list_news(
    limit: int = Query(default=50, ge=1, le=200),
    market: Optional[MarketQuery] = Query(
        default=None,
        description="stock | crypto board filter over stored news",
    ),
    symbol: Optional[str] = Query(default=None, description="Asset symbol token"),
    name: Optional[str] = Query(default=None, description="Asset display name token"),
    assetId: Optional[str] = Query(default=None, alias="assetId"),
    assetType: Optional[MarketQuery] = Query(default=None, alias="assetType"),
    q: Optional[str] = Query(
        default=None,
        description="Comma-separated extra keywords to search in title/symbols",
    ),
    user: UserProfile = Depends(get_current_user),
    svc: NewsService = Depends(get_news_service),
) -> list[dict[str, Any]]:
    """Auth-gated news search over the shared News store (keyword + recency)."""
    _ = user
    if market is not None and market not in ("stock", "crypto"):
        raise HTTPException(status_code=400, detail="market must be stock or crypto")

    extra = [part.strip() for part in (q or "").split(",") if part.strip()]
    asset_queries = [
        *(extra),
        *([symbol.strip()] if symbol and symbol.strip() else []),
        *([name.strip()] if name and name.strip() else []),
        *([assetId.strip()] if assetId and assetId.strip() else []),
    ]

    if asset_queries:
        # Asset detail (and explicit q): search by tokens; optional assetType scopes board.
        scope = assetType or market
        items = svc.search(limit=limit, market=scope, queries=asset_queries)
    elif market is not None:
        items = svc.list_market(limit=limit, market=market)
    else:
        items = svc.list_market(limit=limit)

    return [news_item_to_dict(i) for i in items]
