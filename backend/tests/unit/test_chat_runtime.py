from __future__ import annotations

import pytest

from app.adapters.memory.admin import InMemorySettingsRepo
from app.adapters.llm.fallback import FallbackProvider
from app.core import deps
from app.core.config import Settings
from app.ports.admin import SystemSettings
from app.services.llm.chat_service import ChatConfigError
from tests.fakes.llm import ScriptedLlmProvider


def test_chat_service_reads_a_fresh_settings_snapshot_per_request(monkeypatch) -> None:
    runtime_settings = Settings(
        LLM_DEFAULT_MODEL="env:free",
        LLM_FALLBACK_MODELS="env-fallback:free",
        LLM_MAX_TOKENS=1200,
    )
    repo = InMemorySettingsRepo()
    inner = ScriptedLlmProvider()
    configured = FallbackProvider(inner, default_model="env:free")
    monkeypatch.setattr(deps, "get_settings", lambda: runtime_settings)
    monkeypatch.setattr(deps, "get_settings_repo", lambda: repo)
    monkeypatch.setattr(deps, "get_llm_provider", lambda: configured)
    monkeypatch.setattr(deps, "get_tool_registry", lambda: None)
    monkeypatch.setattr(deps, "get_holdings_service", lambda: None)
    monkeypatch.setattr(deps, "get_watchlist_service", lambda: None)
    monkeypatch.setattr(deps, "get_portfolio_service", lambda: None)
    monkeypatch.setattr(deps, "get_market_service", lambda: None)
    monkeypatch.setattr(deps, "get_asset_detail_service", lambda: None)
    monkeypatch.setattr(deps, "get_news_service", lambda: None)
    monkeypatch.setattr(deps, "get_chat_idempotency_repo", lambda: None)

    first = deps.get_chat_service()
    assert first._runtime.model == "env:free"
    assert first._runtime.max_tokens == 1200
    assert first._runtime.fallback_models == ("env-fallback:free",)

    saved = repo.save(
        SystemSettings(
            chat_model="first:free",
            chat_fallback_models=["second:free"],
            chat_temperature=0.25,
            chat_top_p=0.8,
            chat_max_tokens=321,
        ),
        expected_version=0,
    )
    second = deps.get_chat_service()
    assert saved.version == 1
    assert first._runtime.model == "env:free"  # existing turns retain their snapshot
    assert second._runtime.model == "first:free"
    assert second._runtime.fallback_models == ("second:free",)
    assert second._runtime.temperature == 0.25
    assert second._runtime.top_p == 0.8
    assert second._runtime.max_tokens == 321
    assert isinstance(second._provider, FallbackProvider)


def test_chat_service_maps_invalid_effective_settings_to_config_error(monkeypatch) -> None:
    """Regression: EB shipped LLM_DEFAULT_MODEL=openrouter with FREE_ONLY=true.

    resolve_chat_runtime rejects that combination; the dependency must surface
    it as ChatConfigError (HTTP 503 via api/chat) instead of an unhandled 500.
    """
    runtime_settings = Settings(
        LLM_DEFAULT_MODEL="openrouter",
        LLM_FREE_ONLY=True,
    )
    monkeypatch.setattr(deps, "get_settings", lambda: runtime_settings)
    monkeypatch.setattr(deps, "get_settings_repo", lambda: InMemorySettingsRepo())

    with pytest.raises(ChatConfigError, match="Chat settings are invalid"):
        deps.get_chat_service()
