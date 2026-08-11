"""Portfolio valuation routes (auth required; cache-first prices; stored FX only)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user, get_portfolio_service
from app.domain.models import CurrencyTotals, PortfolioLine, PortfolioSummary
from app.domain.portfolio_math import pnl_percent
from app.ports.market import MarketDataError
from app.ports.users import UserProfile
from app.services.portfolio_service import PortfolioService, PortfolioView, ValidationError

router = APIRouter(tags=["portfolio"])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def _dec_str(d: Optional[Decimal]) -> Optional[str]:
    if d is None:
        return None
    return format(d, "f")


def _currency_totals_to_dict(t: CurrencyTotals) -> dict[str, Any]:
    pct = pnl_percent(t.pnl, t.cost_basis)
    return {
        "marketValue": _dec_str(t.market_value),
        "costBasis": _dec_str(t.cost_basis),
        "pnl": _dec_str(t.pnl),
        "pnlPercent": _dec_str(pct),
    }


def _line_to_dict(line: PortfolioLine) -> dict[str, Any]:
    return {
        "userId": line.user_id,
        "assetType": line.asset_type,
        "symbol": line.symbol,
        "assetId": line.asset_id,
        "qty": _dec_str(line.qty),
        "avgCost": _dec_str(line.avg_cost),
        "currency": line.currency,
        "note": line.note,
        "price": _dec_str(line.price),
        "marketValue": _dec_str(line.market_value),
        "costBasis": _dec_str(line.cost_basis),
        "pnl": _dec_str(line.pnl),
        "pnlPercent": _dec_str(line.pnl_percent),
        "missingPrice": line.missing_price,
        "displayCurrency": line.display_currency,
        "marketValueDisplay": _dec_str(line.market_value_display),
        "costBasisDisplay": _dec_str(line.cost_basis_display),
        "pnlDisplay": _dec_str(line.pnl_display),
        "allocation": _dec_str(line.allocation),
    }


def _totals_display(summary: PortfolioSummary) -> Optional[dict[str, Any]]:
    if summary.market_value_display is None:
        return None
    return {
        "currency": summary.display_currency,
        "marketValue": _dec_str(summary.market_value_display),
        "costBasis": _dec_str(summary.cost_basis_display),
        "pnl": _dec_str(summary.pnl_display),
        "pnlPercent": _dec_str(summary.pnl_percent_display),
    }


def portfolio_view_to_response(view: PortfolioView) -> dict[str, Any]:
    """Serialize PortfolioView to camelCase API DTO (Decimals as strings)."""
    summary = view.summary
    fx_status = summary.fx_status or "missing"
    rates = {
        k: format(Decimal(v), "f") for k, v in (view.fx_rates or {}).items()
    }
    return {
        "lines": [_line_to_dict(ln) for ln in summary.lines],
        "totalsByCurrency": {
            cur: _currency_totals_to_dict(tot)
            for cur, tot in summary.totals_by_currency.items()
        },
        "totalsDisplay": _totals_display(summary),
        "fx": {
            "status": fx_status,
            "asOf": _iso(summary.fx_as_of),
            "rates": rates,
        },
        "asOf": _iso(view.as_of),
        "displayCurrency": summary.display_currency,
    }


@router.get("/api/portfolio")
def get_portfolio(
    displayCurrency: Optional[str] = Query(default=None),  # noqa: N803 — API camelCase
    assetType: Optional[str] = Query(default=None),  # noqa: N803
    user: UserProfile = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
) -> dict[str, Any]:
    """Aggregate holdings + cache-first prices; optional stored FX conversion."""
    try:
        view = svc.get_portfolio(
            user.user_id,
            display_currency=displayCurrency,
            preferred_currency=user.preferred_currency,
            asset_type=assetType,
            force_refresh=False,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=getattr(exc, "detail", None) or str(exc),
        ) from exc
    return portfolio_view_to_response(view)


@router.post("/api/portfolio/refresh")
def refresh_portfolio(
    displayCurrency: Optional[str] = Query(default=None),  # noqa: N803
    assetType: Optional[str] = Query(default=None),  # noqa: N803
    user: UserProfile = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
) -> dict[str, Any]:
    """Force market fetch for user's holding symbols; return same portfolio shape.

    Does **not** call any FX HTTP provider — only MarketService with force=True.
    """
    try:
        view = svc.get_portfolio(
            user.user_id,
            display_currency=displayCurrency,
            preferred_currency=user.preferred_currency,
            asset_type=assetType,
            force_refresh=True,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=getattr(exc, "detail", None) or str(exc),
        ) from exc
    return portfolio_view_to_response(view)
