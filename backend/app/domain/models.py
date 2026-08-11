"""Pure domain models for portfolio valuation and FX.

Money amounts use ``Decimal`` — never float.
No I/O, no FastAPI, no AWS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

AssetType = Literal["crypto", "stock"]
FxStatus = Literal["missing", "stale_ok", "fresh"]


@dataclass(frozen=True)
class Holding:
    """User position in an asset (native currency)."""

    user_id: str
    asset_type: AssetType
    symbol: str
    qty: Decimal
    avg_cost: Decimal
    currency: str
    asset_id: Optional[str] = None
    note: Optional[str] = None


@dataclass(frozen=True)
class PriceQuote:
    """Market price for an asset in its native quote currency."""

    asset_type: AssetType
    symbol: str
    price: Decimal
    currency: str
    as_of: datetime


@dataclass(frozen=True)
class FxRates:
    """Stored exchange rates (injected; never fetched inside domain).

    Rate key scheme: flat ``"{SRC}_{DST}"`` e.g. ``USD_VND``, ``VND_USD``.
    Values are multipliers: ``amount_dst = amount_src * rates["SRC_DST"]``.
    """

    base: str
    rates: dict[str, Decimal]
    status: FxStatus
    as_of: Optional[datetime] = None


@dataclass(frozen=True)
class CurrencyTotals:
    """Aggregated market value / cost / PnL in one currency."""

    currency: str
    market_value: Decimal
    cost_basis: Decimal
    pnl: Decimal


@dataclass
class PortfolioLine:
    """One holding after native valuation (and optional FX conversion)."""

    user_id: str
    asset_type: AssetType
    symbol: str
    qty: Decimal
    avg_cost: Decimal
    currency: str
    asset_id: Optional[str] = None
    note: Optional[str] = None
    price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    cost_basis: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    pnl_percent: Optional[Decimal] = None
    missing_price: bool = False
    # Display (after apply_fx)
    display_currency: Optional[str] = None
    market_value_display: Optional[Decimal] = None
    cost_basis_display: Optional[Decimal] = None
    pnl_display: Optional[Decimal] = None
    allocation: Optional[Decimal] = None


@dataclass
class PortfolioSummary:
    """Full portfolio: lines + native currency totals + optional display totals."""

    lines: list[PortfolioLine] = field(default_factory=list)
    totals_by_currency: dict[str, CurrencyTotals] = field(default_factory=dict)
    display_currency: Optional[str] = None
    market_value_display: Optional[Decimal] = None
    cost_basis_display: Optional[Decimal] = None
    pnl_display: Optional[Decimal] = None
    pnl_percent_display: Optional[Decimal] = None
    fx_status: Optional[FxStatus] = None
    fx_as_of: Optional[datetime] = None
    fx_base: Optional[str] = None
