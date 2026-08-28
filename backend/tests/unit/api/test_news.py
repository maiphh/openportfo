"""News API: market boards + asset keyword search over shared storage."""

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


def _seed_repo() -> InMemoryNewsRepo:
    repo = InMemoryNewsRepo()
    repo.seed(
        [
            NewsItem(
                id="1",
                title="Bitcoin rallies on ETF inflows",
                url="https://ex/1",
                source="CoinDesk",
                published_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
                symbols=["BTC"],
            ),
            NewsItem(
                id="2",
                title="VN-Index climbs as bank stocks rise",
                url="https://ex/2",
                source="CafeF",
                published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                symbols=["VCB"],
            ),
            NewsItem(
                id="3",
                title="Vinamilk expands distribution network",
                url="https://ex/3",
                source="CafeF",
                published_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
                symbols=["VNM"],
            ),
            NewsItem(
                id="4",
                title="Celebrity wedding photos",
                url="https://ex/4",
                source="Gossip",
                published_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
            ),
            NewsItem(
                id="5",
                title="Ethereum upgrade lands successfully",
                url="https://ex/5",
                source="CoinDesk",
                published_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            ),
        ]
    )
    return repo


def _setup(repo: InMemoryNewsRepo | None = None) -> tuple[TestClient, InMemoryNewsRepo, InMemoryUserProfileRepo]:
    profiles = InMemoryUserProfileRepo()
    repo = repo or _seed_repo()
    set_user_profile_repo(profiles)
    set_news_repo(repo)
    set_news_service(NewsService(repo))
    return TestClient(create_app()), repo, profiles


def test_news_401() -> None:
    client, *_ = _setup()
    assert client.get("/api/news").status_code == 401


def test_stock_market_board_excludes_crypto_and_gossip() -> None:
    client, _, profiles = _setup()
    profiles.get_or_create("u1", email="u@test.com", name="U")
    r = client.get("/api/news?market=stock", headers=_auth("u1"))
    assert r.status_code == 200
    titles = [x["title"] for x in r.json()]
    assert "Celebrity wedding photos" not in titles
    assert "Bitcoin rallies on ETF inflows" not in titles
    assert any("VN-Index" in t for t in titles)
    assert any("Vinamilk" in t for t in titles)


def test_crypto_market_board() -> None:
    client, _, profiles = _setup()
    profiles.get_or_create("u1", email="u@test.com", name="U")
    r = client.get("/api/news?market=crypto", headers=_auth("u1"))
    assert r.status_code == 200
    titles = [x["title"] for x in r.json()]
    assert any("Bitcoin" in t for t in titles)
    assert any("Ethereum" in t for t in titles)
    assert not any("VN-Index" in t for t in titles)
    assert "Celebrity wedding photos" not in titles


def test_asset_detail_search_by_symbol_and_name() -> None:
    client, _, profiles = _setup()
    profiles.get_or_create("u1", email="u@test.com", name="U")
    r = client.get(
        "/api/news",
        params={
            "assetType": "stock",
            "symbol": "VNM",
            "name": "Vinamilk",
            "assetId": "VNM",
            "limit": 10,
        },
        headers=_auth("u1"),
    )
    assert r.status_code == 200
    titles = [x["title"] for x in r.json()]
    assert titles == ["Vinamilk expands distribution network"]


def test_asset_detail_crypto_tokens() -> None:
    client, _, profiles = _setup()
    profiles.get_or_create("u1", email="u@test.com", name="U")
    r = client.get(
        "/api/news",
        params={
            "assetType": "crypto",
            "symbol": "BTC",
            "name": "Bitcoin",
            "assetId": "bitcoin",
        },
        headers=_auth("u1"),
    )
    assert r.status_code == 200
    titles = [x["title"] for x in r.json()]
    assert len(titles) == 1
    assert "Bitcoin" in titles[0]
