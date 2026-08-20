"""Sprint 00: settings loading."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, clear_settings_cache, get_settings
from app.main import create_app


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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("APP_ENV", "staging"),
        ("AUTH_MODE", "basic"),
        ("STORAGE_BACKEND", "redis"),
        ("MARKET_CLIENT_MODE", "cache"),
    ],
)
def test_settings_rejects_unknown_mode_values(monkeypatch, field: str, value: str) -> None:
    monkeypatch.setenv(field, value)
    with pytest.raises(ValidationError):
        Settings()


def test_settings_keeps_lambda_prod_fake_auth_constructible() -> None:
    settings = Settings(
        APP_ENV="prod",
        AUTH_MODE="fake",
        STORAGE_BACKEND="aws",
        DATA_BUCKET="jobs-bucket",
    )
    assert settings.app_env == "prod"
    assert settings.auth_mode == "fake"


def test_api_runtime_rejects_unsafe_production_defaults() -> None:
    settings = Settings(APP_ENV="prod")
    with pytest.raises(RuntimeError, match="STORAGE_BACKEND must be aws"):
        settings.validate_api_runtime()


def test_api_runtime_rejects_blank_data_plane_values() -> None:
    valid = {
        "APP_ENV": "prod",
        "AUTH_MODE": "cognito",
        "STORAGE_BACKEND": "aws",
        "DATA_BUCKET": "api-bucket",
        "MARKET_CLIENT_MODE": "http",
        "COGNITO_USER_POOL_ID": "us-east-1_pool",
        "COGNITO_APP_CLIENT_ID": "client-id",
    }

    for field in ("AWS_REGION", "USERS_TABLE", "SNAPSHOTS_TABLE"):
        settings = Settings(**valid, **{field: "   "})
        with pytest.raises(RuntimeError) as exc_info:
            settings.validate_api_runtime()
        message = str(exc_info.value)
        assert field in message
        assert "api-bucket" not in message


@pytest.mark.parametrize("field", ["DYNAMODB_ENDPOINT_URL", "S3_ENDPOINT_URL"])
@pytest.mark.parametrize(
    "endpoint",
    [
        "http://127.0.0.1:4566",
        "http://localstack:4566",
        "http://host.docker.internal:4566",
        "not a URL",
        "http://[::1",
    ],
)
def test_api_runtime_rejects_any_non_empty_data_plane_endpoint(
    field: str,
    endpoint: str,
) -> None:
    settings = Settings(
        APP_ENV="prod",
        AUTH_MODE="cognito",
        STORAGE_BACKEND="aws",
        DATA_BUCKET="api-bucket",
        MARKET_CLIENT_MODE="http",
        COGNITO_USER_POOL_ID="us-east-1_pool",
        COGNITO_APP_CLIENT_ID="client-id",
        **{field: endpoint},
    )
    with pytest.raises(RuntimeError, match=field):
        settings.validate_api_runtime()


@pytest.mark.parametrize("field", ["DYNAMODB_ENDPOINT_URL", "S3_ENDPOINT_URL"])
@pytest.mark.parametrize("endpoint", ["", "   ", "\t\n"])
def test_api_runtime_allows_empty_data_plane_endpoint(field: str, endpoint: str) -> None:
    settings = Settings(
        APP_ENV="prod",
        AUTH_MODE="cognito",
        STORAGE_BACKEND="aws",
        DATA_BUCKET="api-bucket",
        MARKET_CLIENT_MODE="http",
        COGNITO_USER_POOL_ID="us-east-1_pool",
        COGNITO_APP_CLIENT_ID="client-id",
        **{field: endpoint},
    )
    settings.validate_api_runtime()


@pytest.mark.parametrize("field", ["DYNAMODB_ENDPOINT_URL", "S3_ENDPOINT_URL"])
@pytest.mark.parametrize(
    "endpoint",
    [
        "http://127.0.0.1:4566",
        "http://localstack:4566",
        "http://host.docker.internal:4566",
        "not a URL",
        "http://[::1",
    ],
)
def test_job_runtime_rejects_any_non_empty_data_plane_endpoint(
    field: str,
    endpoint: str,
) -> None:
    settings = Settings(
        APP_ENV="prod",
        AUTH_MODE="fake",
        STORAGE_BACKEND="aws",
        DATA_BUCKET="jobs-bucket",
        MARKET_CLIENT_MODE="http",
        **{field: endpoint},
    )
    with pytest.raises(RuntimeError, match=field) as exc_info:
        settings.validate_job_runtime()
    assert endpoint not in str(exc_info.value)


@pytest.mark.parametrize("field", ["DYNAMODB_ENDPOINT_URL", "S3_ENDPOINT_URL"])
@pytest.mark.parametrize("endpoint", ["", "   ", "\t\n"])
def test_job_runtime_allows_empty_data_plane_endpoint(field: str, endpoint: str) -> None:
    settings = Settings(
        APP_ENV="prod",
        AUTH_MODE="fake",
        STORAGE_BACKEND="aws",
        DATA_BUCKET="jobs-bucket",
        MARKET_CLIENT_MODE="http",
        **{field: endpoint},
    )
    settings.validate_job_runtime()


def test_job_runtime_allows_prod_fake_auth_without_cognito() -> None:
    settings = Settings(
        APP_ENV="prod",
        AUTH_MODE="fake",
        STORAGE_BACKEND="aws",
        DATA_BUCKET="jobs-bucket",
    )
    settings.validate_job_runtime()


def test_lambda_startup_rejects_prod_memory_before_building_context(monkeypatch) -> None:
    from app.jobs import lambda_entry

    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("AUTH_MODE", "fake")
    monkeypatch.setenv("STORAGE_BACKEND", "memory")
    monkeypatch.setenv("MARKET_CLIENT_MODE", "http")
    clear_settings_cache()
    monkeypatch.setattr(
        lambda_entry,
        "build_job_context",
        lambda _settings: pytest.fail("job context must not be built for invalid config"),
    )
    try:
        with pytest.raises(RuntimeError, match="STORAGE_BACKEND must be aws"):
            lambda_entry.handler({"job": "price"})
    finally:
        clear_settings_cache()


def test_lambda_startup_allows_prod_fake_auth_without_cognito(monkeypatch) -> None:
    from app.jobs import lambda_entry

    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("AUTH_MODE", "fake")
    monkeypatch.setenv("STORAGE_BACKEND", "aws")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("DATA_BUCKET", "jobs-bucket")
    monkeypatch.setenv("MARKET_CLIENT_MODE", "http")
    clear_settings_cache()
    monkeypatch.setattr(lambda_entry, "build_job_context", lambda _settings: object())
    monkeypatch.setattr(
        lambda_entry,
        "job_handler",
        lambda _event, _context: {"status": "started"},
    )
    try:
        assert lambda_entry.handler({"job": "price"}) == {"status": "started"}
    finally:
        clear_settings_cache()


def test_create_app_accepts_explicit_production_fixture_override(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("AUTH_MODE", "cognito")
    monkeypatch.setenv("STORAGE_BACKEND", "aws")
    monkeypatch.setenv("DATA_BUCKET", "api-bucket")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_pool")
    monkeypatch.setenv("COGNITO_APP_CLIENT_ID", "client-id")
    monkeypatch.setenv("MARKET_CLIENT_MODE", "fixture")
    monkeypatch.setenv("ALLOW_FIXTURE_MARKET_DATA", "true")
    clear_settings_cache()
    try:
        assert create_app().title == "OpenPortfo"
    finally:
        clear_settings_cache()
