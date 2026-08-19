"""Unit tests for FX rate lookup (including USD-base triangulation)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.domain.fx_math import apply_fx, get_rate
from app.domain.models import FxRates, PortfolioLine, PortfolioSummary


def _fx(rates: dict[str, Decimal], *, base: str = "USD", status: str = "fresh") -> FxRates:
    return FxRates(
        base=base,
        rates=rates,
        status=status,  # type: ignore[arg-type]
        as_of=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


def test_get_rate_same_currency() -> None:
    fx = _fx({"USD_VND": Decimal("25000")})
    assert get_rate(fx, "VND", "vnd") == Decimal("1")


def test_get_rate_direct_and_inverse() -> None:
    fx = _fx({"USD_VND": Decimal("25000")})
    assert get_rate(fx, "USD", "VND") == Decimal("25000")
    assert get_rate(fx, "VND", "USD") == Decimal("1") / Decimal("25000")


def test_get_rate_triangulates_via_usd_base() -> None:
    """Admin store typically has USD_* legs only — VND↔EUR must chain."""
    fx = _fx({"USD_VND": Decimal("25000"), "USD_EUR": Decimal("0.92")})
    vnd_eur = get_rate(fx, "VND", "EUR")
    assert vnd_eur is not None
    assert vnd_eur == (Decimal("1") / Decimal("25000")) * Decimal("0.92")

    eur_vnd = get_rate(fx, "EUR", "VND")
    assert eur_vnd is not None
    assert eur_vnd == (Decimal("1") / Decimal("0.92")) * Decimal("25000")


def test_get_rate_missing_triangulation_leg_returns_none() -> None:
    fx = _fx({"USD_VND": Decimal("25000")})
    assert get_rate(fx, "VND", "EUR") is None


def test_apply_fx_converts_vnd_holding_to_eur_via_triangulation() -> None:
    fx = _fx({"USD_VND": Decimal("25000"), "USD_EUR": Decimal("0.92")})
    line = PortfolioLine(
        user_id="u1",
        asset_type="stock",
        symbol="VNM",
        qty=Decimal("1"),
        avg_cost=Decimal("25000"),
        currency="VND",
        price=Decimal("25000"),
        market_value=Decimal("25000"),
        cost_basis=Decimal("25000"),
        pnl=Decimal("0"),
        missing_price=False,
    )
    summary = PortfolioSummary(lines=[line], totals_by_currency={})
    out = apply_fx(summary, fx, "EUR")
    assert out.fx_status == "fresh"
    assert out.market_value_display == Decimal("0.92")
    assert out.lines[0].market_value_display == Decimal("0.92")
    assert out.lines[0].display_currency == "EUR"
