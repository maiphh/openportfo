"""Holdings application service: validation + repository orchestration."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional, Protocol

from app.ports.holdings import (
    AssetType,
    DuplicateHoldingError,
    HoldingNotFoundError,
    HoldingRecord,
    HoldingsRepo,
    utc_now,
)
from app.ports.market import AssetSearchResult
from app.services.fx_service import ConversionError, FxService


class ValidationError(Exception):
    """Client input failed business validation (maps to HTTP 400)."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AssetResolver(Protocol):
    """Minimal market surface needed to validate holding symbols."""

    def search(self, q: str, asset_type: str) -> list[AssetSearchResult]: ...

    def list_assets(
        self,
        asset_type: str,
        *,
        limit: int = 250,
    ) -> list[AssetSearchResult]: ...


_ALLOWED_ASSET_TYPES = frozenset({"crypto", "stock"})


def native_currency_for_asset(asset_type: str) -> str:
    """Stock costs store in VND; crypto in USD."""
    return "USD" if asset_type == "crypto" else "VND"


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


def resolve_holding_asset(
    market: AssetResolver,
    asset_type: str,
    symbol: str,
    asset_id: Optional[str] = None,
) -> AssetSearchResult:
    """Resolve a holding against market search/catalog; raise if unknown."""
    at = _normalize_asset_type(asset_type)
    sym = _normalize_symbol(symbol)
    aid = (asset_id or "").strip() or None

    hits: list[AssetSearchResult] = []
    try:
        hits = list(market.search(sym, at))
    except Exception:  # noqa: BLE001 — treat provider/search failure as no hits
        hits = []

    def _exact(candidates: list[AssetSearchResult]) -> Optional[AssetSearchResult]:
        for c in candidates:
            if c.symbol.upper() == sym:
                if aid is None or c.asset_id.lower() == aid.lower():
                    return c
        if aid:
            for c in candidates:
                if c.asset_id.lower() == aid.lower():
                    return c
        return None

    hit = _exact(hits)
    if hit is None and aid:
        try:
            id_hits = list(market.search(aid, at))
        except Exception:  # noqa: BLE001
            id_hits = []
        hit = _exact(id_hits) or next(
            (c for c in id_hits if c.asset_id.lower() == aid.lower()),
            None,
        )

    if hit is None:
        try:
            catalog = list(market.list_assets(at, limit=500))
        except Exception:  # noqa: BLE001
            catalog = []
        hit = _exact(catalog)
        if hit is None:
            for c in catalog:
                if c.symbol.upper() == sym or (
                    aid and c.asset_id.lower() == aid.lower()
                ):
                    hit = c
                    break

    if hit is None:
        raise ValidationError(f"Unknown or invalid asset: {at}/{sym}")
    return hit


class HoldingsService:
    """Orchestrates HoldingsRepo with qty/avgCost + catalog validation."""

    def __init__(
        self,
        repo: HoldingsRepo,
        market: Optional[AssetResolver] = None,
        fx: Optional[FxService] = None,
    ) -> None:
        self._repo = repo
        self._market = market
        self._fx = fx

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

    def _require_resolved(
        self,
        asset_type: AssetType,
        symbol: str,
        asset_id: Optional[str],
    ) -> tuple[str, Optional[str]]:
        """Validate symbol against market catalog when a resolver is wired."""
        if self._market is None:
            return symbol, asset_id
        hit = resolve_holding_asset(self._market, asset_type, symbol, asset_id)
        return hit.symbol.upper(), hit.asset_id

    def _to_native_cost(
        self,
        avg_cost: Decimal,
        *,
        entry_currency: str,
        native_currency: str,
    ) -> Decimal:
        """Convert session/entry cost into native holding currency via stored FX."""
        src = (entry_currency or "").strip().upper()
        dst = native_currency.upper()
        if not src:
            raise ValidationError("currency is required")
        if src == dst:
            return avg_cost
        if self._fx is None:
            raise ValidationError(
                f"Cannot convert cost from {src} to {dst}: FX service unavailable"
            )
        try:
            converted, _rate = self._fx.convert(avg_cost, src, dst)
        except ConversionError as exc:
            raise ValidationError(
                f"Cannot convert cost from {src} to {dst}: {exc}"
            ) from exc
        return converted

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
        entry_cur = (currency or "").strip().upper()
        if not entry_cur:
            raise ValidationError("currency is required")

        sym, resolved_id = self._require_resolved(at, sym, asset_id)
        native = native_currency_for_asset(at)
        avg_native = self._to_native_cost(
            avg_d, entry_currency=entry_cur, native_currency=native
        )

        now = utc_now()
        record = HoldingRecord(
            user_id=user_id,
            asset_type=at,
            symbol=sym,
            qty=qty_d,
            avg_cost=avg_native,
            currency=native,
            asset_id=resolved_id,
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

        # Re-check catalog when market is wired (rejects corrupted/unknown rows).
        if self._market is not None:
            existing = self._repo.get(user_id, at, sym)
            if existing is not None:
                resolve_holding_asset(
                    self._market, at, sym, asset_id or existing.asset_id
                )

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
            native = native_currency_for_asset(at)
            entry_cur = (currency or native).strip().upper()
            if not entry_cur:
                raise ValidationError("currency cannot be empty")
            avg_d = self._to_native_cost(
                avg_d, entry_currency=entry_cur, native_currency=native
            )
            # Always persist native currency after cost conversion.
            currency = native

        cur: Optional[str] = None
        if currency is not None:
            cur = currency.strip().upper()
            if not cur:
                raise ValidationError("currency cannot be empty")
            # Disallow writing non-native currency codes.
            native = native_currency_for_asset(at)
            if cur != native:
                # Treat as entry currency for a no-cost update — force native store.
                cur = native

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
    "resolve_holding_asset",
    "native_currency_for_asset",
]
