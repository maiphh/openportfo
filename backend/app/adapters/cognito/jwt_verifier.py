"""Cognito JWKS-backed TokenVerifier (AUTH_MODE=cognito).

Validates RS256 ID tokens: iss, aud=client_id, exp, token_use preferably "id".
JWKS is fetched from the pool's well-known URL and cached briefly.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import jwt
from jwt import PyJWKClient

from app.ports.auth import Claims, UnauthorizedError

# Optional injectable HTTP GET for unit tests (returns JWKS JSON dict).
JwksFetcher = Callable[[str], dict[str, Any]]


class CognitoJwtVerifier:
    """Verify Cognito JWT (prefer ID token) via JWKS."""

    def __init__(
        self,
        region: str,
        user_pool_id: str,
        app_client_id: str,
        *,
        jwks_client: Optional[PyJWKClient] = None,
        jwks_fetcher: Optional[JwksFetcher] = None,
        jwks_cache_ttl: float = 300.0,
        clock_skew_leeway: float = 120.0,
    ) -> None:
        if not region or not user_pool_id or not app_client_id:
            raise ValueError(
                "CognitoJwtVerifier requires region, user_pool_id, and app_client_id"
            )
        self.region = region
        self.user_pool_id = user_pool_id
        self.app_client_id = app_client_id
        self.issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        self.jwks_url = f"{self.issuer}/.well-known/jwks.json"
        self._jwks_fetcher = jwks_fetcher
        self._jwks_client = jwks_client
        self._jwks_cache_ttl = jwks_cache_ttl
        # Tolerance (seconds) for IdP/API clock skew on iat/exp/nbf. Without
        # this, a just-minted token is rejected with "not yet valid (iat)"
        # whenever the Cognito clock runs slightly ahead of the API host
        # (typical on dev machines without tight NTP sync).
        self._clock_skew_leeway = clock_skew_leeway
        if self._jwks_client is None and self._jwks_fetcher is None:
            # Live JWKS client with short lifespan cache
            self._jwks_client = PyJWKClient(
                self.jwks_url,
                cache_jwk_set=True,
                lifespan=int(jwks_cache_ttl),
            )

    def verify(self, token: str) -> Claims:
        if not token or not isinstance(token, str):
            raise UnauthorizedError("Missing or empty token")

        try:
            signing_key = self._get_signing_key(token)
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.app_client_id,
                issuer=self.issuer,
                leeway=self._clock_skew_leeway,
                options={
                    "require": ["exp", "iss", "sub"],
                    "verify_at_hash": False,
                },
            )
        except UnauthorizedError:
            raise
        except jwt.PyJWTError as exc:
            raise UnauthorizedError(f"Invalid token: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 — map unexpected JWKS/network errors
            raise UnauthorizedError(f"Token verification failed: {exc}") from exc

        token_use = payload.get("token_use")
        # Prefer ID tokens; reject access tokens when token_use is present and not "id"
        if token_use is not None and token_use != "id":
            raise UnauthorizedError("Expected Cognito ID token (token_use=id)")

        sub = payload.get("sub")
        if not sub:
            raise UnauthorizedError("Token missing sub claim")

        return Claims(
            sub=str(sub),
            email=payload.get("email"),
            name=payload.get("name"),
            token_use=token_use,
        )

    def _get_signing_key(self, token: str) -> Any:
        if self._jwks_fetcher is not None:
            return self._signing_key_from_fetcher(token)
        assert self._jwks_client is not None
        try:
            return self._jwks_client.get_signing_key_from_jwt(token).key
        except Exception as exc:  # noqa: BLE001
            raise UnauthorizedError(f"Unable to resolve signing key: {exc}") from exc

    def _signing_key_from_fetcher(self, token: str) -> Any:
        """Resolve RSA key via injectable JWKS JSON (unit tests)."""
        assert self._jwks_fetcher is not None
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise UnauthorizedError(f"Invalid token header: {exc}") from exc
        kid = header.get("kid")
        if not kid:
            raise UnauthorizedError("Token missing kid header")

        jwks = self._jwks_fetcher(self.jwks_url)
        keys = jwks.get("keys") or []
        matching = next((k for k in keys if k.get("kid") == kid), None)
        if matching is None:
            raise UnauthorizedError("Signing key not found in JWKS")
        try:
            return jwt.algorithms.RSAAlgorithm.from_jwk(matching)
        except Exception as exc:  # noqa: BLE001
            raise UnauthorizedError(f"Invalid JWK: {exc}") from exc
