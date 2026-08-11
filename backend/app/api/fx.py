"""FX rates routes: read stored rates; admin on-demand refresh."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from fastapi.responses import JSONResponse

from app.core.deps import get_current_user, get_fx_service, require_admin
from app.ports.users import UserProfile
from app.services.fx_service import ConversionError, FxService, stored_to_api

router = APIRouter(tags=["fx"])


class FxConversionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: str
    source_currency: str = Field(alias="sourceCurrency")
    target_currency: str = Field(alias="targetCurrency")


@router.get("/api/fx/rates")
def get_fx_rates(
    user: UserProfile = Depends(get_current_user),
    fx: FxService = Depends(get_fx_service),
) -> dict[str, Any]:
    """Return stored FX rates only — zero provider HTTP calls."""
    _ = user
    return stored_to_api(fx.get_rates())


@router.post("/api/fx/convert")
def convert_currency(
    body: FxConversionRequest,
    user: UserProfile = Depends(get_current_user),
    fx: FxService = Depends(get_fx_service),
) -> dict[str, str]:
    """Convert with last stored rates; does not contact the FX provider."""
    _ = user
    try:
        converted, rate = fx.convert(body.amount, body.source_currency, body.target_currency)
    except ConversionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "amount": body.amount,
        "sourceCurrency": body.source_currency.strip().upper(),
        "targetCurrency": body.target_currency.strip().upper(),
        "rate": format(rate, "f"),
        "convertedAmount": format(converted, "f"),
    }


@router.post("/api/admin/fx/refresh")
def admin_fx_refresh(
    admin: UserProfile = Depends(require_admin),
    fx: FxService = Depends(get_fx_service),
) -> Any:
    """Admin on-demand provider fetch; save on success; keep previous on failure."""
    result = fx.refresh(admin_user_id=admin.user_id, base="USD")
    if result.ok:
        return stored_to_api(result.stored)

    body: dict[str, Any] = {
        "detail": result.error or "Exchange rate refresh failed",
        "rates": stored_to_api(result.stored),
    }
    return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=body)
