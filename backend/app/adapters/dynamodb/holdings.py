"""DynamoDB HoldingsRepo.

Table: openportfo-holdings
PK: userId  SK: HOLD#{assetType}#{symbol}
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from boto3.dynamodb.conditions import Key

from app.adapters.dynamodb.base import (
    dt_to_iso,
    get_table,
    iso_to_dt,
    sanitize_for_dynamo,
    to_decimal,
    utc_now,
)
from app.ports.holdings import (
    DuplicateHoldingError,
    HoldingNotFoundError,
    HoldingRecord,
)


def holding_sk(asset_type: str, symbol: str) -> str:
    return f"HOLD#{asset_type}#{symbol.upper()}"


def holding_to_item(holding: HoldingRecord) -> dict[str, Any]:
    return sanitize_for_dynamo(
        {
            "userId": holding.user_id,
            "sk": holding_sk(holding.asset_type, holding.symbol),
            "assetType": holding.asset_type,
            "symbol": holding.symbol.upper(),
            "qty": to_decimal(holding.qty),
            "avgCost": to_decimal(holding.avg_cost),
            "currency": holding.currency,
            "assetId": holding.asset_id,
            "note": holding.note,
            "createdAt": dt_to_iso(holding.created_at),
            "updatedAt": dt_to_iso(holding.updated_at),
        }
    )


def item_to_holding(item: dict[str, Any]) -> HoldingRecord:
    return HoldingRecord(
        user_id=str(item["userId"]),
        asset_type=item["assetType"],  # type: ignore[arg-type]
        symbol=str(item["symbol"]).upper(),
        qty=to_decimal(item["qty"]),
        avg_cost=to_decimal(item["avgCost"]),
        currency=str(item["currency"]),
        asset_id=item.get("assetId"),
        note=item.get("note"),
        created_at=iso_to_dt(item.get("createdAt")) or utc_now(),
        updated_at=iso_to_dt(item.get("updatedAt")) or utc_now(),
    )


class DynamoHoldingsRepo:
    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table=None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)

    def list(self, user_id: str) -> list[HoldingRecord]:
        resp = self._table.query(
            KeyConditionExpression=Key("userId").eq(user_id)
            & Key("sk").begins_with("HOLD#"),
        )
        items = [item_to_holding(i) for i in resp.get("Items") or []]
        while resp.get("LastEvaluatedKey"):
            resp = self._table.query(
                KeyConditionExpression=Key("userId").eq(user_id)
                & Key("sk").begins_with("HOLD#"),
                ExclusiveStartKey=resp["LastEvaluatedKey"],
            )
            items.extend(item_to_holding(i) for i in resp.get("Items") or [])
        return sorted(items, key=lambda h: (h.asset_type, h.symbol))

    def list_all_users(self) -> list[str]:
        """Job helper: distinct user ids with holdings (scan, demo-scale)."""
        user_ids: set[str] = set()
        resp = self._table.scan(ProjectionExpression="userId")
        for item in resp.get("Items") or []:
            if "userId" in item:
                user_ids.add(str(item["userId"]))
        while resp.get("LastEvaluatedKey"):
            resp = self._table.scan(
                ProjectionExpression="userId",
                ExclusiveStartKey=resp["LastEvaluatedKey"],
            )
            for item in resp.get("Items") or []:
                if "userId" in item:
                    user_ids.add(str(item["userId"]))
        return sorted(user_ids)

    def get(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
    ) -> Optional[HoldingRecord]:
        resp = self._table.get_item(
            Key={"userId": user_id, "sk": holding_sk(asset_type, symbol)},
        )
        item = resp.get("Item")
        return item_to_holding(item) if item else None

    def create(self, holding: HoldingRecord) -> HoldingRecord:
        sk = holding_sk(holding.asset_type, holding.symbol)
        existing = self._table.get_item(Key={"userId": holding.user_id, "sk": sk}).get("Item")
        if existing:
            raise DuplicateHoldingError(
                f"Holding already exists: {holding.asset_type}/{holding.symbol}"
            )
        stored = HoldingRecord(
            user_id=holding.user_id,
            asset_type=holding.asset_type,
            symbol=holding.symbol.upper(),
            qty=holding.qty,
            avg_cost=holding.avg_cost,
            currency=holding.currency,
            asset_id=holding.asset_id,
            note=holding.note,
            created_at=holding.created_at,
            updated_at=holding.updated_at,
        )
        self._table.put_item(Item=holding_to_item(stored))
        return stored

    def update(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
        *,
        qty: Optional[Decimal] = None,
        avg_cost: Optional[Decimal] = None,
        currency: Optional[str] = None,
        asset_id: Optional[str] = None,
        note: Optional[str] = None,
        clear_note: bool = False,
    ) -> HoldingRecord:
        item = self.get(user_id, asset_type, symbol)
        if item is None:
            raise HoldingNotFoundError(f"Holding not found: {asset_type}/{symbol}")
        if qty is not None:
            item.qty = qty
        if avg_cost is not None:
            item.avg_cost = avg_cost
        if currency is not None:
            item.currency = currency
        if asset_id is not None:
            item.asset_id = asset_id
        if clear_note:
            item.note = None
        elif note is not None:
            item.note = note
        item.updated_at = utc_now()
        self._table.put_item(Item=holding_to_item(item))
        return item

    def delete(self, user_id: str, asset_type: str, symbol: str) -> None:
        sk = holding_sk(asset_type, symbol)
        existing = self._table.get_item(Key={"userId": user_id, "sk": sk}).get("Item")
        if not existing:
            raise HoldingNotFoundError(f"Holding not found: {asset_type}/{symbol}")
        self._table.delete_item(Key={"userId": user_id, "sk": sk})


__all__ = [
    "DynamoHoldingsRepo",
    "holding_sk",
    "holding_to_item",
    "item_to_holding",
]
