"""Validation and per-request resolution for administrator chat overrides."""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, replace
from typing import Any, Mapping, Optional

from app.core.config import Settings
from app.ports.admin import SystemSettings


class ChatSettingsValidationError(ValueError):
    code = "validation_error"

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        self.detail = {"code": self.code, "errors": errors}
        super().__init__(self.code)


class ChatSettingsConflictError(Exception):
    code = "settings_conflict"


@dataclass(frozen=True)
class ChatRuntimeConfig:
    model: str
    fallback_models: tuple[str, ...]
    temperature: Optional[float]
    top_p: Optional[float]
    max_tokens: int
    system_prompt_extra: Optional[str]


_MODEL_RE = re.compile(r"^[^\s\x00-\x1f\x7f]{1,200}$")


def _model(value: object, field: str, errors: dict[str, str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        errors[field] = "must be a string or null"
        return None
    value = value.strip()
    if not value or _MODEL_RE.fullmatch(value) is None:
        errors[field] = "must be 1-200 characters without whitespace or controls"
        return None
    return value


def _free(model: str) -> bool:
    return model.endswith(":free") or model == "openrouter/free" or model.startswith("openrouter/free")


def _float(value: object, field: str, low: float, high: float, errors: dict[str, str]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors[field] = f"must be between {low:g} and {high:g} or null"
        return None
    result = float(value)
    if not math.isfinite(result):
        errors[field] = f"must be between {low:g} and {high:g} or null"
        return None
    if result < low or result > high:
        errors[field] = f"must be between {low:g} and {high:g}"
        return None
    return result


def _prompt(value: object, field: str, errors: dict[str, str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        errors[field] = "must be a string or null"
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) > 4000 or any(
        unicodedata.category(char).startswith("C") and char not in "\n\t" for char in text
    ):
        errors[field] = "must be 1-4000 characters without controls"
        return None
    return text


def _max_tokens(value: object, field: str, errors: dict[str, str]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 32768:
        errors[field] = "must be an integer from 1 to 32768 or null"
        return None
    return value


def _effective_runtime(
    settings: Settings,
    stored: SystemSettings,
    errors: dict[str, str],
) -> Optional[ChatRuntimeConfig]:
    """Validate the complete post-patch runtime, including env fallbacks."""
    model = _model(
        stored.chat_model if stored.chat_model is not None else settings.llm_default_model,
        "model",
        errors,
    )
    raw_fallbacks = (
        settings.llm_fallback_model_list
        if stored.chat_fallback_models is None
        else stored.chat_fallback_models
    )
    fallback_models: list[str] = []
    if not isinstance(raw_fallbacks, list):
        errors["fallbackModels"] = "must be an array or null"
    else:
        seen: set[str] = set()
        for index, item in enumerate(raw_fallbacks):
            candidate = _model(item, f"fallbackModels[{index}]", errors)
            if candidate is not None and candidate != model and candidate not in seen:
                seen.add(candidate)
                fallback_models.append(candidate)

    temperature = _float(
        stored.chat_temperature if stored.chat_temperature is not None else settings.llm_temperature,
        "temperature",
        0,
        2,
        errors,
    )
    top_p = _float(
        stored.chat_top_p if stored.chat_top_p is not None else settings.llm_top_p,
        "topP",
        0,
        1,
        errors,
    )
    max_tokens = _max_tokens(
        stored.chat_max_tokens if stored.chat_max_tokens is not None else settings.llm_max_tokens,
        "maxTokens",
        errors,
    )
    suffix = _prompt(
        stored.chat_system_prompt_extra
        if stored.chat_system_prompt_extra is not None
        else settings.llm_system_prompt_extra,
        "systemPromptExtra",
        errors,
    )
    candidates = [model, *fallback_models]
    if settings.llm_free_only and any(candidate and not _free(candidate) for candidate in candidates):
        errors.setdefault("model", "all effective models must satisfy the free-model policy")
    if errors or model is None or max_tokens is None:
        return None
    return ChatRuntimeConfig(
        model=model,
        fallback_models=tuple(fallback_models),
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        system_prompt_extra=suffix,
    )


def normalize_chat_patch(
    payload: Mapping[str, Any],
    *,
    settings: Settings,
    current: Optional[SystemSettings] = None,
) -> dict[str, Any]:
    """Validate a partial patch against the complete resulting runtime."""
    errors: dict[str, str] = {}
    values: dict[str, Any] = {}
    aliases = {
        "model": "model",
        "fallbackModels": "fallback_models",
        "fallback_models": "fallback_models",
        "temperature": "temperature",
        "topP": "top_p",
        "top_p": "top_p",
        "maxTokens": "max_tokens",
        "max_tokens": "max_tokens",
        "systemPromptExtra": "system_prompt_extra",
        "system_prompt_extra": "system_prompt_extra",
    }
    known = {key for key in aliases}
    unknown = set(payload) - known
    if unknown:
        for key in sorted(unknown):
            errors[str(key)] = "is not supported"

    if "model" in payload:
        values["model"] = _model(payload["model"], "model", errors)

    fallback_key = "fallbackModels" if "fallbackModels" in payload else "fallback_models"
    if fallback_key in payload:
        raw = payload[fallback_key]
        if raw is None:
            values["fallback_models"] = None
        elif not isinstance(raw, list):
            errors["fallbackModels"] = "must be an array or null"
        elif len(raw) > 8:
            errors["fallbackModels"] = "must contain at most 8 models"
        else:
            models: list[str] = []
            seen: set[str] = set()
            for index, item in enumerate(raw):
                model = _model(item, f"fallbackModels[{index}]", errors)
                if model is not None and model not in seen:
                    seen.add(model)
                    models.append(model)
            values["fallback_models"] = models

    if "temperature" in payload:
        values["temperature"] = _float(payload["temperature"], "temperature", 0, 2, errors)
    top_key = "topP" if "topP" in payload else "top_p"
    if top_key in payload:
        values["top_p"] = _float(payload[top_key], "topP", 0, 1, errors)
    if "maxTokens" in payload or "max_tokens" in payload:
        raw = payload.get("maxTokens", payload.get("max_tokens"))
        if raw is None:
            values["max_tokens"] = None
        elif isinstance(raw, bool) or not isinstance(raw, int) or not 1 <= raw <= 32768:
            errors["maxTokens"] = "must be an integer from 1 to 32768 or null"
        else:
            values["max_tokens"] = raw
    prompt_key = "systemPromptExtra" if "systemPromptExtra" in payload else "system_prompt_extra"
    if prompt_key in payload:
        raw = payload[prompt_key]
        if raw is None:
            values["system_prompt_extra"] = None
        elif not isinstance(raw, str):
            errors["systemPromptExtra"] = "must be a string or null"
        else:
            values["system_prompt_extra"] = _prompt(raw, "systemPromptExtra", errors)

    candidate = replace(current) if current is not None else SystemSettings()
    for field, value in values.items():
        setattr(candidate, f"chat_{field}", value)
    _effective_runtime(settings, candidate, errors)
    if errors:
        raise ChatSettingsValidationError(errors)
    return values


def _stable_models(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = (value or "").strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def resolve_chat_runtime(settings: Settings, stored: SystemSettings) -> ChatRuntimeConfig:
    errors: dict[str, str] = {}
    runtime = _effective_runtime(settings, stored, errors)
    if runtime is None:
        raise ChatSettingsValidationError(errors or {"chat": "invalid effective settings"})
    return runtime


def chat_settings_view(settings: Settings, stored: SystemSettings) -> dict[str, Any]:
    runtime = resolve_chat_runtime(settings, stored)
    defaults = {
        "model": settings.llm_default_model,
        "fallbackModels": settings.llm_fallback_model_list,
        "temperature": settings.llm_temperature,
        "topP": settings.llm_top_p,
        "maxTokens": settings.llm_max_tokens,
        "systemPromptExtra": settings.llm_system_prompt_extra,
    }
    overrides = {
        "model": stored.chat_model,
        "fallbackModels": stored.chat_fallback_models,
        "temperature": stored.chat_temperature,
        "topP": stored.chat_top_p,
        "maxTokens": stored.chat_max_tokens,
        "systemPromptExtra": stored.chat_system_prompt_extra,
    }
    ids = _stable_models(
        [
            str(settings.llm_default_model or ""),
            *settings.llm_fallback_model_list,
            str(stored.chat_model or ""),
            *(stored.chat_fallback_models or []),
        ]
    )
    if settings.llm_free_only:
        ids = [model for model in ids if _free(model)]
    return {
        "version": stored.version,
        "chat": {
            "overrides": overrides,
            "defaults": defaults,
            "effective": {
                "model": runtime.model,
                "fallbackModels": list(runtime.fallback_models),
                "temperature": runtime.temperature,
                "topP": runtime.top_p,
                "maxTokens": runtime.max_tokens,
                "systemPromptExtra": runtime.system_prompt_extra,
            },
            "availableModels": ids,
        },
    }


__all__ = [
    "ChatRuntimeConfig",
    "ChatSettingsConflictError",
    "ChatSettingsValidationError",
    "chat_settings_view",
    "normalize_chat_patch",
    "resolve_chat_runtime",
]
