"""User snapshot history (read path for the daily snapshot job)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user, get_snapshot_service
from app.ports.users import UserProfile
from app.services.snapshot_service import (
    SnapshotService,
    SnapshotValidationError,
    record_to_dict,
    snapshot_amount_in_currency,
    snapshot_value_in_currency,
)
from app.services.currency_service import CurrencyValidationError, normalize_currency

router = APIRouter(tags=["snapshots"])


def _snapshot_response(record, currency: Optional[str] = None) -> dict[str, Any]:
    body = record_to_dict(record)
    if not currency:
        return body
    payload = deepcopy(body.get("payload") or {})
    value = snapshot_value_in_currency(payload, currency)
    if value is not None:
        converted: dict[str, str] = {}
        for key in ("marketValue", "costBasis", "pnl"):
            amount = snapshot_amount_in_currency(payload, currency, key)
            if amount is not None:
                converted[key] = format(amount, "f")
        payload["totalsDisplay"] = {
            "currency": currency,
            **converted,
            "marketValue": format(value, "f"),
        }
        payload["displayCurrency"] = currency
    body["payload"] = payload
    return body


@router.get("/api/snapshots")
def list_snapshots(
    date_from: Optional[str] = Query(default=None, alias="from"),
    date_to: Optional[str] = Query(default=None, alias="to"),
    currency: Optional[str] = Query(default=None),
    user: UserProfile = Depends(get_current_user),
    svc: SnapshotService = Depends(get_snapshot_service),
) -> list[dict[str, Any]]:
    try:
        target = normalize_currency(currency, allow_none=True)
        records = svc.list(user.user_id, date_from=date_from, date_to=date_to)
    except (SnapshotValidationError, CurrencyValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    return [_snapshot_response(r, target) for r in records]


@router.get("/api/snapshots/{date}")
def get_snapshot(
    date: str,
    currency: Optional[str] = Query(default=None),
    user: UserProfile = Depends(get_current_user),
    svc: SnapshotService = Depends(get_snapshot_service),
) -> dict[str, Any]:
    try:
        target = normalize_currency(currency, allow_none=True)
        record = svc.get(user.user_id, date)
    except (SnapshotValidationError, CurrencyValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")
    return _snapshot_response(record, target)
