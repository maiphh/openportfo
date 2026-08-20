"""News list API (filtered by user keywords / holdings / watchlist)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user, get_news_service
from app.ports.news import NewsItem
from app.ports.users import UserProfile
from app.services.news_service import NewsService
from app.api.schemas import NewsItemResponse

router = APIRouter(tags=["news"])


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
    user: UserProfile = Depends(get_current_user),
    svc: NewsService = Depends(get_news_service),
) -> list[dict[str, Any]]:
    items = svc.list_for_user(user, limit=limit)
    return [news_item_to_dict(i) for i in items]
