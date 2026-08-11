"""DynamoDB ExchangeRateRepo.

Table: openportfo-fx
PK: FX  SK: LATEST
"""

from __future__ import annotations

from typing import Any, Optional

from app.adapters.dynamodb.base import (
    dt_to_iso,
    get_table,
    iso_to_dt,
    sanitize_for_dynamo,
    to_decimal,
    utc_now,
)
from app.ports.fx import RateSnapshot, StoredRates

FX_PK = "FX"
FX_SK = "LATEST"


def rates_to_item(stored: StoredRates) -> dict[str, Any]:
    rates_map = {k: to_decimal(v) for k, v in (stored.rates or {}).items()}
    return sanitize_for_dynamo(
        {
            "pk": FX_PK,
            "sk": FX_SK,
            "base": stored.base,
            "rates": rates_map,
            "asOf": dt_to_iso(stored.as_of),
            "provider": stored.provider,
            "status": stored.status,
            "lastRefreshStatus": stored.last_refresh_status,
            "lastRefreshError": stored.last_refresh_error,
            "updatedBy": stored.updated_by,
        }
    )


def item_to_rates(item: Optional[dict[str, Any]]) -> Optional[StoredRates]:
    if not item:
        return None
    raw_rates = item.get("rates") or {}
    rates = {str(k): to_decimal(v) for k, v in raw_rates.items()}
    return StoredRates(
        base=str(item.get("base") or "USD"),
        rates=rates,
        as_of=iso_to_dt(item.get("asOf")),
        provider=item.get("provider"),
        status=item.get("status") or ("fresh" if rates else "missing"),  # type: ignore[arg-type]
        last_refresh_status=item.get("lastRefreshStatus"),
        last_refresh_error=item.get("lastRefreshError"),
        updated_by=item.get("updatedBy"),
    )


class DynamoExchangeRateRepo:
    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table=None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)

    def get_latest(self) -> Optional[StoredRates]:
        resp = self._table.get_item(Key={"pk": FX_PK, "sk": FX_SK})
        return item_to_rates(resp.get("Item"))

    def save(
        self,
        snapshot: RateSnapshot,
        *,
        updated_by: Optional[str] = None,
    ) -> StoredRates:
        as_of = snapshot.fetched_at or utc_now()
        stored = StoredRates(
            base=snapshot.base,
            rates=dict(snapshot.rates),
            as_of=as_of,
            provider=snapshot.provider,
            status="fresh" if snapshot.rates else "missing",
            last_refresh_status="success",
            last_refresh_error=None,
            updated_by=updated_by,
        )
        self._table.put_item(Item=rates_to_item(stored))
        return stored


__all__ = [
    "DynamoExchangeRateRepo",
    "rates_to_item",
    "item_to_rates",
    "FX_PK",
    "FX_SK",
]
