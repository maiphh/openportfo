"""Qty / notional conversion for chatbot add-holding."""

from decimal import Decimal

import pytest

from app.services.llm.qty import QtyError, compute_qty_and_avg_cost, weighted_avg_cost


def test_amount_and_price_to_qty() -> None:
    qty, avg = compute_qty_and_avg_cost(amount="10", price="50000")
    assert qty == Decimal("10") / Decimal("50000")
    assert avg == Decimal("50000")


def test_qty_and_price() -> None:
    qty, avg = compute_qty_and_avg_cost(qty="0.5", price=40000)
    assert qty == Decimal("0.5")
    assert avg == Decimal("40000")


def test_qty_uses_market_price_when_no_cost() -> None:
    qty, avg = compute_qty_and_avg_cost(qty="2", market_price="100")
    assert qty == Decimal("2")
    assert avg == Decimal("100")


def test_avg_cost_wins_over_price() -> None:
    qty, avg = compute_qty_and_avg_cost(qty="1", avg_cost="10", price="99")
    assert avg == Decimal("10")


def test_qty_and_amount_together_rejected() -> None:
    with pytest.raises(QtyError, match="not both"):
        compute_qty_and_avg_cost(qty="1", amount="10", price="50000")


def test_missing_inputs_raise() -> None:
    with pytest.raises(QtyError):
        compute_qty_and_avg_cost()
    with pytest.raises(QtyError):
        compute_qty_and_avg_cost(amount="10")
    with pytest.raises(QtyError):
        compute_qty_and_avg_cost(qty="1")


def test_weighted_average() -> None:
    qty, avg = weighted_avg_cost(Decimal("1"), Decimal("100"), Decimal("1"), Decimal("200"))
    assert qty == Decimal("2")
    assert avg == Decimal("150")
