"""Chatbot routes: Bearer-auth user; tools run as that user (token never sent to LLM)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import get_chat_service, get_current_user, get_settings
from app.ports.llm import LlmAuthError, LlmError, LlmProviderError, LlmRateLimitError
from app.ports.users import UserProfile
from app.services.llm.chat_service import ChatConfigError, ChatService, ChatValidationError

router = APIRouter(tags=["chat"])


class ChatHistoryItem(BaseModel):
    role: str
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(max_length=8000)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=32)
    model: Optional[str] = None
    free_only: Optional[bool] = Field(default=None, alias="freeOnly")


def _chat_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ChatValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)
    if isinstance(exc, ChatConfigError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.detail)
    if isinstance(exc, LlmAuthError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM authentication failed: {exc.detail}",
        )
    if isinstance(exc, LlmRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=exc.detail,
        )
    if isinstance(exc, LlmProviderError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.detail,
        )
    if isinstance(exc, LlmError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.detail,
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
    )


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


@router.post("/api/chat")
def post_chat(
    body: ChatRequest,
    user: UserProfile = Depends(get_current_user),
    svc: ChatService = Depends(get_chat_service),
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Orchestrator turn. Tools execute as the Bearer-authenticated user."""
    token = ""
    if authorization:
        scheme, _, rest = authorization.partition(" ")
        if scheme.lower() == "bearer":
            token = rest.strip()
    try:
        turn = svc.chat(
            user,
            body.message,
            history=[item.model_dump() for item in body.history],
            model=body.model,
            free_only=body.free_only,
            user_token=token or None,
        )
    except (ChatValidationError, ChatConfigError, LlmError) as exc:
        raise _chat_http_error(exc) from exc
    return {
        "reply": turn.reply,
        "model": turn.model,
        "toolCalls": turn.tool_calls,
        "usage": turn.usage,
        "triedModels": turn.tried_models,
        "rounds": turn.rounds,
    }
