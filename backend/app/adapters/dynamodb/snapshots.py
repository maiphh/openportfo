"""DynamoDB SnapshotRepo.

Table: openportfo-snapshots
PK: userId  SK: SNAP#YYYY-MM-DD
"""

from __future__ import annotations

from typing import Any, Optional

from app.adapters.dynamodb.base import (
    deep_from_dynamo,
    dt_to_iso,
    get_table,
    iso_to_dt,
    sanitize_for_dynamo,
    utc_now,
)
from app.ports.snapshots import SnapshotRecord


def snapshot_sk(date: str) -> str:
    return f"SNAP#{date}"


def snapshot_to_item(record: SnapshotRecord) -> dict[str, Any]:
    return sanitize_for_dynamo(
        {
            "userId": record.user_id,
            "sk": snapshot_sk(record.date),
            "date": record.date,
            "payload": record.payload or {},
            "createdAt": dt_to_iso(record.created_at or utc_now()),
        }
    )


def item_to_snapshot(item: dict[str, Any]) -> SnapshotRecord:
    payload = item.get("payload") or {}
    if isinstance(payload, dict):
        payload = deep_from_dynamo(payload)
    return SnapshotRecord(
        user_id=str(item["userId"]),
        date=str(item.get("date") or str(item.get("sk", "")).replace("SNAP#", "")),
        payload=payload if isinstance(payload, dict) else {},
        created_at=iso_to_dt(item.get("createdAt")),
    )


class DynamoSnapshotRepo:
    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table=None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)

    def put(self, record: SnapshotRecord) -> None:
        self._table.put_item(Item=snapshot_to_item(record))

    def get(self, user_id: str, date: str) -> Optional[SnapshotRecord]:
        resp = self._table.get_item(Key={"userId": user_id, "sk": snapshot_sk(date)})
        item = resp.get("Item")
        return item_to_snapshot(item) if item else None


__all__ = [
    "DynamoSnapshotRepo",
    "snapshot_sk",
    "snapshot_to_item",
    "item_to_snapshot",
]
