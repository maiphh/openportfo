"""Shared DynamoDB helpers (boto3 only inside adapters)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Optional

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer


def get_dynamodb_resource(region: str, endpoint_url: Optional[str] = None):
    """Create a boto3 DynamoDB resource (optional local endpoint for tests)."""
    kwargs: dict[str, Any] = {"region_name": region or "us-east-1"}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
        # LocalStack accepts dummy credentials; passing them here keeps .env-based
        # local runs independent of the host AWS credential chain.
        kwargs["aws_access_key_id"] = "test"
        kwargs["aws_secret_access_key"] = "test"
    return boto3.resource("dynamodb", **kwargs)


def get_table(table_name: str, *, region: str = "us-east-1", endpoint_url: Optional[str] = None):
    """Return a DynamoDB Table resource."""
    return get_dynamodb_resource(region, endpoint_url).Table(table_name)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def dt_to_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def iso_to_dt(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def to_decimal(value: Any) -> Decimal:
    """Convert numbers / strings to Decimal (Dynamo money-safe)."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(str(value))


def decimal_to_str(value: Decimal) -> str:
    return format(value, "f")


def sanitize_for_dynamo(obj: Any) -> Any:
    """Recursively convert floats → Decimal and drop None values for put_item."""
    if obj is None:
        return None
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, Decimal):
        return obj
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if v is None:
                continue
            out[k] = sanitize_for_dynamo(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_dynamo(v) for v in obj if v is not None]
    return obj


def deep_from_dynamo(obj: Any) -> Any:
    """Convert Dynamo Decimals to int/float/str-friendly forms for nested payloads."""
    if isinstance(obj, list):
        return [deep_from_dynamo(v) for v in obj]
    if isinstance(obj, dict):
        return {k: deep_from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        if obj == obj.to_integral_value():
            return int(obj)
        return float(obj)
    return obj


__all__ = [
    "get_dynamodb_resource",
    "get_table",
    "utc_now",
    "dt_to_iso",
    "iso_to_dt",
    "to_decimal",
    "decimal_to_str",
    "sanitize_for_dynamo",
    "deep_from_dynamo",
    "TypeSerializer",
    "TypeDeserializer",
]
