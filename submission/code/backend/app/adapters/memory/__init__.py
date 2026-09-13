"""In-memory adapters for local development and isolated tests."""

# Re-export the local adapter implementations for convenient composition.
from app.adapters.memory.admin import (
    InMemoryJobRunsRepo,
    InMemoryRssSourcesRepo,
    InMemorySettingsRepo,
)
from app.adapters.memory.auth import FakeTokenVerifier
from app.adapters.memory.fx import InMemoryExchangeRateRepo
from app.adapters.memory.holdings import InMemoryHoldingsRepo
from app.adapters.memory.news import InMemoryNewsRepo
from app.adapters.memory.price_cache import InMemoryPriceCacheRepo
from app.adapters.memory.rss import FakeRssFetcher
from app.adapters.memory.snapshots import InMemorySnapshotRepo
from app.adapters.memory.storage import InMemoryObjectStorage
from app.adapters.memory.users import InMemoryUserProfileRepo
from app.adapters.memory.watchlist import InMemoryWatchlistRepo
from app.adapters.memory.chat_idempotency import InMemoryChatIdempotencyRepo

__all__ = [
    "FakeTokenVerifier",
    "FakeRssFetcher",
    "InMemoryExchangeRateRepo",
    "InMemoryHoldingsRepo",
    "InMemoryPriceCacheRepo",
    "InMemoryObjectStorage",
    "InMemoryNewsRepo",
    "InMemoryUserProfileRepo",
    "InMemoryWatchlistRepo",
    "InMemorySettingsRepo",
    "InMemoryRssSourcesRepo",
    "InMemoryJobRunsRepo",
    "InMemoryChatIdempotencyRepo",
]
