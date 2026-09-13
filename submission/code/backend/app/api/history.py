"""Asset history chart API (cache-aside ObjectStorage)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user, get_history_service
from app.api.schemas import HistoryResponse
from app.ports.market import MarketDataError
from app.ports.users import UserProfile
from app.services.history_service import HistoryService, HistoryValidationError

router = APIRouter(tags=["history"])


@router.get(
    "/api/assets/{asset_id}/history",
    response_model=HistoryResponse,
    response_model_by_alias=True,
)
def get_asset_history(
    asset_id: str,
    range: str = Query(default="30d"),  # noqa: A002 — API name
    type: str = Query(default="crypto"),  # noqa: A002 — API name
    force: bool = Query(default=False),
    refresh: bool = Query(default=False),
    user: UserProfile = Depends(get_current_user),
    svc: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    """Return history with ``source`` and ``stale`` cache state fields."""
    _ = user
    try:
        return svc.get_history(
            asset_id=asset_id,
            asset_type=type,
            range_=range,
            force=bool(force or refresh),
        )
    except HistoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=getattr(exc, "detail", None) or str(exc),
        ) from exc
