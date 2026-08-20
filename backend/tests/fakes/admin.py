"""Test compatibility exports for in-memory admin adapters."""

from app.adapters.memory.admin import (
    AdminNotFoundError,
    AdminValidationError,
    InMemoryJobRunsRepo,
    InMemoryRssSourcesRepo,
    InMemorySettingsRepo,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "InMemorySettingsRepo",
    "InMemoryRssSourcesRepo",
    "InMemoryJobRunsRepo",
    "ValidationError",
    "NotFoundError",
    "AdminValidationError",
    "AdminNotFoundError",
]
