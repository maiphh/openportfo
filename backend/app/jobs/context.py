"""JobContext: ports dataclass for Lambda-shaped jobs (no boto3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.ports.admin import JobRunsRepo, RssSourcesRepo, SettingsRepo
from app.ports.fx import ExchangeRateRepo
from app.ports.holdings import HoldingsRepo
from app.ports.news import NewsRepo
from app.ports.rss import RssFetcher
from app.ports.snapshots import SnapshotRepo
from app.ports.storage import ObjectStorage
from app.ports.users import UserProfileRepo
from app.ports.watchlist import WatchlistRepo
from app.services.market_service import MarketService
from app.services.portfolio_service import PortfolioService


@dataclass
class JobContext:
    """All ports jobs need. Intentionally no ExchangeRateClient."""

    settings_repo: SettingsRepo
    rss_sources_repo: RssSourcesRepo
    job_runs_repo: JobRunsRepo
    news_repo: NewsRepo
    rss_fetcher: RssFetcher
    holdings_repo: HoldingsRepo
    watchlist_repo: WatchlistRepo
    market_service: MarketService
    portfolio_service: PortfolioService
    snapshot_repo: SnapshotRepo
    object_storage: ObjectStorage
    user_profile_repo: UserProfileRepo
    fx_repo: Optional[ExchangeRateRepo] = None  # get only


__all__ = ["JobContext"]
