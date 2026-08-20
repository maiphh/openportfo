"""Small conditional-operation fake for Dynamo chat ledger tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import RLock

from botocore.exceptions import ClientError

from app.adapters.dynamodb.chat_idempotency import DynamoChatIdempotencyRepo, _item_to_record
from app.ports.chat_idempotency import ChatIdempotencyRecord, ChatReplay, utc_now


def _conditional_error(operation: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "condition"}},
        operation,
    )


class ConditionalTable:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict] = {}
        self.lock = RLock()

    def put_item(self, *, Item: dict, ConditionExpression: str, ExpressionAttributeValues=None, **_kwargs):
        key = (Item["userId"], Item["requestId"])
        with self.lock:
            current = self.items.get(key)
            if ConditionExpression.startswith("attribute_not_exists"):
                if current is not None:
                    raise _conditional_error("PutItem")
            elif "expiresAt <= :now" in ConditionExpression:
                if current is None or int(current.get("expiresAt", 0)) > int(ExpressionAttributeValues[":now"]):
                    raise _conditional_error("PutItem")
            else:
                values = ExpressionAttributeValues or {}
                if (
                    current is None
                    or current.get("ownerToken") != values.get(":owner")
                    or current.get("state") != values.get(":expected")
                ):
                    raise _conditional_error("PutItem")
            self.items[key] = deepcopy(Item)

    def get_item(self, *, Key: dict, **_kwargs):
        with self.lock:
            item = self.items.get((Key["userId"], Key["requestId"]))
            return {"Item": deepcopy(item)} if item is not None else {}

    def update_item(self, *, Key: dict, ExpressionAttributeValues: dict, **_kwargs):
        key = (Key["userId"], Key["requestId"])
        with self.lock:
            current = self.items.get(key)
            if (
                current is None
                or current.get("ownerToken") != ExpressionAttributeValues[":owner"]
                or current.get("state") not in {"in_progress", "mutation_started"}
            ):
                raise _conditional_error("UpdateItem")
            current["state"] = "mutation_started"
            current["expiresAt"] = ExpressionAttributeValues[":expires"]
            current["updatedAt"] = ExpressionAttributeValues[":updated"]

    def delete_item(self, *, Key: dict, ExpressionAttributeValues: dict, **_kwargs):
        key = (Key["userId"], Key["requestId"])
        with self.lock:
            current = self.items.get(key)
            if (
                current is None
                or current.get("ownerToken") != ExpressionAttributeValues[":owner"]
                or current.get("state") != ExpressionAttributeValues[":expected"]
            ):
                raise _conditional_error("DeleteItem")
            self.items.pop(key, None)


def _parallel_claims(repo: DynamoChatIdempotencyRepo, count: int = 16):
    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = [
            pool.submit(repo.claim, "alice", "request-1", ttl_seconds=300)
            for _ in range(count)
        ]
        return [future.result() for future in futures]


def test_dynamo_simultaneous_first_claim_has_one_owner() -> None:
    table = ConditionalTable()
    repo = DynamoChatIdempotencyRepo("ledger", table=table)
    claims = _parallel_claims(repo)
    winners = [claim for claim in claims if claim.existing is None]
    assert len(winners) == 1
    assert all(
        claim.existing is None or claim.existing.owner_token == winners[0].owner_token
        for claim in claims
    )


def test_dynamo_expired_takeover_is_conditional() -> None:
    table = ConditionalTable()
    repo = DynamoChatIdempotencyRepo("ledger", table=table)
    first = repo.claim("alice", "request-1", ttl_seconds=300)
    assert first.existing is None
    table.items[("alice", "request-1")]["expiresAt"] = int(utc_now().timestamp()) - 1

    claims = _parallel_claims(repo)
    winners = [claim for claim in claims if claim.existing is None]
    assert len(winners) == 1
    assert winners[0].owner_token != first.owner_token


def test_dynamo_stale_save_and_release_are_rejected() -> None:
    table = ConditionalTable()
    repo = DynamoChatIdempotencyRepo("ledger", table=table)
    first = repo.claim("alice", "request-1", ttl_seconds=300)
    assert first.existing is None
    table.items[("alice", "request-1")]["expiresAt"] = int(utc_now().timestamp()) - 1
    second = repo.claim("alice", "request-1", ttl_seconds=300)
    assert second.existing is None

    record = ChatIdempotencyRecord(
        user_id="alice",
        request_id="request-1",
        state="completed",
        expires_at=utc_now() + timedelta(minutes=5),
        replay=ChatReplay(reply="stale"),
    )
    assert not repo.save(record, owner_token=first.owner_token, expected_state="in_progress")
    assert not repo.release(
        "alice", "request-1", owner_token=first.owner_token, expected_state="in_progress"
    )
    current = table.items[("alice", "request-1")]
    assert current["ownerToken"] == second.owner_token
    assert current["state"] == "in_progress"


def test_dynamo_round_trips_mutation_started_state() -> None:
    record = _item_to_record(
        {
            "userId": "alice",
            "requestId": "request-1",
            "state": "mutation_started",
            "ownerToken": "opaque",
            "expiresAt": int(utc_now().timestamp()) + 300,
            "updatedAt": utc_now().isoformat(),
        }
    )
    assert record.state == "mutation_started"
    assert record.owner_token == "opaque"
