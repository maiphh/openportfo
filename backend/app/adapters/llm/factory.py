"""Build an LlmProvider from Settings (swap provider / URL / key here)."""

from __future__ import annotations

from typing import Optional

from app.adapters.llm.fallback import FallbackProvider
from app.adapters.llm.openai_compat import OpenAiCompatProvider, OpenRouterProvider
from app.core.config import Settings
from app.ports.llm import LlmProvider

_PROVIDER_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "xai": "https://api.x.ai/v1",
}


def resolved_api_key(settings: Settings) -> str:
    """LLM_API_KEY, else provider-specific key (OPENROUTER_API_KEY / XAI / OPENAI)."""
    generic = (settings.llm_api_key or "").strip()
    if generic:
        return generic
    provider = (settings.llm_provider or "openrouter").strip().lower()
    if provider == "openrouter":
        return (settings.openrouter_api_key or "").strip()
    if provider == "xai":
        return (settings.xai_api_key or "").strip()
    if provider == "openai":
        return (settings.openai_api_key or "").strip()
    return (
        (settings.openrouter_api_key or "").strip()
        or (settings.openai_api_key or "").strip()
        or (settings.xai_api_key or "").strip()
    )


def resolved_base_url(settings: Settings) -> str:
    override = (settings.llm_base_url or "").strip().rstrip("/")
    if override:
        return override
    provider = (settings.llm_provider or "openrouter").strip().lower()
    return _PROVIDER_URLS.get(provider, _PROVIDER_URLS["openrouter"])


def build_inner_provider(settings: Settings) -> Optional[LlmProvider]:
    """Raw HTTP provider (no retry wrapper). None when key missing or provider=fake."""
    provider = (settings.llm_provider or "openrouter").strip().lower()
    if provider in {"fake", "none", "off"}:
        return None
    key = resolved_api_key(settings)
    if not key:
        return None
    base = resolved_base_url(settings)
    timeout = float(settings.llm_timeout_seconds or 90.0)
    default_model = (settings.llm_default_model or "").strip()
    if provider == "openrouter" or "openrouter.ai" in base:
        return OpenRouterProvider(
            key,
            base_url=base,
            timeout_seconds=timeout,
            http_referer=settings.llm_http_referer,
            app_title=settings.llm_app_title,
            default_model=default_model or "openrouter/free",
        )
    return OpenAiCompatProvider(
        key,
        base,
        timeout_seconds=timeout,
        extra_headers={},
        enable_route_fallback=False,
        default_model=default_model,
    )


def build_llm_provider(settings: Settings) -> Optional[LlmProvider]:
    """Provider + client-side retry / model fallback. None if unconfigured."""
    inner = build_inner_provider(settings)
    if inner is None:
        return None
    return FallbackProvider(
        inner,
        fallback_models=settings.llm_fallback_model_list,
        default_model=(settings.llm_default_model or "").strip() or None,
        retry_max=int(settings.llm_retry_max or 0),
        max_retry_sleep=float(settings.llm_retry_max_sleep or 8.0),
    )


__all__ = [
    "resolved_api_key",
    "resolved_base_url",
    "build_inner_provider",
    "build_llm_provider",
]
