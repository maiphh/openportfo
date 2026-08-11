"""Sprint 03: watchlist ports, service, REST add/list/remove + isolation."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.deps import (
    get_user_profile_repo,
    get_watchlist_repo,
    set_user_profile_repo,
    set_watchlist_repo,
)
from app.main import create_app
from app.ports.watchlist import (
    DuplicateWatchlistError,
    WatchlistItem,
    WatchlistNotFoundError,
)
from app.services.watchlist_service import ValidationError, WatchlistService
from tests.fakes.users import InMemoryUserProfileRepo
from tests.fakes.watchlist import InMemoryWatchlistRepo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{user_id}"}


def _item_body(
    *,
    asset_type: str = "crypto",
    symbol: str = "BTC",
    asset_id: str | None = "bitcoin",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "assetType": asset_type,
        "symbol": symbol,
    }
    if asset_id is not None:
        body["assetId"] = asset_id
    return body


def _make_client(
    watchlist: InMemoryWatchlistRepo | None = None,
    profiles: InMemoryUserProfileRepo | None = None,
) -> tuple[TestClient, InMemoryWatchlistRepo, InMemoryUserProfileRepo]:
    w_repo = watchlist or InMemoryWatchlistRepo()
    p_repo = profiles or InMemoryUserProfileRepo()
    set_watchlist_repo(w_repo)
    set_user_profile_repo(p_repo)
    app = create_app()
    app.dependency_overrides[get_watchlist_repo] = lambda: w_repo
    app.dependency_overrides[get_user_profile_repo] = lambda: p_repo
    return TestClient(app), w_repo, p_repo


@pytest.fixture(autouse=True)
def _reset_repos() -> Any:
    set_watchlist_repo(None)
    set_user_profile_repo(None)
    yield
    set_watchlist_repo(None)
    set_user_profile_repo(None)


# ---------------------------------------------------------------------------
# In-memory repo
# ---------------------------------------------------------------------------


def test_inmemory_watchlist_add_list_remove() -> None:
    repo = InMemoryWatchlistRepo()
    item = repo.add(
        WatchlistItem(
            user_id="alice",
            asset_type="crypto",
            symbol="btc",
            asset_id="bitcoin",
        )
    )
    assert item.symbol == "BTC"
    assert item.sk == "WATCH#crypto#BTC"
    listed = repo.list("alice")
    assert len(listed) == 1
    repo.remove("alice", "crypto", "BTC")
    assert repo.list("alice") == []
    with pytest.raises(WatchlistNotFoundError):
        repo.remove("alice", "crypto", "BTC")


def test_inmemory_watchlist_duplicate_raises() -> None:
    repo = InMemoryWatchlistRepo()
    item = WatchlistItem(user_id="alice", asset_type="crypto", symbol="ETH")
    repo.add(item)
    with pytest.raises(DuplicateWatchlistError):
        repo.add(item)


def test_inmemory_watchlist_user_isolation() -> None:
    repo = InMemoryWatchlistRepo()
    repo.add(WatchlistItem(user_id="a", asset_type="crypto", symbol="BTC"))
    repo.add(WatchlistItem(user_id="b", asset_type="stock", symbol="VNM"))
    assert [i.symbol for i in repo.list("a")] == ["BTC"]
    assert [i.symbol for i in repo.list("b")] == ["VNM"]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


def test_service_rejects_bad_asset_type() -> None:
    svc = WatchlistService(InMemoryWatchlistRepo())
    with pytest.raises(ValidationError, match="assetType"):
        svc.add_item("u1", asset_type="nft", symbol="X")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_watchlist_require_auth() -> None:
    client, _, _ = _make_client()
    assert client.get("/api/watchlist").status_code == 401
    assert client.post("/api/watchlist", json=_item_body()).status_code == 401


def test_watchlist_add_list_remove() -> None:
    client, _, _ = _make_client()
    r = client.post(
        "/api/watchlist",
        headers=_auth("alice"),
        json=_item_body(),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["userId"] == "alice"
    assert body["assetType"] == "crypto"
    assert body["symbol"] == "BTC"
    assert body["assetId"] == "bitcoin"
    assert "addedAt" in body

    listed = client.get("/api/watchlist", headers=_auth("alice"))
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    d = client.delete("/api/watchlist/crypto/BTC", headers=_auth("alice"))
    assert d.status_code == 204
    assert client.get("/api/watchlist", headers=_auth("alice")).json() == []


def test_watchlist_user_isolation() -> None:
    client, _, _ = _make_client()
    client.post(
        "/api/watchlist",
        headers=_auth("alice"),
        json=_item_body(symbol="BTC"),
    )
    client.post(
        "/api/watchlist",
        headers=_auth("bob"),
        json=_item_body(symbol="ETH", asset_id="ethereum"),
    )
    alice = client.get("/api/watchlist", headers=_auth("alice")).json()
    bob = client.get("/api/watchlist", headers=_auth("bob")).json()
    assert len(alice) == 1 and alice[0]["symbol"] == "BTC"
    assert len(bob) == 1 and bob[0]["symbol"] == "ETH"


def test_watchlist_duplicate_409() -> None:
    """Duplicate policy: POST same key → 409 Conflict (not idempotent)."""
    client, _, _ = _make_client()
    assert (
        client.post(
            "/api/watchlist",
            headers=_auth("alice"),
            json=_item_body(),
        ).status_code
        == 201
    )
    r = client.post(
        "/api/watchlist",
        headers=_auth("alice"),
        json=_item_body(asset_id="bitcoin-again"),
    )
    assert r.status_code == 409
    assert "detail" in r.json()


def test_watchlist_remove_missing_404() -> None:
    client, _, _ = _make_client()
    r = client.delete("/api/watchlist/crypto/BTC", headers=_auth("alice"))
    assert r.status_code == 404


def test_bob_cannot_remove_alice_watchlist_item() -> None:
    client, _, _ = _make_client()
    client.post(
        "/api/watchlist",
        headers=_auth("alice"),
        json=_item_body(),
    )
    assert (
        client.delete(
            "/api/watchlist/crypto/BTC",
            headers=_auth("bob"),
        ).status_code
        == 404
    )
    assert len(client.get("/api/watchlist", headers=_auth("alice")).json()) == 1


def test_never_trust_user_id_from_body_watchlist() -> None:
    client, w_repo, _ = _make_client()
    body = _item_body()
    body["userId"] = "eve"
    r = client.post("/api/watchlist", headers=_auth("alice"), json=body)
    assert r.status_code == 201
    assert r.json()["userId"] == "alice"
    assert len(w_repo.list("eve")) == 0
