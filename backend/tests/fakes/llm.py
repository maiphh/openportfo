"""Scripted LLM provider for unit tests (no HTTP)."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from app.ports.llm import (
    ChatMessage,
    LlmCompletion,
    LlmError,
    LlmModelInfo,
    LlmProviderError,
    LlmUsage,
    ToolCall,
)


class ScriptedLlmProvider:
    def __init__(
        self,
        script: Optional[Sequence[LlmCompletion | Exception]] = None,
        *,
        models: Optional[list[LlmModelInfo]] = None,
    ) -> None:
        self.script: list[LlmCompletion | Exception] = list(script or [])
        self.calls: list[dict[str, Any]] = []
        self.models = models or [
            LlmModelInfo(
                id="meta-llama/llama-3.3-70b-instruct:free",
                name="Llama 3.3 70B (free)",
                free=True,
                tools=True,
            )
        ]

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
        self.calls.append(
            {
                "messages": list(messages),
                "tools": tools,
                "model": model,
                "tool_choice": tool_choice,
                "extra_models": list(extra_models or []),
                "max_tokens": max_tokens,
            }
        )
        if not self.script:
            raise LlmProviderError("script exhausted")
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def list_models(
        self,
        *,
        free_only: bool = False,
        tools_only: bool = False,
    ) -> list[LlmModelInfo]:
        out = self.models
        if free_only:
            out = [m for m in out if m.free]
        if tools_only:
            out = [m for m in out if m.tools]
        return out


def completion_text(text: str, model: str = "fake-model") -> LlmCompletion:
    return LlmCompletion(content=text, model=model, finish_reason="stop", usage=LlmUsage())


def completion_tools(
    *calls: ToolCall,
    model: str = "fake-model",
    content: Optional[str] = None,
) -> LlmCompletion:
    return LlmCompletion(
        content=content,
        tool_calls=list(calls),
        model=model,
        finish_reason="tool_calls",
        usage=LlmUsage(),
    )


__all__ = [
    "ScriptedLlmProvider",
    "completion_text",
    "completion_tools",
    "LlmError",
]
