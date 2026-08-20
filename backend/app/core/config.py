"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import List, Tuple

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class AppEnvironment(str, Enum):
    """Supported runtime environments."""

    LOCAL = "local"
    TEST = "test"
    PROD = "prod"


class AuthMode(str, Enum):
    """Supported authentication implementations."""

    FAKE = "fake"
    COGNITO = "cognito"


class StorageBackend(str, Enum):
    """Supported persistence backends."""

    MEMORY = "memory"
    AWS = "aws"


class MarketClientMode(str, Enum):
    """Supported market-data client implementations."""

    FIXTURE = "fixture"
    HTTP = "http"


# Every production API dependency and every scheduled-job context is wired
# through these durable adapters. Keep the environment names here so runtime
# validation reports only safe configuration keys, never configured values.
_DURABLE_TABLE_FIELDS: tuple[tuple[str, str], ...] = (
    ("USERS_TABLE", "users_table"),
    ("HOLDINGS_TABLE", "holdings_table"),
    ("WATCHLIST_TABLE", "watchlist_table"),
    ("PRICE_CACHE_TABLE", "price_cache_table"),
    ("NEWS_TABLE", "news_table"),
    ("SETTINGS_TABLE", "settings_table"),
    ("FX_TABLE", "fx_table"),
    ("RSS_TABLE", "rss_table"),
    ("JOB_RUNS_TABLE", "job_runs_table"),
    ("SNAPSHOTS_TABLE", "snapshots_table"),
)


def _missing_settings(
    settings: "Settings",
    fields: tuple[tuple[str, str], ...],
) -> list[str]:
    """Return missing environment names without exposing configured values."""
    return [
        env_name
        for env_name, field_name in fields
        if not str(getattr(settings, field_name, "") or "").strip()
    ]


def _value_text(value: object) -> str:
    """Normalize enum/string settings for comparisons."""
    value = getattr(value, "value", value)
    return str(value or "").strip().lower()


def _durable_data_plane_errors(settings: "Settings") -> list[str]:
    """Validate configuration shared by API and scheduled-job AWS adapters."""
    errors: list[str] = []
    if _value_text(settings.storage_backend) != StorageBackend.AWS.value:
        errors.append("STORAGE_BACKEND must be aws")
    if not str(settings.aws_region or "").strip():
        errors.append("AWS_REGION is required")
    if not str(settings.data_bucket or "").strip():
        errors.append("DATA_BUCKET is required")

    errors.extend(
        f"{name} is required"
        for name in _missing_settings(settings, _DURABLE_TABLE_FIELDS)
    )

    for env_name, field_name in (
        ("DYNAMODB_ENDPOINT_URL", "dynamodb_endpoint_url"),
        ("S3_ENDPOINT_URL", "s3_endpoint_url"),
    ):
        # Endpoint overrides are for LocalStack and other test/integration
        # environments only.  Production must fail closed for every non-empty
        # value, including host.docker.internal, malformed URLs, and any other
        # hostname that could bypass a hostname-based local-only check.
        if str(getattr(settings, field_name, "") or "").strip():
            errors.append(f"{env_name} must be empty in production")
    return errors


def _disable_env_file() -> bool:
    """Skip .env so pytest (and explicit opt-out) see code defaults."""
    if os.environ.get("OPENPORTFO_DISABLE_ENV_FILE") == "1":
        return True
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    return False


class Settings(BaseSettings):
    """Runtime configuration for OpenPortfo API.

    Defaults keep unit tests offline with fakes (AUTH_MODE=fake, STORAGE_BACKEND=memory).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        use_enum_values=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        if _disable_env_file():
            return (init_settings, env_settings, file_secret_settings)
        return (init_settings, env_settings, dotenv_settings, file_secret_settings)

    app_name: str = Field(default="OpenPortfo", alias="APP_NAME")
    app_env: AppEnvironment = Field(default=AppEnvironment.LOCAL, alias="APP_ENV")
    auth_mode: AuthMode = Field(default=AuthMode.FAKE, alias="AUTH_MODE")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")

    # Adapter selection: memory (default) | aws
    # Also: USE_AWS_ADAPTERS=true or APP_ENV=prod (unless STORAGE_BACKEND=memory)
    storage_backend: StorageBackend = Field(
        default=StorageBackend.MEMORY,
        alias="STORAGE_BACKEND",
    )
    use_aws_adapters: bool = Field(default=False, alias="USE_AWS_ADAPTERS")

    # Optional DynamoDB local / LocalStack endpoint (tests/integration only)
    dynamodb_endpoint_url: str = Field(default="", alias="DYNAMODB_ENDPOINT_URL")
    s3_endpoint_url: str = Field(default="", alias="S3_ENDPOINT_URL")

    # Comma-separated origins
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:5500,http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    # Cognito (Sprint 02 / 12)
    cognito_region: str = Field(default="us-east-1", alias="COGNITO_REGION")
    cognito_user_pool_id: str = Field(default="", alias="COGNITO_USER_POOL_ID")
    cognito_app_client_id: str = Field(default="", alias="COGNITO_APP_CLIENT_ID")

    # DynamoDB table names (Sprint 02+ / 12)
    users_table: str = Field(default="openportfo-users", alias="USERS_TABLE")
    holdings_table: str = Field(default="openportfo-holdings", alias="HOLDINGS_TABLE")
    watchlist_table: str = Field(default="openportfo-watchlist", alias="WATCHLIST_TABLE")
    price_cache_table: str = Field(default="openportfo-price-cache", alias="PRICE_CACHE_TABLE")
    news_table: str = Field(default="openportfo-news", alias="NEWS_TABLE")
    settings_table: str = Field(default="openportfo-settings", alias="SETTINGS_TABLE")
    fx_table: str = Field(default="openportfo-fx", alias="FX_TABLE")
    rss_table: str = Field(default="openportfo-rss", alias="RSS_TABLE")
    job_runs_table: str = Field(default="openportfo-job-runs", alias="JOB_RUNS_TABLE")
    snapshots_table: str = Field(default="openportfo-snapshots", alias="SNAPSHOTS_TABLE")

    # S3 (Sprint 07 / 12)
    data_bucket: str = Field(default="", alias="DATA_BUCKET")

    # Third-party (never commit real secrets)
    exchange_rate_api_key: str = Field(default="", alias="EXCHANGE_RATE_API_KEY", repr=False)
    coingecko_api_key: str = Field(default="", alias="COINGECKO_API_KEY", repr=False)
    vnstock_api_key: str = Field(default="", alias="VNSTOCK_API_KEY", repr=False)

    # LLM / chatbot (OpenRouter by default; swap LLM_PROVIDER + LLM_BASE_URL + key)
    llm_provider: str = Field(default="openrouter", alias="LLM_PROVIDER")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY", repr=False)
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY", repr=False)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY", repr=False)
    xai_api_key: str = Field(default="", alias="XAI_API_KEY", repr=False)
    llm_default_model: str = Field(default="openrouter/free", alias="LLM_DEFAULT_MODEL")
    llm_fallback_models: str = Field(
        default=(
            "openrouter/free,"
            "meta-llama/llama-3.3-70b-instruct:free,"
            "qwen/qwen3-32b:free,"
            "mistralai/mistral-small-3.1-24b-instruct:free,"
            "google/gemma-3-27b-it:free"
        ),
        alias="LLM_FALLBACK_MODELS",
    )
    llm_free_only: bool = Field(default=True, alias="LLM_FREE_ONLY")
    llm_timeout_seconds: float = Field(default=90.0, alias="LLM_TIMEOUT_SECONDS")
    llm_max_tool_rounds: int = Field(default=8, alias="LLM_MAX_TOOL_ROUNDS")
    llm_max_tokens: int = Field(default=2048, alias="LLM_MAX_TOKENS")
    llm_retry_max: int = Field(default=2, alias="LLM_RETRY_MAX")
    llm_retry_max_sleep: float = Field(default=8.0, alias="LLM_RETRY_MAX_SLEEP")
    llm_http_referer: str = Field(default="https://openportfo.local", alias="LLM_HTTP_REFERER")
    llm_app_title: str = Field(default="OpenPortfo", alias="LLM_APP_TITLE")

    # Market client mode: fixture (default for tests) | http (live HTTP when aws/prod)
    market_client_mode: MarketClientMode = Field(
        default=MarketClientMode.FIXTURE,
        alias="MARKET_CLIENT_MODE",
    )
    # Fixture data is useful for local/test and explicit production demos, but
    # must never be selected accidentally by a production API deployment.
    allow_fixture_market_data: bool = Field(
        default=False,
        alias="ALLOW_FIXTURE_MARKET_DATA",
    )

    # Price cache TTL (Sprint 04) — seconds; default 600 (10 min)
    price_cache_ttl_seconds: int = Field(default=600, alias="PRICE_CACHE_TTL_SECONDS")

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_fallback_model_list(self) -> List[str]:
        return [m.strip() for m in (self.llm_fallback_models or "").split(",") if m.strip()]

    def aws_adapters_enabled(self) -> bool:
        """True when production AWS adapters should be used (not unit-test fakes)."""
        backend = (self.storage_backend or "memory").strip().lower()
        if backend == "memory":
            # Explicit memory wins even if APP_ENV=prod (safety for local)
            if self.use_aws_adapters:
                return True
            return False
        if backend == "aws":
            return True
        if self.use_aws_adapters:
            return True
        if (self.app_env or "").strip().lower() == "prod":
            return True
        return False

    def validate_api_runtime(self) -> None:
        """Fail closed for unsafe production API configuration.

        This is intentionally an explicit API-runtime check instead of a
        model-level production validator. Scheduled Lambda jobs run with
        ``APP_ENV=prod`` but do not authenticate users, so they must still be
        able to construct settings with ``AUTH_MODE=fake``.
        """
        if self.app_env != AppEnvironment.PROD:
            return

        errors = _durable_data_plane_errors(self)
        if _value_text(self.auth_mode) != AuthMode.COGNITO.value:
            errors.append("AUTH_MODE must be cognito when APP_ENV=prod")
        if _value_text(self.auth_mode) == AuthMode.COGNITO.value:
            if not (self.cognito_user_pool_id or "").strip():
                errors.append("COGNITO_USER_POOL_ID is required")
            if not (self.cognito_app_client_id or "").strip():
                errors.append("COGNITO_APP_CLIENT_ID is required")
        if (
            self.market_client_mode == MarketClientMode.FIXTURE
            and not self.allow_fixture_market_data
        ):
            errors.append(
                "MARKET_CLIENT_MODE=http is required unless "
                "ALLOW_FIXTURE_MARKET_DATA=true"
            )

        if errors:
            raise RuntimeError(
                "Invalid production API configuration: " + "; ".join(errors)
            )

    def validate_job_runtime(self) -> None:
        """Fail closed for production scheduled-job data-plane settings.

        Jobs do not authenticate end users, so ``AUTH_MODE=fake`` is valid and
        Cognito settings are intentionally not required. They do, however,
        construct every durable repository in :func:`build_job_context` and
        therefore require the complete AWS data plane.
        """
        if self.app_env != AppEnvironment.PROD:
            return

        errors = _durable_data_plane_errors(self)

        if errors:
            raise RuntimeError(
                "Invalid production job configuration: " + "; ".join(errors)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Clear cached settings (call from tests after monkeypatching env)."""
    get_settings.cache_clear()
