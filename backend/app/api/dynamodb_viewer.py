"""Read-only DynamoDB inspector for the local temporary UI."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.adapters.dynamodb.base import deep_from_dynamo, get_dynamodb_resource
from app.core.config import Settings, get_settings
from app.core.deps import get_current_user
from app.ports.users import UserProfile


router = APIRouter(prefix="/api/dev/dynamodb", tags=["dev"])


def _configured_tables(settings: Settings) -> list[str]:
    return [
        settings.users_table,
        settings.holdings_table,
        settings.watchlist_table,
        settings.price_cache_table,
        settings.news_table,
        settings.settings_table,
        settings.fx_table,
        settings.rss_table,
        settings.job_runs_table,
        settings.snapshots_table,
    ]


def _local_resource(settings: Settings):
    if settings.app_env.strip().lower() not in {"local", "test"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DynamoDB viewer is available only in local/test environments",
        )
    if not settings.dynamodb_endpoint_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DYNAMODB_ENDPOINT_URL is not configured",
        )
    return get_dynamodb_resource(settings.aws_region, settings.dynamodb_endpoint_url)


@router.get("")
def list_tables(
    _user: UserProfile = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    dynamodb = _local_resource(settings)
    configured = _configured_tables(settings)
    try:
        existing = set(dynamodb.meta.client.list_tables().get("TableNames", []))
        tables = []
        for name in configured:
            if name not in existing:
                tables.append({"name": name, "status": "missing", "itemCount": 0})
                continue
            description = dynamodb.meta.client.describe_table(TableName=name)["Table"]
            tables.append(
                {
                    "name": name,
                    "status": description.get("TableStatus", "unknown"),
                    "itemCount": description.get("ItemCount", 0),
                    "keySchema": description.get("KeySchema", []),
                }
            )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not query local DynamoDB: {exc}",
        ) from exc
    return {"endpoint": settings.dynamodb_endpoint_url, "region": settings.aws_region, "tables": tables}


@router.get("/{table_name}")
def scan_table(
    table_name: str,
    limit: int = Query(default=25, ge=1, le=100),
    _user: UserProfile = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if table_name not in _configured_tables(settings):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown application table")
    dynamodb = _local_resource(settings)
    try:
        result = dynamodb.Table(table_name).scan(Limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not scan {table_name}: {exc}",
        ) from exc
    return {
        "table": table_name,
        "count": result.get("Count", 0),
        "scannedCount": result.get("ScannedCount", 0),
        "truncated": "LastEvaluatedKey" in result,
        "items": deep_from_dynamo(result.get("Items", [])),
    }
