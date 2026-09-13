"""Client-side 429 retry + model fallback."""

from __future__ import annotations

from app.adapters.llm.fallback import FallbackProvider
from app.ports.llm import LlmAuthError, LlmCompletion, LlmRateLimitError, LlmUsage
from tests.fakes.llm import ScriptedLlmProvider, completion_text


def test_retries_rate_limit_then_succeeds() -> None:
    sleeps: list[float] = []
    inner = ScriptedLlmProvider(
        [
            LlmRateLimitError("slow", retry_after=0.5),
            completion_text("ok", model="m1"),
        ]
    )
    wrapped = FallbackProvider(
        inner,
        fallback_models=["m2"],
        default_model="m1",
        retry_max=2,
        sleeper=sleeps.append,
    )
    result = wrapped.complete([], model="m1")
    assert result.content == "ok"
    assert sleeps == [0.5]
    assert result.tried_models[-1] == "m1"


def test_falls_back_to_next_model_after_retries() -> None:
    inner = ScriptedLlmProvider(
        [
            LlmRateLimitError("a", retry_after=0),
            LlmRateLimitError("b", retry_after=0),
            completion_text("from-fallback", model="m2"),
        ]
    )
    wrapped = FallbackProvider(
        inner,
        fallback_models=["m2"],
        default_model="m1",
        retry_max=1,
        sleeper=lambda _s: None,
    )
    result = wrapped.complete([], model="m1")
    assert result.content == "from-fallback"
    assert "m2" in result.tried_models


def test_auth_error_does_not_fallback() -> None:
    inner = ScriptedLlmProvider([LlmAuthError("bad key"), completion_text("nope")])
    wrapped = FallbackProvider(inner, fallback_models=["m2"], default_model="m1", retry_max=2)
    try:
        wrapped.complete([])
        raise AssertionError("expected LlmAuthError")
    except LlmAuthError as exc:
        assert "bad key" in exc.detail
    assert len(inner.calls) == 1


def test_passes_remaining_models_as_extra() -> None:
    inner = ScriptedLlmProvider([completion_text("ok")])
    wrapped = FallbackProvider(
        inner,
        fallback_models=["b", "c"],
        default_model="a",
        retry_max=0,
    )
    wrapped.complete([], model="a")
    extras = inner.calls[0]["extra_models"]
    assert extras == ["b", "c"]


def test_passes_runtime_sampling_and_token_parameters() -> None:
    inner = ScriptedLlmProvider([completion_text("ok")])
    wrapped = FallbackProvider(inner, default_model="a", retry_max=0)
    wrapped.complete(
        [],
        model="a",
        max_tokens=321,
        temperature=0.25,
        top_p=0.8,
    )
    assert inner.calls[0]["max_tokens"] == 321
    assert inner.calls[0]["temperature"] == 0.25
    assert inner.calls[0]["top_p"] == 0.8


def test_empty_completion_usage_ok() -> None:
    result = LlmCompletion(content="x", usage=LlmUsage())
    assert result.usage.total_tokens == 0
