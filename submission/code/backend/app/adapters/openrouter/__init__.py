"""OpenRouter adapter (OpenAI-compatible chat completions)."""

from app.adapters.llm.openai_compat import OpenAiCompatProvider, OpenRouterProvider

__all__ = ["OpenAiCompatProvider", "OpenRouterProvider"]
