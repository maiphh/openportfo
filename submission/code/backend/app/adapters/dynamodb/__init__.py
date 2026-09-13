"""DynamoDB production adapters (boto3 confined here)."""

from app.adapters.dynamodb.users import DynamoUserProfileRepo
from app.adapters.dynamodb.holdings import DynamoHoldingsRepo
from app.adapters.dynamodb.watchlist import DynamoWatchlistRepo
from app.adapters.dynamodb.price_cache import DynamoPriceCacheRepo
from app.adapters.dynamodb.news import DynamoNewsRepo
from app.adapters.dynamodb.settings import DynamoSettingsRepo
from app.adapters.dynamodb.rss import DynamoRssSourcesRepo
from app.adapters.dynamodb.fx import DynamoExchangeRateRepo
from app.adapters.dynamodb.job_runs import DynamoJobRunsRepo
from app.adapters.dynamodb.snapshots import DynamoSnapshotRepo
from app.adapters.dynamodb.chat_idempotency import DynamoChatIdempotencyRepo

__all__ = [
    "DynamoUserProfileRepo",
    "DynamoHoldingsRepo",
    "DynamoWatchlistRepo",
    "DynamoPriceCacheRepo",
    "DynamoNewsRepo",
    "DynamoSettingsRepo",
    "DynamoRssSourcesRepo",
    "DynamoExchangeRateRepo",
    "DynamoJobRunsRepo",
    "DynamoSnapshotRepo",
    "DynamoChatIdempotencyRepo",
]
