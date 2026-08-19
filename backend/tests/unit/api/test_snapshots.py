"""Snapshot list/get + user isolation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.deps import (
    get_snapshot_repo,
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


def _record(user_id: str, date: str, value: str = "100") -> SnapshotRecord:
    return SnapshotRecord(
        user_id=user_id,
        date=date,
        payload={
            "totalsDisplay": {"currency": "USD", "marketValue": value},
            "totalsByCurrency": {"USD": {"marketValue": value}},
        },
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


def _make_client(
    snaps: InMemorySnapshotRepo | None = None,
) -> tuple[TestClient, InMemorySnapshotRepo]:
    repo = snaps or InMemorySnapshotRepo()
    profiles = InMemoryUserProfileRepo()
    set_snapshot_repo(repo)
    set_snapshot_service(SnapshotService(repo))
    set_user_profile_repo(profiles)
    app = create_app()
    app.dependency_overrides[get_snapshot_repo] = lambda: repo
    app.dependency_overrides[get_snapshot_service] = lambda: SnapshotService(repo)
    app.dependency_overrides[get_user_profile_repo] = lambda: profiles
    return TestClient(app), repo


@pytest.fixture(autouse=True)
def _reset() -> Any:
    set_snapshot_repo(None)
    set_snapshot_service(None)
    set_user_profile_repo(None)
    yield
    set_snapshot_repo(None)
    set_snapshot_service(None)
    set_user_profile_repo(None)


def test_snapshots_require_auth() -> None:
    client, _ = _make_client()
    assert client.get("/api/snapshots").status_code == 401
    assert client.get("/api/snapshots/2026-08-01").status_code == 401


def test_list_and_get_snapshot() -> None:
    repo = InMemorySnapshotRepo()
    repo.put(_record("alice", "2026-08-01", "100"))
    repo.put(_record("alice", "2026-08-10", "150"))
    repo.put(_record("bob", "2026-08-10", "999"))
    client, _ = _make_client(repo)

    listed = client.get("/api/snapshots", headers=_auth("alice"))
    assert listed.status_code == 200
    dates = [row["date"] for row in listed.json()]
    assert dates == ["2026-08-01", "2026-08-10"]

    ranged = client.get(
        "/api/snapshots",
        params={"from": "2026-08-05", "to": "2026-08-31"},
        headers=_auth("alice"),
    )
    assert [row["date"] for row in ranged.json()] == ["2026-08-10"]

    one = client.get("/api/snapshots/2026-08-01", headers=_auth("alice"))
    assert one.status_code == 200
    assert one.json()["payload"]["totalsDisplay"]["marketValue"] == "100"


def test_snapshot_not_found_and_isolation() -> None:
    repo = InMemorySnapshotRepo()
    repo.put(_record("alice", "2026-08-01"))
    client, _ = _make_client(repo)
    assert client.get("/api/snapshots/2026-08-02", headers=_auth("alice")).status_code == 404
    assert client.get("/api/snapshots/2026-08-01", headers=_auth("bob")).status_code == 404


def test_snapshot_bad_date_400() -> None:
    client, _ = _make_client()
    assert client.get("/api/snapshots/not-a-date", headers=_auth("alice")).status_code == 400
    assert (
        client.get(
            "/api/snapshots",
            params={"from": "2026-08-10", "to": "2026-08-01"},
            headers=_auth("alice"),
        ).status_code
        == 400
    )
