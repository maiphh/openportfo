"""In-memory auth adapter for local development and tests."""

from __future__ import annotations

from typing import Mapping, Optional

from app.ports.auth import Claims, UnauthorizedError


class FakeTokenVerifier:
    """Accepts tokens of the form ``fake:<userId>`` only."""

    PREFIX = "fake:"

    def __init__(
        self,
        *,
        emails: Optional[Mapping[str, str]] = None,
        names: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._emails = dict(emails or {})
        self._names = dict(names or {})

    def verify(self, token: str) -> Claims:
        if not token or not isinstance(token, str):
            raise UnauthorizedError("Missing or empty token")
        if not token.startswith(self.PREFIX):
            raise UnauthorizedError("Invalid token")
        user_id = token[len(self.PREFIX) :]
        if not user_id:
            raise UnauthorizedError("Invalid token")
        return Claims(
            sub=user_id,
            email=self._emails.get(user_id),
            name=self._names.get(user_id),
            token_use="id",
        )

