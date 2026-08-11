"""Sprint 08: news list + filter."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.deps import (
    set_news_repo,
    set_news_service,
    set_user_profile_repo,
)
from app.main import create_app
from app.ports.news import NewsItem
from app.services.news_service import NewsService
from tests.fakes.news import InMemoryNewsRepo
from tests.fakes.users import InMemoryUserProfileRepo


def _auth(uid: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{uid}"}


def _setup(repo: InMemoryNewsRepo | None = None) -> tuple[TestClient, InMemoryNewsRepo, InMemoryUserProfileRepo]:
    profiles = InMemoryUserProfileRepo()
    repo = repo or InMemoryNewsRepo()
    set_user_profile_repo(profiles)
    set_news_repo(repo)
    set_news_service(NewsService(repo))
    return TestClient(create_app()), repo, profiles


def test_news_401() -> None:
    client, *_ = _setup()
    assert client.get("/api/news").status_code == 401


def test_list_seeded_unfiltered() -> None:
    repo = InMemoryNewsRepo()
    repo.seed(
        [
            NewsItem(
                id="1",
                title="Bitcoin rallies",
                url="https://ex/1",
                source="CoinDesk",
                published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                symbols=["BTC"],
            ),
            NewsItem(
                id="2",
                title="Oil markets",
                url="https://ex/2",
                source="Reuters",
                published_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
            ),
            NewsItem(
                id="3",
                title="Vinamilk expands",
                url="https://ex/3",
                source="CafeF",
                symbols=["VNM"],
            ),
        ]
    )
    client, repo, profiles = _setup(repo)
    profiles.get_or_create("u1", email="u@test.com", name="U")
    r = client.get("/api/news", headers=_auth("u1"))
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_filter_by_keyword() -> None:
    repo = InMemoryNewsRepo()
    repo.seed(
        [
            NewsItem(id="1", title="Bitcoin rallies", url="https://ex/1", source="A"),
            NewsItem(id="2", title="Oil markets", url="https://ex/2", source="B"),
            NewsItem(id="3", title="Ethereum upgrade", url="https://ex/3", source="C"),
        ]
    )
    client, repo, profiles = _setup(repo)
    p = profiles.get_or_create("u1", email="u@test.com", name="U")
    profiles.update_settings(p.user_id, news_keywords=["bitcoin", "ethereum"])
    r = client.get("/api/news", headers=_auth("u1"))
    assert r.status_code == 200
    titles = [x["title"] for x in r.json()]
    assert "Bitcoin rallies" in titles
    assert "Ethereum upgrade" in titles
    assert "Oil markets" not in titles
