"""Sprint 09: admin settings, RSS, job runs."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.deps import (
    set_job_runs_repo,
    set_rss_sources_repo,
    set_settings_repo,
    set_user_profile_repo,
)
from app.main import create_app
from tests.fakes.admin import (
    InMemoryJobRunsRepo,
    InMemoryRssSourcesRepo,
    InMemorySettingsRepo,
)
from tests.fakes.users import InMemoryUserProfileRepo


def _auth(uid: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{uid}"}


def _setup() -> tuple[TestClient, InMemoryUserProfileRepo]:
    profiles = InMemoryUserProfileRepo()
    set_user_profile_repo(profiles)
    set_settings_repo(InMemorySettingsRepo())
    set_rss_sources_repo(InMemoryRssSourcesRepo())
    set_job_runs_repo(InMemoryJobRunsRepo())
    return TestClient(create_app()), profiles


def test_user_forbidden_on_admin() -> None:
    client, profiles = _setup()
    profiles.get_or_create("u1", email="u@test.com", name="U")
    for path in (
        "/api/admin/settings",
        "/api/admin/rss-sources",
        "/api/admin/job-runs",
    ):
        r = client.get(path, headers=_auth("u1"))
        assert r.status_code == 403, path


def test_admin_get_put_settings() -> None:
    client, profiles = _setup()
    profiles.get_or_create("admin1", email="a@test.com", name="A")
    profiles.set_role("admin1", "admin")
    r = client.get("/api/admin/settings", headers=_auth("admin1"))
    assert r.status_code == 200
    jobs = r.json()["jobs"]
    assert "news" in jobs
    assert "snapshot" in jobs
    assert "email" in jobs
    assert "price" in jobs
    r2 = client.put(
        "/api/admin/settings",
        headers=_auth("admin1"),
        json={
            "version": 0,
            "emailEnabled": True,
            "jobs": {"news": False, "snapshot": True, "email": False, "price": False},
        },
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["emailEnabled"] is True
    assert body["jobs"]["news"] is False
    assert body["jobs"]["price"] is False


def test_admin_chat_settings_are_versioned_and_effective() -> None:
    client, profiles = _setup()
    profiles.get_or_create("admin1", email="a@test.com", name="A")
    profiles.set_role("admin1", "admin")
    current = client.get("/api/admin/settings", headers=_auth("admin1"))
    assert current.status_code == 200
    assert current.json()["version"] == 0
    updated = client.put(
        "/api/admin/settings",
        headers=_auth("admin1"),
        json={
            "version": 0,
            "chat": {"fallbackModels": [], "temperature": 0.5},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 1
    assert updated.json()["chat"]["overrides"]["fallbackModels"] == []
    stale = client.put(
        "/api/admin/settings",
        headers=_auth("admin1"),
        json={"version": 0, "chat": {"temperature": 1}},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "settings_conflict"


def test_rss_crud() -> None:
    client, profiles = _setup()
    profiles.get_or_create("admin1", email="a@test.com", name="A")
    profiles.set_role("admin1", "admin")
    r = client.post(
        "/api/admin/rss-sources",
        headers=_auth("admin1"),
        json={"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
    )
    assert r.status_code == 201
    sid = r.json()["sourceId"]
    r2 = client.get("/api/admin/rss-sources", headers=_auth("admin1"))
    assert r2.status_code == 200
    assert len(r2.json()) == 1
    r3 = client.delete(f"/api/admin/rss-sources/{sid}", headers=_auth("admin1"))
    assert r3.status_code == 204
    assert client.get("/api/admin/rss-sources", headers=_auth("admin1")).json() == []


def test_job_runs_empty() -> None:
    client, profiles = _setup()
    profiles.get_or_create("admin1", email="a@test.com", name="A")
    profiles.set_role("admin1", "admin")
    r = client.get("/api/admin/job-runs", headers=_auth("admin1"))
    assert r.status_code == 200
    assert r.json() == []
