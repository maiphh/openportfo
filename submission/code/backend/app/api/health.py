"""Health check routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.deps import get_object_storage, get_settings_repo

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> Any:
    """Readiness: DynamoDB (or in-memory settings) + object storage ping."""
    checks: dict[str, dict[str, str]] = {}
    try:
        get_settings_repo().get()
        checks["database"] = {"status": "ok"}
    except Exception:
        checks["database"] = {"status": "error", "detail": "unreachable"}
    try:
        get_object_storage().ping()
        checks["storage"] = {"status": "ok"}
    except Exception:
        checks["storage"] = {"status": "error", "detail": "unreachable"}
    ok = all(item.get("status") == "ok" for item in checks.values())
    body = {"status": "ok" if ok else "degraded", "checks": checks}
    if ok:
        return body
    return JSONResponse(status_code=503, content=body)
