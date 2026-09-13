from __future__ import annotations

from types import SimpleNamespace

from botocore.exceptions import ClientError
from botocore.stub import ANY, Stubber
import boto3
import pytest

from app.adapters.dynamodb.users import DynamoUserProfileRepo
from app.adapters.memory.users import InMemoryUserProfileRepo
from app.ports.users import UserSettingsPatch
from app.services.admin_user_service import LastAdminError, RoleConflictError


class FakeTable:
    def __init__(self) -> None:
        self.items = {
            "u1": {
                "userId": "u1",
                "email": "u@example.com",
                "role": "admin",
                "newsKeywords": ["btc"],
                "emailOptIn": False,
                "preferredCurrency": "USD",
                "avatarStyle": "notionists",
                "avatarSeed": "seed",
                "avatarColor": "aabbcc",
                "createdAt": "2026-01-01T00:00:00+00:00",
                "updatedAt": "2026-01-01T00:00:00+00:00",
            }
        }
        self.update_calls: list[dict[str, object]] = []
        self.put_calls = 0

    def get_item(self, *, Key, **_kwargs):
        return {"Item": self.items.get(Key["userId"])}

    def put_item(self, **_kwargs):
        self.put_calls += 1

    def update_item(self, **kwargs):
        self.update_calls.append(kwargs)
        item = dict(self.items[kwargs["Key"]["userId"]])
        names = kwargs["ExpressionAttributeNames"]
        values = kwargs["ExpressionAttributeValues"]
        expression = kwargs["UpdateExpression"]
        if "#avatarSeed" in expression:
            item.pop("avatarSeed", None)
        if "#avatarColor" in expression:
            item.pop("avatarColor", None)
        item["updatedAt"] = values[":updatedAt"]
        self.items["u1"] = item
        return {"Attributes": item}


class StubbedDynamoTable:
    name = "users"

    def __init__(self, client, *, target_role: str = "admin", target_roles: list[str] | None = None, admin_count: int = 2, admin_counts: list[int] | None = None, guard_version: int = 1, guard_versions: list[int] | None = None):
        self.meta = SimpleNamespace(client=client)
        self.target_role = target_role
        self.target_roles = list(target_roles or [target_role])
        self.admin_count = admin_count
        self.admin_counts = list(admin_counts or [admin_count])
        self.guard_version = guard_version
        self.guard_versions = list(guard_versions or [guard_version])
        self.get_calls: list[dict[str, object]] = []
        self.scan_calls: list[dict[str, object]] = []

    def get_item(self, *, Key, **kwargs):
        self.get_calls.append({"Key": Key, **kwargs})
        if "userId" in Key:
            role = self.target_roles.pop(0) if len(self.target_roles) > 1 else self.target_roles[0]
            item = {
                "userId": Key["userId"],
                "email": "admin@example.com",
                "role": role,
                "createdAt": "2026-01-01T00:00:00+00:00",
                "updatedAt": "2026-01-01T00:00:00+00:00",
            }
            return {"Item": item}
        version = self.guard_versions.pop(0) if len(self.guard_versions) > 1 else self.guard_versions[0]
        return {"Item": {"pk": "ADMIN_ROLE_GUARD", "sk": "GLOBAL", "version": version}}

    def scan(self, **kwargs):
        self.scan_calls.append(kwargs)
        count = self.admin_counts.pop(0) if len(self.admin_counts) > 1 else self.admin_counts[0]
        items = [{"userId": f"admin-{index}", "role": "admin"} for index in range(count)]
        return {"Items": items}


def _transaction_expected(*, users_name: str = "users", settings_name: str = "settings", version: int = 1):
    return {
        "TransactItems": [
            {
                "Update": {
                    "TableName": users_name,
                    "Key": {"userId": {"S": "u1"}},
                    "UpdateExpression": "SET #role = :user, #updatedAt = :updatedAt",
                    "ConditionExpression": "attribute_exists(#userId) AND #role = :admin",
                    "ExpressionAttributeNames": {
                        "#userId": "userId",
                        "#role": "role",
                        "#updatedAt": "updatedAt",
                    },
                    "ExpressionAttributeValues": {
                        ":user": {"S": "user"},
                        ":admin": {"S": "admin"},
                        ":updatedAt": ANY,
                    },
                }
            },
            {
                "Update": {
                    "TableName": settings_name,
                    "Key": {
                        "pk": {"S": "ADMIN_ROLE_GUARD"},
                        "sk": {"S": "GLOBAL"},
                    },
                    "UpdateExpression": "SET #version = :next, #updatedAt = :updatedAt",
                    "ConditionExpression": "attribute_not_exists(#version) OR #version = :version",
                    "ExpressionAttributeNames": {"#version": "version", "#updatedAt": "updatedAt"},
                    "ExpressionAttributeValues": {
                        ":next": {"N": str(version + 1)},
                        ":version": {"N": str(version)},
                        ":updatedAt": ANY,
                    },
                }
            },
        ]
    }


def _client():
    return boto3.client("dynamodb", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x")


def _client_error(code: str, operation: str = "UpdateItem") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, operation)


def test_memory_patch_omitted_and_clear_preserve_role() -> None:
    repo = InMemoryUserProfileRepo()
    repo.get_or_create("u1")
    repo.set_role("u1", "admin")
    repo.update_settings("u1", patch=UserSettingsPatch(avatar_style="big-smile", avatar_seed="seed", avatar_color="aabbcc"))
    cleared = repo.update_settings("u1", patch=UserSettingsPatch(avatar_seed=None, avatar_color=None))
    assert cleared.role == "admin"
    assert cleared.avatar_style == "big-smile"
    assert cleared.avatar_seed is None
    assert cleared.avatar_color is None


def test_dynamo_patch_uses_field_update_and_remove_not_put() -> None:
    table = FakeTable()
    repo = DynamoUserProfileRepo("users", table=table)
    updated = repo.update_settings("u1", patch=UserSettingsPatch(avatar_seed=None, avatar_color=None))
    assert updated.role == "admin"
    assert table.put_calls == 0
    assert len(table.update_calls) == 1
    call = table.update_calls[0]
    assert "REMOVE #avatarSeed, #avatarColor" in call["UpdateExpression"]


def test_dynamo_reads_strongly_and_serializes_guarded_transaction_for_client() -> None:
    client = _client()
    table = StubbedDynamoTable(client, target_roles=["admin", "user"])
    guard = StubbedDynamoTable(client)
    guard.name = "settings"
    stubber = Stubber(client)
    stubber.add_response("transact_write_items", {}, expected_params=_transaction_expected())
    stubber.activate()
    try:
        repo = DynamoUserProfileRepo("users", table=table, role_guard_table=guard)
        updated = repo.change_role_guarded("u1", "user")
    finally:
        stubber.deactivate()
        client.close()
    assert updated.role == "user"
    assert table.get_calls[0]["ConsistentRead"] is True
    assert table.get_calls[-1]["ConsistentRead"] is True
    assert table.scan_calls[0]["ConsistentRead"] is True
    assert guard.get_calls[0]["ConsistentRead"] is True


def test_dynamo_guard_retries_one_conditional_transaction_conflict() -> None:
    client = _client()
    table = StubbedDynamoTable(client, target_roles=["admin", "admin", "user"])
    guard = StubbedDynamoTable(client)
    guard.name = "settings"
    guard.guard_version = 1
    stubber = Stubber(client)
    expected = _transaction_expected()
    stubber.add_client_error(
        "transact_write_items",
        service_error_code="TransactionCanceledException",
        service_message="conditional conflict",
        expected_params=expected,
    )
    guard.guard_versions = [1, 2]
    stubber.add_response("transact_write_items", {}, expected_params=_transaction_expected(version=2))
    stubber.activate()
    try:
        repo = DynamoUserProfileRepo("users", table=table, role_guard_table=guard)
        updated = repo.change_role_guarded("u1", "user")
    finally:
        stubber.deactivate()
        client.close()
    assert updated.role == "user"
    assert len(table.scan_calls) == 2


def test_dynamo_access_denied_is_not_misreported_as_role_conflict() -> None:
    client = _client()
    table = StubbedDynamoTable(client, target_roles=["admin"])
    guard = StubbedDynamoTable(client)
    guard.name = "settings"
    stubber = Stubber(client)
    stubber.add_client_error(
        "transact_write_items",
        service_error_code="AccessDeniedException",
        service_message="denied",
        expected_params=_transaction_expected(),
    )
    stubber.activate()
    try:
        repo = DynamoUserProfileRepo("users", table=table, role_guard_table=guard)
        with pytest.raises(Exception) as exc_info:
            repo.change_role_guarded("u1", "user")
    finally:
        stubber.deactivate()
        client.close()
    assert exc_info.value.__class__.__name__ == "ClientError"


def test_dynamo_absent_target_is_key_error_before_transaction() -> None:
    class MissingTable(StubbedDynamoTable):
        def get_item(self, *, Key, **kwargs):
            self.get_calls.append({"Key": Key, **kwargs})
            return {}

    client = _client()
    table = MissingTable(client)
    guard = StubbedDynamoTable(client)
    guard.name = "settings"
    try:
        repo = DynamoUserProfileRepo("users", table=table, role_guard_table=guard)
        with pytest.raises(KeyError):
            repo.change_role_guarded("u1", "user")
    finally:
        client.close()


@pytest.mark.parametrize("operation", ["update_settings", "update_identity", "set_role"])
def test_dynamo_absent_profile_mutations_translate_only_conditional_not_found(operation: str) -> None:
    class MissingMutationTable:
        def get_item(self, *, Key, **kwargs):
            return {}

        def update_item(self, **kwargs):
            raise _client_error("ConditionalCheckFailedException")

    repo = DynamoUserProfileRepo("users", table=MissingMutationTable())
    with pytest.raises(KeyError):
        if operation == "update_settings":
            repo.update_settings("missing", patch=UserSettingsPatch(avatar_seed="x"))
        elif operation == "update_identity":
            repo.update_identity("missing", email="new@example.com")
        else:
            repo.set_role("missing", "admin")


def test_dynamo_unrelated_profile_mutation_errors_propagate() -> None:
    class FailingMutationTable:
        def update_item(self, **kwargs):
            raise _client_error("AccessDeniedException")

    repo = DynamoUserProfileRepo("users", table=FailingMutationTable())
    with pytest.raises(ClientError) as exc_info:
        repo.update_identity("u1", email="new@example.com")
    assert exc_info.value.response["Error"]["Code"] == "AccessDeniedException"


def test_dynamo_transaction_target_change_returns_role_conflict_after_reread() -> None:
    client = _client()
    table = StubbedDynamoTable(client, target_roles=["admin", "user"])
    guard = StubbedDynamoTable(client)
    guard.name = "settings"
    stubber = Stubber(client)
    stubber.add_client_error(
        "transact_write_items",
        service_error_code="TransactionCanceledException",
        service_message="target changed",
        expected_params=_transaction_expected(),
    )
    stubber.activate()
    try:
        repo = DynamoUserProfileRepo("users", table=table, role_guard_table=guard)
        with pytest.raises(RoleConflictError):
            repo.change_role_guarded("u1", "user")
    finally:
        stubber.deactivate()
        client.close()


def test_dynamo_last_admin_is_rechecked_after_first_transaction_conflict() -> None:
    client = _client()
    table = StubbedDynamoTable(client, target_roles=["admin", "admin"], admin_counts=[2, 1])
    guard = StubbedDynamoTable(client)
    guard.name = "settings"
    stubber = Stubber(client)
    stubber.add_client_error(
        "transact_write_items",
        service_error_code="TransactionCanceledException",
        service_message="last admin",
        expected_params=_transaction_expected(),
    )
    stubber.activate()
    try:
        repo = DynamoUserProfileRepo("users", table=table, role_guard_table=guard)
        with pytest.raises(LastAdminError):
            repo.change_role_guarded("u1", "user")
    finally:
        stubber.deactivate()
        client.close()


def test_dynamo_second_transaction_conflict_is_role_conflict() -> None:
    client = _client()
    table = StubbedDynamoTable(client, target_roles=["admin", "admin", "admin"], admin_counts=[2, 2])
    guard = StubbedDynamoTable(client, guard_versions=[1, 2])
    guard.name = "settings"
    stubber = Stubber(client)
    stubber.add_client_error(
        "transact_write_items",
        service_error_code="TransactionCanceledException",
        service_message="first conflict",
        expected_params=_transaction_expected(),
    )
    stubber.add_client_error(
        "transact_write_items",
        service_error_code="TransactionCanceledException",
        service_message="second conflict",
        expected_params=_transaction_expected(version=2),
    )
    stubber.activate()
    try:
        repo = DynamoUserProfileRepo("users", table=table, role_guard_table=guard)
        with pytest.raises(RoleConflictError):
            repo.change_role_guarded("u1", "user")
    finally:
        stubber.deactivate()
        client.close()


def test_dynamo_conditional_create_loser_strongly_reloads_winner() -> None:
    winner = {
        "userId": "u1",
        "email": "winner@example.com",
        "role": "admin",
        "newsKeywords": ["btc"],
        "createdAt": "2026-01-01T00:00:00+00:00",
        "updatedAt": "2026-01-01T00:00:00+00:00",
    }

    class RaceTable:
        def __init__(self):
            self.put_kwargs = None
            self.get_kwargs = []

        def get_item(self, **kwargs):
            self.get_kwargs.append(kwargs)
            return {"Item": None if len(self.get_kwargs) == 1 else winner}

        def put_item(self, **kwargs):
            self.put_kwargs = kwargs
            raise _client_error("ConditionalCheckFailedException", "PutItem")

    table = RaceTable()
    profile = DynamoUserProfileRepo("users", table=table).get_or_create("u1", email="loser@example.com")
    assert profile.role == "admin"
    assert profile.email == "winner@example.com"
    assert table.put_kwargs["ConditionExpression"] == "attribute_not_exists(#userId)"
    assert table.get_kwargs[-1]["ConsistentRead"] is True
