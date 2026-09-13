"""Tool-calling loop: one LLM (orchestrator) plus registry-executed tools."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence

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


class ChatCancelled(LlmError):
    """The browser disconnected or the server deadline was reached."""

    def __init__(self, detail: str = "Chat request cancelled") -> None:
        super().__init__(detail)


class ChatMutationBlocked(LlmError):
    """A mutating tool was fenced because its durable ledger transition failed."""

    def __init__(self, tool_name: str) -> None:
        super().__init__("The requested change could not be safely started")
        self.tool_name = tool_name


class ChatOrchestrator:
    """Runs complete() → tools → complete() until the model stops calling tools."""

    def __init__(
        self,
        provider: LlmProvider,
        registry: ToolRegistry,
        *,
        max_rounds: int = 8,
        max_tokens: int = 2048,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        system_prompt: str = ORCHESTRATOR_SYSTEM,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._max_rounds = max(1, int(max_rounds))
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._top_p = top_p
        self._system_prompt = system_prompt

    def run(
        self,
        user_text: str,
        ctx: ToolContext,
        *,
        history: Optional[Sequence[ChatMessage]] = None,
        model: Optional[str] = None,
        on_progress: Optional[Callable[[dict[str, str]], None]] = None,
        should_stop: Optional[Callable[[], bool]] = None,
        before_mutating_tool: Optional[Callable[[str], bool]] = None,
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
            _check_should_stop(should_stop, executions, round_i, model)
            _emit_progress(on_progress, {"kind": "status", "status": "thinking"})
            try:
                last = self._provider.complete(
                    messages,
                    tools=tools,
                    model=model,
                    tool_choice="auto",
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                    top_p=self._top_p,
                )
            except LlmError as exc:
                # Preserve completed executions for the service's ambiguity
                # ledger. The original provider detail is never published.
                setattr(exc, "tool_executions", list(executions))
                setattr(exc, "tool_rounds", round_i)
                setattr(exc, "tool_model", model or "")
                raise
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
                    if self._registry.is_mutating(call.name):
                        _check_should_stop(should_stop, executions, round_i, model)
                        if before_mutating_tool is not None:
                            try:
                                allowed = bool(before_mutating_tool(call.name))
                            except Exception:  # noqa: BLE001 - fail closed before writes
                                allowed = False
                            if not allowed:
                                error = ChatMutationBlocked(call.name)
                                setattr(error, "tool_executions", list(executions))
                                setattr(error, "tool_rounds", round_i)
                                setattr(error, "tool_model", model or "")
                                raise error
                    _emit_progress(
                        on_progress,
                        {"kind": "tool", "name": call.name, "status": "started"},
                    )
                    executed = self._execute_call(call, ctx)
                    executions.append(executed)
                    _emit_progress(
                        on_progress,
                        {
                            "kind": "tool",
                            "name": executed.name,
                            "status": "completed" if executed.ok else "failed",
                        },
                    )
                    messages.append(
                        ChatMessage(
                            role="tool",
                            # Tool payloads are model-internal.  Strip tenant
                            # identifiers and credential/prompt-shaped keys
                            # before they leave this process for a provider.
                            content=json.dumps(
                                _sanitize_tool_payload(executed.result),
                                default=str,
                            ),
                            tool_call_id=call.id or executed.tool_call_id,
                            name=call.name,
                        )
                    )
                continue

            reply = (last.content or "").strip()
            if not reply and executions:
                reply = "Done. I used tools but the model returned an empty message."
            _emit_progress(on_progress, {"kind": "status", "status": "answering"})
            return OrchestratorResult(
                reply=_sanitize_assistant_text(reply) or "I could not produce a reply.",
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
            reply=_sanitize_assistant_text(tail.strip()),
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


def _emit_progress(
    callback: Optional[Callable[[dict[str, str]], None]],
    event: dict[str, str],
) -> None:
    """Invoke progress observers without allowing UI telemetry to break chat."""
    if callback is None:
        return
    try:
        callback(event)
    except Exception:  # noqa: BLE001 - progress is best-effort
        return


def _check_should_stop(
    callback: Optional[Callable[[], bool]],
    executions: list[ToolExecution],
    round_i: int,
    model: Optional[str],
) -> None:
    if callback is None:
        return
    try:
        stopped = bool(callback())
    except Exception:  # noqa: BLE001 - cancellation checks are fail-closed
        stopped = True
    if not stopped:
        return
    error = ChatCancelled()
    setattr(error, "tool_executions", list(executions))
    setattr(error, "tool_rounds", round_i)
    setattr(error, "tool_model", model or "")
    raise error


_SENSITIVE_PAYLOAD_KEYS = {
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


def _sanitize_tool_payload(value: Any, *, depth: int = 0) -> Any:
    """Remove sensitive fields from tool data before provider serialization."""
    if depth > 8:
        return "[nested data omitted]"
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).replace("-", "_").lower()
            if normalized in _SENSITIVE_PAYLOAD_KEYS:
                continue
            clean[str(key)] = _sanitize_tool_payload(item, depth=depth + 1)
        return clean
    if isinstance(value, list):
        return [_sanitize_tool_payload(item, depth=depth + 1) for item in value[:100]]
    if isinstance(value, tuple):
        return [_sanitize_tool_payload(item, depth=depth + 1) for item in value[:100]]
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
    """Keep provider content user-facing; drop common hidden-reasoning tags."""
    clean = _HIDDEN_REASONING_BLOCK.sub("", text)
    clean = _BRACKET_REASONING_BLOCK.sub("", clean)
    clean = _UNMATCHED_REASONING_BLOCK.sub("", clean)
    return clean.strip()


__all__ = [
    "ChatCancelled",
    "ChatMutationBlocked",
    "ChatOrchestrator",
    "OrchestratorResult",
    "LlmError",
]
