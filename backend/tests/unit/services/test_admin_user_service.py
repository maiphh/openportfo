from __future__ import annotations

import base64
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.adapters.memory.users import InMemoryUserProfileRepo
from app.services.admin_user_service import (
    InvalidCursorError,
    LastAdminError,
    WhitelistAdminError,
    decode_user_cursor,
    encode_user_cursor,
    parse_admin_emails,
    AdminUserService,
)


def test_admin_emails_normalize_case_whitespace_and_duplicates() -> None:
    assert parse_admin_emails(" A@EXAMPLE.COM, a@example.com, , B@example.com ") == {
        "a@example.com",
        "b@example.com",
    }


@pytest.mark.parametrize("raw", ["missing-at", "a@@b", "@example.com", "a @b.com", "a\tb.com"])
def test_admin_emails_reject_invalid_without_value(raw: str) -> None:
    with pytest.raises(ValueError, match="ADMIN_EMAILS") as exc:
        parse_admin_emails(raw)
    assert raw not in str(exc.value)


def test_cursor_round_trip_and_strict_shape() -> None:
    cursor = encode_user_cursor("u-1")
    assert "=" not in cursor
    assert decode_user_cursor(cursor) == "u-1"
    payload = base64.urlsafe_b64encode(
        json.dumps({"v": 1, "key": {"userId": "u-1", "extra": 1}}).encode()
    ).decode().rstrip("=")
    with pytest.raises(InvalidCursorError):
        decode_user_cursor(payload)


@pytest.mark.parametrize("cursor", ["not base64", "e30", "", "A" * 2049])
def test_cursor_rejects_malformed(cursor: str) -> None:
    if cursor == "":
        assert decode_user_cursor(cursor) is None
        return
    with pytest.raises(InvalidCursorError):
        decode_user_cursor(cursor)


def test_memory_admin_service_promotes_and_blocks_whitelist_demotion() -> None:
    repo = InMemoryUserProfileRepo()
    profile = repo.get_or_create("u1", email="Admin@Example.com")
    service = AdminUserService(repo, {"admin@example.com"})
    promoted = service.promote_claim(profile, "Admin@Example.com")
    assert promoted.role == "admin"
    with pytest.raises(WhitelistAdminError):
        service.change_role("u1", "user")


def test_memory_admin_service_blocks_last_admin() -> None:
    repo = InMemoryUserProfileRepo()
    repo.get_or_create("u1", email="a@example.com")
    repo.set_role("u1", "admin")
    with pytest.raises(LastAdminError):
        AdminUserService(repo).change_role("u1", "user")


def test_memory_admin_guard_serializes_concurrent_demotions() -> None:
    repo = InMemoryUserProfileRepo()
    for user_id in ("u1", "u2"):
        repo.get_or_create(user_id)
        repo.set_role(user_id, "admin")
    service = AdminUserService(repo)

    def demote(user_id: str):
        try:
            service.change_role(user_id, "user")
            return "ok"
        except LastAdminError:
            return "last_admin"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(demote, ("u1", "u2")))
    assert outcomes == ["last_admin", "ok"]
    assert sum(1 for user_id in ("u1", "u2") if repo.get(user_id).role == "admin") == 1


def test_memory_admin_service_cursor_pages_forward() -> None:
    repo = InMemoryUserProfileRepo()
    for user_id in ("u1", "u2", "u3"):
        repo.get_or_create(user_id)
    service = AdminUserService(repo)
    first = service.list_page(2)
    assert [p.user_id for p in first.items] == ["u1", "u2"]
    second = service.list_page(2, first.next_cursor)
    assert [p.user_id for p in second.items] == ["u3"]
    assert second.next_cursor is None
