"""FX rate lookup and portfolio conversion (pure; rates are inputs only).

Rate key convention: flat ``"{SRC}_{DST}"`` e.g. ``USD_VND``.
``get_rate`` returns 1 when src == dst; looks up direct key; falls back to
inverse of ``DST_SRC`` when present.

If FX status is ``missing`` or required rates cannot convert all priced lines,
display totals stay None and ``fx_status`` is ``missing`` (native kept).
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Optional

from app.domain.models import FxRates, PortfolioLine, PortfolioSummary
from app.domain.portfolio_math import pnl_percent


def rate_key(src: str, dst: str) -> str:
    """Canonical flat key for a currency pair."""
    return f"{src.upper()}_{dst.upper()}"


def get_rate(fx: FxRates, src: str, dst: str) -> Optional[Decimal]:
    """Resolve conversion multiplier: ``amount_dst = amount_src * rate``.

    - Same currency → ``Decimal("1")``
    - Direct ``SRC_DST`` key
    - Inverse of ``DST_SRC`` if only that exists
    - Otherwise ``None``
    """
    src_u = src.upper()
    dst_u = dst.upper()
    if src_u == dst_u:
        return Decimal("1")

    direct = fx.rates.get(rate_key(src_u, dst_u))
    if direct is not None:
        return Decimal(direct)

    inverse = fx.rates.get(rate_key(dst_u, src_u))
    if inverse is not None and inverse != 0:
        return Decimal("1") / Decimal(inverse)

    return None


def _clone_line(line: PortfolioLine) -> PortfolioLine:
    return deepcopy(line)


def apply_fx(
    summary: PortfolioSummary,
    fx: FxRates,
    display_currency: str,
) -> PortfolioSummary:
    """Convert native portfolio lines into ``display_currency``.

    Pure: does not fetch rates. On missing FX (status ``missing`` empty rates,
    or any priced line cannot convert), returns native-only summary with
    ``fx_status="missing"`` and no display totals/allocations.
    """
    display = display_currency.upper()
    result = PortfolioSummary(
        lines=[_clone_line(ln) for ln in summary.lines],
        totals_by_currency=dict(summary.totals_by_currency),
        display_currency=display,
        fx_status=fx.status,
        fx_as_of=fx.as_of,
        fx_base=fx.base,
    )

    if fx.status == "missing" or not fx.rates:
        result.fx_status = "missing"
        return result

    # Resolve rates per native currency among priced lines
    currencies_needed = {
        ln.currency.upper()
        for ln in result.lines
        if not ln.missing_price and ln.market_value is not None
    }
    rates: dict[str, Decimal] = {}
    for cur in currencies_needed:
        r = get_rate(fx, cur, display)
        if r is None:
            result.fx_status = "missing"
            return result
        rates[cur] = r

    total_mv = Decimal("0")
    total_cost = Decimal("0")

    for line in result.lines:
        if line.missing_price or line.market_value is None or line.cost_basis is None:
            continue
        rate = rates[line.currency.upper()]
        mv_d = line.market_value * rate
        cost_d = line.cost_basis * rate
        pnl_d = mv_d - cost_d
        line.display_currency = display
        line.market_value_display = mv_d
        line.cost_basis_display = cost_d
        line.pnl_display = pnl_d
        total_mv += mv_d
        total_cost += cost_d

    result.market_value_display = total_mv
    result.cost_basis_display = total_cost
    result.pnl_display = total_mv - total_cost
    result.pnl_percent_display = pnl_percent(result.pnl_display, total_cost)

    # Allocation within display currency (sums ≈ 1.0 when total_mv > 0)
    if total_mv == 0:
        for line in result.lines:
            if line.market_value_display is not None:
                line.allocation = None
    else:
        for line in result.lines:
            if line.market_value_display is not None:
                line.allocation = line.market_value_display / total_mv

    return result
