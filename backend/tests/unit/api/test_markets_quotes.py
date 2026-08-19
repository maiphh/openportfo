"""Public GET /api/markets/quotes."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.adapters.vnstock.client import FixtureVnstockClient
from app.adapters.vnstock.http_client import HttpVnstockClient
from app.core.deps import get_stock_market_client, set_stock_market_client
from app.main import create_app
from app.ports.market import QuoteGroup, QuoteRow


@pytest.fixture(autouse=True)
def _reset_stock_client() -> Any:
    set_stock_market_client(None)
    yield
    set_stock_market_client(None)


def test_quotes_returns_fixture_groups() -> None:
    stock = FixtureVnstockClient()
    set_stock_market_client(stock)
    app = create_app()
    app.dependency_overrides[get_stock_market_client] = lambda: stock

    res = TestClient(app).get("/api/markets/quotes?limit=20")
    assert res.status_code == 200
    body = res.json()
    assert body["exchange"] == "HOSE"
    assert body["source"] == "vnstock"
    assert body["limit"] == 20
    assert isinstance(body["groups"], list)
    assert body["groups"]
    total = sum(len(g["rows"]) for g in body["groups"])
    assert 1 <= total <= 20
    first = body["groups"][0]["rows"][0]
    for key in ("symbol", "name", "value", "change", "changePct", "open", "high", "low", "prev"):
        assert key in first


def test_quotes_uses_injected_client() -> None:
    class Stub:
        def get_quotes(self, *, exchange: str = "HOSE", limit: int = 80):
            return [
                QuoteGroup(
                    name="Ngân hàng",
                    rows=(
                        QuoteRow(
                            symbol="VCB",
                            name="Vietcombank",
                            value=91000,
                            change=500,
                            change_pct=0.55,
                            open=90500,
                            high=91500,
                            low=90200,
                            prev=90500,
                        ),
                    ),
                )
            ]

    stub = Stub()
    set_stock_market_client(stub)  # type: ignore[arg-type]
    app = create_app()
    app.dependency_overrides[get_stock_market_client] = lambda: stub

    res = TestClient(app).get("/api/markets/quotes")
    assert res.status_code == 200
    groups = res.json()["groups"]
    assert groups[0]["name"] == "Ngân hàng"
    row = groups[0]["rows"][0]
    assert row["symbol"] == "VCB"
    assert row["changePct"] == 0.55
    assert row["value"] == 91000


def test_quotes_provider_error_returns_502() -> None:
    class Boom:
        def get_quotes(self, *, exchange: str = "HOSE", limit: int = 80):
            raise RuntimeError("vnstock down")

    stub = Boom()
    set_stock_market_client(stub)  # type: ignore[arg-type]
    app = create_app()
    app.dependency_overrides[get_stock_market_client] = lambda: stub

    res = TestClient(app).get("/api/markets/quotes")
    assert res.status_code == 502
    assert "unavailable" in (res.json().get("detail") or "").lower()


def test_http_quotes_no_fallback_returns_502_not_catalog(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=False)
    client._live = True
    monkeypatch.setattr(client, "_live_quotes", lambda *_a, **_k: [])
    set_stock_market_client(client)
    app = create_app()
    app.dependency_overrides[get_stock_market_client] = lambda: client

    res = TestClient(app).get("/api/markets/quotes")
    assert res.status_code == 502
    body = res.json()
    assert "unavailable" in (body.get("detail") or "").lower()
    assert "groups" not in body
