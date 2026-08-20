"""DynamoDB-backed chatbot request ledger.

Table keys: ``userId`` (partition key), ``requestId`` (sort key).  Only the
safe replay text/activity metadata is stored; tool arguments/results are never
written to this ledger.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import secrets
from typing import Any, Optional

from botocore.exceptions import ClientError

from app.adapters.dynamodb.base import get_table, sanitize_for_dynamo
from app.ports.chat_idempotency import (
    ChatIdempotencyClaim,
    ChatIdempotencyRecord,
    ChatIdempotencyRepo,
    ChatReplay,
    IdempotencyState,
    utc_now,
)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float, Decimal)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return utc_now()


def _replay_to_item(replay: Optional[ChatReplay]) -> Optional[dict[str, Any]]:
    if replay is None:
        return None
    return {
        "reply": replay.reply[:8_000],
        "model": replay.model[:200],
        "toolCalls": [
            {"name": str(item.get("name") or "assistant_action")[:80], "ok": bool(item.get("ok"))}
            for item in replay.tool_calls[:32]
        ],
        "triedModels": [str(model)[:200] for model in replay.tried_models[:16]],
        "rounds": max(0, int(replay.rounds)),
        "ambiguous": bool(replay.ambiguous),
    }


def _item_to_record(item: dict[str, Any]) -> ChatIdempotencyRecord:
    raw_replay = item.get("replay")
    replay = None
    if isinstance(raw_replay, dict):
        replay = ChatReplay(
            reply=str(raw_replay.get("reply") or "")[:8_000],
            model=str(raw_replay.get("model") or "")[:200],
            tool_calls=[
                {"name": str(call.get("name") or "assistant_action")[:80], "ok": bool(call.get("ok"))}
                for call in (raw_replay.get("toolCalls") or [])
                if isinstance(call, dict)
            ][:32],
            tried_models=[str(model)[:200] for model in (raw_replay.get("triedModels") or [])[:16]],
            rounds=max(0, int(raw_replay.get("rounds") or 0)),
            ambiguous=bool(raw_replay.get("ambiguous")),
        )
    state = str(item.get("state") or "in_progress")
    if state not in {"in_progress", "mutation_started", "completed", "ambiguous"}:
        state = "in_progress"
    return ChatIdempotencyRecord(
        user_id=str(item.get("userId") or ""),
        request_id=str(item.get("requestId") or ""),
        state=state,  # type: ignore[arg-type]
        expires_at=_parse_dt(item.get("expiresAt")),
        replay=replay,
        updated_at=_parse_dt(item.get("updatedAt")),
        owner_token=str(item.get("ownerToken") or ""),
    )


class DynamoChatIdempotencyRepo(ChatIdempotencyRepo):
    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table=None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)

    def claim(
        self,
        user_id: str,
        request_id: str,
        *,
        ttl_seconds: int,
    ) -> ChatIdempotencyClaim:
        """Atomically claim a new key or take over an expired owner.

        A conditional put replaces an expired item in one DynamoDB operation;
        there is deliberately no delete-then-reclaim window.  Contending
        callers that lose the condition read the winner and receive it as an
        existing claim.
        """
        owner_token = secrets.token_urlsafe(32)
        ttl = max(60, int(ttl_seconds))
        key = {"userId": user_id, "requestId": request_id}
        for _ in range(8):
            now = utc_now()
            item = sanitize_for_dynamo(
                {
                    **key,
                    "state": "in_progress",
                    "expiresAt": int(now.timestamp()) + ttl,
                    "updatedAt": _iso(now),
                    "ownerToken": owner_token,
                }
            )
            try:
                self._table.put_item(
                    Item=item,
                    ConditionExpression="attribute_not_exists(userId) AND attribute_not_exists(requestId)",
                )
                return ChatIdempotencyClaim(owner_token=owner_token)
            except ClientError as exc:
                if not _conditional_failed(exc):
                    raise

            existing = self._table.get_item(Key=key).get("Item")
            if not existing:
                # An external expiry/delete race changed the item between the
                # failed claim and read. Retry the create condition.
                continue
            record = _item_to_record(existing)
            if record.expires_at > now:
                return ChatIdempotencyClaim(existing=record)

            # Expired takeover is itself conditional. Never delete an item
            # first: a concurrent owner must win or lose atomically.
            try:
                self._table.put_item(
                    Item=item,
                    ConditionExpression=(
                        "attribute_exists(userId) AND attribute_exists(requestId) "
                        "AND expiresAt <= :now"
                    ),
                    ExpressionAttributeValues={":now": int(now.timestamp())},
                )
                return ChatIdempotencyClaim(owner_token=owner_token)
            except ClientError as exc:
                if not _conditional_failed(exc):
                    raise
                # Another takeover won; the next read returns its live record.
                continue

        raise RuntimeError("Unable to claim chat request after concurrent updates")

    def mark_mutation_started(
        self,
        user_id: str,
        request_id: str,
        *,
        owner_token: str,
        ttl_seconds: int,
    ) -> bool:
        now = utc_now()
        try:
            self._table.update_item(
                Key={"userId": user_id, "requestId": request_id},
                UpdateExpression="SET #state = :started, expiresAt = :expires, updatedAt = :updated",
                ConditionExpression=(
                    "ownerToken = :owner AND (#state = :in_progress OR #state = :started)"
                ),
                ExpressionAttributeNames={"#state": "state"},
                ExpressionAttributeValues={
                    ":owner": owner_token,
                    ":in_progress": "in_progress",
                    ":started": "mutation_started",
                    ":expires": int(now.timestamp()) + max(60, int(ttl_seconds)),
                    ":updated": _iso(now),
                },
            )
            return True
        except ClientError as exc:
            if _conditional_failed(exc):
                return False
            raise

    def save(
        self,
        record: ChatIdempotencyRecord,
        *,
        owner_token: str,
        expected_state: IdempotencyState,
    ) -> bool:
        try:
            self._table.put_item(
                Item=sanitize_for_dynamo(
                    {
                        "userId": record.user_id,
                        "requestId": record.request_id,
                        "state": record.state,
                        "expiresAt": int(record.expires_at.timestamp()),
                        "updatedAt": _iso(record.updated_at),
                        "ownerToken": owner_token,
                        "replay": _replay_to_item(record.replay),
                    }
                ),
                ConditionExpression="ownerToken = :owner AND #state = :expected",
                ExpressionAttributeNames={"#state": "state"},
                ExpressionAttributeValues={
                    ":owner": owner_token,
                    ":expected": expected_state,
                },
            )
            return True
        except ClientError as exc:
            if _conditional_failed(exc):
                return False
            raise

    def release(
        self,
        user_id: str,
        request_id: str,
        *,
        owner_token: str,
        expected_state: IdempotencyState = "in_progress",
    ) -> bool:
        try:
            self._table.delete_item(
                Key={"userId": user_id, "requestId": request_id},
                ConditionExpression="ownerToken = :owner AND #state = :expected",
                ExpressionAttributeNames={"#state": "state"},
                ExpressionAttributeValues={":owner": owner_token, ":expected": expected_state},
            )
            return True
        except ClientError as exc:
            if _conditional_failed(exc):
                return False
            raise


def _conditional_failed(exc: ClientError) -> bool:
    return (exc.response or {}).get("Error", {}).get("Code", "") == "ConditionalCheckFailedException"


__all__ = ["DynamoChatIdempotencyRepo"]
