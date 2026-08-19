"""Sprint 01: pure portfolio valuation math (no I/O)."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.fx_math import apply_fx, get_rate
from app.domain.models import FxRates, Holding, PriceQuote
from app.domain.portfolio_math import (
    compute_asset_class_totals,
    compute_native_portfolio,
    native_line,
    pnl_percent,
)


def _dt() -> datetime:
    return datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _holding(
    *,
    symbol: str = "BTC",
    asset_type: str = "crypto",
    qty: str = "2",
    avg_cost: str = "10000",
    currency: str = "USD",
    user_id: str = "u1",
) -> Holding:
    return Holding(
        user_id=user_id,
        asset_type=asset_type,  # type: ignore[arg-type]
        symbol=symbol,
        qty=Decimal(qty),
        avg_cost=Decimal(avg_cost),
        currency=currency,
    )


def _quote(
    *,
    symbol: str = "BTC",
    asset_type: str = "crypto",
    price: str = "20000",
    currency: str = "USD",
) -> PriceQuote:
    return PriceQuote(
        asset_type=asset_type,  # type: ignore[arg-type]
        symbol=symbol,
        price=Decimal(price),
        currency=currency,
        as_of=_dt(),
    )


# ---------------------------------------------------------------------------
# 1. Single USD holding math
# ---------------------------------------------------------------------------


def test_native_line_single_usd_holding() -> None:
    """qty=2, price=20000, avg_cost=10000 → mv=40000, cost=20000, pnl=20000."""
    h = _holding(qty="2", avg_cost="10000", currency="USD")
    q = _quote(price="20000", currency="USD")

    line = native_line(h, q)

    assert line.market_value == Decimal("40000")
    assert line.cost_basis == Decimal("20000")
    assert line.pnl == Decimal("20000")
    assert line.currency == "USD"
    assert line.price == Decimal("20000")
    assert line.missing_price is False
    assert line.pnl_percent == Decimal("1")  # 20000/20000


def test_compute_native_portfolio_single_usd() -> None:
    holdings = [_holding(qty="2", avg_cost="10000")]
    quotes = [_quote(price="20000")]

    summary = compute_native_portfolio(holdings, quotes)

    assert len(summary.lines) == 1
    assert summary.lines[0].market_value == Decimal("40000")
    usd = summary.totals_by_currency["USD"]
    assert usd.market_value == Decimal("40000")
    assert usd.cost_basis == Decimal("20000")
    assert usd.pnl == Decimal("20000")


# ---------------------------------------------------------------------------
# 2. Mixed USD + VND native subtotals
# ---------------------------------------------------------------------------


def test_mixed_usd_vnd_native_subtotals() -> None:
    holdings = [
        _holding(symbol="BTC", asset_type="crypto", qty="1", avg_cost="30000", currency="USD"),
        _holding(
            symbol="VNM",
            asset_type="stock",
            qty="100",
            avg_cost="70000",
            currency="VND",
        ),
    ]
    quotes = [
        _quote(symbol="BTC", asset_type="crypto", price="40000", currency="USD"),
        _quote(symbol="VNM", asset_type="stock", price="80000", currency="VND"),
    ]

    summary = compute_native_portfolio(holdings, quotes)

    assert len(summary.lines) == 2
    assert set(summary.totals_by_currency.keys()) == {"USD", "VND"}

    usd = summary.totals_by_currency["USD"]
    assert usd.market_value == Decimal("40000")
    assert usd.cost_basis == Decimal("30000")
    assert usd.pnl == Decimal("10000")

    vnd = summary.totals_by_currency["VND"]
    # 100 * 80000 = 8_000_000; cost 100 * 70000 = 7_000_000
    assert vnd.market_value == Decimal("8000000")
    assert vnd.cost_basis == Decimal("7000000")
    assert vnd.pnl == Decimal("1000000")


# ---------------------------------------------------------------------------
# 5. cost_basis 0 → pnl% is None
# ---------------------------------------------------------------------------


def test_pnl_percent_zero_cost_returns_none() -> None:
    assert pnl_percent(Decimal("100"), Decimal("0")) is None
    assert pnl_percent(Decimal("0"), Decimal("0")) is None


def test_pnl_percent_nonzero_cost() -> None:
    assert pnl_percent(Decimal("50"), Decimal("200")) == Decimal("0.25")
    assert pnl_percent(Decimal("-10"), Decimal("100")) == Decimal("-0.1")


def test_native_line_zero_avg_cost_pnl_percent_none() -> None:
    h = _holding(qty="1", avg_cost="0")
    q = _quote(price="100")
    line = native_line(h, q)
    assert line.cost_basis == Decimal("0")
    assert line.market_value == Decimal("100")
    assert line.pnl == Decimal("100")
    assert line.pnl_percent is None


# ---------------------------------------------------------------------------
# Missing quote policy
# ---------------------------------------------------------------------------


def test_missing_quote_excluded_from_totals_and_flagged() -> None:
    holdings = [
        _holding(symbol="BTC", qty="1", avg_cost="10000", currency="USD"),
        _holding(symbol="ETH", qty="5", avg_cost="2000", currency="USD"),
    ]
    # Only BTC has a quote
    quotes = [_quote(symbol="BTC", price="30000")]

    summary = compute_native_portfolio(holdings, quotes)

    assert len(summary.lines) == 2
    btc = next(ln for ln in summary.lines if ln.symbol == "BTC")
    eth = next(ln for ln in summary.lines if ln.symbol == "ETH")

    assert btc.missing_price is False
    assert btc.market_value == Decimal("30000")

    assert eth.missing_price is True
    assert eth.market_value is None
    assert eth.cost_basis is None
    assert eth.pnl is None

    # Totals only include priced lines
    usd = summary.totals_by_currency["USD"]
    assert usd.market_value == Decimal("30000")
    assert usd.cost_basis == Decimal("10000")


def test_usd_quote_vnd_holding_is_missing_price() -> None:
    """USD price must not be multiplied into a VND bucket."""
    h = _holding(symbol="BTC", qty="1", avg_cost="10000", currency="VND")
    q = _quote(symbol="BTC", price="20000", currency="USD")

    line = native_line(h, q)
    assert line.missing_price is True
    assert line.market_value is None
    assert line.cost_basis is None
    assert line.pnl is None
    assert line.price is None

    summary = compute_native_portfolio([h], [q])
    assert len(summary.lines) == 1
    assert summary.lines[0].missing_price is True
    assert summary.totals_by_currency == {}


def test_currency_mismatch_case_insensitive() -> None:
    h = _holding(symbol="BTC", qty="1", avg_cost="10000", currency="vnd")
    q = _quote(symbol="BTC", price="20000", currency="usd")
    line = native_line(h, q)
    assert line.missing_price is True


# ---------------------------------------------------------------------------
# get_rate
# ---------------------------------------------------------------------------


def test_get_rate_same_currency_is_one() -> None:
    fx = FxRates(base="USD", rates={}, status="fresh", as_of=_dt())
    assert get_rate(fx, "USD", "USD") == Decimal("1")
    assert get_rate(fx, "VND", "VND") == Decimal("1")


def test_get_rate_direct_lookup() -> None:
    fx = FxRates(
        base="USD",
        rates={"USD_VND": Decimal("25000")},
        status="fresh",
        as_of=_dt(),
    )
    assert get_rate(fx, "USD", "VND") == Decimal("25000")


def test_get_rate_inverse_fallback() -> None:
    fx = FxRates(
        base="USD",
        rates={"USD_VND": Decimal("25000")},
        status="fresh",
        as_of=_dt(),
    )
    rate = get_rate(fx, "VND", "USD")
    assert rate is not None
    assert rate == Decimal("1") / Decimal("25000")


def test_get_rate_missing_returns_none() -> None:
    fx = FxRates(base="USD", rates={}, status="missing")
    assert get_rate(fx, "USD", "EUR") is None


# ---------------------------------------------------------------------------
# 3. apply_fx with USD_VND rate → single display total
# ---------------------------------------------------------------------------


def test_apply_fx_with_rate_single_display_total() -> None:
    holdings = [
        _holding(symbol="BTC", asset_type="crypto", qty="1", avg_cost="30000", currency="USD"),
        _holding(
            symbol="VNM",
            asset_type="stock",
            qty="100",
            avg_cost="70000",
            currency="VND",
        ),
    ]
    quotes = [
        _quote(symbol="BTC", asset_type="crypto", price="40000", currency="USD"),
        _quote(symbol="VNM", asset_type="stock", price="80000", currency="VND"),
    ]
    native = compute_native_portfolio(holdings, quotes)

    fx = FxRates(
        base="USD",
        rates={
            "USD_VND": Decimal("25000"),
            "VND_USD": Decimal("0.00004"),
        },
        status="fresh",
        as_of=_dt(),
    )

    display = apply_fx(native, fx, "VND")

    assert display.display_currency == "VND"
    assert display.fx_status == "fresh"
    # BTC: 40000 USD * 25000 = 1_000_000_000 VND
    # VNM: 8_000_000 VND
    # total mv = 1_008_000_000
    assert display.market_value_display == Decimal("1008000000")
    # cost: 30000*25000 + 7000000 = 750_000_000 + 7_000_000 = 757_000_000
    assert display.cost_basis_display == Decimal("757000000")
    assert display.pnl_display == Decimal("251000000")

    for line in display.lines:
        if line.missing_price:
            continue
        assert line.market_value_display is not None
        assert line.display_currency == "VND"


# ---------------------------------------------------------------------------
# 4. missing fx → status missing, native only
# ---------------------------------------------------------------------------


def test_apply_fx_missing_keeps_native_only() -> None:
    holdings = [_holding(qty="1", avg_cost="10000")]
    quotes = [_quote(price="20000")]
    native = compute_native_portfolio(holdings, quotes)

    fx = FxRates(base="USD", rates={}, status="missing")

    result = apply_fx(native, fx, "VND")

    assert result.fx_status == "missing"
    assert result.market_value_display is None
    assert result.cost_basis_display is None
    assert result.pnl_display is None
    # native totals still present
    assert result.totals_by_currency["USD"].market_value == Decimal("20000")
    for line in result.lines:
        assert line.market_value_display is None
        assert line.avg_cost_display is None
        assert line.price_display is None
        assert line.allocation is None


# ---------------------------------------------------------------------------
# 6. allocation sums ~1.0 within display currency
# ---------------------------------------------------------------------------


def test_allocation_sums_to_one_in_display_currency() -> None:
    holdings = [
        _holding(symbol="BTC", asset_type="crypto", qty="1", avg_cost="30000", currency="USD"),
        _holding(
            symbol="ETH",
            asset_type="crypto",
            qty="10",
            avg_cost="2000",
            currency="USD",
        ),
        _holding(
            symbol="VNM",
            asset_type="stock",
            qty="100",
            avg_cost="70000",
            currency="VND",
        ),
    ]
    quotes = [
        _quote(symbol="BTC", asset_type="crypto", price="40000", currency="USD"),
        _quote(symbol="ETH", asset_type="crypto", price="3000", currency="USD"),
        _quote(symbol="VNM", asset_type="stock", price="80000", currency="VND"),
    ]
    native = compute_native_portfolio(holdings, quotes)
    fx = FxRates(
        base="USD",
        rates={"USD_VND": Decimal("25000"), "VND_USD": Decimal("0.00004")},
        status="fresh",
        as_of=_dt(),
    )

    display = apply_fx(native, fx, "VND")

    priced = [ln for ln in display.lines if not ln.missing_price]
    alloc_sum = sum((ln.allocation or Decimal("0")) for ln in priced)
    assert alloc_sum == pytest.approx(Decimal("1"), abs=Decimal("0.000001"))
    assert all(ln.allocation is not None for ln in priced)
    assert all(ln.allocation >= 0 for ln in priced)


def test_stale_quote_marks_line() -> None:
    h = _holding()
    q = PriceQuote(
        asset_type="crypto",
        symbol="BTC",
        price=Decimal("20000"),
        currency="USD",
        as_of=_dt(),
        stale=True,
    )
    line = native_line(h, q)
    assert line.stale is True
    assert line.missing_price is False


def test_asset_class_totals_native_and_display() -> None:
    holdings = [
        _holding(symbol="BTC", asset_type="crypto", qty="1", avg_cost="30000", currency="USD"),
        _holding(
            symbol="VNM",
            asset_type="stock",
            qty="100",
            avg_cost="70000",
            currency="VND",
        ),
    ]
    quotes = [
        _quote(symbol="BTC", asset_type="crypto", price="40000", currency="USD"),
        _quote(symbol="VNM", asset_type="stock", price="80000", currency="VND"),
    ]
    native = compute_native_portfolio(holdings, quotes)
    by_class = compute_asset_class_totals(native)
    assert by_class["crypto"].currency == "USD"
    assert by_class["crypto"].market_value == Decimal("40000")
    assert by_class["stock"].currency == "VND"
    assert by_class["stock"].market_value == Decimal("8000000")

    fx = FxRates(
        base="USD",
        rates={"USD_VND": Decimal("25000"), "VND_USD": Decimal("0.00004")},
        status="fresh",
        as_of=_dt(),
    )
    display = apply_fx(native, fx, "VND")
    converted = compute_asset_class_totals(display)
    assert converted["crypto"].currency == "VND"
    assert converted["crypto"].market_value == Decimal("1000000000")
    assert converted["stock"].market_value == Decimal("8000000")


def test_allocation_zero_total_market_value() -> None:
    """All zero prices → allocation None or 0; no division error."""
    holdings = [_holding(qty="1", avg_cost="0")]
    quotes = [_quote(price="0")]
    native = compute_native_portfolio(holdings, quotes)
    fx = FxRates(
        base="USD",
        rates={"USD_VND": Decimal("25000")},
        status="fresh",
        as_of=_dt(),
    )
    display = apply_fx(native, fx, "USD")
    assert display.market_value_display == Decimal("0")
    for line in display.lines:
        assert line.allocation is None or line.allocation == Decimal("0")
