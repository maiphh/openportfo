"""Sprint 06: FxService — save/get, success, failure keeps previous."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.ports.fx import RateSnapshot, StoredRates
from app.services.fx_service import FxService, ensure_pair_rates
from tests.fakes.fx import FakeExchangeRateClient, InMemoryExchangeRateRepo


def test_ensure_pair_rates_adds_inverse() -> None:
    out = ensure_pair_rates({"USD_VND": Decimal("25000")}, base="USD")
    assert out["USD_VND"] == Decimal("25000")
    assert out["VND_USD"] == Decimal("1") / Decimal("25000")


def test_repo_save_and_get() -> None:
    repo = InMemoryExchangeRateRepo()
    assert repo.get_latest() is None
    snap = RateSnapshot(
        base="USD",
        rates={"USD_VND": Decimal("25000"), "VND_USD": Decimal("0.00004")},
        provider="exchangerate-api",
        fetched_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
    )
    stored = repo.save(snap, updated_by="admin1")
    assert stored.last_refresh_status == "success"
    assert stored.updated_by == "admin1"
    got = repo.get_latest()
    assert got is not None
    assert got.rates["USD_VND"] == Decimal("25000")
    assert repo.save_calls == 1


def test_refresh_success_updates_repo() -> None:
    repo = InMemoryExchangeRateRepo()
    client = FakeExchangeRateClient()
    svc = FxService(repo, client)
    result = svc.refresh(admin_user_id="admin1")
    assert result.ok is True
    assert result.stored is not None
    assert result.stored.rates["USD_VND"] == Decimal("25000")
    assert client.fetch_calls == 1
    assert repo.save_calls == 1
    assert repo.get_latest() is not None


def test_refresh_failure_keeps_previous() -> None:
    old = StoredRates(
        base="USD",
        rates={"USD_VND": Decimal("24000"), "VND_USD": Decimal("1") / Decimal("24000")},
        as_of=datetime(2026, 1, 1, tzinfo=timezone.utc),
        provider="exchangerate-api",
        status="fresh",
        last_refresh_status="success",
    )
    repo = InMemoryExchangeRateRepo(initial=old)
    client = FakeExchangeRateClient(fail=True, fail_message="upstream down")
    svc = FxService(repo, client)
    result = svc.refresh(admin_user_id="admin1")
    assert result.ok is False
    assert result.error == "upstream down"
    assert result.stored is not None
    assert result.stored.rates["USD_VND"] == Decimal("24000")
    assert repo.save_calls == 0
    assert client.fetch_calls == 1
    # still previous
    assert repo.get_latest().rates["USD_VND"] == Decimal("24000")


def test_get_rates_never_calls_client() -> None:
    repo = InMemoryExchangeRateRepo()
    client = FakeExchangeRateClient()
    svc = FxService(repo, client)
    svc.get_rates()
    assert client.fetch_calls == 0
