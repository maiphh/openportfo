"""Portfolio application service: holdings + cache prices + domain math.

Uses S01 ``compute_native_portfolio`` / ``apply_fx`` only (no duplicate formulas).
Reads stored FX via ExchangeRateRepo.get_latest — never ExchangeRate HTTP client.
Prices via MarketService (cache-first; force on refresh).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence

from app.domain.fx_math import apply_fx
from app.domain.models import FxRates, Holding, PortfolioSummary, PriceQuote
from app.domain.portfolio_math import compute_asset_class_totals, compute_native_portfolio
from app.ports.fx import ExchangeRateRepo, StoredRates
from app.ports.holdings import HoldingRecord, HoldingsRepo
from app.services.market_service import MarketService, QuoteKey

_ALLOWED_ASSET_TYPES = frozenset({"crypto", "stock"})


class ValidationError(Exception):
    """Client input failed validation (maps to HTTP 400)."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass
class PortfolioView:
    """Domain summary plus FX rate map and portfolio as-of for API mapping."""

    summary: PortfolioSummary
    fx_rates: dict[str, Decimal]
    as_of: Optional[datetime]


def holding_record_to_domain(record: HoldingRecord) -> Holding:
    """Map persisted HoldingRecord (S03) → domain Holding (S01)."""
    return Holding(
        user_id=record.user_id,
        asset_type=record.asset_type,  # type: ignore[arg-type]
        symbol=record.symbol,
        qty=record.qty,
        avg_cost=record.avg_cost,
        currency=record.currency,
        asset_id=record.asset_id,
        note=record.note,
    )


def stored_rates_to_domain(stored: StoredRates) -> FxRates:
    """Map StoredRates → domain FxRates (flat USD_VND keys)."""
    status = stored.status
    if not stored.rates:
        status = "missing"
    return FxRates(
        base=stored.base,
        rates=dict(stored.rates),
        status=status,  # type: ignore[arg-type]
        as_of=stored.as_of,
    )


def _normalize_asset_type_filter(asset_type: Optional[str]) -> Optional[str]:
    if asset_type is None or str(asset_type).strip() == "":
        return None
    t = str(asset_type).strip().lower()
    if t not in _ALLOWED_ASSET_TYPES:
        raise ValidationError("assetType must be 'crypto' or 'stock'")
    return t


def _quotes_as_of(quotes: Sequence[PriceQuote]) -> Optional[datetime]:
    if not quotes:
        return None
    return max(q.as_of for q in quotes)


class PortfolioService:
    """Assemble portfolio DTO inputs from holdings, market cache, and stored FX."""

    def __init__(
        self,
        holdings_repo: HoldingsRepo,
        market_service: MarketService,
        fx_repo: Optional[ExchangeRateRepo] = None,
    ) -> None:
        self._holdings = holdings_repo
        self._market = market_service
        self._fx = fx_repo

    def get_portfolio(
        self,
        user_id: str,
        *,
        display_currency: Optional[str] = None,
        preferred_currency: Optional[str] = None,
        asset_type: Optional[str] = None,
        force_refresh: bool = False,
    ) -> PortfolioView:
        """Load holdings, resolve quotes, run domain math, optionally apply FX.

        Args:
            user_id: Authenticated user.
            display_currency: Explicit query override (e.g. VND).
            preferred_currency: Profile default when display_currency unset.
            asset_type: Optional ``crypto`` | ``stock`` filter.
            force_refresh: Pass-through to MarketService (POST /refresh).
        """
        type_filter = _normalize_asset_type_filter(asset_type)
        records = self._holdings.list(user_id)
        if type_filter is not None:
            records = [r for r in records if r.asset_type == type_filter]

        domain_holdings = [holding_record_to_domain(r) for r in records]
        keys: list[QuoteKey] = [
            QuoteKey(
                asset_type=r.asset_type,
                symbol=r.symbol,
                asset_id=r.asset_id,
            )
            for r in records
        ]
        quotes = self._market.get_quotes(keys, force=force_refresh)
        native = compute_native_portfolio(domain_holdings, quotes)
        as_of = _quotes_as_of(quotes)

        display = (display_currency or preferred_currency or "").strip().upper() or None

        stored: Optional[StoredRates] = None
        if self._fx is not None:
            stored = self._fx.get_latest()

        if stored is not None and display:
            fx_domain = stored_rates_to_domain(stored)
            summary = apply_fx(native, fx_domain, display)
            rates_out = dict(stored.rates)
            summary.totals_by_asset_class = compute_asset_class_totals(summary)
            return PortfolioView(summary=summary, fx_rates=rates_out, as_of=as_of)

        # No conversion: native only; surface missing FX meta
        summary = native
        if summary.fx_status is None:
            summary.fx_status = "missing"
        rates_out: dict[str, Decimal] = dict(stored.rates) if stored is not None else {}
        if stored is not None:
            summary.fx_as_of = stored.as_of
            summary.fx_base = stored.base
            # Still missing conversion path (no display currency or empty rates)
            if not stored.rates or not display:
                summary.fx_status = "missing"
        summary.totals_by_asset_class = compute_asset_class_totals(summary)
        return PortfolioView(summary=summary, fx_rates=rates_out, as_of=as_of)


__all__ = [
    "PortfolioService",
    "PortfolioView",
    "ValidationError",
    "holding_record_to_domain",
    "stored_rates_to_domain",
]
