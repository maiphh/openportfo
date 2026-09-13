"""GET /api/portfolio/performance from stored snapshots."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.deps import (
    get_snapshot_service,
    get_user_profile_repo,
    set_snapshot_repo,
    set_snapshot_service,
    set_user_profile_repo,
)
from app.main import create_app
from app.ports.snapshots import SnapshotRecord
from app.services.snapshot_service import SnapshotService
from tests.fakes.snapshots import InMemorySnapshotRepo
from tests.fakes.users import InMemoryUserProfileRepo


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{user_id}"}


def _snap(user_id: str, day: str, value: str) -> SnapshotRecord:
    return SnapshotRecord(
        user_id=user_id,
        date=day,
        payload={"totalsDisplay": {"currency": "USD", "marketValue": value}},
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


@pytest.fixture(autouse=True)
def _reset() -> Any:
    set_snapshot_repo(None)
    set_snapshot_service(None)
    set_user_profile_repo(None)
    yield
    set_snapshot_repo(None)
    set_snapshot_service(None)
    set_user_profile_repo(None)


def _client(repo: InMemorySnapshotRepo) -> TestClient:
    svc = SnapshotService(repo)
    set_snapshot_repo(repo)
    set_snapshot_service(svc)
    set_user_profile_repo(InMemoryUserProfileRepo())
    app = create_app()
    app.dependency_overrides[get_snapshot_service] = lambda: svc
    return TestClient(app)


def test_performance_requires_auth() -> None:
    assert _client(InMemorySnapshotRepo()).get("/api/portfolio/performance").status_code == 401


def test_performance_1w_change() -> None:
    repo = InMemorySnapshotRepo()
    repo.put(_snap("alice", "2026-08-10", "100"))
    repo.put(_snap("alice", "2026-08-15", "130"))
    repo.put(_snap("bob", "2026-08-15", "9"))
    svc = SnapshotService(repo)
    body = svc.performance("alice", range_="1w", today=date(2026, 8, 16))
    assert body["startValue"] == "100"
    assert body["endValue"] == "130"
    assert body["change"] == "30"
    assert body["changePercent"] == "0.3"
    assert body["currency"] == "USD"
    assert [p["date"] for p in body["points"]] == ["2026-08-10", "2026-08-15"]

    client = _client(repo)
    r = client.get(
        "/api/portfolio/performance",
        params={"range": "max"},
        headers=_auth("alice"),
    )
    assert r.status_code == 200
    assert r.json()["endValue"] == "130"


def test_performance_mixed_currency_does_not_subtract() -> None:
    repo = InMemorySnapshotRepo()
    repo.put(
        SnapshotRecord(
            user_id="alice",
            date="2026-08-10",
            payload={"totalsByCurrency": {"USD": {"marketValue": "100"}}},
            created_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
        )
    )
    repo.put(
        SnapshotRecord(
            user_id="alice",
            date="2026-08-15",
            payload={"totalsDisplay": {"currency": "VND", "marketValue": "2500000"}},
            created_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        )
    )
    body = SnapshotService(repo).performance("alice", range_="1w", today=date(2026, 8, 16))
    assert body["currency"] == "VND"
    assert body["startValue"] == "2500000"
    assert body["endValue"] == "2500000"
    assert body["change"] is None
    assert body["changePercent"] is None


def test_performance_single_point_has_no_change() -> None:
    repo = InMemorySnapshotRepo()
    repo.put(_snap("alice", "2026-08-15", "130"))
    body = SnapshotService(repo).performance("alice", range_="1w", today=date(2026, 8, 16))
    assert body["endValue"] == "130"
    assert body["change"] is None
    assert body["changePercent"] is None


def test_requested_currency_uses_native_totals_before_legacy_display() -> None:
    repo = InMemorySnapshotRepo()
    repo.put(
        SnapshotRecord(
            user_id="alice",
            date="2026-08-15",
            payload={
                "totalsByCurrency": {"USD": {"marketValue": "100"}},
                # Deliberately inconsistent legacy derived data. Native totals
                # must remain the source of truth for historical conversion.
                "totalsDisplay": {"currency": "VND", "marketValue": "1"},
                "fx": {
                    "base": "USD",
                    "status": "fresh",
                    "rates": {"USD_VND": "25000"},
                },
            },
            created_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        )
    )

    body = SnapshotService(repo).performance(
        "alice",
        range_="1w",
        today=date(2026, 8, 16),
        currency="VND",
    )

    assert body["endValue"] == "2500000"
    assert body["currency"] == "VND"


def test_performance_bad_range_400() -> None:
    client = _client(InMemorySnapshotRepo())
    r = client.get(
        "/api/portfolio/performance",
        params={"range": "intraday"},
        headers=_auth("alice"),
    )
    assert r.status_code == 400
