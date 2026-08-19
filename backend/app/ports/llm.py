"""LLM provider port (OpenRouter today; OpenAI / xAI / any OpenAI-compatible later).

Services depend on this protocol only. HTTP lives in adapters.
The user's Bearer token is never sent to the provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Sequence


class LlmError(Exception):
    """Base LLM failure."""

    def __init__(self, detail: str = "LLM request failed") -> None:
        self.detail = detail
        super().__init__(detail)


class LlmAuthError(LlmError):
    """Provider rejected the API key (401/403)."""


class LlmRateLimitError(LlmError):
    """HTTP 429 or provider rate-limit payload."""

    def __init__(
        self,
        detail: str = "LLM rate limited",
        *,
        retry_after: Optional[float] = None,
        model: Optional[str] = None,
    ) -> None:
        super().__init__(detail)
        self.retry_after = retry_after
        self.model = model


class LlmProviderError(LlmError):
    """Non-auth provider/HTTP failure (4xx/5xx, timeout, bad JSON)."""

    def __init__(
        self,
        detail: str = "LLM provider error",
        *,
        status_code: Optional[int] = None,
        model: Optional[str] = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.model = model


@dataclass
class ToolCall:
    """One model-requested function call."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatMessage:
    """One OpenAI-style chat message (system/user/assistant/tool)."""

    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None


@dataclass
class LlmUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: Optional[float] = None


@dataclass
class LlmCompletion:
    content: Optional[str]
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    finish_reason: Optional[str] = None
    usage: LlmUsage = field(default_factory=LlmUsage)
    tried_models: list[str] = field(default_factory=list)


@dataclass
class LlmModelInfo:
    id: str
    name: str
    free: bool
    tools: bool
    context_length: Optional[int] = None


class LlmProvider(Protocol):
    """Port: chat completions + model listing. Swap adapters without changing tools."""

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
        """Run one chat completion. Raises LlmError subclasses."""
        ...

    def list_models(
        self,
        *,
        free_only: bool = False,
        tools_only: bool = False,
    ) -> list[LlmModelInfo]:
        """Catalog models. Empty list is allowed when the provider has no catalog."""
        ...


__all__ = [
    "LlmError",
    "LlmAuthError",
    "LlmRateLimitError",
    "LlmProviderError",
    "ToolCall",
    "ChatMessage",
    "LlmUsage",
    "LlmCompletion",
    "LlmModelInfo",
    "LlmProvider",
]
