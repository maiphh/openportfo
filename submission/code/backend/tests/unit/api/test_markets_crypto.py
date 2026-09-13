"""Public GET /api/markets/crypto/{heatmap,quotes}."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import httpx

from app.adapters.coingecko.client import FixtureCoinGeckoClient
from app.adapters.coingecko.http_client import HttpCoinGeckoClient
from app.core.deps import get_crypto_market_client, set_crypto_market_client
from app.main import create_app
from app.ports.market import HeatmapSector, HeatmapStock, QuoteGroup, QuoteRow


@pytest.fixture(autouse=True)
def _reset_crypto_client() -> Any:
    set_crypto_market_client(None)
    yield
    set_crypto_market_client(None)


def test_crypto_heatmap_returns_fixture_sectors() -> None:
    crypto = FixtureCoinGeckoClient()
    set_crypto_market_client(crypto)
    app = create_app()
    app.dependency_overrides[get_crypto_market_client] = lambda: crypto

    res = TestClient(app).get("/api/markets/crypto/heatmap?limit=20")
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "coingecko"
    assert body["limit"] == 20
    assert isinstance(body["sectors"], list)
    assert body["sectors"]
    total = sum(len(s["stocks"]) for s in body["sectors"])
    assert 1 <= total <= 20
    first = body["sectors"][0]["stocks"][0]
    assert "symbol" in first
    assert "changePct" in first
    assert "marketCap" in first
    btc = next(
        (t for s in body["sectors"] for t in s["stocks"] if t["symbol"] == "BTC"),
        None,
    )
    if btc is not None:
        assert btc.get("imageUrl", "").startswith("https://assets.coingecko.com/")


def test_crypto_heatmap_uses_injected_client() -> None:
    class Stub:
        def get_heatmap(self, *, limit: int = 100):
            return [
                HeatmapSector(
                    name="Layer 1",
                    stocks=(
                        HeatmapStock(
                            symbol="BTC",
                            name="Bitcoin",
                            change_pct=1.2,
                            market_cap=1.2e12,
                        ),
                    ),
                )
            ]

    stub = Stub()
    set_crypto_market_client(stub)  # type: ignore[arg-type]
    app = create_app()
    app.dependency_overrides[get_crypto_market_client] = lambda: stub

    res = TestClient(app).get("/api/markets/crypto/heatmap")
    assert res.status_code == 200
    sectors = res.json()["sectors"]
    assert sectors[0]["name"] == "Layer 1"
    assert sectors[0]["stocks"][0]["symbol"] == "BTC"
    assert sectors[0]["stocks"][0]["changePct"] == 1.2
    assert sectors[0]["stocks"][0]["marketCap"] == 1.2e12


def test_crypto_quotes_returns_fixture_groups() -> None:
    crypto = FixtureCoinGeckoClient()
    set_crypto_market_client(crypto)
    app = create_app()
    app.dependency_overrides[get_crypto_market_client] = lambda: crypto

    res = TestClient(app).get("/api/markets/crypto/quotes?limit=20")
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "coingecko"
    assert body["limit"] == 20
    assert isinstance(body["groups"], list)
    assert body["groups"]
    total = sum(len(g["rows"]) for g in body["groups"])
    assert 1 <= total <= 20
    first = body["groups"][0]["rows"][0]
    for key in ("symbol", "name", "value", "change", "changePct", "open", "high", "low", "prev"):
        assert key in first


def test_crypto_quotes_uses_injected_client() -> None:
    class Stub:
        def get_quotes(self, *, limit: int = 80):
            return [
                QuoteGroup(
                    name="Layer 1",
                    rows=(
                        QuoteRow(
                            symbol="BTC",
                            name="Bitcoin",
                            value=65000,
                            change=1200,
                            change_pct=1.88,
                            open=63800,
                            high=66000,
                            low=63000,
                            prev=63800,
                        ),
                    ),
                )
            ]

    stub = Stub()
    set_crypto_market_client(stub)  # type: ignore[arg-type]
    app = create_app()
    app.dependency_overrides[get_crypto_market_client] = lambda: stub

    res = TestClient(app).get("/api/markets/crypto/quotes")
    assert res.status_code == 200
    groups = res.json()["groups"]
    assert groups[0]["name"] == "Layer 1"
    row = groups[0]["rows"][0]
    assert row["symbol"] == "BTC"
    assert row["changePct"] == 1.88
    assert row["value"] == 65000


@pytest.mark.parametrize(
    "path",
    ("/api/markets/crypto/heatmap", "/api/markets/crypto/quotes"),
)
def test_crypto_provider_error_returns_502(path: str) -> None:
    class Boom:
        def get_heatmap(self, *, limit: int = 100):
            raise RuntimeError("coingecko down")

        def get_quotes(self, *, limit: int = 80):
            raise RuntimeError("coingecko down")

    stub = Boom()
    set_crypto_market_client(stub)  # type: ignore[arg-type]
    app = create_app()
    app.dependency_overrides[get_crypto_market_client] = lambda: stub

    res = TestClient(app).get(path)
    assert res.status_code == 502
    assert "unavailable" in (res.json().get("detail") or "").lower()


@pytest.mark.parametrize(
    "path",
    ("/api/markets/crypto/heatmap", "/api/markets/crypto/quotes"),
)
def test_http_crypto_no_fallback_returns_502_not_catalog(path: str) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"})

    client = HttpCoinGeckoClient(
        transport=httpx.MockTransport(handler),
        use_fixture_fallback=False,
    )
    set_crypto_market_client(client)
    app = create_app()
    app.dependency_overrides[get_crypto_market_client] = lambda: client

    res = TestClient(app).get(path)
    assert res.status_code == 502
    body = res.json()
    assert "unavailable" in (body.get("detail") or "").lower()
    assert "sectors" not in body
    assert "groups" not in body
