"""Portfolio CSV export service — pure, FX-aware, stdlib csv only.

Uses PortfolioView (already FX-converted) so no live FX call. Handles
2-decimal formatting, injection mitigation, UTF-8 without BOM, CRLF lines.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.services.portfolio_service import PortfolioView

CSV_HEADER = [
    "symbol",
    "assetType",
    "assetId",
    "qty",
    "avgCost",
    "currency",
    "avgCostDisplay",
    "price",
    "priceDisplay",
    "marketValue",
    "costBasis",
    "marketValueDisplay",
    "costBasisDisplay",
    "pnl",
    "pnlDisplay",
    "pnlPercent",
    "allocation",
    "currency_display",
    "fxRateUsed",
    "fxStatus",
    "asOf",
]

_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_FULLWIDTH_PREFIXES = ("＝", "＋", "－", "＠")


def _is_injection(cell: str) -> bool:
    stripped = cell.lstrip()
    if not stripped:
        return False
    if stripped.startswith(_INJECTION_PREFIXES) or stripped.startswith(_FULLWIDTH_PREFIXES):
        return True
    return False


def _sanitize_csv_value(value: Optional[str]) -> str:
    """Mitigate CSV injection at export time only (OWASP)."""
    if value is None:
        return ""
    text = str(value)
    if _is_injection(text):
        # Excel-resistant: prefix single quote inside quoted field; csv.writer will quote
        return "'" + text
    return text


def _dec_2dp(value: Optional[Decimal]) -> str:
    if value is None:
        return ""
    # Quantize to 2dp for display columns; keep monetary precision consistent with BL-012
    # Use format with 2dp for display; for native we keep full precision but tests expect formatted
    try:
        # Normalize: if already quantized, format; else quantize
        d = Decimal(value)
        # For display columns we want exactly 2dp
        # Use quantize only for display; native keeps original "f" but we still format 2dp per SA for CSV readability
        # Keep as plain string without exponent
        return format(d, "f")
    except (InvalidOperation, ValueError):
        return str(value)


def _dec_display_2dp(value: Optional[Decimal]) -> str:
    if value is None:
        return ""
    try:
        d = Decimal(value).quantize(Decimal("0.01"))
        return format(d, "f")
    except (InvalidOperation, ValueError):
        return format(Decimal(str(value)), "f") if value is not None else ""


def _dec_percent(value: Optional[Decimal]) -> str:
    if value is None:
        return ""
    try:
        # Keep as decimal string, no % sign
        return format(Decimal(value), "f")
    except (InvalidOperation, ValueError):
        return str(value)


def _iso(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def csv_filename(now: Optional[datetime] = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return f"openportfo-portfolio-{dt.strftime('%Y%m%d')}.csv"


def _fx_rate_for_line(line, fx_rates: dict[str, Decimal], display_currency: Optional[str]) -> str:
    if not display_currency or not line.currency:
        return ""
    src = line.currency.upper()
    dst = display_currency.upper()
    if src == dst:
        return "1"
    key = f"{src}_{dst}"
    inv_key = f"{dst}_{src}"
    if key in fx_rates:
        return _dec_2dp(fx_rates[key])
    if inv_key in fx_rates and fx_rates[inv_key] != 0:
        try:
            return _dec_2dp(Decimal("1") / Decimal(fx_rates[inv_key]))
        except Exception:
            return ""
    # Fallback: derive from marketValue ratio if available
    if line.market_value and line.market_value_display and line.market_value != 0:
        try:
            return _dec_2dp(Decimal(line.market_value_display) / Decimal(line.market_value))
        except Exception:
            return ""
    return ""


class ExportService:
    """Thin service wrapper for CSV rendering (keeps deps.py port-friendly)."""

    def render(self, view: PortfolioView) -> str:
        return render_portfolio_csv(view)

    def render_portfolio_csv(self, view: PortfolioView) -> str:
        return render_portfolio_csv(view)


def render_portfolio_csv(view: PortfolioView) -> str:
    """Render PortfolioView to CSV string (pure, no I/O)."""
    output = io.StringIO()
    writer = csv.writer(
        output,
        dialect="excel",
        lineterminator="\r\n",
        quoting=csv.QUOTE_MINIMAL,
        doublequote=True,
        quotechar='"',
    )
    writer.writerow(CSV_HEADER)
    fx_status = view.summary.fx_status or "missing"
    as_of_str = _iso(view.as_of)
    # Sort by assetType, symbol for determinism
    lines_sorted = sorted(view.summary.lines, key=lambda ln: (ln.asset_type, ln.symbol))
    for line in lines_sorted:
        # Allocation only when display totals exist
        alloc = _dec_2dp(line.allocation) if line.allocation is not None else ""
        # For display columns, we output 2dp when present else blank (missing FX)
        # Sanitize user-controlled text only (symbol/assetType/assetId). Numeric
        # columns are Decimal-formatted and must keep a leading minus.
        row = [
            _sanitize_csv_value(line.symbol),
            _sanitize_csv_value(line.asset_type),
            _sanitize_csv_value(line.asset_id or ""),
            _dec_2dp(line.qty),
            _dec_2dp(line.avg_cost),
            line.currency or "",
            _dec_display_2dp(line.avg_cost_display),
            _dec_2dp(line.price),
            _dec_display_2dp(line.price_display),
            _dec_2dp(line.market_value),
            _dec_2dp(line.cost_basis),
            _dec_display_2dp(line.market_value_display),
            _dec_display_2dp(line.cost_basis_display),
            _dec_2dp(line.pnl),
            _dec_display_2dp(line.pnl_display),
            _dec_percent(line.pnl_percent),
            alloc,
            line.display_currency or view.summary.display_currency or "",
            _fx_rate_for_line(line, view.fx_rates, view.summary.display_currency),
            fx_status,
            as_of_str,
        ]
        writer.writerow(row)
    return output.getvalue()
