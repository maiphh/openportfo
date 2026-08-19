"""High-level chat use-case: auth-scoped tools + orchestrator + model policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from app.core.config import Settings
from app.ports.llm import ChatMessage, LlmAuthError, LlmError, LlmModelInfo, LlmProvider
from app.ports.users import UserProfile
from app.services.asset_detail_service import AssetDetailService
from app.services.holdings_service import HoldingsService
from app.services.llm.analyst import AnalystAgent
from app.services.llm.orchestrator import ChatOrchestrator, OrchestratorResult
from app.services.llm.registry import ToolContext, ToolRegistry
from app.services.market_service import MarketService
from app.services.news_service import NewsService
from app.services.portfolio_service import PortfolioService
from app.services.watchlist_service import WatchlistService


class ChatConfigError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ChatValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass
class ChatTurn:
    reply: str
    model: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    tried_models: list[str] = field(default_factory=list)
    rounds: int = 0


class ChatService:
    def __init__(
        self,
        provider: Optional[LlmProvider],
        registry: ToolRegistry,
        settings: Settings,
        holdings: HoldingsService,
        watchlist: WatchlistService,
        portfolio: PortfolioService,
        market: MarketService,
        *,
        asset_detail: Optional[AssetDetailService] = None,
        news: Optional[NewsService] = None,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._settings = settings
        self._holdings = holdings
        self._watchlist = watchlist
        self._portfolio = portfolio
        self._market = market
        self._asset_detail = asset_detail
        self._news = news

    def configured(self) -> bool:
        return self._provider is not None

    def list_models(self, *, free_only: Optional[bool] = None, tools_only: bool = True) -> list[LlmModelInfo]:
        want_free = _effective_free_only(self._settings, free_only)
        if self._provider is None:
            return _static_model_catalog(self._settings, free_only=want_free)
        try:
            models = self._provider.list_models(free_only=want_free, tools_only=tools_only)
        except LlmAuthError:
            raise
        except LlmError:
            models = []
        if models:
            return models
        return _static_model_catalog(self._settings, free_only=want_free)

    def chat(
        self,
        user: UserProfile,
        message: str,
        *,
        history: Optional[Sequence[dict[str, Any]]] = None,
        model: Optional[str] = None,
        free_only: Optional[bool] = None,
        user_token: Optional[str] = None,
    ) -> ChatTurn:
        if self._provider is None:
            raise ChatConfigError("LLM is not configured (set OPENROUTER_API_KEY or LLM_API_KEY)")
        text = (message or "").strip()
        if not text:
            raise ChatValidationError("message is required")
        if len(text) > 8000:
            raise ChatValidationError("message is too long")

        want_free = _effective_free_only(self._settings, free_only)
        chosen = (model or self._settings.llm_default_model or "").strip() or None
        if chosen and want_free and not self._is_allowed_free_model(chosen):
            raise ChatValidationError(
                f"Model '{chosen}' is not a free variant. Pick a :free model or set LLM_FREE_ONLY=false"
            )

        analyst = AnalystAgent(self._provider, model=chosen)
        ctx = ToolContext(
            user=user,
            holdings=self._holdings,
            watchlist=self._watchlist,
            portfolio=self._portfolio,
            market=self._market,
            asset_detail=self._asset_detail,
            news=self._news,
            run_analyst=analyst.run,
            user_token=user_token,
        )
        orchestrator = ChatOrchestrator(
            self._provider,
            self._registry,
            max_rounds=int(self._settings.llm_max_tool_rounds or 8),
            max_tokens=int(self._settings.llm_max_tokens or 2048),
        )
        result: OrchestratorResult = orchestrator.run(
            text,
            ctx,
            history=_history_from_dicts(history),
            model=chosen,
        )
        return ChatTurn(
            reply=result.reply,
            model=result.model,
            tool_calls=[
                {
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "result": tc.result,
                    "ok": tc.ok,
                }
                for tc in result.tool_calls
            ],
            usage=result.usage,
            tried_models=result.tried_models,
            rounds=result.rounds,
        )

    def _is_allowed_free_model(self, model_id: str) -> bool:
        if _looks_free(model_id):
            return True
        for mid in self._settings.llm_fallback_model_list:
            if mid == model_id:
                return _looks_free(mid)
        try:
            catalog = self.list_models(free_only=True, tools_only=False)
        except Exception:  # noqa: BLE001
            return False
        return any(m.id == model_id and m.free for m in catalog)


def _effective_free_only(settings: Settings, client_flag: Optional[bool]) -> bool:
    """Server LLM_FREE_ONLY is a floor; the client can only tighten it."""
    if settings.llm_free_only:
        return True
    if client_flag is None:
        return False
    return bool(client_flag)


def _looks_free(model_id: str) -> bool:
    mid = (model_id or "").strip()
    if not mid:
        return False
    if mid.endswith(":free") or mid == "openrouter/free":
        return True
    # Explicit allow-list of known free routers / aliases
    return mid.startswith("openrouter/free")


def _static_model_catalog(settings: Settings, *, free_only: bool) -> list[LlmModelInfo]:
    ids = []
    default = (settings.llm_default_model or "").strip()
    if default:
        ids.append(default)
    ids.extend(settings.llm_fallback_model_list)
    seen: set[str] = set()
    out: list[LlmModelInfo] = []
    for mid in ids:
        if not mid or mid in seen:
            continue
        seen.add(mid)
        free = _looks_free(mid)
        if free_only and not free:
            continue
        out.append(LlmModelInfo(id=mid, name=mid, free=free, tools=True))
    return out


def _history_from_dicts(history: Optional[Sequence[dict[str, Any]]]) -> list[ChatMessage]:
    if not history:
        return []
    out: list[ChatMessage] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "")
        content = item.get("content")
        if role not in {"user", "assistant"} or content is None:
            continue
        out.append(ChatMessage(role=role, content=str(content)))
    return out


__all__ = ["ChatService", "ChatTurn", "ChatConfigError", "ChatValidationError"]
