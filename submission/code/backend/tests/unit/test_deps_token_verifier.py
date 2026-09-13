"""Process-local token-verifier caching in the dependency layer."""

from __future__ import annotations

import pytest

from app.adapters.cognito.jwt_verifier import CognitoJwtVerifier
from app.adapters.memory.auth import FakeTokenVerifier
from app.core.config import Settings
from app.core.deps import get_token_verifier, reset_token_verifier_cache


def _settings(**values: str) -> Settings:
    return Settings(_env_file=None, **values)


def _cognito_settings(
    *,
    region: str = "us-east-1",
    pool_id: str = "us-east-1_pool",
    client_id: str = "client-id",
) -> Settings:
    return _settings(
        AUTH_MODE="cognito",
        COGNITO_REGION=region,
        COGNITO_USER_POOL_ID=pool_id,
        COGNITO_APP_CLIENT_ID=client_id,
    )


@pytest.fixture(autouse=True)
def _reset_verifiers() -> None:
    reset_token_verifier_cache()
    yield
    reset_token_verifier_cache()


def test_fake_verifier_is_stable_across_dependency_calls() -> None:
    first = get_token_verifier(_settings(AUTH_MODE="fake"))
    second = get_token_verifier(_settings(AUTH_MODE="fake", AWS_REGION="eu-west-1"))

    assert isinstance(first, FakeTokenVerifier)
    assert second is first
    assert first.verify("fake:stable-user").sub == "stable-user"


def test_cognito_verifier_is_reused_for_same_effective_configuration() -> None:
    first = get_token_verifier(_cognito_settings())
    second = get_token_verifier(_cognito_settings())

    assert isinstance(first, CognitoJwtVerifier)
    assert second is first
    assert first.issuer == "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_pool"


def test_cognito_verifier_cache_key_separates_pool_configuration() -> None:
    first = get_token_verifier(_cognito_settings(pool_id="us-east-1_pool_a"))
    second = get_token_verifier(_cognito_settings(pool_id="us-east-1_pool_b"))

    assert isinstance(first, CognitoJwtVerifier)
    assert isinstance(second, CognitoJwtVerifier)
    assert second is not first
    assert first.issuer != second.issuer


def test_reset_token_verifier_cache_forces_new_instance() -> None:
    settings = _cognito_settings()
    first = get_token_verifier(settings)

    reset_token_verifier_cache()
    second = get_token_verifier(settings)

    assert second is not first


def test_same_cognito_verifier_reuses_its_jwks_client(monkeypatch) -> None:
    class CountingJwksClient:
        instances = 0

        def __init__(self, url: str, *, cache_jwk_set: bool, lifespan: int) -> None:
            type(self).instances += 1
            self.url = url
            self.cache_jwk_set = cache_jwk_set
            self.lifespan = lifespan

    monkeypatch.setattr(
        "app.adapters.cognito.jwt_verifier.PyJWKClient",
        CountingJwksClient,
    )

    first = get_token_verifier(_cognito_settings())
    second = get_token_verifier(_cognito_settings())

    assert CountingJwksClient.instances == 1
    assert first is second
    assert first._jwks_client is second._jwks_client  # noqa: SLF001 - cache assertion
    assert first._jwks_client.cache_jwk_set is True  # noqa: SLF001
