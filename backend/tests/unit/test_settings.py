"""Sprint 00: settings loading."""

from app.core.config import Settings, clear_settings_cache, get_settings


def test_settings_loads_defaults() -> None:
    clear_settings_cache()
    settings = Settings()
    assert settings.app_name == "OpenPortfo"
    assert settings.auth_mode == "fake"
    assert settings.aws_region == "us-east-1"
    assert "http://localhost:3000" in settings.cors_origin_list


def test_settings_loads_from_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_MODE", "fake")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("APP_NAME", "OpenPortfoTest")
    clear_settings_cache()
    settings = get_settings()
    assert settings.app_env == "test"
    assert settings.auth_mode == "fake"
    assert settings.aws_region == "us-east-1"
    assert settings.app_name == "OpenPortfoTest"
    clear_settings_cache()
