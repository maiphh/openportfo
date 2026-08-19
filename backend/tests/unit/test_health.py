"""Sprint 00: health endpoint."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_ok_on_in_memory_backends() -> None:
    client = TestClient(create_app())
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["storage"]["status"] == "ok"


def test_ready_degraded_when_storage_fails() -> None:
    from app.core.deps import get_object_storage, set_object_storage
    from tests.fakes.storage import InMemoryObjectStorage

    storage = InMemoryObjectStorage()
    storage.fail_ping = True
    set_object_storage(storage)
    try:
        client = TestClient(create_app())
        response = client.get("/health/ready")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "degraded"
        assert body["checks"]["storage"]["status"] == "error"
    finally:
        set_object_storage(None)
