"""Concurrency and ownership tests for the chat request ledger."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from app.adapters.memory.chat_idempotency import InMemoryChatIdempotencyRepo
from app.ports.chat_idempotency import ChatIdempotencyRecord, ChatReplay, utc_now


def _parallel_claims(repo: InMemoryChatIdempotencyRepo, count: int = 16):
    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = [
            pool.submit(repo.claim, "alice", "request-1", ttl_seconds=300)
            for _ in range(count)
        ]
        return [future.result() for future in futures]


def test_simultaneous_first_claim_has_one_owner() -> None:
    repo = InMemoryChatIdempotencyRepo()
    claims = _parallel_claims(repo)

    winners = [claim for claim in claims if claim.existing is None]
    assert len(winners) == 1
    assert winners[0].owner_token
    assert all(
        claim.existing is None or claim.existing.owner_token == winners[0].owner_token
        for claim in claims
    )


def test_simultaneous_expired_takeover_has_one_new_owner() -> None:
    repo = InMemoryChatIdempotencyRepo()
    original = repo.claim("alice", "request-1", ttl_seconds=300)
    assert original.existing is None
    repo._records[("alice", "request-1")].expires_at = utc_now() - timedelta(seconds=1)

    claims = _parallel_claims(repo)
    winners = [claim for claim in claims if claim.existing is None]
    assert len(winners) == 1
    assert winners[0].owner_token != original.owner_token
    assert all(
        claim.existing is None or claim.existing.owner_token == winners[0].owner_token
        for claim in claims
    )


def test_stale_owner_cannot_save_or_release_new_takeover() -> None:
    repo = InMemoryChatIdempotencyRepo()
    first = repo.claim("alice", "request-1", ttl_seconds=300)
    assert first.existing is None
    repo._records[("alice", "request-1")].expires_at = utc_now() - timedelta(seconds=1)
    second = repo.claim("alice", "request-1", ttl_seconds=300)
    assert second.existing is None

    stale_record = ChatIdempotencyRecord(
        user_id="alice",
        request_id="request-1",
        state="completed",
        expires_at=utc_now() + timedelta(minutes=5),
        replay=ChatReplay(reply="stale"),
    )
    assert not repo.save(
        stale_record,
        owner_token=first.owner_token,
        expected_state="in_progress",
    )
    assert not repo.release(
        "alice",
        "request-1",
        owner_token=first.owner_token,
        expected_state="in_progress",
    )
    current = repo._records[("alice", "request-1")]
    assert current.owner_token == second.owner_token
    assert current.state == "in_progress"


def test_mutation_transition_and_finalize_are_owner_and_state_bound() -> None:
    repo = InMemoryChatIdempotencyRepo()
    claim = repo.claim("alice", "request-1", ttl_seconds=300)
    assert claim.existing is None
    owner = claim.owner_token

    assert repo.mark_mutation_started(
        "alice", "request-1", owner_token=owner, ttl_seconds=300
    )
    assert not repo.mark_mutation_started(
        "alice", "request-1", owner_token="stale", ttl_seconds=300
    )
    completed = ChatIdempotencyRecord(
        user_id="alice",
        request_id="request-1",
        state="completed",
        expires_at=utc_now() + timedelta(minutes=5),
        replay=ChatReplay(reply="done"),
    )
    assert repo.save(
        completed,
        owner_token=owner,
        expected_state="mutation_started",
    )
    assert not repo.save(
        completed,
        owner_token="stale",
        expected_state="mutation_started",
    )
