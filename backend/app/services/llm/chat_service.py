"""High-level chat use-case: auth-scoped tools + orchestrator + model policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence

from datetime import timedelta
import re
from app.core.config import Settings
from app.ports.llm import ChatMessage, LlmAuthError, LlmError, LlmModelInfo, LlmProvider
from app.ports.chat_idempotency import (
    ChatIdempotencyRecord,
    ChatIdempotencyRepo,
    ChatReplay,
    IdempotencyState,
    utc_now,
)
from app.ports.users import UserProfile
from app.services.asset_detail_service import AssetDetailService
from app.services.holdings_service import HoldingsService
from app.services.llm.analyst import AnalystAgent
from app.services.llm.orchestrator import (
    ChatCancelled,
    ChatMutationBlocked,
    ChatOrchestrator,
    OrchestratorResult,
)
from app.services.llm.registry import ToolContext, ToolRegistry
from app.services.market_service import MarketService
from app.services.news_service import NewsService
from app.services.portfolio_service import PortfolioService
from app.services.watchlist_service import WatchlistService
from app.services.chat_settings_service import ChatRuntimeConfig
from app.services.llm.prompts import ORCHESTRATOR_SYSTEM


class ChatConfigError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ChatValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ChatConflictError(ChatValidationError):
    """The same client request is already being processed."""


class ChatAmbiguousError(LlmError):
    """A write may have completed but the provider did not finish the turn."""

    def __init__(self, detail: str = "A requested change may have completed; verify it before retrying.") -> None:
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
        idempotency: Optional[ChatIdempotencyRepo] = None,
        runtime: Optional[ChatRuntimeConfig] = None,
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
        self._idempotency = idempotency
        self._runtime = runtime or ChatRuntimeConfig(
            model=(settings.llm_default_model or "").strip(),
            fallback_models=tuple(settings.llm_fallback_model_list),
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
            max_tokens=int(settings.llm_max_tokens or 2048),
            system_prompt_extra=settings.llm_system_prompt_extra,
        )

    def configured(self) -> bool:
        return self._provider is not None

    def list_models(self, *, free_only: Optional[bool] = None, tools_only: bool = True) -> list[LlmModelInfo]:
        want_free = _effective_free_only(self._settings, free_only)
        if self._provider is None:
            return _static_model_catalog(self._settings, free_only=want_free, runtime=self._runtime)
        try:
            models = self._provider.list_models(free_only=want_free, tools_only=tools_only)
        except LlmAuthError:
            raise
        except LlmError:
            models = []
        if models:
            return models
        return _static_model_catalog(self._settings, free_only=want_free, runtime=self._runtime)

    def preflight(
        self,
        message: str,
        *,
        model: Optional[str] = None,
        free_only: Optional[bool] = None,
    ) -> None:
        """Validate provider/model policy before an SSE response is opened."""
        if self._provider is None:
            raise ChatConfigError("LLM is not configured (set OPENROUTER_API_KEY or LLM_API_KEY)")
        text = (message or "").strip()
        if not text:
            raise ChatValidationError("message is required")
        if len(text) > 8000:
            raise ChatValidationError("message is too long")
        chosen = (model or self._runtime.model or "").strip() or None
        want_free = _effective_free_only(self._settings, free_only)
        if chosen and want_free and not self._is_allowed_free_model(chosen):
            raise ChatValidationError(
                f"Model '{chosen}' is not a free variant. Pick a :free model or set LLM_FREE_ONLY=false"
            )

    def chat(
        self,
        user: UserProfile,
        message: str,
        *,
        history: Optional[Sequence[dict[str, Any]]] = None,
        model: Optional[str] = None,
        free_only: Optional[bool] = None,
        user_token: Optional[str] = None,
        on_progress: Optional[Callable[[dict[str, str]], None]] = None,
        should_stop: Optional[Callable[[], bool]] = None,
        client_request_id: Optional[str] = None,
        reject_unprotected_mutations: bool = True,
    ) -> ChatTurn:
        # Kept as a source-compatible no-op for older internal callers. The
        # credential is never stored on ToolContext or serialized anywhere.
        _ = user_token
        self.preflight(message, model=model, free_only=free_only)
        request_id = _normalize_request_id(client_request_id)
        claimed = False
        owner_token: Optional[str] = None
        mutation_started = False
        mutation_guard_error: Optional[Exception] = None
        if request_id and self._idempotency is not None:
            try:
                claim = self._idempotency.claim(
                    user.user_id,
                    request_id,
                    ttl_seconds=int(self._settings.chat_idempotency_ttl_seconds),
                )
            except Exception as exc:  # noqa: BLE001 - fail closed before tools run
                raise ChatConfigError("Chat request protection is temporarily unavailable") from exc
            existing = claim.existing
            if existing is not None:
                if existing.state == "completed" and existing.replay is not None:
                    return _turn_from_replay(existing.replay)
                if existing.state in {"ambiguous", "mutation_started"}:
                    _emit_replay_progress(on_progress, existing.replay)
                    raise ChatAmbiguousError()
                raise ChatConflictError("A request with this id is already in progress")
            owner_token = claim.owner_token
            if not owner_token:
                raise ChatConfigError("Chat request protection is temporarily unavailable")
            claimed = True

        want_free = _effective_free_only(self._settings, free_only)
        chosen = (model or self._runtime.model or "").strip() or None
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
        )
        orchestrator = ChatOrchestrator(
            self._provider,
            self._registry,
            max_rounds=int(self._settings.llm_max_tool_rounds or 8),
            max_tokens=int(self._runtime.max_tokens),
            temperature=self._runtime.temperature,
            top_p=self._runtime.top_p,
            system_prompt=_orchestrator_prompt(self._runtime.system_prompt_extra),
        )
        text = (message or "").strip()

        def before_mutating_tool(_name: str) -> bool:
            """Durably fence each write immediately before executing it."""
            nonlocal mutation_started, mutation_guard_error
            if not request_id:
                if reject_unprotected_mutations:
                    return False
                return True
            if self._idempotency is None or not claimed or not owner_token:
                mutation_guard_error = ChatConfigError(
                    "Chat request protection is temporarily unavailable"
                )
                return False
            try:
                allowed = self._idempotency.mark_mutation_started(
                    user.user_id,
                    request_id,
                    owner_token=owner_token,
                    ttl_seconds=int(self._settings.chat_idempotency_ttl_seconds),
                )
            except Exception as exc:  # noqa: BLE001 - fail closed before a write
                mutation_guard_error = ChatConfigError(
                    "Chat request protection is temporarily unavailable"
                )
                mutation_guard_error.__cause__ = exc
                return False
            if allowed:
                mutation_started = True
            return allowed

        try:
            result: OrchestratorResult = orchestrator.run(
                text,
                ctx,
                history=_history_from_dicts(history),
                model=chosen,
                on_progress=on_progress,
                should_stop=should_stop,
                before_mutating_tool=before_mutating_tool,
            )
        except ChatMutationBlocked as exc:
            executions = getattr(exc, "tool_executions", [])
            if not request_id and reject_unprotected_mutations:
                if claimed and owner_token:
                    self._release_claim(user.user_id, request_id, owner_token)
                raise ChatValidationError(
                    "clientRequestId is required before a request can change your data"
                ) from exc
            if mutation_guard_error is not None:
                if isinstance(mutation_guard_error, ChatConfigError):
                    if claimed and owner_token and not mutation_started:
                        self._release_claim(user.user_id, request_id, owner_token)
                    raise mutation_guard_error from exc
            if claimed and request_id and owner_token and mutation_started:
                self._save_ambiguous(
                    user.user_id,
                    request_id,
                    executions,
                    chosen,
                    owner_token=owner_token,
                )
                _emit_replay_progress(
                    on_progress,
                    _safe_replay_from_executions(
                        executions, model=chosen, registry=self._registry
                    ),
                )
                raise ChatAmbiguousError() from exc
            if claimed and request_id and owner_token:
                self._release_claim(user.user_id, request_id, owner_token)
            raise ChatAmbiguousError() from exc
        except ChatCancelled as exc:
            executions = getattr(exc, "tool_executions", [])
            if claimed and request_id and owner_token:
                if mutation_started or _has_mutating_execution(self._registry, executions):
                    self._save_ambiguous(
                        user.user_id,
                        request_id,
                        executions,
                        chosen,
                        owner_token=owner_token,
                    )
                    _emit_replay_progress(on_progress, _safe_replay_from_executions(executions, model=chosen, registry=self._registry))
                else:
                    self._release_claim(user.user_id, request_id, owner_token)
            raise
        except LlmError as exc:
            executions = getattr(exc, "tool_executions", [])
            if claimed and request_id and owner_token:
                if mutation_started or _has_mutating_execution(self._registry, executions):
                    self._save_ambiguous(
                        user.user_id,
                        request_id,
                        executions,
                        chosen,
                        owner_token=owner_token,
                    )
                    _emit_replay_progress(on_progress, _safe_replay_from_executions(executions, model=chosen, registry=self._registry))
                    raise ChatAmbiguousError() from exc
                self._release_claim(user.user_id, request_id, owner_token)
            raise

        turn = ChatTurn(
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
        if claimed and request_id and owner_token:
            replay = _safe_replay_from_turn(turn, registry=self._registry)
            expected_state: IdempotencyState = "mutation_started" if mutation_started else "in_progress"
            try:
                saved = self._idempotency.save(  # type: ignore[union-attr]
                    ChatIdempotencyRecord(
                        user_id=user.user_id,
                        request_id=request_id,
                        state="completed",
                        expires_at=utc_now() + timedelta(seconds=int(self._settings.chat_idempotency_ttl_seconds)),
                        replay=replay,
                        updated_at=utc_now(),
                        owner_token=owner_token,
                    ),
                    owner_token=owner_token,
                    expected_state=expected_state,
                )
                if not saved:
                    raise ChatAmbiguousError()
            except Exception as exc:  # noqa: BLE001 - do not invite a duplicate write
                if isinstance(exc, ChatAmbiguousError):
                    raise
                raise ChatAmbiguousError() from exc
        return turn

    def _release_claim(self, user_id: str, request_id: Optional[str], owner_token: str) -> None:
        if self._idempotency is None or not request_id:
            return
        try:
            released = self._idempotency.release(
                user_id,
                request_id,
                owner_token=owner_token,
                expected_state="in_progress",
            )
        except Exception as exc:  # noqa: BLE001 - fail closed
            raise ChatConfigError("Chat request protection is temporarily unavailable") from exc
        if not released:
            raise ChatConflictError("Chat request ownership changed; verify before retrying")

    def _save_ambiguous(
        self,
        user_id: str,
        request_id: str,
        executions: Sequence[Any],
        model: Optional[str],
        *,
        owner_token: str,
    ) -> None:
        if self._idempotency is None:
            return
        replay = _safe_replay_from_executions(executions, model=model, registry=self._registry)
        now = utc_now()
        try:
            saved = self._idempotency.save(
                ChatIdempotencyRecord(
                    user_id=user_id,
                    request_id=request_id,
                    state="ambiguous",
                    expires_at=now + timedelta(seconds=int(self._settings.chat_idempotency_ttl_seconds)),
                    replay=ChatReplay(
                        reply=replay.reply,
                        model=replay.model,
                        tool_calls=replay.tool_calls,
                        tried_models=replay.tried_models,
                        rounds=replay.rounds,
                        ambiguous=True,
                    ),
                    updated_at=now,
                    owner_token=owner_token,
                ),
                owner_token=owner_token,
                expected_state="mutation_started",
            )
            if not saved:
                raise ChatAmbiguousError()
        except Exception as exc:  # noqa: BLE001 - surface ambiguity, never auto-retry
            raise ChatAmbiguousError() from exc

    def public_tool_calls(self, turn: ChatTurn) -> list[dict[str, Any]]:
        """Return allow-listed activity metadata for a browser client.

        Arguments, results, call ids, and model internals intentionally stay
        inside the service boundary.  Unknown tool names are represented by a
        generic activity so model-controlled text cannot become UI metadata.
        """
        out: list[dict[str, Any]] = []
        for call in turn.tool_calls:
            metadata = self._registry.public_tool_metadata(str(call.get("name") or ""))
            if metadata is None:
                metadata = {"name": "assistant_action", "label": "Assistant action"}
            out.append(
                {
                    **metadata,
                    "status": "completed" if bool(call.get("ok")) else "failed",
                    "ok": bool(call.get("ok")),
                }
            )
        return out

    def public_tool_metadata(self, name: str) -> Optional[dict[str, str]]:
        """Return allow-listed display metadata for one tool name."""
        return self._registry.public_tool_metadata(name)

    def _is_allowed_free_model(self, model_id: str) -> bool:
        if _looks_free(model_id):
            return True
        for mid in self._runtime.fallback_models:
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


def _orchestrator_prompt(extra: Optional[str]) -> str:
    suffix = (extra or "").strip()
    if not suffix:
        return ORCHESTRATOR_SYSTEM
    return (
        ORCHESTRATOR_SYSTEM
        + "\n\n--- Administrator guidance (supplemental) ---\n"
        + suffix
    )


def _looks_free(model_id: str) -> bool:
    mid = (model_id or "").strip()
    if not mid:
        return False
    if mid.endswith(":free") or mid == "openrouter/free":
        return True
    # Explicit allow-list of known free routers / aliases
    return mid.startswith("openrouter/free")


def _static_model_catalog(
    settings: Settings,
    *,
    free_only: bool,
    runtime: Optional[ChatRuntimeConfig] = None,
) -> list[LlmModelInfo]:
    ids = []
    default = ((runtime.model if runtime else settings.llm_default_model) or "").strip()
    if default:
        ids.append(default)
    ids.extend(list(runtime.fallback_models) if runtime else settings.llm_fallback_model_list)
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


_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")


def _normalize_request_id(raw: Optional[str]) -> Optional[str]:
    text = (raw or "").strip()
    if not text:
        return None
    if _REQUEST_ID_RE.fullmatch(text) is None:
        raise ChatValidationError("clientRequestId is invalid")
    return text


def _safe_tool_name(name: Any, registry: Optional[ToolRegistry]) -> str:
    raw = str(name or "")
    if registry is not None and registry.public_tool_metadata(raw) is not None:
        return raw
    return "assistant_action"


def _safe_replay_from_turn(turn: ChatTurn, *, registry: Optional[ToolRegistry] = None) -> ChatReplay:
    return ChatReplay(
        reply=str(turn.reply or "")[:8_000],
        model=str(turn.model or "")[:200],
        tool_calls=[
            {"name": _safe_tool_name(call.get("name"), registry), "ok": bool(call.get("ok"))}
            for call in turn.tool_calls[:32]
        ],
        tried_models=[str(model)[:200] for model in turn.tried_models[:16]],
        rounds=max(0, int(turn.rounds)),
    )


def _safe_replay_from_executions(
    executions: Sequence[Any],
    *,
    model: Optional[str] = None,
    registry: Optional[ToolRegistry] = None,
) -> ChatReplay:
    """Create an ambiguity marker without retaining model-controlled payloads."""
    calls: list[dict[str, Any]] = []
    for execution in executions[:32]:
        name = getattr(execution, "name", None)
        ok = bool(getattr(execution, "ok", False))
        if isinstance(execution, dict):
            name = execution.get("name")
            ok = bool(execution.get("ok"))
        calls.append({"name": _safe_tool_name(name, registry), "ok": ok})
    return ChatReplay(
        reply="A requested change may have completed; verify it before retrying.",
        model=str(model or "")[:200],
        tool_calls=calls,
        tried_models=[],
        rounds=len(calls),
        ambiguous=True,
    )


def _turn_from_replay(replay: ChatReplay) -> ChatTurn:
    return ChatTurn(
        reply=replay.reply,
        model=replay.model,
        tool_calls=[
            {
                "name": str(call.get("name") or "assistant_action"),
                "arguments": {},
                "result": {},
                "ok": bool(call.get("ok")),
            }
            for call in replay.tool_calls[:32]
            if isinstance(call, dict)
        ],
        usage={},
        tried_models=[str(model)[:200] for model in replay.tried_models[:16]],
        rounds=max(0, int(replay.rounds)),
    )


def _emit_replay_progress(
    callback: Optional[Callable[[dict[str, str]], None]], replay: Optional[ChatReplay]
) -> None:
    if callback is None or replay is None:
        return
    for call in replay.tool_calls[:32]:
        if isinstance(call, dict):
            callback(
                {
                    "kind": "tool",
                    "name": str(call.get("name") or "assistant_action"),
                    "status": "completed" if bool(call.get("ok")) else "failed",
                }
            )


def _has_mutating_execution(registry: ToolRegistry, executions: Sequence[Any]) -> bool:
    for execution in executions:
        name = getattr(execution, "name", None)
        if isinstance(execution, dict):
            name = execution.get("name")
        if registry.is_mutating(str(name or "")):
            return True
    return False


__all__ = [
    "ChatService",
    "ChatTurn",
    "ChatConfigError",
    "ChatValidationError",
    "ChatConflictError",
    "ChatAmbiguousError",
]
