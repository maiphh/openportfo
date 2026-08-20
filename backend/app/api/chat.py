"""Authenticated chatbot routes with a privacy-safe progress stream."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import get_chat_service, get_current_user, get_settings
from app.ports.llm import LlmAuthError, LlmError, LlmProviderError, LlmRateLimitError
from app.ports.users import UserProfile
from app.services.llm.chat_service import (
    ChatAmbiguousError,
    ChatConfigError,
    ChatConflictError,
    ChatService,
    ChatValidationError,
)

router = APIRouter(tags=["chat"])

# Provider calls are synchronous today. Keep their bridge bounded so a burst
# of browser streams cannot create an unbounded thread per connection.
_STREAM_MAX_CONCURRENCY = max(1, min(32, int(get_settings().chat_stream_max_concurrency)))
_STREAM_EXECUTOR = ThreadPoolExecutor(
    max_workers=_STREAM_MAX_CONCURRENCY,
    thread_name_prefix="chat-stream",
)
_STREAM_SLOTS = threading.BoundedSemaphore(_STREAM_MAX_CONCURRENCY)
_STREAM_HEARTBEAT_SECONDS = 12.0
_STREAM_QUEUE_SIZE = 128


class ChatHistoryItem(BaseModel):
    role: str
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(max_length=8000)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=32)
    model: Optional[str] = Field(default=None, max_length=200)
    free_only: Optional[bool] = Field(default=None, alias="freeOnly")
    client_request_id: Optional[str] = Field(
        default=None,
        alias="clientRequestId",
        min_length=1,
        max_length=96,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$",
    )


def _chat_http_error(exc: Exception) -> HTTPException:
    """Map failures to bounded, user-facing messages.

    Provider exception text can contain request ids, upstream payloads, or
    accidental credentials. It is intentionally not copied to the browser.
    """
    if isinstance(exc, ChatConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail)
    if isinstance(exc, ChatValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)
    if isinstance(exc, ChatAmbiguousError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.detail,
            headers={"X-Chat-Ambiguous": "true"},
        )
    if isinstance(exc, ChatConfigError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.detail)
    if isinstance(exc, LlmAuthError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat provider authentication is unavailable.",
        )
    if isinstance(exc, LlmRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The chat provider is busy. Please try again shortly.",
        )
    if isinstance(exc, (LlmProviderError, LlmError)):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The chat provider could not complete this request.",
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to complete the chat request.",
    )


def _history(body: ChatRequest) -> list[dict[str, str]]:
    # The service applies a second cap before sending history to the provider;
    # this first cap keeps request memory bounded at the HTTP boundary.
    return [
        {"role": item.role, "content": item.content[:4000]}
        for item in body.history[-32:]
    ]


def _safe_tool_calls(svc: ChatService, turn: Any) -> list[dict[str, Any]]:
    return svc.public_tool_calls(turn)


def _legacy_response(svc: ChatService, turn: Any) -> dict[str, Any]:
    """Keep the original POST keys with an explicitly versioned safe contract.

    The old endpoint exposed provider token/cost internals through ``usage``.
    Version 2 keeps the key for clients that destructure it, but makes the
    privacy behavior explicit instead of returning a misleading empty object.
    """
    return {
        "responseVersion": 2,
        "reply": turn.reply,
        "model": turn.model,
        "toolCalls": _safe_tool_calls(svc, turn),
        "usage": {"available": False, "redacted": True},
        # Model routing history is part of the legacy response contract, but
        # cap it to short identifiers rather than exposing provider payloads.
        "triedModels": [str(model)[:200] for model in (turn.tried_models or [])[:16]],
        "rounds": max(0, int(turn.rounds or 0)),
    }


def _sse(event: str, payload: dict[str, Any]) -> str:
    # json.dumps ensures model text cannot inject an SSE event boundary.
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    return f"event: {event}\ndata: {encoded}\n\n"


def _public_progress(svc: ChatService, raw: object) -> Optional[tuple[str, dict[str, Any]]]:
    """Translate internal callbacks into the tiny public activity vocabulary."""
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind") or "")
    if kind == "status":
        state = str(raw.get("status") or "")
        messages = {
            "thinking": "Thinking about your request",
            "answering": "Writing a response",
        }
        if state not in messages:
            return None
        return "status", {"status": state, "message": messages[state]}
    if kind == "tool":
        name = str(raw.get("name") or "")
        metadata = svc.public_tool_metadata(name)
        if metadata is None:
            metadata = {"name": "assistant_action", "label": "Assistant action"}
        state = str(raw.get("status") or "")
        if state not in {"started", "completed", "failed"}:
            return None
        return "tool", {**metadata, "status": state}
    return None


@router.get("/api/chat/models")
def list_chat_models(
    free: bool = Query(default=True),
    tools: bool = Query(default=True),
    user: UserProfile = Depends(get_current_user),
    svc: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    """List models (free + tool-capable by default). Auth required."""
    _ = user
    settings = get_settings()
    models = svc.list_models(free_only=free if not settings.llm_free_only else True, tools_only=tools)
    return {
        "configured": svc.configured(),
        "provider": settings.llm_provider,
        "defaultModel": settings.llm_default_model,
        "freeOnly": settings.llm_free_only,
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "free": m.free,
                "tools": m.tools,
                "contextLength": m.context_length,
            }
            for m in models
        ],
    }


def _run_turn(
    body: ChatRequest,
    user: UserProfile,
    svc: ChatService,
    *,
    on_progress: Any = None,
    should_stop: Any = None,
    reject_unprotected_mutations: bool = True,
) -> Any:
    return svc.chat(
        user,
        body.message,
        history=_history(body),
        model=body.model,
        free_only=body.free_only,
        on_progress=on_progress,
        should_stop=should_stop,
        client_request_id=body.client_request_id,
        reject_unprotected_mutations=reject_unprotected_mutations,
    )


@router.post("/api/chat")
def post_chat(
    body: ChatRequest,
    user: UserProfile = Depends(get_current_user),
    svc: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    """Compatibility JSON turn; tools execute as the authenticated user."""
    try:
        turn = _run_turn(body, user, svc, reject_unprotected_mutations=True)
    except (ChatValidationError, ChatConfigError, LlmError) as exc:
        raise _chat_http_error(exc) from exc
    return _legacy_response(svc, turn)


def _stream_error_payload(exc: Exception) -> dict[str, Any]:
    error = _chat_http_error(exc)
    payload: dict[str, Any] = {
        "message": str(error.detail),
        "status": error.status_code,
    }
    if isinstance(exc, ChatAmbiguousError):
        payload["ambiguous"] = True
    return payload


@router.post("/api/chat/events", include_in_schema=False)
@router.post("/api/chat/stream")
async def stream_chat(
    request: Request,
    body: ChatRequest,
    user: UserProfile = Depends(get_current_user),
    svc: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Stream safe status/tool/final events without exposing model internals."""

    if not body.client_request_id:
        # Streams are the production client path and always carry a durable
        # request key so a write can be fenced before its tool executes.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="clientRequestId is required for chat streams",
        )

    # Validate configuration and model policy before opening a 200 SSE
    # response. Invalid input/configuration remains an ordinary 4xx/503.
    try:
        svc.preflight(body.message, model=body.model, free_only=body.free_only)
    except (ChatValidationError, ChatConfigError, LlmError) as exc:
        raise _chat_http_error(exc) from exc

    if not _STREAM_SLOTS.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat stream capacity is temporarily full. Please try again shortly.",
        )

    loop = asyncio.get_running_loop()
    events: asyncio.Queue[Optional[tuple[str, dict[str, Any]]]] = asyncio.Queue(
        maxsize=_STREAM_QUEUE_SIZE
    )
    stop_event = threading.Event()

    def put_now(item: Optional[tuple[str, dict[str, Any]]]) -> None:
        if events.full():
            # Progress is deliberately lossy and bounded. Always make room
            # for terminal events/sentinel so a busy stream cannot hang until
            # its deadline merely because its progress queue filled.
            terminal = item is None or item[0] in {"message", "done", "error"}
            if not terminal:
                return
            try:
                events.get_nowait()
            except asyncio.QueueEmpty:
                return
        events.put_nowait(item)

    def enqueue(item: Optional[tuple[str, dict[str, Any]]]) -> None:
        try:
            loop.call_soon_threadsafe(put_now, item)
        except RuntimeError:
            stop_event.set()

    def on_progress(raw: dict[str, str]) -> None:
        public = _public_progress(svc, raw)
        if public is not None:
            enqueue(public)

    def worker() -> None:
        try:
            turn = _run_turn(
                body,
                user,
                svc,
                on_progress=on_progress,
                should_stop=stop_event.is_set,
                reject_unprotected_mutations=True,
            )
            if stop_event.is_set():
                return
            enqueue(
                (
                    "message",
                    {
                        "content": turn.reply,
                        "done": True,
                        "toolCalls": _safe_tool_calls(svc, turn),
                    },
                )
            )
            enqueue(("done", {"ok": True}))
        except (ChatValidationError, ChatConfigError, LlmError) as exc:
            if not stop_event.is_set():
                enqueue(("error", _stream_error_payload(exc)))
        except Exception:
            if not stop_event.is_set():
                enqueue(
                    (
                        "error",
                        {"message": "Unable to complete the chat request.", "status": 500},
                    )
                )
        finally:
            enqueue(None)
            _STREAM_SLOTS.release()

    try:
        future = loop.run_in_executor(_STREAM_EXECUTOR, worker)
    except Exception:
        _STREAM_SLOTS.release()
        raise

    def consume_future(done: Any) -> None:
        try:
            done.result()
        except Exception:
            # Expected failures are translated into safe SSE events. This
            # prevents an unobserved future exception after disconnect.
            return

    future.add_done_callback(consume_future)

    async def event_stream():
        yield _sse("status", {"status": "started", "message": "Starting chat"})
        started_at = time.monotonic()
        deadline = max(5.0, float(get_settings().chat_stream_deadline_seconds))
        try:
            while True:
                if await request.is_disconnected():
                    stop_event.set()
                    break
                remaining = deadline - (time.monotonic() - started_at)
                if remaining <= 0:
                    stop_event.set()
                    yield _sse(
                        "error",
                        {
                            "message": "The chat request timed out. Verify any requested changes before retrying.",
                            "status": 504,
                            "ambiguous": True,
                        },
                    )
                    break
                try:
                    item = await asyncio.wait_for(
                        events.get(), timeout=min(_STREAM_HEARTBEAT_SECONDS, remaining)
                    )
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        stop_event.set()
                        break
                    yield _sse("heartbeat", {"at": int(time.time())})
                    continue
                if item is None:
                    break
                if await request.is_disconnected():
                    stop_event.set()
                    break
                event, payload = item
                yield _sse(event, payload)
        finally:
            stop_event.set()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = ["ChatHistoryItem", "ChatRequest", "router"]
