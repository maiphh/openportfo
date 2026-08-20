"""Bounded process-local chatbot idempotency ledger."""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import secrets
from threading import RLock
from typing import Optional

from app.ports.chat_idempotency import (
    ChatIdempotencyClaim,
    ChatIdempotencyRecord,
    ChatIdempotencyRepo,
    IdempotencyState,
    utc_now,
)


class InMemoryChatIdempotencyRepo(ChatIdempotencyRepo):
    """Thread-safe fallback used by local/test runtimes.

    Production dependency wiring uses the DynamoDB implementation.  This
    fallback is still bounded so tests and local development cannot grow a
    request ledger without limit.
    """

    def __init__(self, *, max_records: int = 2048) -> None:
        self._records: dict[tuple[str, str], ChatIdempotencyRecord] = {}
        self._lock = RLock()
        self._max_records = max(16, int(max_records))

    def _prune(self, now, *, exclude: Optional[tuple[str, str]] = None) -> None:
        expired = [
            key
            for key, record in self._records.items()
            if key != exclude and record.expires_at <= now
        ]
        for key in expired:
            self._records.pop(key, None)
        while len(self._records) > self._max_records:
            oldest = min(self._records, key=lambda key: self._records[key].updated_at)
            self._records.pop(oldest, None)

    def claim(
        self,
        user_id: str,
        request_id: str,
        *,
        ttl_seconds: int,
    ) -> ChatIdempotencyClaim:
        now = utc_now()
        key = (user_id, request_id)
        owner_token = secrets.token_urlsafe(32)
        with self._lock:
            # Keep the requested key until the conditional takeover below. A
            # single lock makes first-claim and expired-takeover linearizable.
            self._prune(now, exclude=key)
            existing = self._records.get(key)
            if existing is not None:
                if existing.expires_at > now:
                    return ChatIdempotencyClaim(existing=deepcopy(existing))
                self._records[key] = ChatIdempotencyRecord(
                    user_id=user_id,
                    request_id=request_id,
                    state="in_progress",
                    expires_at=now + timedelta(seconds=max(60, int(ttl_seconds))),
                    updated_at=now,
                    owner_token=owner_token,
                )
                return ChatIdempotencyClaim(owner_token=owner_token)
            self._records[key] = ChatIdempotencyRecord(
                user_id=user_id,
                request_id=request_id,
                state="in_progress",
                expires_at=now + timedelta(seconds=max(60, int(ttl_seconds))),
                updated_at=now,
                owner_token=owner_token,
            )
            return ChatIdempotencyClaim(owner_token=owner_token)

    def mark_mutation_started(
        self,
        user_id: str,
        request_id: str,
        *,
        owner_token: str,
        ttl_seconds: int,
    ) -> bool:
        now = utc_now()
        with self._lock:
            self._prune(now)
            current = self._records.get((user_id, request_id))
            if current is None or current.owner_token != owner_token:
                return False
            if current.state not in {"in_progress", "mutation_started"}:
                return False
            current.state = "mutation_started"
            current.expires_at = now + timedelta(seconds=max(60, int(ttl_seconds)))
            current.updated_at = now
            return True

    def save(
        self,
        record: ChatIdempotencyRecord,
        *,
        owner_token: str,
        expected_state: IdempotencyState,
    ) -> bool:
        with self._lock:
            self._prune(utc_now())
            key = (record.user_id, record.request_id)
            current = self._records.get(key)
            if current is None or current.owner_token != owner_token or current.state != expected_state:
                return False
            updated = deepcopy(record)
            updated.owner_token = owner_token
            self._records[key] = updated
            return True

    def release(
        self,
        user_id: str,
        request_id: str,
        *,
        owner_token: str,
        expected_state: IdempotencyState = "in_progress",
    ) -> bool:
        with self._lock:
            self._prune(utc_now())
            key = (user_id, request_id)
            current = self._records.get(key)
            if current is None or current.owner_token != owner_token or current.state != expected_state:
                return False
            self._records.pop(key, None)
            return True

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


__all__ = ["InMemoryChatIdempotencyRepo"]
