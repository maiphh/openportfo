"""Holdings application service: validation + repository orchestration."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from app.ports.holdings import (
    AssetType,
    DuplicateHoldingError,
    HoldingNotFoundError,
    HoldingRecord,
    HoldingsRepo,
    utc_now,
)


class ValidationError(Exception):
    """Client input failed business validation (maps to HTTP 400)."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


_ALLOWED_ASSET_TYPES = frozenset({"crypto", "stock"})


def _parse_decimal(value: object, field_name: str) -> Decimal:
    if value is None:
        raise ValidationError(f"{field_name} is required")
    try:
        if isinstance(value, Decimal):
            d = value
        elif isinstance(value, (int, float, str)):
            d = Decimal(str(value))
        else:
            raise ValidationError(f"{field_name} must be a number")
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a valid number") from exc
    if not d.is_finite():
        raise ValidationError(f"{field_name} must be a finite number")
    return d


def _normalize_symbol(symbol: str) -> str:
    s = (symbol or "").strip().upper()
    if not s:
        raise ValidationError("symbol is required")
    return s


def _normalize_asset_type(asset_type: str) -> AssetType:
    t = (asset_type or "").strip().lower()
    if t not in _ALLOWED_ASSET_TYPES:
        raise ValidationError("assetType must be 'crypto' or 'stock'")
    return t  # type: ignore[return-value]


class HoldingsService:
    """Orchestrates HoldingsRepo with qty/avgCost validation (no AWS SDK)."""

    def __init__(self, repo: HoldingsRepo) -> None:
        self._repo = repo

    def list_holdings(self, user_id: str) -> list[HoldingRecord]:
        return self._repo.list(user_id)

    def get_holding(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
    ) -> HoldingRecord:
        at = _normalize_asset_type(asset_type)
        sym = _normalize_symbol(symbol)
        item = self._repo.get(user_id, at, sym)
        if item is None:
            raise HoldingNotFoundError(f"Holding not found: {at}/{sym}")
        return item

    def create_holding(
        self,
        user_id: str,
        *,
        asset_type: str,
        symbol: str,
        qty: object,
        avg_cost: object,
        currency: str,
        asset_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> HoldingRecord:
        at = _normalize_asset_type(asset_type)
        sym = _normalize_symbol(symbol)
        qty_d = _parse_decimal(qty, "qty")
        avg_d = _parse_decimal(avg_cost, "avgCost")
        if qty_d <= 0:
            raise ValidationError("qty must be greater than 0")
        if avg_d < 0:
            raise ValidationError("avgCost must be greater than or equal to 0")
        cur = (currency or "").strip().upper()
        if not cur:
            raise ValidationError("currency is required")

        now = utc_now()
        record = HoldingRecord(
            user_id=user_id,
            asset_type=at,
            symbol=sym,
            qty=qty_d,
            avg_cost=avg_d,
            currency=cur,
            asset_id=asset_id,
            note=note,
            created_at=now,
            updated_at=now,
        )
        return self._repo.create(record)

    def update_holding(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
        *,
        qty: object = None,
        avg_cost: object = None,
        currency: Optional[str] = None,
        asset_id: Optional[str] = None,
        note: Optional[str] = None,
        note_provided: bool = False,
    ) -> HoldingRecord:
        at = _normalize_asset_type(asset_type)
        sym = _normalize_symbol(symbol)

        qty_d: Optional[Decimal] = None
        avg_d: Optional[Decimal] = None
        if qty is not None:
            qty_d = _parse_decimal(qty, "qty")
            if qty_d <= 0:
                raise ValidationError("qty must be greater than 0")
        if avg_cost is not None:
            avg_d = _parse_decimal(avg_cost, "avgCost")
            if avg_d < 0:
                raise ValidationError("avgCost must be greater than or equal to 0")

        cur: Optional[str] = None
        if currency is not None:
            cur = currency.strip().upper()
            if not cur:
                raise ValidationError("currency cannot be empty")

        clear_note = note_provided and note is None
        return self._repo.update(
            user_id,
            at,
            sym,
            qty=qty_d,
            avg_cost=avg_d,
            currency=cur,
            asset_id=asset_id,
            note=note if note_provided and note is not None else None,
            clear_note=clear_note,
        )

    def delete_holding(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
    ) -> None:
        at = _normalize_asset_type(asset_type)
        sym = _normalize_symbol(symbol)
        self._repo.delete(user_id, at, sym)


__all__ = [
    "HoldingsService",
    "ValidationError",
    "DuplicateHoldingError",
    "HoldingNotFoundError",
]
