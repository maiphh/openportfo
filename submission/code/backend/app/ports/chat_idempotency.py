"""Per-user idempotency ledger for chatbot turns that may mutate data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional, Protocol

IdempotencyState = Literal["in_progress", "mutation_started", "completed", "ambiguous"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ChatReplay:
    """Safe replay payload; raw tool arguments/results never belong here."""

    reply: str
    model: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tried_models: list[str] = field(default_factory=list)
    rounds: int = 0
    ambiguous: bool = False


@dataclass
class ChatIdempotencyRecord:
    user_id: str
    request_id: str
    state: IdempotencyState
    expires_at: datetime
    replay: Optional[ChatReplay] = None
    updated_at: datetime = field(default_factory=utc_now)
    # Opaque server-generated ownership proof.  It is never sent to a client.
    owner_token: str = ""


@dataclass(frozen=True)
class ChatIdempotencyClaim:
    """Result of an atomic claim attempt.

    ``existing`` is populated when another live owner already holds the key.
    A successful claim has an opaque ``owner_token`` and no existing record.
    """

    owner_token: str = ""
    existing: Optional[ChatIdempotencyRecord] = None


class ChatIdempotencyRepo(Protocol):
    """Claim and finalize one bounded request id for one authenticated user."""

    def claim(
        self,
        user_id: str,
        request_id: str,
        *,
        ttl_seconds: int,
    ) -> ChatIdempotencyClaim:
        """Return an existing live record, or atomically claim a new one."""
        ...

    def mark_mutation_started(
        self,
        user_id: str,
        request_id: str,
        *,
        owner_token: str,
        ttl_seconds: int,
    ) -> bool:
        """Conditionally mark a request before every mutating tool call."""
        ...

    def save(
        self,
        record: ChatIdempotencyRecord,
        *,
        owner_token: str,
        expected_state: IdempotencyState,
    ) -> bool:
        """Conditionally finalize a record owned by this request."""
        ...

    def release(
        self,
        user_id: str,
        request_id: str,
        *,
        owner_token: str,
        expected_state: IdempotencyState = "in_progress",
    ) -> bool:
        """Conditionally release a claim when no mutation was started."""
        ...


__all__ = [
    "ChatIdempotencyRecord",
    "ChatIdempotencyClaim",
    "ChatIdempotencyRepo",
    "ChatReplay",
    "IdempotencyState",
    "utc_now",
]
