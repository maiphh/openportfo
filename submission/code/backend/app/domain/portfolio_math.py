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


def _currency_mismatch(holding: Holding, quote: PriceQuote) -> bool:
    """True when both sides have a currency and they differ (case-insensitive)."""
    qc = (quote.currency or "").strip()
    hc = (holding.currency or "").strip()
    if not qc or not hc:
        return False
    return qc.upper() != hc.upper()


def native_line(holding: Holding, quote: PriceQuote) -> PortfolioLine:
    """Value a single holding against a matching quote (native currency).

    Assumes quote is for the same asset; caller is responsible for matching.
    Uses holding.currency as line currency. If quote.currency differs,
    treat as missing price (do not mix e.g. USD into a VND bucket).
    """
    if _currency_mismatch(holding, quote):
        return _missing_line(holding)

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
        stale=bool(quote.stale),
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
        stale=False,
    )


def compute_native_portfolio(
    holdings: Iterable[Holding],
    quotes: Iterable[PriceQuote],
) -> PortfolioSummary:
    """Compute per-line native valuation and totals grouped by currency.

    Lines without a matching quote (asset_type + symbol), or with a
    quote/holding currency mismatch, are flagged ``missing_price`` and
    excluded from ``totals_by_currency``.
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
        if line.missing_price:
            continue

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


def compute_asset_class_totals(summary: PortfolioSummary) -> dict[str, CurrencyTotals]:
    """Roll up priced lines by ``crypto`` / ``stock``.

    Uses converted display amounts when FX succeeded; otherwise native amounts
    only when every priced line in that class shares one currency.
    """
    use_display = any(ln.market_value_display is not None for ln in summary.lines)
    out: dict[str, CurrencyTotals] = {}
    for asset_type in ("crypto", "stock"):
        priced = [
            ln
            for ln in summary.lines
            if ln.asset_type == asset_type and not ln.missing_price
        ]
        if not priced:
            continue
        if use_display:
            valued = [ln for ln in priced if ln.market_value_display is not None]
            if not valued:
                continue
            mv = sum((ln.market_value_display or Decimal("0")) for ln in valued)
            cost = sum((ln.cost_basis_display or Decimal("0")) for ln in valued)
            currency = (summary.display_currency or "").upper() or valued[0].currency
        else:
            currencies = {(ln.currency or "").upper() for ln in priced}
            if len(currencies) != 1:
                continue
            mv = sum((ln.market_value or Decimal("0")) for ln in priced)
            cost = sum((ln.cost_basis or Decimal("0")) for ln in priced)
            currency = next(iter(currencies))
        out[asset_type] = CurrencyTotals(
            currency=currency,
            market_value=mv,
            cost_basis=cost,
            pnl=mv - cost,
        )
    return out
