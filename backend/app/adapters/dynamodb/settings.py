"""DynamoDB SettingsRepo (singleton SETTINGS/GLOBAL).

Table: openportfo-settings
PK: SETTINGS  SK: GLOBAL
"""

from __future__ import annotations

from typing import Any, Optional

from botocore.exceptions import ClientError

from app.adapters.dynamodb.base import get_table, sanitize_for_dynamo
from app.ports.admin import SettingsConflictError, SystemSettings
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
            "version": int(settings.version),
            "chatModel": settings.chat_model,
            "chatFallbackModels": list(settings.chat_fallback_models)
            if settings.chat_fallback_models is not None
            else None,
            "chatTemperature": settings.chat_temperature,
            "chatTopP": settings.chat_top_p,
            "chatMaxTokens": settings.chat_max_tokens,
            "chatSystemPromptExtra": settings.chat_system_prompt_extra,
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
        version=int(item.get("version") or 0),
        chat_model=item.get("chatModel"),
        chat_fallback_models=(
            list(item.get("chatFallbackModels"))
            if item.get("chatFallbackModels") is not None
            else None
        ),
        chat_temperature=(
            float(item["chatTemperature"])
            if item.get("chatTemperature") is not None
            else None
        ),
        chat_top_p=(float(item["chatTopP"]) if item.get("chatTopP") is not None else None),
        chat_max_tokens=(
            int(item["chatMaxTokens"]) if item.get("chatMaxTokens") is not None else None
        ),
        chat_system_prompt_extra=item.get("chatSystemPromptExtra"),
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
        resp = self._table.get_item(
            Key={"pk": SETTINGS_PK, "sk": SETTINGS_SK},
            ConsistentRead=True,
        )
        return item_to_settings(resp.get("Item"))

    def save(
        self,
        settings: SystemSettings,
        *,
        expected_version: Optional[int] = None,
    ) -> SystemSettings:
        current = self.get()
        if expected_version is not None and expected_version != current.version:
            raise SettingsConflictError()
        saved = SystemSettings(
            email_time=settings.email_time,
            timezone=settings.timezone,
            email_enabled=settings.email_enabled,
            price_cache_ttl_minutes=settings.price_cache_ttl_minutes,
            jobs_news=settings.jobs_news,
            jobs_snapshot=settings.jobs_snapshot,
            jobs_email=settings.jobs_email,
            jobs_price=settings.jobs_price,
            default_display_currency=settings.default_display_currency,
            version=current.version + 1,
            chat_model=settings.chat_model,
            chat_fallback_models=(
                list(settings.chat_fallback_models)
                if settings.chat_fallback_models is not None
                else None
            ),
            chat_temperature=settings.chat_temperature,
            chat_top_p=settings.chat_top_p,
            chat_max_tokens=settings.chat_max_tokens,
            chat_system_prompt_extra=settings.chat_system_prompt_extra,
        )
        kwargs: dict[str, Any] = {"Item": settings_to_item(saved)}
        if expected_version is not None:
            if expected_version == 0:
                # A missing singleton and legacy items without a version both
                # read as version zero.  The conditional put is still atomic:
                # only an absent key, missing version, or explicit zero may
                # win the initial write.
                condition = (
                    "attribute_not_exists(#pk) OR attribute_not_exists(#version) "
                    "OR #version = :expected"
                )
                names = {"#pk": "pk", "#version": "version"}
            else:
                # Once a positive version has been observed, a delete between
                # the strong read and put must become a conflict, never a
                # recreation of the singleton.
                condition = (
                    "attribute_exists(#pk) AND attribute_exists(#sk) "
                    "AND #version = :expected"
                )
                names = {"#pk": "pk", "#sk": "sk", "#version": "version"}
            kwargs.update(
                {
                    "ConditionExpression": condition,
                    "ExpressionAttributeNames": names,
                    "ExpressionAttributeValues": {":expected": expected_version},
                }
            )
        try:
            self._table.put_item(**kwargs)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise SettingsConflictError() from exc
            raise
        return saved


__all__ = [
    "DynamoSettingsRepo",
    "settings_to_item",
    "item_to_settings",
    "SETTINGS_PK",
    "SETTINGS_SK",
]
