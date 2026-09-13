"""Local object-storage inspector."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.deps import (
    get_object_storage,
    get_user_profile_repo,
    set_object_storage,
    set_user_profile_repo,
)
from app.main import create_app
from tests.fakes.storage import InMemoryObjectStorage
from tests.fakes.users import InMemoryUserProfileRepo


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{user_id}"}


def _client() -> tuple[TestClient, InMemoryObjectStorage, InMemoryUserProfileRepo]:
    storage = InMemoryObjectStorage()
    profiles = InMemoryUserProfileRepo()
    set_object_storage(storage)
    set_user_profile_repo(profiles)
    admin = profiles.get_or_create("admin")
    profiles.set_role(admin.user_id, "admin")
    profiles.get_or_create("alice")
    app = create_app()
    app.dependency_overrides[get_object_storage] = lambda: storage
    app.dependency_overrides[get_user_profile_repo] = lambda: profiles
    return TestClient(app), storage, profiles


@pytest.fixture(autouse=True)
def _reset() -> Any:
    set_object_storage(None)
    set_user_profile_repo(None)
    yield
    set_object_storage(None)
    set_user_profile_repo(None)


def test_s3_viewer_requires_admin() -> None:
    client, _, _ = _client()
    assert client.get("/api/dev/s3").status_code == 401
    assert client.get("/api/dev/s3", headers=_auth("alice")).status_code == 403


def test_list_and_get_cached_profile() -> None:
    client, storage, _ = _client()
    storage.put_json("profile/crypto/bitcoin.json", {"assetId": "bitcoin", "name": "Bitcoin"})
    storage.put_json("history/crypto/bitcoin/30d.json", {"points": []})
    listed = client.get("/api/dev/s3", headers=_auth("admin"), params={"prefix": "profile/"})
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["backend"] == "memory"
    assert body["keys"] == ["profile/crypto/bitcoin.json"]
    obj = client.get(
        "/api/dev/s3/object",
        headers=_auth("admin"),
        params={"key": "profile/crypto/bitcoin.json"},
    )
    assert obj.status_code == 200
    assert obj.json()["body"]["name"] == "Bitcoin"


def test_rejects_unknown_prefix_and_missing_key() -> None:
    client, _, _ = _client()
    assert (
        client.get("/api/dev/s3", headers=_auth("admin"), params={"prefix": "secrets/"}).status_code
        == 400
    )
    missing = client.get(
        "/api/dev/s3/object",
        headers=_auth("admin"),
        params={"key": "profile/crypto/missing.json"},
    )
    assert missing.status_code == 404
