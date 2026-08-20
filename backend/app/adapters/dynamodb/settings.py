"""DynamoDB SettingsRepo (singleton SETTINGS/GLOBAL).

Table: openportfo-settings
PK: SETTINGS  SK: GLOBAL
"""

from __future__ import annotations

from typing import Any, Optional

from app.adapters.dynamodb.base import get_table, sanitize_for_dynamo
from app.ports.admin import SystemSettings
from app.services.currency_service import normalize_stored_currency

SETTINGS_PK = "SETTINGS"
SETTINGS_SK = "GLOBAL"


def settings_to_item(settings: SystemSettings) -> dict[str, Any]:
    return sanitize_for_dynamo(
        {
            "pk": SETTINGS_PK,
            "sk": SETTINGS_SK,
            "emailTime": settings.email_time,
            "timezone": settings.timezone,
            "emailEnabled": bool(settings.email_enabled),
            "priceCacheTtlMinutes": int(settings.price_cache_ttl_minutes),
            "jobsNews": bool(settings.jobs_news),
            "jobsSnapshot": bool(settings.jobs_snapshot),
            "jobsEmail": bool(settings.jobs_email),
            "jobsPrice": bool(settings.jobs_price),
            "defaultDisplayCurrency": normalize_stored_currency(settings.default_display_currency) or "USD",
        }
    )


def item_to_settings(item: Optional[dict[str, Any]]) -> SystemSettings:
    if not item:
        return SystemSettings()
    return SystemSettings(
        email_time=str(item.get("emailTime") or "08:00"),
        timezone=str(item.get("timezone") or "Asia/Ho_Chi_Minh"),
        email_enabled=bool(item.get("emailEnabled", False)),
        price_cache_ttl_minutes=int(item.get("priceCacheTtlMinutes") or 10),
        jobs_news=bool(item.get("jobsNews", True)),
        jobs_snapshot=bool(item.get("jobsSnapshot", True)),
        jobs_email=bool(item.get("jobsEmail", False)),
        jobs_price=bool(item.get("jobsPrice", True)),
        default_display_currency=normalize_stored_currency(item.get("defaultDisplayCurrency")) or "USD",
    )


class DynamoSettingsRepo:
    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table=None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)

    def get(self) -> SystemSettings:
        resp = self._table.get_item(Key={"pk": SETTINGS_PK, "sk": SETTINGS_SK})
        return item_to_settings(resp.get("Item"))

    def save(self, settings: SystemSettings) -> SystemSettings:
        self._table.put_item(Item=settings_to_item(settings))
        return SystemSettings(
            email_time=settings.email_time,
            timezone=settings.timezone,
            email_enabled=settings.email_enabled,
            price_cache_ttl_minutes=settings.price_cache_ttl_minutes,
            jobs_news=settings.jobs_news,
            jobs_snapshot=settings.jobs_snapshot,
            jobs_email=settings.jobs_email,
            jobs_price=settings.jobs_price,
            default_display_currency=settings.default_display_currency,
        )


__all__ = [
    "DynamoSettingsRepo",
    "settings_to_item",
    "item_to_settings",
    "SETTINGS_PK",
    "SETTINGS_SK",
]
