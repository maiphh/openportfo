"""Admin authority, opaque user cursors, and role mutation rules.

The service deliberately depends on the user repository protocol.  This keeps
the whitelist and last-admin policy identical for local memory tests and the
production Dynamo adapter while allowing each adapter to provide its own
atomic primitive where one is available.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import unicodedata
from dataclasses import dataclass
from threading import RLock
from typing import Iterable, Optional

from app.ports.users import Role, UserProfile, UserProfileRepo


_EMAIL_TOKEN = re.compile(r"^[^\s\x00-\x1f\x7f]+@[^\s\x00-\x1f\x7f]+$")
_CURSOR_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")
MAX_CURSOR_LENGTH = 2048


class InvalidCursorError(ValueError):
    """Raised when an opaque admin-user cursor is not canonical."""


class AdminUserError(Exception):
    """Base class for policy errors surfaced by the admin API."""

    code = "admin_error"
    status_code = 400


class UserNotFoundError(AdminUserError):
    code = "not_found"
    status_code = 404


class WhitelistAdminError(AdminUserError):
    code = "whitelist_admin"


class LastAdminError(AdminUserError):
    code = "last_admin"
    status_code = 409


class RoleConflictError(AdminUserError):
    code = "role_conflict"
    status_code = 409


def parse_admin_emails(raw: str | None) -> frozenset[str]:
    """Parse ADMIN_EMAILS without exposing configured values in errors."""
    result: set[str] = set()
    for segment in str(raw or "").split(","):
        email = segment.strip()
        if not email:
            continue
        if (
            email.count("@") != 1
            or not _EMAIL_TOKEN.fullmatch(email)
            or any(unicodedata.category(char).startswith("C") for char in email)
        ):
            raise ValueError("ADMIN_EMAILS contains invalid email configuration")
        local, domain = email.split("@", 1)
        if not local or not domain:
            raise ValueError("ADMIN_EMAILS contains invalid email configuration")
        result.add(email.casefold())
    return frozenset(result)


def encode_user_cursor(user_id: str) -> str:
    """Encode the public versioned cursor as unpadded canonical base64url."""
    if not isinstance(user_id, str) or not user_id:
        raise InvalidCursorError("invalid cursor")
    payload = json.dumps(
        {"v": 1, "key": {"userId": user_id}},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_user_cursor(cursor: str | None) -> Optional[str]:
    """Strictly decode a cursor and return its Dynamo userId continuation."""
    if cursor is None or cursor == "":
        return None
    if not isinstance(cursor, str) or len(cursor) > MAX_CURSOR_LENGTH:
        raise InvalidCursorError("invalid cursor")
    if not _CURSOR_TOKEN.fullmatch(cursor):
        raise InvalidCursorError("invalid cursor")
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    except (ValueError, binascii.Error, UnicodeError) as exc:
        raise InvalidCursorError("invalid cursor") from exc
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidCursorError("invalid cursor") from exc
    if not isinstance(parsed, dict) or set(parsed) != {"v", "key"}:
        raise InvalidCursorError("invalid cursor")
    if parsed.get("v") != 1 or not isinstance(parsed.get("key"), dict):
        raise InvalidCursorError("invalid cursor")
    key = parsed["key"]
    if set(key) != {"userId"} or not isinstance(key.get("userId"), str) or not key["userId"]:
        raise InvalidCursorError("invalid cursor")
    if encode_user_cursor(key["userId"]) != cursor:
        raise InvalidCursorError("invalid cursor")
    return key["userId"]


@dataclass(frozen=True)
class UsersPage:
    items: list[UserProfile]
    next_cursor: Optional[str]


class AdminUserService:
    """Apply grant-only admin policy and guarded role changes."""

    def __init__(self, repo: UserProfileRepo, whitelist: Iterable[str] = ()) -> None:
        self.repo = repo
        self.whitelist = frozenset(str(v).strip().casefold() for v in whitelist if str(v).strip())
        self._lock = RLock()

    def is_whitelisted(self, profile: UserProfile) -> bool:
        return bool(profile.email and profile.email.casefold() in self.whitelist)

    def promote_claim(self, profile: UserProfile, claim_email: str | None) -> UserProfile:
        """Promote from verified claim email, never from stale stored email."""
        if claim_email and claim_email.casefold() in self.whitelist and profile.role != "admin":
            try:
                return self.repo.set_role(profile.user_id, "admin")
            except KeyError as exc:
                raise UserNotFoundError("User not found") from exc
        return profile

    def list_page(self, limit: int, cursor: str | None = None) -> UsersPage:
        start_after = decode_user_cursor(cursor)
        try:
            items, last_id = self.repo.list_page(limit=limit, start_after=start_after)
        except KeyError as exc:
            raise InvalidCursorError("invalid cursor") from exc
        return UsersPage(items=items, next_cursor=encode_user_cursor(last_id) if last_id else None)

    def change_role(self, user_id: str, role: Role) -> UserProfile:
        """Change a role while preserving whitelist and last-admin invariants."""
        with self._lock:
            target = self.repo.get(user_id)
            if target is None:
                raise UserNotFoundError("User not found")
            if role == "user" and target.role == "admin":
                if self.is_whitelisted(target):
                    raise WhitelistAdminError("Whitelist-managed admins cannot be demoted")
                guarded = getattr(self.repo, "change_role_guarded", None)
                if callable(guarded):
                    try:
                        return guarded(user_id, role)
                    except KeyError as exc:
                        raise UserNotFoundError("User not found") from exc
                admin_count = sum(1 for p in self.repo.iter_all() if p.role == "admin")
                if admin_count <= 1:
                    raise LastAdminError("At least one admin is required")
            try:
                return self.repo.set_role(user_id, role)
            except KeyError as exc:
                raise UserNotFoundError("User not found") from exc


__all__ = [
    "AdminUserError",
    "AdminUserService",
    "InvalidCursorError",
    "LastAdminError",
    "RoleConflictError",
    "UserNotFoundError",
    "UsersPage",
    "WhitelistAdminError",
    "decode_user_cursor",
    "encode_user_cursor",
    "parse_admin_emails",
]
