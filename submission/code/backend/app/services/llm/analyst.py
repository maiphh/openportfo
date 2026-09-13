"""On-demand specialist: no tools, dedicated system prompt, JSON context only."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.ports.llm import ChatMessage, LlmProvider
from app.services.llm.prompts import ANALYST_SYSTEM


class AnalystAgent:
    def __init__(
        self,
        provider: LlmProvider,
        *,
        model: Optional[str] = None,
        max_tokens: int = 700,
        system_prompt: str = ANALYST_SYSTEM,
    ) -> None:
        self._provider = provider
        self._model = model
        self._max_tokens = max_tokens
        self._system_prompt = system_prompt

    def run(self, kind: str, payload: dict[str, Any]) -> str:
        label = "asset" if kind == "asset" else "portfolio"
        body = json.dumps(_sanitize_payload(payload), default=str)[:12000]
        messages = [
            ChatMessage(role="system", content=self._system_prompt),
            ChatMessage(
                role="user",
                content=(
                    f"Write a {label} analysis from this JSON. "
                    "Cite only numbers present in the JSON.\n\n"
                    f"{body}"
                ),
            ),
        ]
        completion = self._provider.complete(
            messages,
            tools=None,
            model=self._model,
            tool_choice="none",
            max_tokens=self._max_tokens,
            temperature=0.3,
        )
        text = _sanitize_assistant_text(completion.content or "")
        return text or "No analysis text returned."


_SENSITIVE_KEYS = {
    "userid",
    "user_id",
    "token",
    "accesstoken",
    "access_token",
    "authorization",
    "cookie",
    "systemprompt",
    "system_prompt",
    "prompt",
    "raw",
    "arguments",
}


def _sanitize_payload(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[nested data omitted]"
    if isinstance(value, dict):
        return {
            str(key): _sanitize_payload(item, depth=depth + 1)
            for key, item in value.items()
            if str(key).replace("-", "_").lower() not in _SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_payload(item, depth=depth + 1) for item in value[:100]]
    return value


_HIDDEN_REASONING_BLOCK = re.compile(
    r"<\s*(?:think|analysis|reasoning)\b[^>]*>.*?<\s*/\s*(?:think|analysis|reasoning)\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
_UNMATCHED_REASONING_BLOCK = re.compile(
    r"<\s*(?:think|analysis|reasoning)\b[^>]*>.*$",
    flags=re.IGNORECASE | re.DOTALL,
)
_BRACKET_REASONING_BLOCK = re.compile(
    r"\[\s*(?:think|analysis|reasoning)\s*\].*?(?:\[\s*/\s*(?:think|analysis|reasoning)\s*\]|$)",
    flags=re.IGNORECASE | re.DOTALL,
)


def _sanitize_assistant_text(text: str) -> str:
    clean = _HIDDEN_REASONING_BLOCK.sub("", text)
    clean = _BRACKET_REASONING_BLOCK.sub("", clean)
    clean = _UNMATCHED_REASONING_BLOCK.sub("", clean)
    return clean.strip()


__all__ = ["AnalystAgent"]
