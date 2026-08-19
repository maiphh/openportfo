"""Tool-calling loop: one LLM (orchestrator) plus registry-executed tools."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from app.ports.llm import ChatMessage, LlmCompletion, LlmError, LlmProvider, ToolCall
from app.services.llm.prompts import ORCHESTRATOR_SYSTEM
from app.services.llm.registry import ToolContext, ToolExecution, ToolRegistry


@dataclass
class OrchestratorResult:
    reply: str
    model: str
    tool_calls: list[ToolExecution] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    tried_models: list[str] = field(default_factory=list)
    rounds: int = 0
    finish_reason: Optional[str] = None


class ChatOrchestrator:
    """Runs complete() → tools → complete() until the model stops calling tools."""

    def __init__(
        self,
        provider: LlmProvider,
        registry: ToolRegistry,
        *,
        max_rounds: int = 8,
        max_tokens: int = 2048,
        system_prompt: str = ORCHESTRATOR_SYSTEM,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._max_rounds = max(1, int(max_rounds))
        self._max_tokens = max_tokens
        self._system_prompt = system_prompt

    def run(
        self,
        user_text: str,
        ctx: ToolContext,
        *,
        history: Optional[Sequence[ChatMessage]] = None,
        model: Optional[str] = None,
    ) -> OrchestratorResult:
        messages: list[ChatMessage] = [ChatMessage(role="system", content=self._system_prompt)]
        if history:
            messages.extend(_sanitize_history(history))
        messages.append(ChatMessage(role="user", content=user_text))

        tools = self._registry.openai_tools()
        executions: list[ToolExecution] = []
        usage_acc = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0.0}
        tried: list[str] = []
        last: Optional[LlmCompletion] = None

        for round_i in range(self._max_rounds):
            last = self._provider.complete(
                messages,
                tools=tools,
                model=model,
                tool_choice="auto",
                max_tokens=self._max_tokens,
            )
            _accumulate_usage(usage_acc, last)
            for mid in last.tried_models:
                if mid not in tried:
                    tried.append(mid)

            if last.tool_calls:
                messages.append(
                    ChatMessage(
                        role="assistant",
                        content=last.content,
                        tool_calls=last.tool_calls,
                    )
                )
                for call in last.tool_calls:
                    executed = self._execute_call(call, ctx)
                    executions.append(executed)
                    messages.append(
                        ChatMessage(
                            role="tool",
                            content=json.dumps(executed.result, default=str),
                            tool_call_id=call.id or executed.tool_call_id,
                            name=call.name,
                        )
                    )
                continue

            reply = (last.content or "").strip()
            if not reply and executions:
                reply = "Done. I used tools but the model returned an empty message."
            return OrchestratorResult(
                reply=reply or "I could not produce a reply.",
                model=last.model,
                tool_calls=executions,
                usage=usage_acc,
                tried_models=tried,
                rounds=round_i + 1,
                finish_reason=last.finish_reason,
            )

        # Budget exhausted: one last attempt without tools if we still have no text.
        tail = (last.content if last else None) or ""
        if not tail.strip():
            tail = (
                "I reached the tool-call limit before finishing. "
                "Please retry with a simpler request."
            )
        return OrchestratorResult(
            reply=tail.strip(),
            model=(last.model if last else model) or "",
            tool_calls=executions,
            usage=usage_acc,
            tried_models=tried,
            rounds=self._max_rounds,
            finish_reason="max_rounds",
        )

    def _execute_call(self, call: ToolCall, ctx: ToolContext) -> ToolExecution:
        args = call.arguments if isinstance(call.arguments, dict) else {}
        return self._registry.execute(
            call.name,
            args,
            ctx,
            tool_call_id=call.id,
        )


def _sanitize_history(history: Sequence[ChatMessage]) -> list[ChatMessage]:
    out: list[ChatMessage] = []
    for msg in history:
        if msg.role not in {"user", "assistant"}:
            continue
        content = (msg.content or "").strip()
        if not content:
            continue
        out.append(ChatMessage(role=msg.role, content=content[:4000]))
    return out[-16:]


def _accumulate_usage(acc: dict[str, Any], completion: LlmCompletion) -> None:
    usage = completion.usage
    acc["prompt_tokens"] += int(usage.prompt_tokens or 0)
    acc["completion_tokens"] += int(usage.completion_tokens or 0)
    acc["total_tokens"] += int(usage.total_tokens or 0)
    if usage.cost:
        acc["cost"] = float(acc.get("cost") or 0) + float(usage.cost)


__all__ = ["ChatOrchestrator", "OrchestratorResult", "LlmError"]
