"""Native portfolio valuation (pure functions, Decimal money).

Formulas (PRD §8.5):
  market_value = qty * price
  cost_basis   = qty * avg_cost
  pnl          = market_value - cost_basis
  pnl%         = pnl / cost_basis  (None if cost_basis == 0)

Missing quote policy: line is kept with ``missing_price=True`` and excluded
from currency totals (market_value/cost_basis/pnl remain None).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Optional

from app.domain.models import (
    CurrencyTotals,
    Holding,
    PortfolioLine,
    PortfolioSummary,
    PriceQuote,
)


def pnl_percent(pnl: Decimal, cost: Decimal) -> Optional[Decimal]:
    """Return pnl / cost, or ``None`` when cost is zero (undefined %)."""
    if cost == 0:
        return None
    return pnl / cost


def native_line(holding: Holding, quote: PriceQuote) -> PortfolioLine:
    """Value a single holding against a matching quote (native currency).

    Assumes quote is for the same asset; caller is responsible for matching.
    Uses holding.currency as line currency (quote currency should match).
    """
    market_value = holding.qty * quote.price
    cost_basis = holding.qty * holding.avg_cost
    pnl = market_value - cost_basis
    return PortfolioLine(
        user_id=holding.user_id,
        asset_type=holding.asset_type,
        symbol=holding.symbol,
        qty=holding.qty,
        avg_cost=holding.avg_cost,
        currency=holding.currency,
        asset_id=holding.asset_id,
        note=holding.note,
        price=quote.price,
        market_value=market_value,
        cost_basis=cost_basis,
        pnl=pnl,
        pnl_percent=pnl_percent(pnl, cost_basis),
        missing_price=False,
    )


# Alias preferred by some call sites / components checklist
line_native = native_line


def _quote_key(asset_type: str, symbol: str) -> tuple[str, str]:
    return (asset_type, symbol.upper())


def _missing_line(holding: Holding) -> PortfolioLine:
    return PortfolioLine(
        user_id=holding.user_id,
        asset_type=holding.asset_type,
        symbol=holding.symbol,
        qty=holding.qty,
        avg_cost=holding.avg_cost,
        currency=holding.currency,
        asset_id=holding.asset_id,
        note=holding.note,
        price=None,
        market_value=None,
        cost_basis=None,
        pnl=None,
        pnl_percent=None,
        missing_price=True,
    )


def compute_native_portfolio(
    holdings: Iterable[Holding],
    quotes: Iterable[PriceQuote],
) -> PortfolioSummary:
    """Compute per-line native valuation and totals grouped by currency.

    Lines without a matching quote (asset_type + symbol) are flagged
    ``missing_price`` and excluded from ``totals_by_currency``.
    """
    quote_map: dict[tuple[str, str], PriceQuote] = {
        _quote_key(q.asset_type, q.symbol): q for q in quotes
    }

    lines: list[PortfolioLine] = []
    # currency -> running (mv, cost)
    acc: dict[str, list[Decimal]] = {}

    for holding in holdings:
        key = _quote_key(holding.asset_type, holding.symbol)
        quote = quote_map.get(key)
        if quote is None:
            lines.append(_missing_line(holding))
            continue

        line = native_line(holding, quote)
        lines.append(line)

        assert line.market_value is not None and line.cost_basis is not None
        bucket = acc.setdefault(
            holding.currency,
            [Decimal("0"), Decimal("0")],
        )
        bucket[0] += line.market_value
        bucket[1] += line.cost_basis

    totals: dict[str, CurrencyTotals] = {}
    for currency, (mv, cost) in acc.items():
        totals[currency] = CurrencyTotals(
            currency=currency,
            market_value=mv,
            cost_basis=cost,
            pnl=mv - cost,
        )

    return PortfolioSummary(lines=lines, totals_by_currency=totals)
