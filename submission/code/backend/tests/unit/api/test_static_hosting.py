"""BL-031: single-EB static hosting — FastAPI serves Next.js static export.

TDD-first coverage for the SA design (D1/D4/D5):
- GET / returns bundled HTML (AC1)
- Deep links (/portfolio/, /auth/callback/) fall back to HTML (AC2)
- /_next/static/* served with JS MIME; /health stays JSON (AC3)
- /api/* without token stays 401 JSON, never HTML (AC2)
- Missing static dir -> API-only mode: / is JSON 404, API still works (edge)
- SERVE_FRONTEND=false forces API-only even when bundled (rollback)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import clear_settings_cache
from app.main import create_app

INDEX_HTML = """<!DOCTYPE html><html><head><title>OpenPortfo</title></head>"""
INDEX_HTML += """<body><div id="__next">OpenPortfo app root</div></body></html>"""


def _write_bundle(root: Path) -> None:
    (root / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (root / "portfolio").mkdir(parents=True, exist_ok=True)
    (root / "portfolio" / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (root / "auth" / "callback").mkdir(parents=True, exist_ok=True)
    (root / "auth" / "callback" / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (root / "_next" / "static").mkdir(parents=True, exist_ok=True)
    (root / "_next" / "static" / "x.js").write_text(
        'console.log("openportfo");', encoding="utf-8"
    )


@pytest.fixture()
def bundled_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """App with FRONTEND_DIR pointing at a fake Next.js export bundle."""
    web = tmp_path / "static_web"
    web.mkdir()
    _write_bundle(web)
    monkeypatch.setenv("SERVE_FRONTEND", "true")
    monkeypatch.setenv("FRONTEND_DIR", str(web))
    clear_settings_cache()
    try:
        return TestClient(create_app())
    finally:
        clear_settings_cache()


@pytest.fixture()
def api_only_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """App with FRONTEND_DIR pointing at a missing dir (API-only mode)."""
    missing = tmp_path / "no-such-static_web"
    assert not missing.exists()
    monkeypatch.setenv("SERVE_FRONTEND", "true")
    monkeypatch.setenv("FRONTEND_DIR", str(missing))
    clear_settings_cache()
    try:
        return TestClient(create_app())
    finally:
        clear_settings_cache()


def test_root_serves_bundled_html(bundled_app: TestClient) -> None:
    r = bundled_app.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "__next" in r.text


def test_deep_links_fall_back_to_html(bundled_app: TestClient) -> None:
    for path in ("/portfolio/", "/portfolio", "/auth/callback/", "/auth/callback"):
        r = bundled_app.get(path)
        assert r.status_code == 200, path
        assert "text/html" in r.headers["content-type"], path
        assert "__next" in r.text, path


def test_next_static_asset_mime(bundled_app: TestClient) -> None:
    r = bundled_app.get("/_next/static/x.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]
    assert "openportfo" in r.text


def test_health_stays_json(bundled_app: TestClient) -> None:
    r = bundled_app.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert "application/json" in r.headers["content-type"]


def test_api_without_token_is_401_json_never_html(bundled_app: TestClient) -> None:
    for path in ("/api/portfolio", "/api/auth/me"):
        r = bundled_app.get(path)
        assert r.status_code == 401, path
        assert "application/json" in r.headers["content-type"], path
        assert "text/html" not in r.headers["content-type"], path
        assert "detail" in r.json(), path


def test_unknown_api_path_is_json_404_not_html(bundled_app: TestClient) -> None:
    r = bundled_app.get("/api/does-not-exist-bl031")
    assert r.status_code == 404
    assert "application/json" in r.headers["content-type"]
    assert "text/html" not in r.headers["content-type"]


def test_missing_static_dir_root_is_json_404(api_only_app: TestClient) -> None:
    r = api_only_app.get("/")
    assert r.status_code == 404
    assert "application/json" in r.headers["content-type"]
    assert r.json() == {"detail": "frontend not bundled"}


def test_missing_static_dir_api_still_works(api_only_app: TestClient) -> None:
    assert api_only_app.get("/health").json() == {"status": "ok"}
    r = api_only_app.get("/api/auth/me")
    assert r.status_code == 401
    assert "detail" in r.json()


def test_serve_frontend_false_forces_api_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    web = tmp_path / "static_web"
    web.mkdir()
    _write_bundle(web)
    monkeypatch.setenv("SERVE_FRONTEND", "false")
    monkeypatch.setenv("FRONTEND_DIR", str(web))
    clear_settings_cache()
    try:
        client = TestClient(create_app())
    finally:
        clear_settings_cache()
    r = client.get("/")
    assert r.status_code == 404
    assert r.json() == {"detail": "frontend not bundled"}
    assert client.get("/health").json() == {"status": "ok"}


def test_late_registered_routes_keep_precedence_over_fallback(
    bundled_app: TestClient,
) -> None:
    """Routes added after create_app() (e.g. test-only routes) win."""
    @bundled_app.app.get("/_test/late-route")
    def _late_route() -> dict[str, str]:
        return {"late": "yes"}

    r = bundled_app.get("/_test/late-route")
    assert r.status_code == 200
    assert r.json() == {"late": "yes"}
