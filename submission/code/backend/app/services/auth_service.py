"""Auth application service: resolve user from token + bootstrap profile."""

from __future__ import annotations

from typing import Optional, Sequence

from app.ports.auth import TokenVerifier, UnauthorizedError
from app.ports.users import UserProfile, UserProfileRepo


class AuthService:
    """Orchestrates TokenVerifier + UserProfileRepo (no AWS SDK)."""

    def __init__(self, verifier: TokenVerifier, users: UserProfileRepo) -> None:
        self._verifier = verifier
        self._users = users

    def resolve_user(self, token: str) -> UserProfile:
        """Verify bearer token and return bootstrap profile (role from repo)."""
        claims = self._verifier.verify(token)
        return self._users.get_or_create(
            claims.sub,
            email=claims.email,
            name=claims.name,
        )

    def get_me(self, token: str) -> UserProfile:
        """Alias used by GET /api/auth/me."""
        return self.resolve_user(token)

    def update_settings(
        self,
        user_id: str,
        *,
        news_keywords: Optional[Sequence[str]] = None,
        email_opt_in: Optional[bool] = None,
        preferred_currency: Optional[str] = None,
    ) -> UserProfile:
        return self._users.update_settings(
            user_id,
            news_keywords=news_keywords,
            email_opt_in=email_opt_in,
            preferred_currency=preferred_currency,
        )


__all__ = ["AuthService", "UnauthorizedError"]
