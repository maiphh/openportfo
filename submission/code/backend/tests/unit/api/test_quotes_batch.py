"""POST /api/quotes batch endpoint."""

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


def _make_client() -> tuple[TestClient, FixtureCryptoMarketClient]:
    crypto = FixtureCryptoMarketClient()
    stock = FixtureStockMarketClient()
    cache = InMemoryPriceCacheRepo()
    users = InMemoryUserProfileRepo()
    market = MarketService(crypto, stock, cache, default_ttl_seconds=600)
    set_crypto_market_client(crypto)
    set_stock_market_client(stock)
    set_price_cache_repo(cache)
    set_user_profile_repo(users)
    set_market_service(market)
    app = create_app()
    app.dependency_overrides[get_crypto_market_client] = lambda: crypto
    app.dependency_overrides[get_stock_market_client] = lambda: stock
    app.dependency_overrides[get_price_cache_repo] = lambda: cache
    app.dependency_overrides[get_user_profile_repo] = lambda: users
    app.dependency_overrides[get_market_service] = lambda: market
    return TestClient(app), crypto


@pytest.fixture(autouse=True)
def _reset() -> Any:
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_user_profile_repo(None)
    set_market_service(None)
    yield
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_user_profile_repo(None)
    set_market_service(None)


def test_batch_quotes_requires_auth() -> None:
    client, _ = _make_client()
    r = client.post("/api/quotes", json={"items": [{"assetType": "crypto", "symbol": "BTC"}]})
    assert r.status_code == 401


def test_batch_quotes_mixed_types() -> None:
    client, crypto = _make_client()
    r = client.post(
        "/api/quotes",
        headers=_auth("alice"),
        json={
            "items": [
                {"assetType": "crypto", "symbol": "BTC", "assetId": "bitcoin"},
                {"assetType": "stock", "symbol": "VNM", "assetId": "VNM"},
            ]
        },
    )
    assert r.status_code == 200, r.text
    quotes = r.json()["quotes"]
    by_symbol = {q["symbol"]: q for q in quotes}
    assert by_symbol["BTC"]["price"] == "65000"
    assert by_symbol["BTC"]["stale"] is False
    assert by_symbol["VNM"]["currency"] == "VND"
    assert crypto.price_calls == 1


def test_batch_quotes_empty_400() -> None:
    client, _ = _make_client()
    r = client.post("/api/quotes", headers=_auth("alice"), json={"items": []})
    assert r.status_code == 400
