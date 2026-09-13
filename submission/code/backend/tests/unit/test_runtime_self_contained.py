"""Invariants for runtime adapters and local application startup."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys


def test_app_source_does_not_import_tests_packages() -> None:
    app_root = Path(__file__).parents[2] / "app"
    violations: list[str] = []

    for path in sorted(app_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: str | None = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported = alias.name
                    if imported == "tests" or imported.startswith("tests."):
                        violations.append(f"{path}: import {imported}")
            elif isinstance(node, ast.ImportFrom):
                imported = node.module
                if imported == "tests" or (imported and imported.startswith("tests.")):
                    violations.append(f"{path}: from {imported} import ...")

    assert violations == []


def test_local_startup_works_without_backend_tests_on_sys_path() -> None:
    backend_root = Path(__file__).parents[2]
    script = r'''
import sys
from pathlib import Path

backend_root = Path.cwd().resolve()
assert str(backend_root / "tests") not in {str(Path(p).resolve()) for p in sys.path if p}

from app.core.config import clear_settings_cache, get_settings
from app.core.deps import (
    get_exchange_rate_repo,
    get_holdings_repo,
    get_job_runs_repo,
    get_news_repo,
    get_object_storage,
    get_price_cache_repo,
    get_rss_fetcher,
    get_rss_sources_repo,
    get_settings_repo,
    get_snapshot_repo,
    get_token_verifier,
    get_user_profile_repo,
    get_watchlist_repo,
)
from app.main import create_app

clear_settings_cache()
assert get_settings().auth_mode == "fake"
assert get_token_verifier().verify("fake:clean-room").sub == "clean-room"

factories = (
    get_user_profile_repo,
    get_holdings_repo,
    get_watchlist_repo,
    get_price_cache_repo,
    get_exchange_rate_repo,
    get_object_storage,
    get_news_repo,
    get_settings_repo,
    get_rss_sources_repo,
    get_job_runs_repo,
    get_snapshot_repo,
    get_rss_fetcher,
)
for factory in factories:
    adapter = factory()
    assert adapter.__class__.__module__.startswith("app.adapters.memory"), (
        factory.__name__,
        adapter.__class__.__module__,
    )

assert create_app().title == "OpenPortfo"
'''
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(backend_root),
            "OPENPORTFO_DISABLE_ENV_FILE": "1",
            "APP_ENV": "local",
            "AUTH_MODE": "fake",
            "STORAGE_BACKEND": "memory",
            "MARKET_CLIENT_MODE": "fixture",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
