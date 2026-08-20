"""Sprint 06: GET /api/fx/rates + POST /api/admin/fx/refresh."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.deps import (
    set_exchange_rate_client,
    set_exchange_rate_repo,
    set_fx_service,
    set_holdings_repo,
    set_market_service,
    set_portfolio_service,
    set_price_cache_repo,
    set_user_profile_repo,
)
from app.domain.models import PriceQuote
from app.main import create_app
from app.ports.fx import StoredRates
from app.ports.holdings import HoldingRecord
from app.services.fx_service import FxService
from app.services.market_service import MarketService
from app.services.portfolio_service import PortfolioService
from tests.fakes.fx import FakeExchangeRateClient, InMemoryExchangeRateRepo
from tests.fakes.holdings import InMemoryHoldingsRepo
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.price_cache import InMemoryPriceCacheRepo
from tests.fakes.users import InMemoryUserProfileRepo


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{user_id}"}


def _reset() -> None:
    set_user_profile_repo(None)
    set_exchange_rate_repo(None)
    set_exchange_rate_client(None)
    set_fx_service(None)
    set_holdings_repo(None)
    set_price_cache_repo(None)
    set_market_service(None)
    set_portfolio_service(None)


def _client(
    *,
    repo: InMemoryExchangeRateRepo | None = None,
    fx_client: FakeExchangeRateClient | None = None,
    profiles: InMemoryUserProfileRepo | None = None,
) -> tuple[TestClient, InMemoryExchangeRateRepo, FakeExchangeRateClient, InMemoryUserProfileRepo]:
    _reset()
    repo = repo or InMemoryExchangeRateRepo()
    fx_client = fx_client or FakeExchangeRateClient()
    profiles = profiles or InMemoryUserProfileRepo()
    set_user_profile_repo(profiles)
    set_exchange_rate_repo(repo)
    set_exchange_rate_client(fx_client)
    set_fx_service(FxService(repo, fx_client))
    return TestClient(create_app()), repo, fx_client, profiles


def test_get_rates_is_public_for_frontend_display_conversion() -> None:
    client, _, _, _ = _client()
    r = client.get("/api/fx/rates")
    assert r.status_code == 200
    assert r.json()["status"] == "missing"


def test_get_rates_does_not_call_provider() -> None:
    client, repo, fx_client, profiles = _client()
    profiles.get_or_create("u1", email="u1@test.com", name="U1")
    repo.seed(
        StoredRates(
            base="USD",
            rates={"USD_VND": Decimal("25000")},
            as_of=datetime(2026, 8, 1, tzinfo=timezone.utc),
            status="fresh",
            last_refresh_status="success",
        )
    )
    r = client.get("/api/fx/rates")
    assert r.status_code == 200
    body = r.json()
    assert body["rates"]["USD_VND"] == "25000"
    assert "lastRefreshError" not in body
    assert "updatedBy" not in body
    assert fx_client.fetch_calls == 0


def test_convert_uses_stored_direct_and_inverse_rates() -> None:
    client, repo, fx_client, profiles = _client()
    profiles.get_or_create("u1", email="u1@test.com", name="U1")
    repo.seed(
        StoredRates(
            base="USD",
            rates={"USD_VND": Decimal("25000")},
            as_of=datetime(2026, 8, 1, tzinfo=timezone.utc),
            status="fresh",
        )
    )
    usd_to_vnd = client.post(
        "/api/fx/convert",
        json={"amount": "2", "sourceCurrency": "USD", "targetCurrency": "VND"},
        headers=_auth("u1"),
    )
    assert usd_to_vnd.status_code == 200
    assert usd_to_vnd.json()["convertedAmount"] == "50000"

    vnd_to_usd = client.post(
        "/api/fx/convert",
        json={"amount": "25000", "sourceCurrency": "VND", "targetCurrency": "USD"},
        headers=_auth("u1"),
    )
    assert vnd_to_usd.status_code == 200
    assert Decimal(vnd_to_usd.json()["convertedAmount"]) == Decimal("1")
    assert fx_client.fetch_calls == 0


def test_refresh_non_admin_403() -> None:
    client, _, fx_client, profiles = _client()
    profiles.get_or_create("u1", email="u1@test.com", name="U1")
    r = client.post("/api/admin/fx/refresh", headers=_auth("u1"))
    assert r.status_code == 403
    assert fx_client.fetch_calls == 0


def test_refresh_success_admin() -> None:
    client, repo, fx_client, profiles = _client()
    profiles.get_or_create("admin1", email="a@test.com", name="Admin")
    profiles.set_role("admin1", "admin")
    r = client.post("/api/admin/fx/refresh", headers=_auth("admin1"))
    assert r.status_code == 200
    body = r.json()
    assert "USD_VND" in body["rates"]
    assert body["lastRefreshStatus"] == "success"
    assert fx_client.fetch_calls == 1
    assert repo.save_calls == 1


def test_refresh_failure_502_keeps_previous() -> None:
    old = StoredRates(
        base="USD",
        rates={"USD_VND": Decimal("24000"), "VND_USD": Decimal("1") / Decimal("24000")},
        as_of=datetime(2026, 1, 1, tzinfo=timezone.utc),
        provider="exchangerate-api",
        status="fresh",
        last_refresh_status="success",
    )
    repo = InMemoryExchangeRateRepo(initial=old)
    fx_client = FakeExchangeRateClient(fail=True, fail_message="boom")
    client, repo, fx_client, profiles = _client(repo=repo, fx_client=fx_client)
    profiles.get_or_create("admin1", email="a@test.com", name="Admin")
    profiles.set_role("admin1", "admin")
    r = client.post("/api/admin/fx/refresh", headers=_auth("admin1"))
    assert r.status_code == 502
    body = r.json()
    assert "boom" in body["detail"]
    assert body["rates"]["rates"]["USD_VND"] == "24000"
    assert repo.save_calls == 0
    assert repo.get_latest().rates["USD_VND"] == Decimal("24000")


def test_portfolio_uses_stored_rates_after_seed() -> None:
    """After seeding FX, portfolio converts with stored rates (no provider)."""
    _reset()
    profiles = InMemoryUserProfileRepo()
    holdings = InMemoryHoldingsRepo()
    cache = InMemoryPriceCacheRepo()
    crypto = FixtureCryptoMarketClient()
    stock = FixtureStockMarketClient()
    fx_repo = InMemoryExchangeRateRepo()
    fx_client = FakeExchangeRateClient()

    profiles.get_or_create("alice", email="a@test.com", name="Alice")
    holdings.create(
        HoldingRecord(
            user_id="alice",
            asset_type="crypto",
            symbol="BTC",
            qty=Decimal("1"),
            avg_cost=Decimal("30000"),
            currency="USD",
            asset_id="bitcoin",
        )
    )
    cache.put(
        PriceQuote(
            asset_type="crypto",
            symbol="BTC",
            price=Decimal("40000"),
            currency="USD",
            as_of=datetime(2026, 8, 9, tzinfo=timezone.utc),
        ),
        ttl_seconds=600,
    )
    fx_repo.seed(
        StoredRates(
            base="USD",
            rates={
                "USD_VND": Decimal("25000"),
                "VND_USD": Decimal("1") / Decimal("25000"),
            },
            as_of=datetime(2026, 8, 9, tzinfo=timezone.utc),
            status="fresh",
            last_refresh_status="success",
        )
    )

    set_user_profile_repo(profiles)
    set_holdings_repo(holdings)
    set_price_cache_repo(cache)
    set_exchange_rate_repo(fx_repo)
    set_exchange_rate_client(fx_client)
    market = MarketService(crypto, stock, cache, default_ttl_seconds=600)
    set_market_service(market)
    set_portfolio_service(PortfolioService(holdings, market, fx_repo=fx_repo))
    set_fx_service(FxService(fx_repo, fx_client))

    client = TestClient(create_app())
    r = client.get(
        "/api/portfolio",
        headers=_auth("alice"),
        params={"displayCurrency": "VND"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["fx"]["status"] != "missing"
    # 40000 * 25000 = 1_000_000_000
    assert body["totalsDisplay"] is not None or body.get("marketValueDisplay") is not None or any(
        line.get("marketValueDisplay") for line in body.get("lines", [])
    )
    assert fx_client.fetch_calls == 0
    _reset()
