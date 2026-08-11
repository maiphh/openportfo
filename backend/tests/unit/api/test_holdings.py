"""Sprint 03: holdings ports, service validation, REST CRUD + isolation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.deps import (
    get_holdings_repo,
    get_user_profile_repo,
    set_holdings_repo,
    set_user_profile_repo,
)
from app.main import create_app
from app.ports.holdings import DuplicateHoldingError, HoldingNotFoundError, HoldingRecord
from app.services.holdings_service import HoldingsService, ValidationError
from tests.fakes.holdings import InMemoryHoldingsRepo
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


def _make_client(
    holdings: InMemoryHoldingsRepo | None = None,
    profiles: InMemoryUserProfileRepo | None = None,
) -> tuple[TestClient, InMemoryHoldingsRepo, InMemoryUserProfileRepo]:
    h_repo = holdings or InMemoryHoldingsRepo()
    p_repo = profiles or InMemoryUserProfileRepo()
    set_holdings_repo(h_repo)
    set_user_profile_repo(p_repo)
    app = create_app()
    app.dependency_overrides[get_holdings_repo] = lambda: h_repo
    app.dependency_overrides[get_user_profile_repo] = lambda: p_repo
    return TestClient(app), h_repo, p_repo


@pytest.fixture(autouse=True)
def _reset_repos() -> Any:
    set_holdings_repo(None)
    set_user_profile_repo(None)
    yield
    set_holdings_repo(None)
    set_user_profile_repo(None)


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
