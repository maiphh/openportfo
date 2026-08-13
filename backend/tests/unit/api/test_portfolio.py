"""Sprint 05: GET/POST /api/portfolio — auth, shape, cache, no FX HTTP."""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.core.deps as deps_mod
from app.core.deps import (
    get_crypto_market_client,
    get_exchange_rate_repo,
    get_holdings_repo,
    get_market_service,
    get_portfolio_service,
    get_price_cache_repo,
    get_stock_market_client,
    get_user_profile_repo,
    set_crypto_market_client,
    set_exchange_rate_repo,
    set_holdings_repo,
    set_market_service,
    set_portfolio_service,
    set_price_cache_repo,
    set_settings_repo,
    set_stock_market_client,
    set_user_profile_repo,
)
from app.domain.models import PriceQuote
from app.main import create_app
from app.ports.admin import SystemSettings
from app.ports.fx import StoredRates
from app.ports.holdings import HoldingRecord
from app.services.market_service import MarketService
from app.services.portfolio_service import PortfolioService
from tests.fakes.admin import InMemorySettingsRepo
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

    set_holdings_repo(h)
    set_crypto_market_client(c)
    set_stock_market_client(s)
    set_price_cache_repo(p)
    set_exchange_rate_repo(f)
    set_user_profile_repo(u)
    set_market_service(None)
    set_portfolio_service(None)

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
    set_user_profile_repo(None)
    set_settings_repo(None)


# ---------------------------------------------------------------------------
# 6. API 401 / 200 shape
# ---------------------------------------------------------------------------


def test_get_portfolio_unauthorized_401() -> None:
    client, *_ = _make_client()
    r = client.get("/api/portfolio")
    assert r.status_code == 401


def test_refresh_portfolio_unauthorized_401() -> None:
    client, *_ = _make_client()
    r = client.post("/api/portfolio/refresh")
    assert r.status_code == 401


def test_get_portfolio_200_shape_empty() -> None:
    client, *_ = _make_client()
    r = client.get("/api/portfolio", headers=_auth("alice"))
    assert r.status_code == 200
    data = r.json()
    assert data["lines"] == []
    assert data["totalsByCurrency"] == {}
    assert data["totalsDisplay"] is None
    assert data["fx"]["status"] == "missing"
    assert data["fx"]["asOf"] is None
    assert data["fx"]["rates"] == {}
    assert data["asOf"] is None


def test_get_portfolio_200_one_holding_shape() -> None:
    client, holdings, crypto, *_ = _make_client()
    _seed_btc(holdings)

    r = client.get("/api/portfolio", headers=_auth("alice"))
    assert r.status_code == 200
    data = r.json()

    assert len(data["lines"]) == 1
    line = data["lines"][0]
    assert line["symbol"] == "BTC"
    assert line["assetType"] == "crypto"
    assert line["qty"] == "1"
    assert line["avgCost"] == "30000"
    assert line["price"] == "40000"
    assert line["marketValue"] == "40000"
    assert line["costBasis"] == "30000"
    assert line["pnl"] == "10000"
    assert line["missingPrice"] is False
    assert isinstance(line["pnlPercent"], str)

    usd = data["totalsByCurrency"]["USD"]
    assert usd["marketValue"] == "40000"
    assert usd["costBasis"] == "30000"
    assert usd["pnl"] == "10000"
    assert "pnlPercent" in usd

    assert data["totalsDisplay"] is None
    assert data["fx"]["status"] == "missing"
    assert data["asOf"] is not None
    assert crypto.price_calls == 1


# ---------------------------------------------------------------------------
# Warm cache / refresh
# ---------------------------------------------------------------------------


def test_get_warm_cache_does_not_call_market() -> None:
    cache = InMemoryPriceCacheRepo()
    cache.put(
        PriceQuote(
            asset_type="crypto",
            symbol="BTC",
            price=Decimal("41000"),
            currency="USD",
            as_of=_now(),
        ),
        600,
    )
    client, holdings, crypto, stock, *_ = _make_client(cache=cache)
    _seed_btc(holdings)

    r = client.get("/api/portfolio", headers=_auth("alice"))
    assert r.status_code == 200
    assert r.json()["lines"][0]["price"] == "41000"
    assert crypto.price_calls == 0
    assert stock.price_calls == 0


def test_refresh_invokes_market_client() -> None:
    cache = InMemoryPriceCacheRepo()
    cache.put(
        PriceQuote(
            asset_type="crypto",
            symbol="BTC",
            price=Decimal("41000"),
            currency="USD",
            as_of=_now(),
        ),
        600,
    )
    client, holdings, crypto, *_ = _make_client(cache=cache)
    _seed_btc(holdings)

    r = client.post("/api/portfolio/refresh", headers=_auth("alice"))
    assert r.status_code == 200
    assert r.json()["lines"][0]["price"] == "40000"
    assert crypto.price_calls == 1


# ---------------------------------------------------------------------------
# No ExchangeRateClient on GET/refresh
# ---------------------------------------------------------------------------


def test_portfolio_wiring_uses_fx_repo_not_client() -> None:
    """Portfolio path uses ExchangeRateRepo only; FX HTTP client is admin/S06."""
    import app.api.portfolio as portfolio_api
    import app.services.portfolio_service as portfolio_svc

    assert "ExchangeRateClient" not in inspect.getsource(portfolio_api)
    assert "ExchangeRateClient" not in inspect.getsource(portfolio_svc)
    # PortfolioService factory must not inject ExchangeRateClient
    src = inspect.getsource(deps_mod.get_portfolio_service)
    assert "ExchangeRateClient" not in src
    assert "get_exchange_rate_client" not in src
    assert "get_exchange_rate_repo" in src


def test_get_and_refresh_never_need_fx_http_client() -> None:
    """FX repo get_latest may run; portfolio GET/refresh never fetch provider rates."""
    import app.api.portfolio as portfolio_api
    import app.services.portfolio_service as portfolio_svc

    assert "ExchangeRateClient" not in inspect.getsource(portfolio_api)
    assert "ExchangeRateClient" not in inspect.getsource(portfolio_svc)

    fx = InMemoryExchangeRateRepo()
    client, holdings, *_rest = _make_client(fx=fx)
    _seed_btc(holdings)

    r1 = client.get("/api/portfolio", headers=_auth("alice"))
    assert r1.status_code == 200
    r2 = client.post("/api/portfolio/refresh", headers=_auth("alice"))
    assert r2.status_code == 200
    # Repo was consulted for stored rates only
    assert fx.get_latest_calls >= 1


def test_portfolio_with_stored_fx_display_currency() -> None:
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
        "/api/portfolio",
        params={"displayCurrency": "VND"},
        headers=_auth("alice"),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["fx"]["status"] == "fresh"
    assert data["fx"]["rates"]["USD_VND"] == "25000"
    assert data["totalsDisplay"] is not None
    assert data["totalsDisplay"]["currency"] == "VND"
    assert data["totalsDisplay"]["marketValue"] == "1000000000"
    assert data["displayCurrency"] == "VND"


def test_admin_default_display_currency_when_user_pref_empty() -> None:
    """Query override → user pref → admin default_display_currency."""
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
    set_settings_repo(
        InMemorySettingsRepo(SystemSettings(default_display_currency="VND"))
    )
    client, holdings, *_rest, profiles = _make_client(fx=fx)
    _seed_btc(holdings)
    profiles.get_or_create("alice")
    profiles.update_settings("alice", preferred_currency="")

    r = client.get("/api/portfolio", headers=_auth("alice"))
    assert r.status_code == 200
    data = r.json()
    assert data["displayCurrency"] == "VND"
    assert data["totalsDisplay"] is not None
    assert data["totalsDisplay"]["currency"] == "VND"
    assert data["totalsDisplay"]["marketValue"] == "1000000000"

    r2 = client.post("/api/portfolio/refresh", headers=_auth("alice"))
    assert r2.status_code == 200
    assert r2.json()["displayCurrency"] == "VND"


# ---------------------------------------------------------------------------
# Filter assetType
# ---------------------------------------------------------------------------


def test_filter_asset_type_stock() -> None:
    client, holdings, crypto, stock, *_ = _make_client()
    _seed_btc(holdings)
    holdings.create(
        HoldingRecord(
            user_id="alice",
            asset_type="stock",
            symbol="VNM",
            qty=Decimal("100"),
            avg_cost=Decimal("70000"),
            currency="VND",
            asset_id="VNM",
        )
    )

    r = client.get(
        "/api/portfolio",
        params={"assetType": "stock"},
        headers=_auth("alice"),
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["lines"]) == 1
    assert data["lines"][0]["symbol"] == "VNM"
    assert "VND" in data["totalsByCurrency"]
    assert "USD" not in data["totalsByCurrency"]
    assert stock.price_calls == 1
    assert crypto.price_calls == 0


def test_filter_invalid_asset_type_400() -> None:
    client, *_ = _make_client()
    r = client.get(
        "/api/portfolio",
        params={"assetType": "forex"},
        headers=_auth("alice"),
    )
    assert r.status_code == 400
