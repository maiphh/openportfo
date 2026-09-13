"""OpenAI-compat adapter: tool-call parse + 429 mapping."""

from __future__ import annotations

import json

import httpx

from app.adapters.llm.openai_compat import (
    OpenAiCompatProvider,
    _is_free_model,
    messages_to_openai,
)
from app.ports.llm import ChatMessage, LlmRateLimitError, ToolCall


def test_messages_to_openai_tool_roundtrip() -> None:
    msgs = [
        ChatMessage(role="system", content="s"),
        ChatMessage(role="user", content="u"),
        ChatMessage(
            role="assistant",
            content=None,
            tool_calls=[ToolCall(id="1", name="add_holding", arguments={"symbol": "BTC"})],
        ),
        ChatMessage(role="tool", content='{"ok":true}', tool_call_id="1", name="add_holding"),
    ]
    encoded = messages_to_openai(msgs)
    assert encoded[2]["tool_calls"][0]["function"]["name"] == "add_holding"
    assert json.loads(encoded[2]["tool_calls"][0]["function"]["arguments"])["symbol"] == "BTC"
    assert encoded[3]["tool_call_id"] == "1"


def test_complete_maps_429() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "3"},
            json={"error": {"message": "Rate limit exceeded", "code": 429}},
        )

    client = OpenAiCompatProvider(
        "sk-test",
        "https://openrouter.ai/api/v1",
        transport=httpx.MockTransport(handler),
        default_model="x:free",
    )
    try:
        client.complete([ChatMessage(role="user", content="hi")], model="x:free")
        raise AssertionError("expected rate limit")
    except LlmRateLimitError as exc:
        assert exc.retry_after == 3.0
        assert "Rate limit" in exc.detail


def test_complete_parses_tool_calls() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "gen-1",
                "model": "used-model",
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "type": "function",
                                    "function": {
                                        "name": "get_portfolio",
                                        "arguments": "{}",
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            },
        )

    client = OpenAiCompatProvider(
        "sk-test",
        "https://openrouter.ai/api/v1",
        transport=httpx.MockTransport(handler),
    )
    result = client.complete(
        [ChatMessage(role="user", content="analyze my portfo")],
        model="used-model",
    )
    assert result.model == "used-model"
    assert result.tool_calls[0].name == "get_portfolio"
    assert result.usage.total_tokens == 3


def test_complete_emits_effective_runtime_parameters() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"model": "m", "choices": [{"message": {"content": "ok"}}]},
        )

    client = OpenAiCompatProvider(
        "sk-test",
        "https://openrouter.ai/api/v1",
        transport=httpx.MockTransport(handler),
    )
    client.complete(
        [ChatMessage(role="user", content="hi")],
        model="m",
        max_tokens=321,
        temperature=0.25,
        top_p=0.8,
    )
    assert captured["model"] == "m"
    assert captured["max_tokens"] == 321
    assert captured["temperature"] == 0.25
    assert captured["top_p"] == 0.8


def test_complete_omits_null_runtime_parameters() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"model": "m", "choices": [{"message": {"content": "ok"}}]},
        )

    client = OpenAiCompatProvider(
        "sk-test",
        "https://openrouter.ai/api/v1",
        transport=httpx.MockTransport(handler),
    )
    client.complete(
        [ChatMessage(role="user", content="hi")],
        model="m",
        max_tokens=None,
        temperature=None,
        top_p=None,
    )
    assert "max_tokens" not in captured
    assert "temperature" not in captured
    assert "top_p" not in captured


def test_list_models_filters_free_and_tools() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "a:free",
                        "name": "A",
                        "pricing": {"prompt": "0", "completion": "0"},
                        "supported_parameters": ["tools", "temperature"],
                    },
                    {
                        "id": "paid",
                        "name": "P",
                        "pricing": {"prompt": "0.001", "completion": "0.002"},
                        "supported_parameters": ["tools"],
                    },
                    {
                        "id": "b:free",
                        "name": "B",
                        "pricing": {"prompt": "0", "completion": "0"},
                        "supported_parameters": ["temperature"],
                    },
                ]
            },
        )

    client = OpenAiCompatProvider(
        "sk-test",
        "https://openrouter.ai/api/v1",
        transport=httpx.MockTransport(handler),
    )
    models = client.list_models(free_only=True, tools_only=True)
    assert [m.id for m in models] == ["a:free"]


def test_numeric_zero_pricing_is_free() -> None:
    assert _is_free_model(
        {"id": "zero-price", "pricing": {"prompt": 0, "completion": 0.0}}
    )
    assert not _is_free_model(
        {"id": "paid", "pricing": {"prompt": 0.001, "completion": 0}}
    )
