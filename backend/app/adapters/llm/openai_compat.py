"""OpenAI-compatible chat-completions HTTP client.

Works with OpenRouter (`https://openrouter.ai/api/v1`), xAI (`https://api.x.ai/v1`),
and OpenAI (`https://api.openai.com/v1`) by swapping base_url + api_key.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Sequence

import httpx

from app.ports.llm import (
    ChatMessage,
    LlmAuthError,
    LlmCompletion,
    LlmModelInfo,
    LlmProviderError,
    LlmRateLimitError,
    LlmUsage,
    ToolCall,
)


def messages_to_openai(messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
    """Serialize port messages to the OpenAI/OpenRouter request shape."""
    out: list[dict[str, Any]] = []
    for msg in messages:
        item: dict[str, Any] = {"role": msg.role}
        if msg.tool_calls:
            item["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments or {}),
                    },
                }
                for tc in msg.tool_calls
            ]
            item["content"] = msg.content
        elif msg.role == "tool":
            item["content"] = msg.content if msg.content is not None else ""
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            if msg.name:
                item["name"] = msg.name
        else:
            item["content"] = msg.content if msg.content is not None else ""
        if msg.name and msg.role != "tool":
            item["name"] = msg.name
        out.append(item)
    return out


def _parse_retry_after(resp: httpx.Response) -> Optional[float]:
    raw = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


def _error_message(data: Any, fallback: str) -> str:
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or err.get("metadata")
            if isinstance(msg, str) and msg.strip():
                return msg.strip()
        if isinstance(err, str) and err.strip():
            return err.strip()
        msg = data.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    return fallback


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {"_raw": raw}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw}
    return parsed if isinstance(parsed, dict) else {"_raw": parsed}


def _usage_from(payload: Any) -> LlmUsage:
    if not isinstance(payload, dict):
        return LlmUsage()
    cost = payload.get("cost")
    try:
        cost_f = float(cost) if cost is not None else None
    except (TypeError, ValueError):
        cost_f = None
    return LlmUsage(
        prompt_tokens=int(payload.get("prompt_tokens") or 0),
        completion_tokens=int(payload.get("completion_tokens") or 0),
        total_tokens=int(payload.get("total_tokens") or 0),
        cost=cost_f,
    )


def _price_or_none(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _is_free_model(item: dict[str, Any]) -> bool:
    mid = str(item.get("id") or "")
    if mid.endswith(":free") or mid == "openrouter/free":
        return True
    pricing = item.get("pricing") or {}
    if not isinstance(pricing, dict):
        return False
    prompt = _price_or_none(pricing.get("prompt"))
    completion = _price_or_none(pricing.get("completion"))
    if prompt is None or completion is None:
        return False
    return prompt == 0.0 and completion == 0.0


def _supports_tools(item: dict[str, Any]) -> bool:
    params = item.get("supported_parameters")
    if not params:
        # OpenAI / xAI catalog often omits this field.
        return True
    if isinstance(params, str):
        return "tools" in {p.strip() for p in params.split(",")}
    if isinstance(params, (list, tuple, set)):
        return "tools" in {str(p) for p in params}
    return False


class OpenAiCompatProvider:
    """POST {base}/chat/completions + GET {base}/models."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        timeout_seconds: float = 90.0,
        extra_headers: Optional[dict[str, str]] = None,
        enable_route_fallback: bool = False,
        transport: Optional[httpx.BaseTransport] = None,
        default_model: str = "",
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._base_url = (base_url or "").rstrip("/")
        self._timeout = timeout_seconds
        self._extra_headers = dict(extra_headers or {})
        self._enable_route_fallback = enable_route_fallback
        self._transport = transport
        self._default_model = default_model

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self._extra_headers)
        return headers

    def _raise_for_status(self, resp: httpx.Response, model: Optional[str]) -> None:
        if resp.status_code < 400:
            return
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001
            data = None
        detail = _error_message(data, f"LLM HTTP {resp.status_code}")
        if resp.status_code in (401, 402):
            raise LlmAuthError(detail)
        if resp.status_code == 429:
            raise LlmRateLimitError(
                detail,
                retry_after=_parse_retry_after(resp),
                model=model,
            )
        raise LlmProviderError(detail, status_code=resp.status_code, model=model)

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
        if not self._api_key:
            raise LlmAuthError("LLM API key is not configured")
        chosen = (model or self._default_model or "").strip()
        if not chosen:
            raise LlmProviderError("No LLM model specified")

        body: dict[str, Any] = {
            "model": chosen,
            "messages": messages_to_openai(messages),
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = tool_choice or "auto"
        if max_tokens is not None:
            body["max_tokens"] = int(max_tokens)
        if temperature is not None:
            body["temperature"] = float(temperature)
        extras = [m for m in (extra_models or []) if m and m != chosen]
        if self._enable_route_fallback and extras:
            body["models"] = extras
            body["route"] = "fallback"

        url = f"{self._base_url}/chat/completions"
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                resp = client.post(url, headers=self._headers(), json=body)
        except httpx.TimeoutException as exc:
            raise LlmProviderError(
                f"LLM request timed out after {self._timeout}s",
                model=chosen,
            ) from exc
        except httpx.HTTPError as exc:
            raise LlmProviderError(f"LLM request failed: {exc}", model=chosen) from exc

        self._raise_for_status(resp, chosen)

        try:
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise LlmProviderError("Invalid JSON from LLM provider", model=chosen) from exc

        if not isinstance(data, dict):
            raise LlmProviderError("Unexpected LLM response shape", model=chosen)

        err = data.get("error")
        if isinstance(err, dict):
            code = err.get("code")
            msg = _error_message(data, "LLM provider error")
            if code == 429 or "rate limit" in msg.lower():
                raise LlmRateLimitError(msg, model=chosen)
            raise LlmProviderError(msg, model=chosen)

        choices = data.get("choices") or []
        if not choices:
            raise LlmProviderError("LLM response missing choices", model=chosen)
        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message") or {}
        raw_calls = message.get("tool_calls") or []
        tool_calls: list[ToolCall] = []
        for raw in raw_calls:
            if not isinstance(raw, dict):
                continue
            fn = raw.get("function") or {}
            tool_calls.append(
                ToolCall(
                    id=str(raw.get("id") or ""),
                    name=str(fn.get("name") or ""),
                    arguments=_parse_arguments(fn.get("arguments")),
                )
            )
        used_model = str(data.get("model") or chosen)
        return LlmCompletion(
            content=message.get("content"),
            tool_calls=tool_calls,
            model=used_model,
            finish_reason=choice.get("finish_reason"),
            usage=_usage_from(data.get("usage")),
            tried_models=[chosen],
        )

    def list_models(
        self,
        *,
        free_only: bool = False,
        tools_only: bool = False,
    ) -> list[LlmModelInfo]:
        if not self._api_key:
            raise LlmAuthError("LLM API key is not configured")
        url = f"{self._base_url}/models"
        params: dict[str, str] = {}
        if tools_only:
            params["supported_parameters"] = "tools"
        try:
            with httpx.Client(timeout=min(self._timeout, 30.0), transport=self._transport) as client:
                resp = client.get(url, headers=self._headers(), params=params or None)
        except httpx.HTTPError as exc:
            raise LlmProviderError(f"LLM models request failed: {exc}") from exc
        self._raise_for_status(resp, None)
        try:
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise LlmProviderError("Invalid JSON from LLM models endpoint") from exc
        rows = data.get("data") if isinstance(data, dict) else data
        if not isinstance(rows, list):
            return []
        out: list[LlmModelInfo] = []
        for item in rows:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            info = LlmModelInfo(
                id=str(item["id"]),
                name=str(item.get("name") or item["id"]),
                free=_is_free_model(item),
                tools=_supports_tools(item),
                context_length=(
                    int(item["context_length"])
                    if item.get("context_length") is not None
                    else None
                ),
            )
            if free_only and not info.free:
                continue
            if tools_only and not info.tools:
                continue
            out.append(info)
        return out


class OpenRouterProvider(OpenAiCompatProvider):
    """OpenRouter defaults: referer headers + native `models` fallback routing."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 90.0,
        http_referer: str = "https://openportfo.local",
        app_title: str = "OpenPortfo",
        transport: Optional[httpx.BaseTransport] = None,
        default_model: str = "openrouter/free",
    ) -> None:
        super().__init__(
            api_key,
            base_url,
            timeout_seconds=timeout_seconds,
            extra_headers={
                "HTTP-Referer": http_referer,
                "X-OpenRouter-Title": app_title,
                "X-Title": app_title,
            },
            enable_route_fallback=True,
            transport=transport,
            default_model=default_model,
        )
