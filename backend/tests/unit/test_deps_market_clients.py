"""MARKET_CLIENT_MODE wiring: http never swaps in catalog fixtures."""

from __future__ import annotations

from typing import Any

import pytest

from app.adapters.coingecko.client import FixtureCoinGeckoClient
from app.adapters.coingecko.http_client import HttpCoinGeckoClient
from app.adapters.vnstock.client import FixtureVnstockClient
from app.adapters.vnstock import http_client as vnstock_http
from app.adapters.vnstock.http_client import HttpVnstockClient
from app.core.config import clear_settings_cache
from app.core.deps import (
    get_crypto_market_client,
    get_stock_market_client,
    set_crypto_market_client,
    set_stock_market_client,
)
from app.core import deps


@pytest.fixture(autouse=True)
def _reset_clients() -> Any:
    set_stock_market_client(None)
    set_crypto_market_client(None)
    yield
    set_stock_market_client(None)
    set_crypto_market_client(None)
    clear_settings_cache()


def test_fixture_mode_still_uses_catalog_clients(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_CLIENT_MODE", "fixture")
    clear_settings_cache()
    assert isinstance(get_stock_market_client(), FixtureVnstockClient)
    assert isinstance(get_crypto_market_client(), FixtureCoinGeckoClient)


def test_http_mode_builds_http_clients_without_fallback(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_CLIENT_MODE", "http")
    clear_settings_cache()
    stock = get_stock_market_client()
    crypto = get_crypto_market_client()
    assert isinstance(stock, HttpVnstockClient)
    assert stock._fallback is None
    assert isinstance(crypto, HttpCoinGeckoClient)
    assert crypto._fallback is None


def test_http_mode_stock_construct_error_does_not_swap_fixture(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_CLIENT_MODE", "http")
    clear_settings_cache()

    def boom(*_a, **_k):
        raise RuntimeError("vnstock client init failed")

    monkeypatch.setattr(vnstock_http, "HttpVnstockClient", boom)
    with pytest.raises(RuntimeError, match="vnstock client init failed"):
        get_stock_market_client()
    assert deps._stock_market_client is None


def test_http_mode_crypto_construct_error_does_not_swap_fixture(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_CLIENT_MODE", "http")
    clear_settings_cache()

    import app.adapters.coingecko.http_client as cg_http

    def boom(*_a, **_k):
        raise RuntimeError("coingecko client init failed")

    monkeypatch.setattr(cg_http, "HttpCoinGeckoClient", boom)
    with pytest.raises(RuntimeError, match="coingecko client init failed"):
        get_crypto_market_client()
    assert deps._crypto_market_client is None
