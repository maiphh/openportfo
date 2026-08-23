from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import clear_settings_cache
from app.core.deps import (
    get_token_verifier,
    set_settings_repo,
    set_user_profile_repo,
)
from app.main import create_app
from tests.fakes.admin import InMemorySettingsRepo
from tests.fakes.auth import FakeTokenVerifier
from tests.fakes.users import InMemoryUserProfileRepo


def _auth(uid: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{uid}"}


@pytest.fixture(autouse=True)
def _reset() -> None:
    set_user_profile_repo(None)
    set_settings_repo(None)
    clear_settings_cache()
    yield
    set_user_profile_repo(None)
    set_settings_repo(None)
    clear_settings_cache()


def _setup(*, verifier: FakeTokenVerifier | None = None) -> tuple[TestClient, InMemoryUserProfileRepo]:
    repo = InMemoryUserProfileRepo()
    set_user_profile_repo(repo)
    set_settings_repo(InMemorySettingsRepo())
    app = create_app()
    if verifier is not None:
        app.dependency_overrides[get_token_verifier] = lambda: verifier
    return TestClient(app), repo


def test_admin_users_list_schema_pagination_and_mutations() -> None:
    client, repo = _setup()
    repo.get_or_create("admin", email="admin@example.com", name="Admin")
    repo.set_role("admin", "admin")
    repo.get_or_create("target", email="target@example.com", name="Target")
    response = client.get("/api/admin/users?limit=1", headers=_auth("admin"))
    assert response.status_code == 200
    assert response.json()["items"][0]["userId"] == "admin"
    assert response.json()["items"][0]["isCurrentUser"] is True
    assert response.json()["nextCursor"]
    cursor = response.json()["nextCursor"]
    second = client.get(f"/api/admin/users?limit=10&cursor={cursor}", headers=_auth("admin"))
    assert second.status_code == 200
    assert second.json()["items"][0]["userId"] == "target"
    changed = client.put(
        "/api/admin/users/target/role",
        headers=_auth("admin"),
        json={"role": "admin"},
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == "admin"
    settings = client.put(
        "/api/admin/users/target/settings",
        headers=_auth("admin"),
        json={"avatarColor": "#abc", "newsKeywords": [" BTC ", "btc"]},
    )
    assert settings.status_code == 200
    assert settings.json()["avatarColor"] == "aabbcc"
    assert settings.json()["newsKeywords"] == ["BTC"]


def test_admin_users_reject_bad_cursor_and_non_admin() -> None:
    client, repo = _setup()
    repo.get_or_create("u1")
    assert client.get("/api/admin/users", headers=_auth("u1")).status_code == 403
    repo.set_role("u1", "admin")
    bad = client.get("/api/admin/users?cursor=not-valid", headers=_auth("u1"))
    assert bad.status_code == 400
    assert bad.json()["detail"] == {"code": "invalid_cursor"}


def test_whitelist_promotes_first_auth_me_and_is_grant_only(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_EMAILS", " ADMIN@EXAMPLE.COM ")
    clear_settings_cache()
    verifier = FakeTokenVerifier(
        emails={"u1": "admin@example.com"},
        names={"u1": "A"},
    )
    client, repo = _setup(verifier=verifier)
    response = client.get("/api/auth/me", headers=_auth("u1"))
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert repo.get("u1").role == "admin"
    demote = client.put(
        "/api/admin/users/u1/role",
        headers=_auth("u1"),
        json={"role": "user"},
    )
    assert demote.status_code == 400
    assert demote.json()["detail"]["code"] == "whitelist_admin"


def test_admin_default_user_can_clear_blank_keywords_and_avatar_fields() -> None:
    client, repo = _setup()
    repo.get_or_create("admin", email="admin@example.com", name="Admin")
    repo.set_role("admin", "admin")
    repo.get_or_create("target", email="target@example.com", name="Target")
    response = client.put(
        "/api/admin/users/target/settings",
        headers=_auth("admin"),
        json={"newsKeywords": [], "avatarStyle": None, "avatarSeed": None, "avatarColor": None},
    )
    assert response.status_code == 200
    assert response.json()["newsKeywords"] == []
    assert response.json()["avatarStyle"] is None


def test_admin_malformed_user_settings_are_400_field_errors() -> None:
    client, repo = _setup()
    repo.get_or_create("admin", email="admin@example.com", name="Admin")
    repo.set_role("admin", "admin")
    repo.get_or_create("target")
    response = client.put(
        "/api/admin/users/target/settings",
        headers=_auth("admin"),
        json={"newsKeywords": 42, "unknown": True},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "validation_error"
    assert set(response.json()["detail"]["errors"]) == {"newsKeywords", "unknown"}
