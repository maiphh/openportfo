"""DynamoDB WatchlistRepo.

Table: openportfo-watchlist
PK: userId  SK: WATCH#{assetType}#{symbol}
"""

from __future__ import annotations

from typing import Any, Optional

from boto3.dynamodb.conditions import Key

from app.adapters.dynamodb.base import (
    dt_to_iso,
    get_table,
    iso_to_dt,
    sanitize_for_dynamo,
    utc_now,
)
from app.ports.watchlist import (
    DuplicateWatchlistError,
    WatchlistItem,
    WatchlistNotFoundError,
)


def watch_sk(asset_type: str, symbol: str) -> str:
    return f"WATCH#{asset_type}#{symbol.upper()}"


def watch_to_item(item: WatchlistItem) -> dict[str, Any]:
    return sanitize_for_dynamo(
        {
            "userId": item.user_id,
            "sk": watch_sk(item.asset_type, item.symbol),
            "assetType": item.asset_type,
            "symbol": item.symbol.upper(),
            "assetId": item.asset_id,
            "addedAt": dt_to_iso(item.added_at),
        }
    )


def item_to_watch(item: dict[str, Any]) -> WatchlistItem:
    return WatchlistItem(
        user_id=str(item["userId"]),
        asset_type=item["assetType"],  # type: ignore[arg-type]
        symbol=str(item["symbol"]).upper(),
        asset_id=item.get("assetId"),
        added_at=iso_to_dt(item.get("addedAt")) or utc_now(),
    )


class DynamoWatchlistRepo:
    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table=None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)

    def list(self, user_id: str) -> list[WatchlistItem]:
        resp = self._table.query(
            KeyConditionExpression=Key("userId").eq(user_id)
            & Key("sk").begins_with("WATCH#"),
        )
        items = [item_to_watch(i) for i in resp.get("Items") or []]
        while resp.get("LastEvaluatedKey"):
            resp = self._table.query(
                KeyConditionExpression=Key("userId").eq(user_id)
                & Key("sk").begins_with("WATCH#"),
                ExclusiveStartKey=resp["LastEvaluatedKey"],
            )
            items.extend(item_to_watch(i) for i in resp.get("Items") or [])
        return sorted(items, key=lambda w: (w.asset_type, w.symbol))

    def get(
        self,
        user_id: str,
        asset_type: str,
        symbol: str,
    ) -> Optional[WatchlistItem]:
        resp = self._table.get_item(
            Key={"userId": user_id, "sk": watch_sk(asset_type, symbol)},
        )
        item = resp.get("Item")
        return item_to_watch(item) if item else None

    def add(self, item: WatchlistItem) -> WatchlistItem:
        sk = watch_sk(item.asset_type, item.symbol)
        existing = self._table.get_item(Key={"userId": item.user_id, "sk": sk}).get("Item")
        if existing:
            raise DuplicateWatchlistError(
                f"Watchlist item already exists: {item.asset_type}/{item.symbol}"
            )
        stored = WatchlistItem(
            user_id=item.user_id,
            asset_type=item.asset_type,
            symbol=item.symbol.upper(),
            asset_id=item.asset_id,
            added_at=item.added_at,
        )
        self._table.put_item(Item=watch_to_item(stored))
        return stored

    def remove(self, user_id: str, asset_type: str, symbol: str) -> None:
        sk = watch_sk(asset_type, symbol)
        existing = self._table.get_item(Key={"userId": user_id, "sk": sk}).get("Item")
        if not existing:
            raise WatchlistNotFoundError(f"Watchlist item not found: {asset_type}/{symbol}")
        self._table.delete_item(Key={"userId": user_id, "sk": sk})


__all__ = [
    "DynamoWatchlistRepo",
    "watch_sk",
    "watch_to_item",
    "item_to_watch",
]
