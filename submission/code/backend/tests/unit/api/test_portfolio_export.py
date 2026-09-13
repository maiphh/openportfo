"""BL-027: GET /api/portfolio/export — auth, CSV headers, isolation, validation."""

from __future__ import annotations

import csv
import inspect
import io
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.core.deps as deps_mod
from app.core.deps import (
    get_crypto_market_client,
    get_exchange_rate_repo,
    get_fx_service,
    get_holdings_repo,
    get_market_service,
    get_portfolio_service,
    get_price_cache_repo,
    get_stock_market_client,
    get_user_profile_repo,
    set_crypto_market_client,
    set_exchange_rate_repo,
    set_fx_service,
    set_holdings_repo,
    set_market_service,
    set_portfolio_service,
    set_price_cache_repo,
    set_settings_repo,
    set_stock_market_client,
    set_user_profile_repo,
)
from app.main import create_app
from app.ports.fx import StoredRates
from app.ports.holdings import HoldingRecord
from app.services.export_service import CSV_HEADER
from app.services.fx_service import FxService
from app.services.market_service import MarketService
from app.services.portfolio_service import PortfolioService
from tests.fakes.fx import InMemoryExchangeRateRepo
from tests.fakes.holdings import InMemoryHoldingsRepo
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.price_cache import InMemoryPriceCacheRepo
from tests.fakes.users import InMemoryUserProfileRepo


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{user_id}"}


def _now() -> datetime:
    return datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _seed_btc(holdings: InMemoryHoldingsRepo, user_id: str = "alice") -> None:
    holdings.create(
        HoldingRecord(
            user_id=user_id,
            asset_type="crypto",
            symbol="BTC",
            qty=Decimal("1"),
            avg_cost=Decimal("30000"),
            currency="USD",
            asset_id="bitcoin",
        )
    )


def _seed_vnm(holdings: InMemoryHoldingsRepo, user_id: str = "bob") -> None:
    holdings.create(
        HoldingRecord(
            user_id=user_id,
            asset_type="stock",
            symbol="VNM",
            qty=Decimal("10"),
            avg_cost=Decimal("70000"),
            currency="VND",
            asset_id="VNM",
        )
    )


def _make_client(
    *,
    holdings: InMemoryHoldingsRepo | None = None,
    crypto: FixtureCryptoMarketClient | None = None,
    stock: FixtureStockMarketClient | None = None,
    cache: InMemoryPriceCacheRepo | None = None,
    fx: InMemoryExchangeRateRepo | None = None,
    profiles: InMemoryUserProfileRepo | None = None,
) -> tuple[
    TestClient,
    InMemoryHoldingsRepo,
    FixtureCryptoMarketClient,
    FixtureStockMarketClient,
    InMemoryPriceCacheRepo,
    InMemoryExchangeRateRepo,
    InMemoryUserProfileRepo,
]:
    h = holdings or InMemoryHoldingsRepo()
    c = crypto or FixtureCryptoMarketClient(
        prices={"bitcoin": (Decimal("40000"), "USD")},
    )
    s = stock or FixtureStockMarketClient(
        prices={"VNM": (Decimal("80000"), "VND")},
    )
    p = cache or InMemoryPriceCacheRepo()
    f = fx if fx is not None else InMemoryExchangeRateRepo()
    u = profiles or InMemoryUserProfileRepo()
    fx_svc = FxService(f)  # stored rates only — no ExchangeRateClient

    set_holdings_repo(h)
    set_crypto_market_client(c)
    set_stock_market_client(s)
    set_price_cache_repo(p)
    set_exchange_rate_repo(f)
    set_user_profile_repo(u)
    set_market_service(None)
    set_portfolio_service(None)
    set_fx_service(fx_svc)

    market = MarketService(c, s, p, default_ttl_seconds=600)
    set_market_service(market)
    portfolio = PortfolioService(h, market, fx_repo=f)
    set_portfolio_service(portfolio)

    app = create_app()
    app.dependency_overrides[get_holdings_repo] = lambda: h
    app.dependency_overrides[get_crypto_market_client] = lambda: c
    app.dependency_overrides[get_stock_market_client] = lambda: s
    app.dependency_overrides[get_price_cache_repo] = lambda: p
    app.dependency_overrides[get_exchange_rate_repo] = lambda: f
    app.dependency_overrides[get_user_profile_repo] = lambda: u
    app.dependency_overrides[get_market_service] = lambda: market
    app.dependency_overrides[get_portfolio_service] = lambda: portfolio
    app.dependency_overrides[get_fx_service] = lambda: fx_svc
    return TestClient(app), h, c, s, p, f, u


@pytest.fixture(autouse=True)
def _reset_deps() -> Any:
    set_holdings_repo(None)
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_exchange_rate_repo(None)
    set_market_service(None)
    set_portfolio_service(None)
    set_fx_service(None)
    set_user_profile_repo(None)
    set_settings_repo(None)
    yield
    set_holdings_repo(None)
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_exchange_rate_repo(None)
    set_market_service(None)
    set_portfolio_service(None)
    set_fx_service(None)
    set_user_profile_repo(None)
    set_settings_repo(None)


def _csv_rows(body: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(body))
    assert reader.fieldnames == CSV_HEADER
    return list(reader)


def test_export_unauthorized_401() -> None:
    client, *_ = _make_client()
    r = client.get("/api/portfolio/export", params={"format": "csv"})
    assert r.status_code == 401


def test_export_200_text_csv_headers_and_math() -> None:
    client, holdings, *_ = _make_client()
    _seed_btc(holdings)

    r = client.get(
        "/api/portfolio/export",
        params={"format": "csv", "displayCurrency": "USD"},
        headers=_auth("alice"),
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "charset=utf-8" in r.headers["content-type"].lower()
    cd = r.headers["content-disposition"]
    assert "attachment" in cd.lower()
    assert re.search(r"openportfo-portfolio-\d{8}\.csv", cd)
    assert r.headers.get("x-fx-status") is not None
    assert "x-fx-as-of" in {k.lower() for k in r.headers.keys()}
    assert r.content[:3] != b"\xef\xbb\xbf"

    rows = _csv_rows(r.text)
    assert len(rows) == 1
    row = rows[0]
    assert row["symbol"] == "BTC"
    assert Decimal(row["qty"]) == Decimal("1")
    assert Decimal(row["price"]) == Decimal("40000")
    assert Decimal(row["marketValue"]) == Decimal("40000")
    assert Decimal(row["costBasis"]) == Decimal("30000")
    assert Decimal(row["pnl"]) == Decimal("10000")


def test_export_isolation_user_a_vs_b() -> None:
    client, holdings, *_ = _make_client()
    _seed_btc(holdings, "alice")
    _seed_vnm(holdings, "bob")

    r_a = client.get(
        "/api/portfolio/export",
        params={"format": "csv", "displayCurrency": "USD"},
        headers=_auth("alice"),
    )
    r_b = client.get(
        "/api/portfolio/export",
        params={"format": "csv", "displayCurrency": "VND"},
        headers=_auth("bob"),
    )
    assert r_a.status_code == 200
    assert r_b.status_code == 200
    symbols_a = {row["symbol"] for row in _csv_rows(r_a.text)}
    symbols_b = {row["symbol"] for row in _csv_rows(r_b.text)}
    assert symbols_a == {"BTC"}
    assert symbols_b == {"VNM"}
    assert "VNM" not in r_a.text.split("\r\n")[0] or "VNM" not in {
        row["symbol"] for row in _csv_rows(r_a.text)
    }


def test_export_empty_header_only() -> None:
    client, *_ = _make_client()
    r = client.get(
        "/api/portfolio/export",
        params={"format": "csv"},
        headers=_auth("alice"),
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    data_rows = [ln for ln in r.text.split("\r\n") if ln]
    assert data_rows[0] == ",".join(CSV_HEADER)
    assert len(data_rows) == 1
    assert _csv_rows(r.text) == []


def test_export_format_json_400() -> None:
    client, *_ = _make_client()
    r = client.get(
        "/api/portfolio/export",
        params={"format": "json"},
        headers=_auth("alice"),
    )
    assert r.status_code == 400
    assert "csv" in str(r.json().get("detail", "")).lower()


def test_export_currency_jpy_400() -> None:
    client, *_ = _make_client()
    r = client.get(
        "/api/portfolio/export",
        params={"format": "csv", "currency": "JPY"},
        headers=_auth("alice"),
    )
    assert r.status_code == 400


def test_export_never_calls_exchange_rate_client() -> None:
    import app.api.portfolio as portfolio_api
    import app.services.export_service as export_svc

    assert "ExchangeRateClient" not in inspect.getsource(portfolio_api)
    assert "ExchangeRateClient" not in inspect.getsource(export_svc)
    src = inspect.getsource(deps_mod.get_export_service)
    assert "ExchangeRateClient" not in src
    assert "boto3" not in inspect.getsource(export_svc)

    fx = InMemoryExchangeRateRepo()
    client, holdings, *_rest = _make_client(fx=fx)
    _seed_btc(holdings)
    r = client.get(
        "/api/portfolio/export",
        params={"format": "csv", "displayCurrency": "VND"},
        headers=_auth("alice"),
    )
    assert r.status_code == 200
    assert fx.get_latest_calls >= 1
    assert r.headers["x-fx-status"] == "missing"


def test_export_fx_conversion_when_stored_rate_exists() -> None:
    fx = InMemoryExchangeRateRepo()
    fx.seed(
        StoredRates(
            base="USD",
            rates={"USD_VND": Decimal("25000")},
            as_of=_now(),
            status="fresh",
            provider="seed",
        )
    )
    client, holdings, *_ = _make_client(fx=fx)
    _seed_btc(holdings)
    r = client.get(
        "/api/portfolio/export",
        params={"format": "csv", "displayCurrency": "VND"},
        headers=_auth("alice"),
    )
    assert r.status_code == 200
    assert r.headers["x-fx-status"] == "fresh"
    row = _csv_rows(r.text)[0]
    assert Decimal(row["marketValueDisplay"]) == Decimal("1000000000")
    assert Decimal(row["costBasisDisplay"]) == Decimal("750000000")
    assert Decimal(row["fxRateUsed"]) == Decimal("25000")
    assert row["fxStatus"] == "fresh"
