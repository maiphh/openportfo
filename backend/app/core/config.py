"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for OpenPortfo API.

    Defaults keep unit tests offline with fakes (AUTH_MODE=fake, STORAGE_BACKEND=memory).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="OpenPortfo", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")  # local | test | prod
    auth_mode: str = Field(default="fake", alias="AUTH_MODE")  # fake | cognito
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")

    # Adapter selection: memory (default) | aws
    # Also: USE_AWS_ADAPTERS=true or APP_ENV=prod (unless STORAGE_BACKEND=memory)
    storage_backend: str = Field(default="memory", alias="STORAGE_BACKEND")
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
    exchange_rate_api_key: str = Field(default="", alias="EXCHANGE_RATE_API_KEY")
    coingecko_api_key: str = Field(default="", alias="COINGECKO_API_KEY")
    vnstock_api_key: str = Field(default="", alias="VNSTOCK_API_KEY")

    # Market client mode: fixture (default for tests) | http (live HTTP when aws/prod)
    market_client_mode: str = Field(default="fixture", alias="MARKET_CLIENT_MODE")

    # Price cache TTL (Sprint 04) — seconds; default 600 (10 min)
    price_cache_ttl_seconds: int = Field(default=600, alias="PRICE_CACHE_TTL_SECONDS")

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Clear cached settings (call from tests after monkeypatching env)."""
    get_settings.cache_clear()
