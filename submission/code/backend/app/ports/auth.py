"""Token verification port (Cognito JWKS in prod, fake in local/test)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


class UnauthorizedError(Exception):
    """Raised when a bearer token is missing, malformed, or fails verification."""

    def __init__(self, detail: str = "Unauthorized") -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class Claims:
    """Identity claims extracted from a verified token."""

    sub: str
    email: Optional[str] = None
    name: Optional[str] = None
    token_use: Optional[str] = None


class TokenVerifier(Protocol):
    """Port: verify a raw bearer token and return claims."""

    def verify(self, token: str) -> Claims:
        """Validate ``token`` and return claims.

        Raises:
            UnauthorizedError: if the token is empty, malformed, or invalid.
        """
        ...
