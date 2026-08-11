"""DynamoDB NewsRepo.

Table: openportfo-news
PK: date (YYYY-MM-DD) or NEWS when date unknown
SK: source#{id}
"""

from __future__ import annotations

from typing import Any, Optional

from app.adapters.dynamodb.base import (
    dt_to_iso,
    get_table,
    iso_to_dt,
    sanitize_for_dynamo,
    utc_now,
)
from app.ports.news import NewsItem


def news_pk(date: Optional[str]) -> str:
    return date or "NEWS"


def news_sk(source: str, item_id: str) -> str:
    src = (source or "unknown").replace("#", "_")
    return f"{src}#{item_id}"


def news_to_item(item: NewsItem) -> dict[str, Any]:
    date = item.date
    if not date and item.published_at is not None:
        date = item.published_at.date().isoformat()
    return sanitize_for_dynamo(
        {
            "pk": news_pk(date),
            "sk": news_sk(item.source, item.id),
            "id": item.id,
            "title": item.title,
            "url": item.url,
            "source": item.source,
            "publishedAt": dt_to_iso(item.published_at),
            "symbols": list(item.symbols or []),
            "keywords": list(item.keywords or []),
            "date": date,
        }
    )


def item_to_news(item: dict[str, Any]) -> NewsItem:
    return NewsItem(
        id=str(item.get("id") or item.get("sk", "").split("#")[-1]),
        title=str(item.get("title") or ""),
        url=str(item.get("url") or ""),
        source=str(item.get("source") or ""),
        published_at=iso_to_dt(item.get("publishedAt")),
        symbols=list(item.get("symbols") or []),
        keywords=list(item.get("keywords") or []),
        date=item.get("date"),
    )


class DynamoNewsRepo:
    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table=None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)

    def list_recent(self, limit: int = 50) -> list[NewsItem]:
        """Scan and sort newest-first (demo scale)."""
        items: list[NewsItem] = []
        resp = self._table.scan()
        for raw in resp.get("Items") or []:
            items.append(item_to_news(raw))
        while resp.get("LastEvaluatedKey"):
            resp = self._table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
            for raw in resp.get("Items") or []:
                items.append(item_to_news(raw))

        def _key(x: NewsItem) -> str:
            if x.published_at is not None:
                return x.published_at.isoformat()
            return x.date or ""

        items.sort(key=_key, reverse=True)
        return items[: max(0, limit)]

    def put(self, item: NewsItem) -> None:
        self._table.put_item(Item=news_to_item(item))


__all__ = [
    "DynamoNewsRepo",
    "news_pk",
    "news_sk",
    "news_to_item",
    "item_to_news",
]
