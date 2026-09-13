from __future__ import annotations

from app.services.llm.analyst import AnalystAgent
from tests.fakes.llm import ScriptedLlmProvider, completion_text


def test_analyst_drops_unmatched_reasoning_before_tool_result_reaches_user() -> None:
    provider = ScriptedLlmProvider([completion_text("<reasoning>private\nVisible answer")])
    result = AnalystAgent(provider).run("asset", {"symbol": "BTC"})
    assert result == "No analysis text returned."


def test_analyst_keeps_public_text_after_closed_reasoning_block() -> None:
    provider = ScriptedLlmProvider([completion_text("<think>private</think>Public answer")])
    assert AnalystAgent(provider).run("asset", {"symbol": "BTC"}) == "Public answer"
