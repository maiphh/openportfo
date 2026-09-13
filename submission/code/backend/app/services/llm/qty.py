"""Derive holding qty + avg cost from qty / price / notional amount."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional


class QtyError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def parse_decimal(value: object, field_name: str) -> Decimal:
    if value is None or value == "":
        raise QtyError(f"{field_name} is required")
    try:
        if isinstance(value, Decimal):
            d = value
        elif isinstance(value, bool):
            raise QtyError(f"{field_name} must be a number")
        elif isinstance(value, (int, float, str)):
            d = Decimal(str(value).strip().replace(",", ""))
        else:
            raise QtyError(f"{field_name} must be a number")
    except (InvalidOperation, ValueError) as exc:
        raise QtyError(f"{field_name} must be a valid number") from exc
    if not d.is_finite():
        raise QtyError(f"{field_name} must be a finite number")
    return d


def optional_decimal(value: object, field_name: str) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    return parse_decimal(value, field_name)


def compute_qty_and_avg_cost(
    *,
    qty: object = None,
    avg_cost: object = None,
    price: object = None,
    amount: object = None,
    market_price: object = None,
) -> tuple[Decimal, Decimal]:
    """Return (qty, avg_cost).

    - qty + (avgCost|price|market) → use qty, unit price as avg cost
    - amount + unit price → qty = amount / price (e.g. 10 USD at 50000 → 0.0002)
    """
    qty_d = optional_decimal(qty, "qty")
    avg_d = optional_decimal(avg_cost, "avgCost")
    price_d = optional_decimal(price, "price")
    amount_d = optional_decimal(amount, "amount")
    if qty_d is not None and amount_d is not None:
        raise QtyError("provide qty or amount, not both")
    market_d = optional_decimal(market_price, "marketPrice") if market_price not in (None, "") else None

    unit = avg_d if avg_d is not None else price_d if price_d is not None else market_d
    if unit is not None and unit < 0:
        raise QtyError("price must be greater than or equal to 0")

    if qty_d is not None:
        if qty_d <= 0:
            raise QtyError("qty must be greater than 0")
        if unit is None:
            raise QtyError("price or avgCost is required (or a market quote must be available)")
        return qty_d, unit

    if amount_d is not None:
        if amount_d <= 0:
            raise QtyError("amount must be greater than 0")
        if unit is None or unit == 0:
            raise QtyError("cannot derive qty from amount without a non-zero price")
        return amount_d / unit, unit

    raise QtyError("provide qty or amount")


def weighted_avg_cost(
    old_qty: Decimal,
    old_avg: Decimal,
    add_qty: Decimal,
    add_avg: Decimal,
) -> tuple[Decimal, Decimal]:
    new_qty = old_qty + add_qty
    if new_qty <= 0:
        raise QtyError("resulting qty must be greater than 0")
    new_avg = (old_qty * old_avg + add_qty * add_avg) / new_qty
    return new_qty, new_avg


__all__ = [
    "QtyError",
    "parse_decimal",
    "optional_decimal",
    "compute_qty_and_avg_cost",
    "weighted_avg_cost",
]
