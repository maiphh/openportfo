"""Public /api/markets/* cache headers (BL-011)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.adapters.coingecko.client import FixtureCoinGeckoClient
from app.adapters.vnstock.client import FixtureVnstockClient
from app.core.deps import (
    get_crypto_market_client,
    get_stock_market_client,
    set_crypto_market_client,
    set_stock_market_client,
)
from app.main import create_app

_CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=120"


@pytest.fixture(autouse=True)
def _reset_market_clients() -> Any:
    set_stock_market_client(None)
    set_crypto_market_client(None)
    yield
    set_stock_market_client(None)
    set_crypto_market_client(None)


@pytest.mark.parametrize(
    "path",
    (
        "/api/markets/heatmap",
        "/api/markets/quotes",
        "/api/markets/crypto/heatmap",
        "/api/markets/crypto/quotes",
    ),
)
def test_markets_success_sets_swr_cache_control(path: str) -> None:
    stock = FixtureVnstockClient()
    crypto = FixtureCoinGeckoClient()
    set_stock_market_client(stock)
    set_crypto_market_client(crypto)
    app = create_app()
    app.dependency_overrides[get_stock_market_client] = lambda: stock
    app.dependency_overrides[get_crypto_market_client] = lambda: crypto

    res = TestClient(app).get(path)
    assert res.status_code == 200
    assert res.headers.get("cache-control") == _CACHE_CONTROL
