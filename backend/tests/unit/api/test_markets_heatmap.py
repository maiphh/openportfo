"""Public GET /api/markets/heatmap."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.adapters.vnstock.client import FixtureVnstockClient
from app.core.deps import get_stock_market_client, set_stock_market_client
from app.main import create_app
from app.ports.market import HeatmapSector, HeatmapStock


@pytest.fixture(autouse=True)
def _reset_stock_client() -> Any:
    set_stock_market_client(None)
    yield
    set_stock_market_client(None)


def test_heatmap_returns_fixture_sectors() -> None:
    stock = FixtureVnstockClient()
    set_stock_market_client(stock)
    app = create_app()
    app.dependency_overrides[get_stock_market_client] = lambda: stock

    res = TestClient(app).get("/api/markets/heatmap?limit=20")
    assert res.status_code == 200
    body = res.json()
    assert body["exchange"] == "HOSE"
    assert body["source"] == "vnstock"
    assert isinstance(body["sectors"], list)
    assert body["sectors"]
    total = sum(len(s["stocks"]) for s in body["sectors"])
    assert 1 <= total <= 20
    first = body["sectors"][0]["stocks"][0]
    assert "symbol" in first
    assert "changePct" in first
    assert "marketCap" in first


def test_heatmap_uses_injected_client() -> None:
    class Stub:
        def get_heatmap(self, *, exchange: str = "HOSE", limit: int = 100):
            return [
                HeatmapSector(
                    name="Ngân hàng",
                    stocks=(
                        HeatmapStock(
                            symbol="VCB",
                            name="Vietcombank",
                            change_pct=1.25,
                            market_cap=9.1e14,
                        ),
                    ),
                )
            ]

    stub = Stub()
    set_stock_market_client(stub)  # type: ignore[arg-type]
    app = create_app()
    app.dependency_overrides[get_stock_market_client] = lambda: stub

    res = TestClient(app).get("/api/markets/heatmap")
    assert res.status_code == 200
    sectors = res.json()["sectors"]
    assert sectors[0]["name"] == "Ngân hàng"
    assert sectors[0]["stocks"][0]["symbol"] == "VCB"
    assert sectors[0]["stocks"][0]["changePct"] == 1.25
