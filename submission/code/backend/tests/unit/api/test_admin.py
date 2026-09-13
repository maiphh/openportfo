"""Sprint 09: admin settings, RSS, job runs."""

from __future__ import annotations

import pytest
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
    r = client.post("/api/admin/jobs/news/run", headers=_auth("u1"))
    assert r.status_code == 403


def test_admin_run_news_job_force_and_dedupes() -> None:
    from app.adapters.memory.news import InMemoryNewsRepo
    from app.core.deps import (
        get_rss_sources_repo,
        get_settings_repo,
        set_news_repo,
        set_rss_fetcher,
    )
    from app.ports.admin import RssSource, SystemSettings
    from app.ports.rss import RssItem
    from tests.fakes.rss import FakeRssFetcher

    client, profiles = _setup()
    profiles.get_or_create("admin1", email="a@test.com", name="A")
    profiles.set_role("admin1", "admin")

    feed = "https://example.com/feed.xml"
    news = InMemoryNewsRepo()
    set_news_repo(news)
    set_rss_fetcher(
        FakeRssFetcher({feed: [RssItem(title="Bitcoin rises", url="https://ex/btc")]})
    )
    get_settings_repo().save(SystemSettings(jobs_news=False))
    get_rss_sources_repo().create(
        RssSource(source_id="s1", name="Ex", url=feed, enabled=True)
    )

    r1 = client.post("/api/admin/jobs/news/run", headers=_auth("admin1"))
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["jobType"] == "news"
    assert body1["status"] == "success"
    assert body1["counts"]["written"] == 1
    assert len(news.list_recent(10)) == 1

    r2 = client.post("/api/admin/jobs/news/run", headers=_auth("admin1"))
    assert r2.status_code == 200
    assert r2.json()["counts"]["written"] == 1
    assert len(news.list_recent(10)) == 1
    assert news.put_calls == 2
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


def test_memory_rejects_unsafe_rss_urls() -> None:
    """InMemoryRssSourcesRepo shares assert_public_http_url with Dynamo (D2)."""
    client, profiles = _setup()
    profiles.get_or_create("admin1", email="a@test.com", name="A")
    profiles.set_role("admin1", "admin")
    for url in (
        "https://127.0.0.1/feed.xml",
        "http://localhost/rss",
        "https://10.1.2.3/rss",
        "https://169.254.169.254/latest",
        "ftp://example.com/feed",
    ):
        r = client.post(
            "/api/admin/rss-sources",
            headers=_auth("admin1"),
            json={"name": "Bad", "url": url},
        )
        assert r.status_code == 400, url


def test_memory_and_dynamo_reject_same_unsafe_rss_urls() -> None:
    from app.adapters.dynamodb.rss import _validate_url as dynamo_validate
    from app.adapters.memory.admin import AdminValidationError, InMemoryRssSourcesRepo
    from app.ports.admin import RssSource

    repo = InMemoryRssSourcesRepo()
    unsafe = [
        "https://127.0.0.1/feed.xml",
        "http://localhost/rss",
        "https://192.168.0.1/rss",
        "https://169.254.1.1/meta",
    ]
    for url in unsafe:
        with pytest.raises(AdminValidationError):
            repo.create(RssSource(source_id="x", name="n", url=url, enabled=True))
        with pytest.raises(AdminValidationError):
            dynamo_validate(url)
