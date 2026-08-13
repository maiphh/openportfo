"""FastAPI dependency injection entrypoints.

Default: in-memory fakes (AUTH_MODE=fake, STORAGE_BACKEND=memory) for unit tests.
Prod: DynamoDB / S3 / Cognito when STORAGE_BACKEND=aws or USE_AWS_ADAPTERS=true.
Services depend on ports only — boto3 only inside adapters (lazy-imported here).
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings
from app.ports.auth import TokenVerifier, UnauthorizedError
from app.ports.admin import JobRunsRepo, RssSourcesRepo, SettingsRepo
from app.ports.fx import ExchangeRateClient, ExchangeRateRepo
from app.ports.holdings import HoldingsRepo
from app.ports.market import CryptoMarketClient, StockMarketClient
from app.ports.news import NewsRepo
from app.ports.price_cache import PriceCacheRepo
from app.ports.rss import RssFetcher
from app.ports.snapshots import SnapshotRepo
from app.ports.storage import ObjectStorage
from app.ports.users import UserProfile, UserProfileRepo
from app.ports.watchlist import WatchlistRepo
from app.services.fx_service import FxService
from app.services.history_service import HistoryService
from app.services.market_service import MarketService
from app.services.news_service import NewsService
from app.services.portfolio_service import PortfolioService

# Process-local stores (until set / first get)
_user_profile_repo: Optional[UserProfileRepo] = None
_holdings_repo: Optional[HoldingsRepo] = None
_watchlist_repo: Optional[WatchlistRepo] = None
_crypto_market_client: Optional[CryptoMarketClient] = None
_stock_market_client: Optional[StockMarketClient] = None
_price_cache_repo: Optional[PriceCacheRepo] = None
_market_service: Optional[MarketService] = None
_exchange_rate_repo: Optional[ExchangeRateRepo] = None
_exchange_rate_client: Optional[ExchangeRateClient] = None
_fx_service: Optional[FxService] = None
_portfolio_service: Optional[PortfolioService] = None
_object_storage: Optional[ObjectStorage] = None
_history_service: Optional[HistoryService] = None
_news_repo: Optional[NewsRepo] = None
_news_service: Optional[NewsService] = None
_settings_repo: Optional[SettingsRepo] = None
_rss_sources_repo: Optional[RssSourcesRepo] = None
_job_runs_repo: Optional[JobRunsRepo] = None
_snapshot_repo: Optional[SnapshotRepo] = None
_rss_fetcher: Optional[RssFetcher] = None


def settings_dep() -> Settings:
    return get_settings()


def _use_aws(settings: Optional[Settings] = None) -> bool:
    s = settings or get_settings()
    return s.aws_adapters_enabled()


def _region(settings: Settings) -> str:
    return settings.aws_region or "us-east-1"


def _ddb_endpoint(settings: Settings) -> Optional[str]:
    url = (settings.dynamodb_endpoint_url or "").strip()
    return url or None


def _s3_endpoint(settings: Settings) -> Optional[str]:
    url = (settings.s3_endpoint_url or "").strip()
    return url or None


def get_token_verifier(
    settings: Settings = Depends(settings_dep),
) -> TokenVerifier:
    """Factory: FakeTokenVerifier or CognitoJwtVerifier from AUTH_MODE."""
    # Direct call may pass Depends sentinel — resolve safely
    if not isinstance(settings, Settings):
        settings = get_settings()
    mode = (settings.auth_mode or "fake").lower()
    if mode == "cognito":
        from app.adapters.cognito.jwt_verifier import CognitoJwtVerifier

        return CognitoJwtVerifier(
            region=settings.cognito_region or settings.aws_region or "us-east-1",
            user_pool_id=settings.cognito_user_pool_id,
            app_client_id=settings.cognito_app_client_id,
        )
    from tests.fakes.auth import FakeTokenVerifier

    return FakeTokenVerifier()


def get_user_profile_repo() -> UserProfileRepo:
    global _user_profile_repo
    if _user_profile_repo is None:
        settings = get_settings()
        if _use_aws(settings):
            from app.adapters.dynamodb.users import DynamoUserProfileRepo

            _user_profile_repo = DynamoUserProfileRepo(
                settings.users_table,
                region=_region(settings),
                endpoint_url=_ddb_endpoint(settings),
            )
        else:
            from tests.fakes.users import InMemoryUserProfileRepo

            _user_profile_repo = InMemoryUserProfileRepo()
    return _user_profile_repo


def set_user_profile_repo(repo: Optional[UserProfileRepo]) -> None:
    global _user_profile_repo
    _user_profile_repo = repo


def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
    verifier: TokenVerifier = Depends(get_token_verifier),
    repo: UserProfileRepo = Depends(get_user_profile_repo),
) -> UserProfile:
    """Resolve Bearer JWT → Claims → bootstrap UserProfile (role from repo)."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    try:
        claims = verifier.verify(token.strip())
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail or "Invalid token",
        ) from exc

    return repo.get_or_create(
        claims.sub,
        email=claims.email,
        name=claims.name,
    )


def require_admin(
    user: UserProfile = Depends(get_current_user),
) -> UserProfile:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


# ---------------------------------------------------------------------------
# Holdings & Watchlist
# ---------------------------------------------------------------------------


def get_holdings_repo() -> HoldingsRepo:
    global _holdings_repo
    if _holdings_repo is None:
        settings = get_settings()
        if _use_aws(settings):
            from app.adapters.dynamodb.holdings import DynamoHoldingsRepo

            _holdings_repo = DynamoHoldingsRepo(
                settings.holdings_table,
                region=_region(settings),
                endpoint_url=_ddb_endpoint(settings),
            )
        else:
            from tests.fakes.holdings import InMemoryHoldingsRepo

            _holdings_repo = InMemoryHoldingsRepo()
    return _holdings_repo


def set_holdings_repo(repo: Optional[HoldingsRepo]) -> None:
    global _holdings_repo
    _holdings_repo = repo


def get_watchlist_repo() -> WatchlistRepo:
    global _watchlist_repo
    if _watchlist_repo is None:
        settings = get_settings()
        if _use_aws(settings):
            from app.adapters.dynamodb.watchlist import DynamoWatchlistRepo

            _watchlist_repo = DynamoWatchlistRepo(
                settings.watchlist_table,
                region=_region(settings),
                endpoint_url=_ddb_endpoint(settings),
            )
        else:
            from tests.fakes.watchlist import InMemoryWatchlistRepo

            _watchlist_repo = InMemoryWatchlistRepo()
    return _watchlist_repo


def set_watchlist_repo(repo: Optional[WatchlistRepo]) -> None:
    global _watchlist_repo
    _watchlist_repo = repo


# ---------------------------------------------------------------------------
# Market clients, PriceCache, MarketService
# ---------------------------------------------------------------------------


def get_crypto_market_client() -> CryptoMarketClient:
    global _crypto_market_client
    if _crypto_market_client is None:
        settings = get_settings()
        mode = (settings.market_client_mode or "fixture").lower()
        if mode == "http":
            try:
                from app.adapters.coingecko.http_client import HttpCoinGeckoClient

                _crypto_market_client = HttpCoinGeckoClient(
                    api_key=settings.coingecko_api_key or None,
                )
            except Exception:
                from app.adapters.coingecko.client import FixtureCoinGeckoClient

                _crypto_market_client = FixtureCoinGeckoClient()
        else:
            from app.adapters.coingecko.client import FixtureCoinGeckoClient

            _crypto_market_client = FixtureCoinGeckoClient()
    return _crypto_market_client


def set_crypto_market_client(client: Optional[CryptoMarketClient]) -> None:
    global _crypto_market_client, _market_service
    _crypto_market_client = client
    _market_service = None


def get_stock_market_client() -> StockMarketClient:
    global _stock_market_client
    if _stock_market_client is None:
        settings = get_settings()
        mode = (settings.market_client_mode or "fixture").lower()
        if mode == "http":
            try:
                from app.adapters.vnstock.http_client import HttpVnstockClient

                _stock_market_client = HttpVnstockClient(
                    api_key=settings.vnstock_api_key or None,
                )
            except Exception:
                from app.adapters.vnstock.client import FixtureVnstockClient

                _stock_market_client = FixtureVnstockClient()
        else:
            from app.adapters.vnstock.client import FixtureVnstockClient

            _stock_market_client = FixtureVnstockClient()
    return _stock_market_client


def set_stock_market_client(client: Optional[StockMarketClient]) -> None:
    global _stock_market_client, _market_service
    _stock_market_client = client
    _market_service = None


def get_price_cache_repo() -> PriceCacheRepo:
    global _price_cache_repo
    if _price_cache_repo is None:
        settings = get_settings()
        if _use_aws(settings):
            from app.adapters.dynamodb.price_cache import DynamoPriceCacheRepo

            _price_cache_repo = DynamoPriceCacheRepo(
                settings.price_cache_table,
                region=_region(settings),
                endpoint_url=_ddb_endpoint(settings),
            )
        else:
            from tests.fakes.price_cache import InMemoryPriceCacheRepo

            _price_cache_repo = InMemoryPriceCacheRepo()
    return _price_cache_repo


def set_price_cache_repo(repo: Optional[PriceCacheRepo]) -> None:
    global _price_cache_repo, _market_service
    _price_cache_repo = repo
    _market_service = None


def get_market_service(
    settings: Settings = Depends(settings_dep),
) -> MarketService:
    global _market_service
    if _market_service is None:
        if not isinstance(settings, Settings):
            settings = get_settings()
        admin_ttl_minutes = get_settings_repo().get().price_cache_ttl_minutes
        if isinstance(admin_ttl_minutes, int) and admin_ttl_minutes > 0:
            ttl_seconds = admin_ttl_minutes * 60
        else:
            ttl_seconds = settings.price_cache_ttl_seconds
        _market_service = MarketService(
            get_crypto_market_client(),
            get_stock_market_client(),
            get_price_cache_repo(),
            default_ttl_seconds=ttl_seconds,
        )
    return _market_service


def set_market_service(svc: Optional[MarketService]) -> None:
    global _market_service, _portfolio_service
    _market_service = svc
    _portfolio_service = None


# ---------------------------------------------------------------------------
# FX + Portfolio
# ---------------------------------------------------------------------------


def get_exchange_rate_repo() -> ExchangeRateRepo:
    global _exchange_rate_repo
    if _exchange_rate_repo is None:
        settings = get_settings()
        if _use_aws(settings):
            from app.adapters.dynamodb.fx import DynamoExchangeRateRepo

            _exchange_rate_repo = DynamoExchangeRateRepo(
                settings.fx_table,
                region=_region(settings),
                endpoint_url=_ddb_endpoint(settings),
            )
        else:
            from tests.fakes.fx import InMemoryExchangeRateRepo

            _exchange_rate_repo = InMemoryExchangeRateRepo()
    return _exchange_rate_repo


def set_exchange_rate_repo(repo: Optional[ExchangeRateRepo]) -> None:
    global _exchange_rate_repo, _portfolio_service, _fx_service
    _exchange_rate_repo = repo
    _portfolio_service = None
    _fx_service = None


def get_exchange_rate_client(
    settings: Settings = Depends(settings_dep),
) -> Optional[ExchangeRateClient]:
    global _exchange_rate_client
    if _exchange_rate_client is not None:
        return _exchange_rate_client
    if not isinstance(settings, Settings):
        settings = get_settings()
    key = (settings.exchange_rate_api_key or "").strip()
    if not key:
        return None
    from app.adapters.exchangerate.client import HttpExchangeRateClient

    _exchange_rate_client = HttpExchangeRateClient(api_key=key)
    return _exchange_rate_client


def set_exchange_rate_client(client: Optional[ExchangeRateClient]) -> None:
    global _exchange_rate_client, _fx_service
    _exchange_rate_client = client
    _fx_service = None


def get_fx_service(
    settings: Settings = Depends(settings_dep),
) -> FxService:
    global _fx_service
    if _fx_service is None:
        if not isinstance(settings, Settings):
            settings = get_settings()
        _fx_service = FxService(
            get_exchange_rate_repo(),
            client=get_exchange_rate_client(settings),
        )
    return _fx_service


def set_fx_service(svc: Optional[FxService]) -> None:
    global _fx_service
    _fx_service = svc


def get_portfolio_service(
    settings: Settings = Depends(settings_dep),
) -> PortfolioService:
    global _portfolio_service
    if _portfolio_service is None:
        if not isinstance(settings, Settings):
            settings = get_settings()
        _portfolio_service = PortfolioService(
            get_holdings_repo(),
            get_market_service(settings),
            fx_repo=get_exchange_rate_repo(),
        )
    return _portfolio_service


def set_portfolio_service(svc: Optional[PortfolioService]) -> None:
    global _portfolio_service
    _portfolio_service = svc


# ---------------------------------------------------------------------------
# ObjectStorage + History
# ---------------------------------------------------------------------------


def get_object_storage() -> ObjectStorage:
    global _object_storage
    if _object_storage is None:
        settings = get_settings()
        if _use_aws(settings):
            from app.adapters.s3.storage import S3ObjectStorage

            bucket = (settings.data_bucket or "").strip()
            if not bucket:
                raise RuntimeError(
                    "DATA_BUCKET is required when STORAGE_BACKEND=aws / USE_AWS_ADAPTERS=true"
                )
            _object_storage = S3ObjectStorage(
                bucket,
                region=_region(settings),
                endpoint_url=_s3_endpoint(settings),
            )
        else:
            from tests.fakes.storage import InMemoryObjectStorage

            _object_storage = InMemoryObjectStorage()
    return _object_storage


def set_object_storage(storage: Optional[ObjectStorage]) -> None:
    global _object_storage, _history_service
    _object_storage = storage
    _history_service = None


def get_history_service() -> HistoryService:
    global _history_service
    if _history_service is None:
        _history_service = HistoryService(
            get_object_storage(),
            get_crypto_market_client(),
            get_stock_market_client(),
        )
    return _history_service


def set_history_service(svc: Optional[HistoryService]) -> None:
    global _history_service
    _history_service = svc


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------


def get_news_repo() -> NewsRepo:
    global _news_repo
    if _news_repo is None:
        settings = get_settings()
        if _use_aws(settings):
            from app.adapters.dynamodb.news import DynamoNewsRepo

            _news_repo = DynamoNewsRepo(
                settings.news_table,
                region=_region(settings),
                endpoint_url=_ddb_endpoint(settings),
            )
        else:
            from tests.fakes.news import InMemoryNewsRepo

            _news_repo = InMemoryNewsRepo()
    return _news_repo


def set_news_repo(repo: Optional[NewsRepo]) -> None:
    global _news_repo, _news_service
    _news_repo = repo
    _news_service = None


def get_news_service() -> NewsService:
    global _news_service
    if _news_service is None:
        _news_service = NewsService(
            get_news_repo(),
            holdings_repo=get_holdings_repo(),
            watchlist_repo=get_watchlist_repo(),
        )
    return _news_service


def set_news_service(svc: Optional[NewsService]) -> None:
    global _news_service
    _news_service = svc


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


def get_settings_repo() -> SettingsRepo:
    global _settings_repo
    if _settings_repo is None:
        settings = get_settings()
        if _use_aws(settings):
            from app.adapters.dynamodb.settings import DynamoSettingsRepo

            _settings_repo = DynamoSettingsRepo(
                settings.settings_table,
                region=_region(settings),
                endpoint_url=_ddb_endpoint(settings),
            )
        else:
            from tests.fakes.admin import InMemorySettingsRepo

            _settings_repo = InMemorySettingsRepo()
    return _settings_repo


def set_settings_repo(repo: Optional[SettingsRepo]) -> None:
    global _settings_repo, _market_service, _portfolio_service
    _settings_repo = repo
    _market_service = None
    _portfolio_service = None


def get_rss_sources_repo() -> RssSourcesRepo:
    global _rss_sources_repo
    if _rss_sources_repo is None:
        settings = get_settings()
        if _use_aws(settings):
            from app.adapters.dynamodb.rss import DynamoRssSourcesRepo

            _rss_sources_repo = DynamoRssSourcesRepo(
                settings.rss_table,
                region=_region(settings),
                endpoint_url=_ddb_endpoint(settings),
            )
        else:
            from tests.fakes.admin import InMemoryRssSourcesRepo

            _rss_sources_repo = InMemoryRssSourcesRepo()
    return _rss_sources_repo


def set_rss_sources_repo(repo: Optional[RssSourcesRepo]) -> None:
    global _rss_sources_repo
    _rss_sources_repo = repo


def get_job_runs_repo() -> JobRunsRepo:
    global _job_runs_repo
    if _job_runs_repo is None:
        settings = get_settings()
        if _use_aws(settings):
            from app.adapters.dynamodb.job_runs import DynamoJobRunsRepo

            _job_runs_repo = DynamoJobRunsRepo(
                settings.job_runs_table,
                region=_region(settings),
                endpoint_url=_ddb_endpoint(settings),
            )
        else:
            from tests.fakes.admin import InMemoryJobRunsRepo

            _job_runs_repo = InMemoryJobRunsRepo()
    return _job_runs_repo


def set_job_runs_repo(repo: Optional[JobRunsRepo]) -> None:
    global _job_runs_repo
    _job_runs_repo = repo


def get_snapshot_repo() -> SnapshotRepo:
    global _snapshot_repo
    if _snapshot_repo is None:
        settings = get_settings()
        if _use_aws(settings):
            from app.adapters.dynamodb.snapshots import DynamoSnapshotRepo

            _snapshot_repo = DynamoSnapshotRepo(
                settings.snapshots_table,
                region=_region(settings),
                endpoint_url=_ddb_endpoint(settings),
            )
        else:
            from tests.fakes.snapshots import InMemorySnapshotRepo

            _snapshot_repo = InMemorySnapshotRepo()
    return _snapshot_repo


def set_snapshot_repo(repo: Optional[SnapshotRepo]) -> None:
    global _snapshot_repo
    _snapshot_repo = repo


def get_rss_fetcher() -> RssFetcher:
    global _rss_fetcher
    if _rss_fetcher is None:
        settings = get_settings()
        if _use_aws(settings) or (settings.app_env or "").lower() == "prod":
            from app.adapters.rss.fetcher import HttpRssFetcher

            _rss_fetcher = HttpRssFetcher()
        else:
            from tests.fakes.rss import FakeRssFetcher

            _rss_fetcher = FakeRssFetcher()
    return _rss_fetcher


def set_rss_fetcher(fetcher: Optional[RssFetcher]) -> None:
    global _rss_fetcher
    _rss_fetcher = fetcher


def build_job_context(settings: Optional[Settings] = None):
    """Build JobContext with current adapter wiring (used by Lambda entry)."""
    from app.jobs.context import JobContext

    # settings reserved for future override; factories read get_settings()
    _ = settings
    return JobContext(
        settings_repo=get_settings_repo(),
        rss_sources_repo=get_rss_sources_repo(),
        job_runs_repo=get_job_runs_repo(),
        news_repo=get_news_repo(),
        rss_fetcher=get_rss_fetcher(),
        holdings_repo=get_holdings_repo(),
        watchlist_repo=get_watchlist_repo(),
        market_service=get_market_service(),
        portfolio_service=get_portfolio_service(),
        snapshot_repo=get_snapshot_repo(),
        object_storage=get_object_storage(),
        user_profile_repo=get_user_profile_repo(),
        fx_repo=get_exchange_rate_repo(),
    )
