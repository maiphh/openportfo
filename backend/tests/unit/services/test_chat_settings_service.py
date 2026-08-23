from __future__ import annotations

import pytest

from app.adapters.memory.admin import InMemorySettingsRepo
from app.core.config import Settings
from app.ports.admin import SystemSettings
from app.services.chat_settings_service import (
    ChatSettingsValidationError,
    normalize_chat_patch,
    resolve_chat_runtime,
)
from app.services.llm.chat_service import _orchestrator_prompt
from app.services.llm.prompts import ORCHESTRATOR_SYSTEM


def _settings(**values) -> Settings:
    return Settings(LLM_FREE_ONLY=False, **values)


def test_chat_patch_preserves_null_vs_empty_fallbacks() -> None:
    settings = _settings(LLM_DEFAULT_MODEL="env-main", LLM_FALLBACK_MODELS="env-a,env-b")
    patch = normalize_chat_patch(
        {"model": "stored-main", "fallbackModels": [], "temperature": 0, "topP": 1},
        settings=settings,
    )
    assert patch == {"model": "stored-main", "fallback_models": [], "temperature": 0.0, "top_p": 1.0}
    runtime = resolve_chat_runtime(settings, SystemSettings(**{
        "chat_model": patch["model"],
        "chat_fallback_models": patch["fallback_models"],
        "chat_temperature": patch["temperature"],
        "chat_top_p": patch["top_p"],
    }))
    assert runtime.model == "stored-main"
    assert runtime.fallback_models == ()


def test_chat_patch_validates_omitted_stored_models_against_free_policy() -> None:
    settings = Settings(
        LLM_FREE_ONLY=True,
        LLM_DEFAULT_MODEL="openrouter/free",
        LLM_FALLBACK_MODELS="qwen:free",
    )
    current = SystemSettings(
        chat_model="provider/paid-model",
        chat_fallback_models=["qwen:free", "provider/paid-fallback"],
    )
    with pytest.raises(ChatSettingsValidationError) as exc_info:
        normalize_chat_patch({"temperature": 0.5}, settings=settings, current=current)
    assert "model" in exc_info.value.errors


def test_chat_patch_deduplicates_current_primary_and_fallbacks() -> None:
    settings = Settings(LLM_FREE_ONLY=True, LLM_DEFAULT_MODEL="openrouter/free")
    current = SystemSettings(
        chat_model="openrouter/free",
        chat_fallback_models=["qwen:free", "openrouter/free", "qwen:free"],
    )
    normalized = normalize_chat_patch({"temperature": 0.5}, settings=settings, current=current)
    assert normalized == {"temperature": 0.5}
    runtime = resolve_chat_runtime(settings, current)
    assert runtime.fallback_models == ("qwen:free",)


def test_chat_patch_rejects_non_finite_numbers() -> None:
    settings = _settings()
    for field, value in (("temperature", float("nan")), ("topP", float("inf"))):
        with pytest.raises(ChatSettingsValidationError) as exc_info:
            normalize_chat_patch({field: value}, settings=settings)
        assert field in exc_info.value.errors


@pytest.mark.parametrize(
    "payload",
    [
        {"model": "bad model"},
        {"fallbackModels": ["a"] * 9},
        {"temperature": 2.1},
        {"topP": -0.1},
        {"maxTokens": 0},
        {"systemPromptExtra": "\x00"},
    ],
)
def test_chat_patch_boundaries_are_field_errors(payload: dict[str, object]) -> None:
    with pytest.raises(ChatSettingsValidationError) as exc_info:
        normalize_chat_patch(payload, settings=_settings())
    assert exc_info.value.detail["code"] == "validation_error"


def test_memory_settings_version_conflict_and_increment() -> None:
    repo = InMemorySettingsRepo()
    initial = repo.get()
    saved = repo.save(SystemSettings(chat_model="m"), expected_version=initial.version)
    assert saved.version == 1
    with pytest.raises(Exception):
        repo.save(SystemSettings(chat_model="stale"), expected_version=initial.version)
    assert repo.get().chat_model == "m"


def test_prompt_suffix_is_delimited_after_immutable_base() -> None:
    prompt = _orchestrator_prompt("Prefer concise answers")
    assert prompt.startswith(ORCHESTRATOR_SYSTEM)
    assert prompt.index("Prefer concise answers") > prompt.index(ORCHESTRATOR_SYSTEM)
