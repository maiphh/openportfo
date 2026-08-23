from __future__ import annotations

from collections.abc import Callable

import boto3
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from botocore.validate import validate_parameters
import pytest

from app.adapters.dynamodb.settings import (
    DynamoSettingsRepo,
    settings_to_item,
)
from app.ports.admin import SettingsConflictError, SystemSettings


_SERIALIZER = TypeSerializer()


def _error(code: str, operation: str = "PutItem") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, operation)


def _resource_table() -> tuple[object, object]:
    resource = boto3.resource(
        "dynamodb",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    table = resource.Table("settings")
    return table, table.meta.client


def _expected_get(item: dict[str, object] | None = None) -> dict[str, object]:
    params: dict[str, object] = {
        "TableName": "settings",
        "Key": {"pk": "SETTINGS", "sk": "GLOBAL"},
        "ConsistentRead": True,
    }
    if item is not None:
        params["Item"] = item
    return params


def _expected_put(
    *,
    condition: str,
    names: dict[str, str],
    expected_version: int,
) -> dict[str, object]:
    saved = SystemSettings(version=1)
    return {
        "TableName": "settings",
        "Item": settings_to_item(saved),
        "ConditionExpression": condition,
        "ExpressionAttributeNames": names,
        "ExpressionAttributeValues": {":expected": expected_version},
    }


def _wire_put(
    *,
    condition: str,
    names: dict[str, str],
    expected_version: int,
) -> dict[str, object]:
    """Return the low-level shape produced by the Table resource boundary."""
    saved = SystemSettings(version=1)
    return {
        "TableName": "settings",
        "Item": {
            key: _SERIALIZER.serialize(value)
            for key, value in settings_to_item(saved).items()
        },
        "ConditionExpression": condition,
        "ExpressionAttributeNames": names,
        "ExpressionAttributeValues": {
            ":expected": _SERIALIZER.serialize(expected_version)
        },
    }


class StatefulSettingsTable:
    """Small document-form table that evaluates the two production conditions."""

    name = "settings"

    def __init__(
        self,
        *,
        item: dict[str, object] | None = None,
        absent_reads: int = 0,
        before_put: Callable[[], None] | None = None,
        error: ClientError | None = None,
    ) -> None:
        self.item = dict(item) if item is not None else None
        self.absent_reads = absent_reads
        self.before_put = before_put
        self.error = error
        self.put_calls: list[dict[str, object]] = []

    def get_item(self, **kwargs: object) -> dict[str, object]:
        if self.absent_reads:
            self.absent_reads -= 1
            return {}
        return {"Item": dict(self.item)} if self.item is not None else {}

    def put_item(self, **kwargs: object) -> dict[str, object]:
        self.put_calls.append(kwargs)
        if self.before_put is not None:
            callback, self.before_put = self.before_put, None
            callback()
        if self.error is not None:
            raise self.error

        condition = str(kwargs["ConditionExpression"])
        expected = int(kwargs["ExpressionAttributeValues"][":expected"])  # type: ignore[index]
        if "attribute_not_exists(#pk) OR" in condition:
            allowed = (
                self.item is None
                or "version" not in self.item
                or self.item.get("version") == expected
            )
        else:
            allowed = (
                self.item is not None
                and self.item.get("pk") == "SETTINGS"
                and self.item.get("sk") == "GLOBAL"
                and self.item.get("version") == expected
            )
        if not allowed:
            raise _error("ConditionalCheckFailedException")
        self.item = dict(kwargs["Item"])  # type: ignore[arg-type]
        return {}


def test_dynamo_settings_fresh_version_zero_create_uses_aws_valid_condition() -> None:
    table, client = _resource_table()
    stubber = Stubber(client)
    condition = (
        "attribute_not_exists(#pk) OR attribute_not_exists(#version) "
        "OR #version = :expected"
    )
    validate_parameters(
        _wire_put(
            condition=condition,
            names={"#pk": "pk", "#version": "version"},
            expected_version=0,
        ),
        client.meta.service_model.operation_model("PutItem").input_shape,
    )
    stubber.add_response("get_item", {}, expected_params=_expected_get())
    stubber.add_response(
        "put_item",
        {},
        expected_params=_expected_put(
            condition=condition,
            names={"#pk": "pk", "#version": "version"},
            expected_version=0,
        ),
    )
    stubber.activate()
    try:
        saved = DynamoSettingsRepo("settings", table=table).save(
            SystemSettings(), expected_version=0
        )
    finally:
        stubber.deactivate()
        client.close()
    assert saved.version == 1


def test_dynamo_settings_two_version_zero_creators_one_loses_conditionally() -> None:
    table = StatefulSettingsTable(absent_reads=2)
    repo = DynamoSettingsRepo("settings", table=table)
    first = repo.save(SystemSettings(), expected_version=0)
    with pytest.raises(SettingsConflictError):
        repo.save(SystemSettings(), expected_version=0)
    assert first.version == 1
    assert table.item is not None and table.item["version"] == 1
    assert len(table.put_calls) == 2


def test_dynamo_settings_legacy_item_without_version_accepts_zero() -> None:
    table = StatefulSettingsTable(item={"pk": "SETTINGS", "sk": "GLOBAL"})
    saved = DynamoSettingsRepo("settings", table=table).save(
        SystemSettings(), expected_version=0
    )
    assert saved.version == 1
    assert table.item is not None and table.item["version"] == 1
    assert "attribute_not_exists(#version)" in table.put_calls[0]["ConditionExpression"]


def test_dynamo_settings_existing_zero_accepts_zero() -> None:
    table = StatefulSettingsTable(item={"pk": "SETTINGS", "sk": "GLOBAL", "version": 0})
    saved = DynamoSettingsRepo("settings", table=table).save(
        SystemSettings(), expected_version=0
    )
    assert saved.version == 1
    assert table.item is not None and table.item["version"] == 1


def test_dynamo_settings_stale_zero_writer_conflicts_with_newer_version() -> None:
    table = StatefulSettingsTable(item={"pk": "SETTINGS", "sk": "GLOBAL", "version": 0})
    table.before_put = lambda: table.item.update(version=2) if table.item else None
    with pytest.raises(SettingsConflictError):
        DynamoSettingsRepo("settings", table=table).save(
            SystemSettings(), expected_version=0
        )
    assert table.item is not None and table.item["version"] == 2


def test_dynamo_settings_delete_after_positive_read_cannot_recreate_singleton() -> None:
    table = StatefulSettingsTable(item={"pk": "SETTINGS", "sk": "GLOBAL", "version": 3})
    table.before_put = lambda: setattr(table, "item", None)
    with pytest.raises(SettingsConflictError):
        DynamoSettingsRepo("settings", table=table).save(
            SystemSettings(), expected_version=3
        )
    assert table.item is None
    assert table.put_calls[0]["ConditionExpression"] == (
        "attribute_exists(#pk) AND attribute_exists(#sk) AND #version = :expected"
    )


def test_dynamo_settings_access_denied_propagates_from_valid_put() -> None:
    table, client = _resource_table()
    stubber = Stubber(client)
    condition = (
        "attribute_not_exists(#pk) OR attribute_not_exists(#version) "
        "OR #version = :expected"
    )
    expected_put = _expected_put(
        condition=condition,
        names={"#pk": "pk", "#version": "version"},
        expected_version=0,
    )
    stubber.add_response("get_item", {}, expected_params=_expected_get())
    stubber.add_client_error(
        "put_item",
        service_error_code="AccessDeniedException",
        service_message="denied",
        expected_params=expected_put,
    )
    stubber.activate()
    try:
        with pytest.raises(ClientError) as exc_info:
            DynamoSettingsRepo("settings", table=table).save(
                SystemSettings(), expected_version=0
            )
    finally:
        stubber.deactivate()
        client.close()
    assert exc_info.value.response["Error"]["Code"] == "AccessDeniedException"
