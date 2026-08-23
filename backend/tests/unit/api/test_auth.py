"""Sprint 02: auth ports, profile bootstrap, /api/auth/me, /api/settings, admin dep."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends
from fastapi.testclient import TestClient

from app.adapters.cognito.jwt_verifier import CognitoJwtVerifier
from app.core.deps import (
    get_current_user,
    get_token_verifier,
    get_user_profile_repo,
    require_admin,
    set_user_profile_repo,
)
from app.main import create_app
from app.ports.auth import UnauthorizedError
from app.ports.users import UserProfile
from app.services.auth_service import AuthService
from tests.fakes.auth import FakeTokenVerifier
from tests.fakes.users import InMemoryUserProfileRepo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_header(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{user_id}"}


def _make_client(
    repo: InMemoryUserProfileRepo | None = None,
    verifier: FakeTokenVerifier | None = None,
) -> tuple[TestClient, InMemoryUserProfileRepo]:
    """App client with isolated in-memory profile repo (and optional verifier)."""
    profile_repo = repo or InMemoryUserProfileRepo()
    set_user_profile_repo(profile_repo)
    app = create_app()

    if verifier is not None:
        app.dependency_overrides[get_token_verifier] = lambda: verifier

    app.dependency_overrides[get_user_profile_repo] = lambda: profile_repo

    return TestClient(app), profile_repo


@pytest.fixture(autouse=True)
def _reset_repo() -> Any:
    set_user_profile_repo(None)
    yield
    set_user_profile_repo(None)


# ---------------------------------------------------------------------------
# 1. FakeTokenVerifier unit
# ---------------------------------------------------------------------------


def test_fake_token_verifier_accepts_fake_prefix() -> None:
    v = FakeTokenVerifier()
    claims = v.verify("fake:user-123")
    assert claims.sub == "user-123"
    assert claims.token_use == "id"


def test_fake_token_verifier_maps_email_name() -> None:
    v = FakeTokenVerifier(
        emails={"u1": "a@example.com"},
        names={"u1": "Ada"},
    )
    claims = v.verify("fake:u1")
    assert claims.sub == "u1"
    assert claims.email == "a@example.com"
    assert claims.name == "Ada"


def test_fake_token_verifier_rejects_empty() -> None:
    v = FakeTokenVerifier()
    with pytest.raises(UnauthorizedError):
        v.verify("")
    with pytest.raises(UnauthorizedError):
        v.verify("fake:")


def test_fake_token_verifier_rejects_invalid_prefix() -> None:
    v = FakeTokenVerifier()
    with pytest.raises(UnauthorizedError):
        v.verify("bearer-not-fake")
    with pytest.raises(UnauthorizedError):
        v.verify("user-123")


# ---------------------------------------------------------------------------
# 2. InMemory profile get_or_create
# ---------------------------------------------------------------------------


def test_inmemory_get_or_create_defaults() -> None:
    repo = InMemoryUserProfileRepo()
    p = repo.get_or_create("u1", email="e@x.com", name="N")
    assert p.user_id == "u1"
    assert p.email == "e@x.com"
    assert p.name == "N"
    assert p.role == "user"
    assert p.news_keywords == []
    assert p.email_opt_in is False
    assert not p.preferred_currency
    assert repo.get("u1") is not None


def test_inmemory_get_or_create_idempotent() -> None:
    repo = InMemoryUserProfileRepo()
    a = repo.get_or_create("u1", email="e@x.com")
    b = repo.get_or_create("u1", email="other@x.com")
    assert a.user_id == b.user_id
    assert b.email == "e@x.com"  # first email kept
    assert a.created_at == b.created_at


def test_inmemory_set_role_and_update_settings() -> None:
    repo = InMemoryUserProfileRepo()
    repo.get_or_create("u1")
    admin = repo.set_role("u1", "admin")
    assert admin.role == "admin"
    updated = repo.update_settings(
        "u1",
        news_keywords=["btc", "vnd"],
        email_opt_in=True,
        preferred_currency="VND",
    )
    assert updated.news_keywords == ["btc", "vnd"]
    assert updated.email_opt_in is True
    assert updated.preferred_currency == "VND"
    assert updated.role == "admin"  # role unchanged by settings


# ---------------------------------------------------------------------------
# AuthService
# ---------------------------------------------------------------------------


def test_auth_service_resolve_user() -> None:
    repo = InMemoryUserProfileRepo()
    svc = AuthService(FakeTokenVerifier(emails={"x": "x@y.com"}), repo)
    profile = svc.resolve_user("fake:x")
    assert profile.user_id == "x"
    assert profile.email == "x@y.com"
    assert profile.role == "user"


# ---------------------------------------------------------------------------
# 3–6. API: 401, me bootstrap, idempotent, PUT settings
# ---------------------------------------------------------------------------


def test_me_missing_authorization_401() -> None:
    client, _ = _make_client()
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    assert "detail" in r.json()


def test_me_invalid_token_401() -> None:
    client, _ = _make_client()
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not-valid"})
    assert r.status_code == 401
    assert "detail" in r.json()


def test_me_invalid_scheme_401() -> None:
    client, _ = _make_client()
    r = client.get("/api/auth/me", headers={"Authorization": "Basic fake:u1"})
    assert r.status_code == 401


def test_me_creates_profile() -> None:
    client, repo = _make_client(
        verifier=FakeTokenVerifier(emails={"alice": "alice@example.com"}, names={"alice": "Alice"})
    )
    r = client.get("/api/auth/me", headers=_auth_header("alice"))
    assert r.status_code == 200
    body = r.json()
    assert body["userId"] == "alice"
    assert body["email"] == "alice@example.com"
    assert body["name"] == "Alice"
    assert body["role"] == "user"
    assert body["newsKeywords"] == []
    assert body["emailOptIn"] is False
    assert not body["preferredCurrency"]
    assert "createdAt" in body
    assert "updatedAt" in body
    assert repo.get("alice") is not None


def test_me_idempotent() -> None:
    client, repo = _make_client()
    r1 = client.get("/api/auth/me", headers=_auth_header("bob"))
    r2 = client.get("/api/auth/me", headers=_auth_header("bob"))
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["userId"] == r2.json()["userId"] == "bob"
    assert r1.json()["createdAt"] == r2.json()["createdAt"]
    # single profile in store
    assert repo.get("bob") is not None
    assert len(repo._profiles) == 1  # noqa: SLF001 — intentional test inspection


def test_put_settings_persists() -> None:
    client, repo = _make_client()
    headers = _auth_header("carol")
    client.get("/api/auth/me", headers=headers)
    r = client.put(
        "/api/settings",
        headers=headers,
        json={
            "newsKeywords": ["ethereum", "vnindex"],
            "emailOptIn": True,
            "preferredCurrency": "VND",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["newsKeywords"] == ["ethereum", "vnindex"]
    assert body["emailOptIn"] is True
    assert body["preferredCurrency"] == "VND"
    assert body["userId"] == "carol"

    stored = repo.get("carol")
    assert stored is not None
    assert stored.news_keywords == ["ethereum", "vnindex"]
    assert stored.email_opt_in is True
    assert stored.preferred_currency == "VND"

    # still visible on me
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["newsKeywords"] == ["ethereum", "vnindex"]
    assert me["preferredCurrency"] == "VND"


def test_profile_and_settings_include_avatar_fields_and_support_explicit_clear() -> None:
    client, repo = _make_client()
    headers = _auth_header("avatar-user")
    client.get("/api/auth/me", headers=headers)
    saved = client.put(
        "/api/settings",
        headers=headers,
        json={
            "avatarStyle": "big-smile",
            "avatarSeed": "Ada",
            "avatarColor": "#abc",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["avatarStyle"] == "big-smile"
    assert saved.json()["avatarSeed"] == "Ada"
    assert saved.json()["avatarColor"] == "aabbcc"
    assert client.get("/api/settings", headers=headers).json()["avatarStyle"] == "big-smile"

    cleared = client.put(
        "/api/settings",
        headers=headers,
        json={"avatarStyle": None, "avatarSeed": None, "avatarColor": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["avatarStyle"] is None
    assert cleared.json()["avatarSeed"] is None
    assert cleared.json()["avatarColor"] is None
    stored = repo.get("avatar-user")
    assert stored is not None
    assert stored.avatar_style is None
    assert stored.avatar_seed is None
    assert stored.avatar_color is None


def test_settings_validation_returns_field_errors() -> None:
    client, _ = _make_client()
    headers = _auth_header("validation-user")
    client.get("/api/auth/me", headers=headers)
    response = client.put(
        "/api/settings",
        headers=headers,
        json={"newsKeywords": None, "avatarStyle": "not-a-style"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "validation_error"
    assert set(response.json()["detail"]["errors"]) == {"newsKeywords", "avatarStyle"}


def test_settings_malformed_json_fields_use_shared_400_validation_contract() -> None:
    client, _ = _make_client()
    headers = _auth_header("raw-validation-user")
    client.get("/api/auth/me", headers=headers)
    response = client.put(
        "/api/settings",
        headers=headers,
        json={"newsKeywords": 42, "unexpected": True},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == {
        "code": "validation_error",
        "errors": {
            "newsKeywords": "must be an array of strings",
            "unexpected": "is not supported",
        },
    }


def test_get_settings_returns_slice() -> None:
    client, _ = _make_client()
    headers = _auth_header("dana")
    client.get("/api/auth/me", headers=headers)
    client.put(
        "/api/settings",
        headers=headers,
        json={"newsKeywords": ["btc"], "emailOptIn": True, "preferredCurrency": "USD"},
    )
    r = client.get("/api/settings", headers=headers)
    assert r.status_code == 200
    assert r.json() == {
        "newsKeywords": ["btc"],
        "emailOptIn": True,
        "preferredCurrency": "USD",
        "avatarStyle": None,
        "avatarSeed": None,
        "avatarColor": None,
    }


def test_get_settings_requires_auth() -> None:
    client, _ = _make_client()
    assert client.get("/api/settings").status_code == 401


def test_put_settings_requires_auth() -> None:
    client, _ = _make_client()
    r = client.put("/api/settings", json={"emailOptIn": True})
    assert r.status_code == 401


def test_debug_make_current_user_admin_in_local_mode() -> None:
    client, repo = _make_client()
    response = client.post(
        "/api/debug/auth/make-admin",
        headers=_auth_header("local-admin"),
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert repo.get("local-admin").role == "admin"


def test_debug_make_admin_hidden_in_production() -> None:
    client, repo = _make_client()
    from app.core.config import Settings, get_settings

    client.app.dependency_overrides[get_settings] = lambda: Settings(
        APP_ENV="prod",
        STORAGE_BACKEND="memory",
        USE_AWS_ADAPTERS=False,
        _env_file=None,
    )
    response = client.post(
        "/api/debug/auth/make-admin",
        headers=_auth_header("prod-user"),
    )
    assert response.status_code == 404
    assert repo.get("prod-user").role == "user"


# ---------------------------------------------------------------------------
# 7. require_admin 403 / 200
# ---------------------------------------------------------------------------


def test_require_admin_403_for_user_role() -> None:
    client, repo = _make_client()
    app = client.app

    @app.get("/_test/admin-only")
    def _admin_only(user: UserProfile = Depends(require_admin)) -> dict[str, str]:
        return {"userId": user.user_id, "role": user.role}

    # bootstrap as normal user
    client.get("/api/auth/me", headers=_auth_header("dave"))
    r = client.get("/_test/admin-only", headers=_auth_header("dave"))
    assert r.status_code == 403
    assert r.json()["detail"]


def test_require_admin_200_for_admin_role() -> None:
    client, repo = _make_client()
    app = client.app

    @app.get("/_test/admin-only")
    def _admin_only(user: UserProfile = Depends(require_admin)) -> dict[str, str]:
        return {"userId": user.user_id, "role": user.role}

    client.get("/api/auth/me", headers=_auth_header("erin"))
    repo.set_role("erin", "admin")
    r = client.get("/_test/admin-only", headers=_auth_header("erin"))
    assert r.status_code == 200
    assert r.json() == {"userId": "erin", "role": "admin"}


# ---------------------------------------------------------------------------
# CognitoJwtVerifier with mocked JWKS
# ---------------------------------------------------------------------------


def _rsa_keypair() -> tuple[Any, dict[str, Any]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()

    def _b64url_uint(val: int) -> str:
        import base64

        length = (val.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(val.to_bytes(length, "big")).rstrip(b"=").decode("ascii")

    jwk = {
        "kty": "RSA",
        "kid": "test-kid-1",
        "use": "sig",
        "alg": "RS256",
        "n": _b64url_uint(public_numbers.n),
        "e": _b64url_uint(public_numbers.e),
    }
    return private_key, jwk


def _mint_cognito_token(
    private_key: Any,
    *,
    sub: str = "cognito-sub-1",
    client_id: str = "app-client-id",
    region: str = "us-east-1",
    pool_id: str = "us-east-1_POOL",
    token_use: str = "id",
    exp_delta_seconds: int = 3600,
    email: str = "c@example.com",
    extra_headers: dict[str, str] | None = None,
) -> str:
    issuer = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "name": "Cognito User",
        "token_use": token_use,
        "iss": issuer,
        "aud": client_id,
        "exp": now + timedelta(seconds=exp_delta_seconds),
        "iat": now,
    }
    headers = {"kid": "test-kid-1", "alg": "RS256"}
    if extra_headers:
        headers.update(extra_headers)
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)


def test_cognito_verifier_accepts_valid_id_token() -> None:
    private_key, jwk = _rsa_keypair()
    region, pool_id, client_id = "us-east-1", "us-east-1_POOL", "app-client-id"
    token = _mint_cognito_token(
        private_key, client_id=client_id, region=region, pool_id=pool_id
    )
    verifier = CognitoJwtVerifier(
        region=region,
        user_pool_id=pool_id,
        app_client_id=client_id,
        jwks_fetcher=lambda _url: {"keys": [jwk]},
    )
    claims = verifier.verify(token)
    assert claims.sub == "cognito-sub-1"
    assert claims.email == "c@example.com"
    assert claims.token_use == "id"


def test_cognito_verifier_rejects_access_token_use() -> None:
    private_key, jwk = _rsa_keypair()
    region, pool_id, client_id = "us-east-1", "us-east-1_POOL", "app-client-id"
    token = _mint_cognito_token(
        private_key,
        client_id=client_id,
        region=region,
        pool_id=pool_id,
        token_use="access",
    )
    verifier = CognitoJwtVerifier(
        region=region,
        user_pool_id=pool_id,
        app_client_id=client_id,
        jwks_fetcher=lambda _url: {"keys": [jwk]},
    )
    with pytest.raises(UnauthorizedError, match="ID token"):
        verifier.verify(token)


def test_cognito_verifier_rejects_wrong_audience() -> None:
    private_key, jwk = _rsa_keypair()
    region, pool_id = "us-east-1", "us-east-1_POOL"
    token = _mint_cognito_token(
        private_key, client_id="other-client", region=region, pool_id=pool_id
    )
    verifier = CognitoJwtVerifier(
        region=region,
        user_pool_id=pool_id,
        app_client_id="app-client-id",
        jwks_fetcher=lambda _url: {"keys": [jwk]},
    )
    with pytest.raises(UnauthorizedError):
        verifier.verify(token)


def test_cognito_verifier_rejects_expired() -> None:
    private_key, jwk = _rsa_keypair()
    region, pool_id, client_id = "us-east-1", "us-east-1_POOL", "app-client-id"
    token = _mint_cognito_token(
        private_key,
        client_id=client_id,
        region=region,
        pool_id=pool_id,
        exp_delta_seconds=-10,
    )
    verifier = CognitoJwtVerifier(
        region=region,
        user_pool_id=pool_id,
        app_client_id=client_id,
        jwks_fetcher=lambda _url: {"keys": [jwk]},
    )
    with pytest.raises(UnauthorizedError):
        verifier.verify(token)


def test_get_current_user_via_dependency() -> None:
    """Smoke: get_current_user returns profile with role from repo."""
    repo = InMemoryUserProfileRepo()
    set_user_profile_repo(repo)
    app = create_app()
    app.dependency_overrides[get_user_profile_repo] = lambda: repo
    app.dependency_overrides[get_token_verifier] = lambda: FakeTokenVerifier()

    @app.get("/_test/whoami")
    def whoami(user: UserProfile = Depends(get_current_user)) -> dict[str, str]:
        return {"userId": user.user_id, "role": user.role}

    client = TestClient(app)
    r = client.get("/_test/whoami", headers=_auth_header("frank"))
    assert r.status_code == 200
    assert r.json() == {"userId": "frank", "role": "user"}
