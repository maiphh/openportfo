"""On-demand specialist: no tools, dedicated system prompt, JSON context only."""

from __future__ import annotations

import json
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
        body = json.dumps(payload, default=str)[:12000]
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
        text = (completion.content or "").strip()
        return text or "No analysis text returned."


__all__ = ["AnalystAgent"]
