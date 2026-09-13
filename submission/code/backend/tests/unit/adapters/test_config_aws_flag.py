"""Config flags for AWS adapter selection (offline)."""

from __future__ import annotations

from app.core.config import Settings, clear_settings_cache


def test_use_aws_adapters_true(monkeypatch) -> None:
    monkeypatch.setenv("USE_AWS_ADAPTERS", "true")
    clear_settings_cache()
    s = Settings()
    assert s.aws_adapters_enabled() is True
    clear_settings_cache()


def test_storage_backend_aws(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "aws")
    clear_settings_cache()
    s = Settings()
    assert s.aws_adapters_enabled() is True
    clear_settings_cache()


def test_memory_backend_stays_off_without_flag(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "memory")
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("USE_AWS_ADAPTERS", raising=False)
    clear_settings_cache()
    s = Settings()
    # memory is explicit offline/safe default even if APP_ENV=prod
    assert s.aws_adapters_enabled() is False
    clear_settings_cache()
