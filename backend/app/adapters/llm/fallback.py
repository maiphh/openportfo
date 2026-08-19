"""Retry 429s and walk a model fallback list. Provider-agnostic wrapper."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional, Sequence

from app.ports.llm import (
    ChatMessage,
    LlmAuthError,
    LlmCompletion,
    LlmError,
    LlmModelInfo,
    LlmProvider,
    LlmProviderError,
    LlmRateLimitError,
)

Sleeper = Callable[[float], None]


class FallbackProvider:
    """Try the requested model, then fallbacks, with bounded 429 retries."""

    def __init__(
        self,
        inner: LlmProvider,
        *,
        fallback_models: Optional[Sequence[str]] = None,
        default_model: Optional[str] = None,
        retry_max: int = 2,
        max_retry_sleep: float = 8.0,
        sleeper: Sleeper = time.sleep,
    ) -> None:
        self._inner = inner
        self._fallbacks = [m.strip() for m in (fallback_models or []) if m and m.strip()]
        self._default_model = (default_model or "").strip() or None
        self._retry_max = max(0, int(retry_max))
        self._max_retry_sleep = max(0.0, float(max_retry_sleep))
        self._sleeper = sleeper

    def _candidates(self, model: Optional[str]) -> list[str]:
        primary = (model or self._default_model or "").strip()
        ordered: list[str] = []
        seen: set[str] = set()
        for item in [primary, *self._fallbacks]:
            if not item or item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        if not ordered:
            ordered.append(primary or "")
        return ordered

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        tools: Optional[list[dict[str, Any]]] = None,
        model: Optional[str] = None,
        tool_choice: str = "auto",
        extra_models: Optional[Sequence[str]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LlmCompletion:
        candidates = self._candidates(model)
        last_error: Optional[LlmError] = None
        tried: list[str] = []

        for index, candidate in enumerate(candidates):
            remaining = [m for m in candidates[index + 1 :]]
            extras = list(extra_models or []) + remaining
            # de-dupe extras
            extra_seen: set[str] = set()
            extra_clean: list[str] = []
            for item in extras:
                if item and item != candidate and item not in extra_seen:
                    extra_seen.add(item)
                    extra_clean.append(item)

            for attempt in range(self._retry_max + 1):
                try:
                    result = self._inner.complete(
                        messages,
                        tools=tools,
                        model=candidate or None,
                        tool_choice=tool_choice,
                        extra_models=extra_clean or None,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    result.tried_models = tried + [result.model or candidate]
                    return result
                except LlmAuthError:
                    raise
                except LlmRateLimitError as exc:
                    last_error = exc
                    if attempt >= self._retry_max:
                        break
                    wait = exc.retry_after if exc.retry_after is not None else float(2**attempt)
                    wait = min(max(wait, 0.0), self._max_retry_sleep)
                    if wait > 0:
                        self._sleeper(wait)
                except LlmProviderError as exc:
                    last_error = exc
                    if exc.status_code == 402:
                        raise
                    # 403/404/5xx may be model-specific → try the next candidate
                    break
                except LlmError as exc:
                    last_error = exc
                    break
            tried.append(candidate)

        if last_error is not None:
            raise last_error
        raise LlmProviderError("No LLM model candidates to try")

    def list_models(
        self,
        *,
        free_only: bool = False,
        tools_only: bool = False,
    ) -> list[LlmModelInfo]:
        return self._inner.list_models(free_only=free_only, tools_only=tools_only)


__all__ = ["FallbackProvider"]
