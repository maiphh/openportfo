"""Sprint 03 + BL-001: holdings ports, catalog validation, REST CRUD."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.deps import (
    get_exchange_rate_repo,
    get_fx_service,
    get_holdings_repo,
    get_market_service,
    get_price_cache_repo,
    get_user_profile_repo,
    set_crypto_market_client,
    set_exchange_rate_repo,
    set_fx_service,
    set_holdings_repo,
    set_market_service,
    set_price_cache_repo,
    set_stock_market_client,
    set_user_profile_repo,
)
from app.main import create_app
from app.ports.fx import StoredRates
from app.ports.holdings import DuplicateHoldingError, HoldingNotFoundError, HoldingRecord
from app.services.fx_service import FxService
from app.services.holdings_service import HoldingsService, ValidationError
from app.services.market_service import MarketService
from tests.fakes.fx import InMemoryExchangeRateRepo
from tests.fakes.holdings import InMemoryHoldingsRepo
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.price_cache import InMemoryPriceCacheRepo
from tests.fakes.users import InMemoryUserProfileRepo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{user_id}"}


def _holding_body(
    *,
    asset_type: str = "crypto",
    symbol: str = "BTC",
    asset_id: str | None = "bitcoin",
    qty: str = "1.5",
    avg_cost: str = "40000",
    currency: str = "USD",
    note: str | None = "optional",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "assetType": asset_type,
        "symbol": symbol,
        "qty": qty,
        "avgCost": avg_cost,
        "currency": currency,
    }
    if asset_id is not None:
        body["assetId"] = asset_id
    if note is not None:
        body["note"] = note
    return body


def _seed_fx(repo: InMemoryExchangeRateRepo) -> None:
    repo.seed(
        StoredRates(
            base="USD",
            rates={
                "USD_VND": Decimal("25000"),
                "VND_USD": Decimal("0.00004"),
                "USD_EUR": Decimal("0.92"),
                "EUR_USD": Decimal("1") / Decimal("0.92"),
            },
            as_of=datetime(2026, 8, 1, tzinfo=timezone.utc),
            provider="test",
            status="fresh",
        )
    )


def _make_client(
    holdings: InMemoryHoldingsRepo | None = None,
    profiles: InMemoryUserProfileRepo | None = None,
    fx: InMemoryExchangeRateRepo | None = None,
) -> tuple[TestClient, InMemoryHoldingsRepo, InMemoryUserProfileRepo]:
    h_repo = holdings or InMemoryHoldingsRepo()
    p_repo = profiles or InMemoryUserProfileRepo()
    crypto = FixtureCryptoMarketClient()
    stock = FixtureStockMarketClient()
    cache = InMemoryPriceCacheRepo()
    fx_repo = fx if fx is not None else InMemoryExchangeRateRepo()
    if fx is None:
        _seed_fx(fx_repo)
    market = MarketService(crypto, stock, cache, default_ttl_seconds=600)
    fx_svc = FxService(fx_repo)

    set_holdings_repo(h_repo)
    set_user_profile_repo(p_repo)
    set_crypto_market_client(crypto)
    set_stock_market_client(stock)
    set_price_cache_repo(cache)
    set_exchange_rate_repo(fx_repo)
    set_market_service(market)
    set_fx_service(fx_svc)

    app = create_app()
    app.dependency_overrides[get_holdings_repo] = lambda: h_repo
    app.dependency_overrides[get_user_profile_repo] = lambda: p_repo
    app.dependency_overrides[get_market_service] = lambda: market
    app.dependency_overrides[get_fx_service] = lambda: fx_svc
    app.dependency_overrides[get_exchange_rate_repo] = lambda: fx_repo
    app.dependency_overrides[get_price_cache_repo] = lambda: cache
    return TestClient(app), h_repo, p_repo


@pytest.fixture(autouse=True)
def _reset_repos() -> Any:
    set_holdings_repo(None)
    set_user_profile_repo(None)
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_exchange_rate_repo(None)
    set_market_service(None)
    set_fx_service(None)
    yield
    set_holdings_repo(None)
    set_user_profile_repo(None)
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_exchange_rate_repo(None)
    set_market_service(None)
    set_fx_service(None)


# ---------------------------------------------------------------------------
# 1. In-memory repo CRUD
# ---------------------------------------------------------------------------


def test_inmemory_holdings_create_list_get() -> None:
    repo = InMemoryHoldingsRepo()
    created = repo.create(
        HoldingRecord(
            user_id="alice",
            asset_type="crypto",
            symbol="btc",
            qty=Decimal("1.5"),
            avg_cost=Decimal("40000"),
            currency="USD",
            asset_id="bitcoin",
        )
    )
    assert created.symbol == "BTC"  # normalized
    assert created.sk == "HOLD#crypto#BTC"
    listed = repo.list("alice")
    assert len(listed) == 1
    assert listed[0].qty == Decimal("1.5")
    got = repo.get("alice", "crypto", "BTC")
    assert got is not None
    assert got.avg_cost == Decimal("40000")


def test_inmemory_holdings_duplicate_raises() -> None:
    repo = InMemoryHoldingsRepo()
    rec = HoldingRecord(
        user_id="alice",
        asset_type="crypto",
        symbol="BTC",
        qty=Decimal("1"),
        avg_cost=Decimal("1"),
        currency="USD",
    )
    repo.create(rec)
    with pytest.raises(DuplicateHoldingError):
        repo.create(rec)


def test_inmemory_holdings_update_delete() -> None:
    repo = InMemoryHoldingsRepo()
    repo.create(
        HoldingRecord(
            user_id="alice",
            asset_type="stock",
            symbol="VNM",
            qty=Decimal("10"),
            avg_cost=Decimal("70000"),
            currency="VND",
        )
    )
    updated = repo.update(
        "alice",
        "stock",
        "VNM",
        qty=Decimal("20"),
        avg_cost=Decimal("71000"),
        note="doubled",
    )
    assert updated.qty == Decimal("20")
    assert updated.avg_cost == Decimal("71000")
    assert updated.note == "doubled"
    repo.delete("alice", "stock", "VNM")
    assert repo.get("alice", "stock", "VNM") is None
    with pytest.raises(HoldingNotFoundError):
        repo.delete("alice", "stock", "VNM")


def test_inmemory_holdings_user_isolation() -> None:
    repo = InMemoryHoldingsRepo()
    repo.create(
        HoldingRecord(
            user_id="a",
            asset_type="crypto",
            symbol="BTC",
            qty=Decimal("1"),
            avg_cost=Decimal("1"),
            currency="USD",
        )
    )
    repo.create(
        HoldingRecord(
            user_id="b",
            asset_type="crypto",
            symbol="ETH",
            qty=Decimal("2"),
            avg_cost=Decimal("2"),
            currency="USD",
        )
    )
    assert len(repo.list("a")) == 1
    assert repo.list("a")[0].symbol == "BTC"
    assert len(repo.list("b")) == 1
    assert repo.list("b")[0].symbol == "ETH"


# ---------------------------------------------------------------------------
# 2. Service validation
# ---------------------------------------------------------------------------


def test_service_rejects_invalid_qty() -> None:
    svc = HoldingsService(InMemoryHoldingsRepo())
    with pytest.raises(ValidationError, match="qty"):
        svc.create_holding(
            "u1",
            asset_type="crypto",
            symbol="BTC",
            qty="0",
            avg_cost="100",
            currency="USD",
        )
    with pytest.raises(ValidationError, match="qty"):
        svc.create_holding(
            "u1",
            asset_type="crypto",
            symbol="BTC",
            qty="-1",
            avg_cost="100",
            currency="USD",
        )


def test_service_rejects_negative_avg_cost() -> None:
    svc = HoldingsService(InMemoryHoldingsRepo())
    with pytest.raises(ValidationError, match="avgCost"):
        svc.create_holding(
            "u1",
            asset_type="crypto",
            symbol="BTC",
            qty="1",
            avg_cost="-0.01",
            currency="USD",
        )


def test_service_allows_zero_avg_cost() -> None:
    svc = HoldingsService(InMemoryHoldingsRepo())
    h = svc.create_holding(
        "u1",
        asset_type="crypto",
        symbol="BTC",
        qty="1",
        avg_cost="0",
        currency="USD",
    )
    assert h.avg_cost == Decimal("0")


# ---------------------------------------------------------------------------
# 3. API: auth, create, list, validation, isolation, update, delete, 409
# ---------------------------------------------------------------------------


def test_holdings_require_auth() -> None:
    client, _, _ = _make_client()
    assert client.get("/api/holdings").status_code == 401
    assert client.post("/api/holdings", json=_holding_body()).status_code == 401


def test_post_and_get_holdings() -> None:
    client, _, _ = _make_client()
    r = client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["userId"] == "alice"
    assert body["assetType"] == "crypto"
    assert body["symbol"] == "BTC"
    assert body["assetId"] == "bitcoin"
    assert body["qty"] == "1.5"
    assert body["avgCost"] == "40000"
    assert body["currency"] == "USD"
    assert body["note"] == "optional"
    assert "createdAt" in body and "updatedAt" in body

    listed = client.get("/api/holdings", headers=_auth("alice"))
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["symbol"] == "BTC"


def test_invalid_qty_returns_400() -> None:
    client, _, _ = _make_client()
    r = client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(qty="0"),
    )
    assert r.status_code == 400
    assert "qty" in r.json()["detail"].lower()

    r2 = client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(qty="-5", avg_cost="-1"),
    )
    assert r2.status_code == 400


def test_user_isolation_holdings() -> None:
    client, _, _ = _make_client()
    assert (
        client.post(
            "/api/holdings",
            headers=_auth("alice"),
            json=_holding_body(symbol="BTC"),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/holdings",
            headers=_auth("bob"),
            json=_holding_body(symbol="ETH", asset_id="ethereum", qty="2"),
        ).status_code
        == 201
    )

    alice_list = client.get("/api/holdings", headers=_auth("alice")).json()
    bob_list = client.get("/api/holdings", headers=_auth("bob")).json()
    assert len(alice_list) == 1
    assert alice_list[0]["symbol"] == "BTC"
    assert alice_list[0]["userId"] == "alice"
    assert len(bob_list) == 1
    assert bob_list[0]["symbol"] == "ETH"
    assert bob_list[0]["userId"] == "bob"


def test_update_holding() -> None:
    client, _, _ = _make_client()
    client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(qty="1", avg_cost="40000"),
    )
    r = client.put(
        "/api/holdings/crypto/BTC",
        headers=_auth("alice"),
        json={"qty": "2.5", "avgCost": "41000", "note": "updated"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["qty"] == "2.5"
    assert body["avgCost"] == "41000"
    assert body["note"] == "updated"


def test_update_holding_invalid_qty_400() -> None:
    client, _, _ = _make_client()
    client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(),
    )
    r = client.put(
        "/api/holdings/crypto/BTC",
        headers=_auth("alice"),
        json={"qty": "0"},
    )
    assert r.status_code == 400


def test_update_missing_holding_404() -> None:
    client, _, _ = _make_client()
    r = client.put(
        "/api/holdings/crypto/BTC",
        headers=_auth("alice"),
        json={"qty": "1"},
    )
    assert r.status_code == 404


def test_delete_holding() -> None:
    client, _, _ = _make_client()
    client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(),
    )
    r = client.delete("/api/holdings/crypto/BTC", headers=_auth("alice"))
    assert r.status_code == 204
    listed = client.get("/api/holdings", headers=_auth("alice")).json()
    assert listed == []
    r2 = client.delete("/api/holdings/crypto/BTC", headers=_auth("alice"))
    assert r2.status_code == 404


def test_duplicate_holding_409() -> None:
    client, _, _ = _make_client()
    assert (
        client.post(
            "/api/holdings",
            headers=_auth("alice"),
            json=_holding_body(),
        ).status_code
        == 201
    )
    r = client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(qty="9", avg_cost="1"),
    )
    assert r.status_code == 409
    assert "detail" in r.json()


def test_never_trust_user_id_from_body() -> None:
    """userId in body is ignored; ownership always current_user.user_id."""
    client, h_repo, _ = _make_client()
    # Extra fields should not assign ownership to another user
    body = _holding_body()
    body["userId"] = "eve"
    r = client.post("/api/holdings", headers=_auth("alice"), json=body)
    assert r.status_code == 201
    assert r.json()["userId"] == "alice"
    assert len(h_repo.list("eve")) == 0
    assert len(h_repo.list("alice")) == 1


def test_bob_cannot_update_or_delete_alice_holding() -> None:
    client, _, _ = _make_client()
    client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(),
    )
    assert (
        client.put(
            "/api/holdings/crypto/BTC",
            headers=_auth("bob"),
            json={"qty": "99"},
        ).status_code
        == 404
    )
    assert (
        client.delete(
            "/api/holdings/crypto/BTC",
            headers=_auth("bob"),
        ).status_code
        == 404
    )
    # Alice still has it
    listed = client.get("/api/holdings", headers=_auth("alice")).json()
    assert len(listed) == 1
    assert listed[0]["qty"] == "1.5"


def test_export_holdings_csv() -> None:
    client, _, _ = _make_client()
    client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(),
    )
    r = client.get("/api/holdings/export", headers=_auth("alice"))
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    text = r.text
    assert "assetType,symbol,assetId,qty,avgCost,currency,note" in text
    assert "crypto,BTC,bitcoin,1.5,40000,USD,optional" in text
    assert client.get("/api/holdings/export").status_code == 401


# ---------------------------------------------------------------------------
# 4. BL-001: catalog validity + session→native cost conversion
# ---------------------------------------------------------------------------


def test_reject_unknown_crypto_holding() -> None:
    client, h_repo, _ = _make_client()
    r = client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(symbol="NOTACOIN", asset_id="not-a-coin"),
    )
    assert r.status_code == 400
    assert "invalid" in r.json()["detail"].lower() or "unknown" in r.json()["detail"].lower()
    assert h_repo.list("alice") == []


def test_reject_unknown_stock_holding() -> None:
    client, h_repo, _ = _make_client()
    r = client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(
            asset_type="stock",
            symbol="ZZZZ",
            asset_id=None,
            avg_cost="10000",
            currency="VND",
            note=None,
        ),
    )
    assert r.status_code == 400
    assert h_repo.list("alice") == []


def test_create_valid_stock_stores_vnd() -> None:
    client, _, _ = _make_client()
    r = client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(
            asset_type="stock",
            symbol="VNM",
            asset_id="VNM",
            qty="10",
            avg_cost="70000",
            currency="VND",
            note=None,
        ),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["symbol"] == "VNM"
    assert body["currency"] == "VND"
    assert body["avgCost"] == "70000"


def test_create_crypto_converts_vnd_session_cost_to_usd() -> None:
    """avgCost entered in session VND → stored native USD."""
    client, _, _ = _make_client()
    r = client.post(
        "/api/holdings",
        headers=_auth("alice"),
        json=_holding_body(
            symbol="BTC",
            asset_id="bitcoin",
            qty="1",
            avg_cost="25000000",  # 25M VND == 1000 USD at test FX
            currency="VND",
            note=None,
        ),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["currency"] == "USD"
    assert Decimal(body["avgCost"]) == Decimal("1000")


def test_update_avg_cost_converts_session_to_native() -> None:
    client, _, _ = _make_client()
    assert (
        client.post(
            "/api/holdings",
            headers=_auth("alice"),
            json=_holding_body(qty="1", avg_cost="40000", currency="USD"),
        ).status_code
        == 201
    )
    r = client.put(
        "/api/holdings/crypto/BTC",
        headers=_auth("alice"),
        json={"avgCost": "50000000", "currency": "VND"},  # 2000 USD
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["currency"] == "USD"
    assert Decimal(body["avgCost"]) == Decimal("2000")


def test_service_rejects_unresolvable_when_market_wired() -> None:
    market = MarketService(
        FixtureCryptoMarketClient(),
        FixtureStockMarketClient(),
        InMemoryPriceCacheRepo(),
    )
    svc = HoldingsService(InMemoryHoldingsRepo(), market=market)
    with pytest.raises(ValidationError, match="[Ii]nvalid|[Uu]nknown"):
        svc.create_holding(
            "u1",
            asset_type="crypto",
            symbol="NOPE",
            qty="1",
            avg_cost="1",
            currency="USD",
        )
