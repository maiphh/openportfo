"""DynamoDB RssSourcesRepo.

Table: openportfo-rss
PK: RSS  SK: sourceId
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from boto3.dynamodb.conditions import Key

from app.adapters.dynamodb.base import get_table, sanitize_for_dynamo
from app.adapters.rss.fetcher import assert_public_http_url
from app.ports.admin import AdminNotFoundError, AdminValidationError, RssSource

RSS_PK = "RSS"


def rss_to_item(source: RssSource) -> dict[str, Any]:
    return sanitize_for_dynamo(
        {
            "pk": RSS_PK,
            "sk": source.source_id,
            "sourceId": source.source_id,
            "name": source.name,
            "url": source.url,
            "enabled": bool(source.enabled),
        }
    )


def item_to_rss(item: dict[str, Any]) -> RssSource:
    return RssSource(
        source_id=str(item.get("sourceId") or item.get("sk")),
        name=str(item.get("name") or ""),
        url=str(item.get("url") or ""),
        enabled=bool(item.get("enabled", True)),
    )


def _validate_url(url: str) -> None:
    try:
        assert_public_http_url(url)
    except ValueError as exc:
        raise AdminValidationError(str(exc) or "URL host is not allowed") from exc


class DynamoRssSourcesRepo:
    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table=None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)

    def list(self) -> list[RssSource]:
        resp = self._table.query(KeyConditionExpression=Key("pk").eq(RSS_PK))
        items = [item_to_rss(i) for i in resp.get("Items") or []]
        while resp.get("LastEvaluatedKey"):
            resp = self._table.query(
                KeyConditionExpression=Key("pk").eq(RSS_PK),
                ExclusiveStartKey=resp["LastEvaluatedKey"],
            )
            items.extend(item_to_rss(i) for i in resp.get("Items") or [])
        return items

    def get(self, source_id: str) -> Optional[RssSource]:
        resp = self._table.get_item(Key={"pk": RSS_PK, "sk": source_id})
        item = resp.get("Item")
        return item_to_rss(item) if item else None

    def create(self, source: RssSource) -> RssSource:
        _validate_url(source.url)
        sid = source.source_id or str(uuid4())
        stored = RssSource(
            source_id=sid,
            name=source.name,
            url=source.url,
            enabled=source.enabled,
        )
        self._table.put_item(Item=rss_to_item(stored))
        return stored

    def update(self, source: RssSource) -> RssSource:
        if not self.get(source.source_id):
            raise AdminNotFoundError(f"RSS source {source.source_id} not found")
        _validate_url(source.url)
        self._table.put_item(Item=rss_to_item(source))
        return RssSource(
            source_id=source.source_id,
            name=source.name,
            url=source.url,
            enabled=source.enabled,
        )

    def delete(self, source_id: str) -> None:
        if not self.get(source_id):
            raise AdminNotFoundError(f"RSS source {source_id} not found")
        self._table.delete_item(Key={"pk": RSS_PK, "sk": source_id})


__all__ = [
    "DynamoRssSourcesRepo",
    "rss_to_item",
    "item_to_rss",
    "RSS_PK",
]
