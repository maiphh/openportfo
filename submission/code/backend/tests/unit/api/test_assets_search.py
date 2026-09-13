"""Sprint 04: GET /api/assets/search API + wiring."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.deps import (
    get_crypto_market_client,
    get_market_service,
    get_price_cache_repo,
    get_stock_market_client,
    get_user_profile_repo,
    set_crypto_market_client,
    set_market_service,
    set_price_cache_repo,
    set_stock_market_client,
    set_user_profile_repo,
)
from app.main import create_app
from app.services.market_service import MarketService
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.price_cache import InMemoryPriceCacheRepo
from tests.fakes.users import InMemoryUserProfileRepo


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{user_id}"}


def _make_client(
    crypto: FixtureCryptoMarketClient | None = None,
    stock: FixtureStockMarketClient | None = None,
    cache: InMemoryPriceCacheRepo | None = None,
    profiles: InMemoryUserProfileRepo | None = None,
) -> tuple[
    TestClient,
    FixtureCryptoMarketClient,
    FixtureStockMarketClient,
    InMemoryPriceCacheRepo,
    InMemoryUserProfileRepo,
]:
    c = crypto or FixtureCryptoMarketClient()
    s = stock or FixtureStockMarketClient()
    p = cache or InMemoryPriceCacheRepo()
    u = profiles or InMemoryUserProfileRepo()
    set_crypto_market_client(c)
    set_stock_market_client(s)
    set_price_cache_repo(p)
    set_user_profile_repo(u)
    set_market_service(None)
    svc = MarketService(c, s, p, default_ttl_seconds=600)
    set_market_service(svc)

    app = create_app()
    app.dependency_overrides[get_crypto_market_client] = lambda: c
    app.dependency_overrides[get_stock_market_client] = lambda: s
    app.dependency_overrides[get_price_cache_repo] = lambda: p
    app.dependency_overrides[get_user_profile_repo] = lambda: u
    app.dependency_overrides[get_market_service] = lambda: svc
    return TestClient(app), c, s, p, u


@pytest.fixture(autouse=True)
def _reset_deps() -> Any:
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_market_service(None)
    set_user_profile_repo(None)
    yield
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_market_service(None)
    set_user_profile_repo(None)


# ---------------------------------------------------------------------------
# 1. Crypto search DTO
# ---------------------------------------------------------------------------


def test_list_stocks_returns_catalog() -> None:
    client, _, stock, _, _ = _make_client()
    r = client.get(
        "/api/assets",
        params={"type": "stock", "limit": 250},
        headers=_auth("alice"),
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 3
    symbols = {x["symbol"] for x in data}
    assert {"VNM", "FPT", "HPG", "VCB"}.issubset(symbols)
    assert all(x["assetType"] == "stock" for x in data)


def test_list_crypto_returns_catalog() -> None:
    client, _, _, _, _ = _make_client()
    r = client.get(
        "/api/assets",
        params={"type": "crypto", "limit": 50},
        headers=_auth("alice"),
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 3
    ids = {x["assetId"] for x in data}
    assert {"bitcoin", "ethereum", "solana"}.issubset(ids)


def test_list_assets_invalid_type_400() -> None:
    client, _, _, _, _ = _make_client()
    r = client.get(
        "/api/assets",
        params={"type": "forex"},
        headers=_auth("alice"),
    )
    assert r.status_code == 400


def test_list_assets_unauthorized_401() -> None:
    client, _, _, _, _ = _make_client()
    r = client.get("/api/assets", params={"type": "stock"})
    assert r.status_code == 401


def test_search_crypto_maps_dto() -> None:
    client, crypto, _, _, _ = _make_client()
    r = client.get(
        "/api/assets/search",
        params={"q": "bit", "type": "crypto"},
        headers=_auth("alice"),
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    btc = next(x for x in data if x["symbol"] == "BTC")
    assert btc["name"] == "Bitcoin"
    assert btc["assetId"] == "bitcoin"
    assert btc["assetType"] == "crypto"
    assert crypto.search_calls == 1


# ---------------------------------------------------------------------------
# 2. Stock search DTO
# ---------------------------------------------------------------------------


def test_search_stock_maps_dto() -> None:
    client, _, stock, _, _ = _make_client()
    r = client.get(
        "/api/assets/search",
        params={"q": "VNM", "type": "stock"},
        headers=_auth("alice"),
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0] == {
        "symbol": "VNM",
        "name": "Vinamilk",
        "assetId": "VNM",
        "assetType": "stock",
    }
    assert stock.search_calls == 1


# ---------------------------------------------------------------------------
# 5. Validation 400
# ---------------------------------------------------------------------------


def test_search_empty_q_400() -> None:
    client, _, _, _, _ = _make_client()
    r = client.get(
        "/api/assets/search",
        params={"q": "", "type": "crypto"},
        headers=_auth("alice"),
    )
    assert r.status_code == 400
    assert "detail" in r.json()


def test_search_whitespace_q_400() -> None:
    client, _, _, _, _ = _make_client()
    r = client.get(
        "/api/assets/search",
        params={"q": "   ", "type": "crypto"},
        headers=_auth("alice"),
    )
    assert r.status_code == 400


def test_search_invalid_type_400() -> None:
    client, _, _, _, _ = _make_client()
    r = client.get(
        "/api/assets/search",
        params={"q": "btc", "type": "forex"},
        headers=_auth("alice"),
    )
    assert r.status_code == 400
    assert "detail" in r.json()


def test_search_missing_type_400() -> None:
    client, _, _, _, _ = _make_client()
    r = client.get(
        "/api/assets/search",
        params={"q": "btc"},
        headers=_auth("alice"),
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# 6. Unauthorized 401
# ---------------------------------------------------------------------------


def test_search_unauthorized_401() -> None:
    client, _, _, _, _ = _make_client()
    r = client.get(
        "/api/assets/search",
        params={"q": "btc", "type": "crypto"},
    )
    assert r.status_code == 401


def test_search_invalid_token_401() -> None:
    client, _, _, _, _ = _make_client()
    r = client.get(
        "/api/assets/search",
        params={"q": "btc", "type": "crypto"},
        headers={"Authorization": "Bearer not-a-fake-token"},
    )
    assert r.status_code == 401


def test_search_no_results_empty_list() -> None:
    client, _, _, _, _ = _make_client()
    r = client.get(
        "/api/assets/search",
        params={"q": "zzzznotfound", "type": "crypto"},
        headers=_auth("bob"),
    )
    assert r.status_code == 200
    assert r.json() == []


def test_get_crypto_quote_and_explicit_refresh() -> None:
    client, crypto, _, _, _ = _make_client()
    path = "/api/assets/crypto/BTC/quote?assetId=bitcoin"
    first = client.get(path, headers=_auth("alice"))
    assert first.status_code == 200
    assert first.json()["price"] == "65000"
    assert first.json()["currency"] == "USD"
    assert first.json()["source"] == "cache-first"
    assert crypto.price_calls == 1

    cached = client.get(path, headers=_auth("alice"))
    assert cached.status_code == 200
    assert crypto.price_calls == 1

    refreshed = client.post(
        "/api/assets/crypto/BTC/quote/refresh?assetId=bitcoin",
        headers=_auth("alice"),
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["source"] == "refreshed"
    assert crypto.price_calls == 2


def test_get_stock_quote() -> None:
    client, _, stock, _, _ = _make_client()
    response = client.get("/api/assets/stock/FPT/quote?assetId=FPT", headers=_auth("alice"))
    assert response.status_code == 200
    assert response.json()["price"] == "120000"
    assert response.json()["currency"] == "VND"
    assert stock.price_calls == 1
