"""Tool registry — add a ToolSpec to expose a new chatbot capability."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from app.ports.users import UserProfile
from app.services.asset_detail_service import AssetDetailService
from app.services.holdings_service import HoldingsService
from app.services.market_service import MarketService
from app.services.news_service import NewsService
from app.services.portfolio_service import PortfolioService
from app.services.watchlist_service import WatchlistService

ToolHandler = Callable[[dict[str, Any], "ToolContext"], dict[str, Any]]
AnalystFn = Callable[[str, dict[str, Any]], str]


@dataclass
class ToolContext:
    """Per-request services scoped to the authenticated user.

    Authentication is resolved before this context is created.  A bearer
    token is deliberately not retained here: tools use the already resolved
    ``UserProfile`` and scoped ports, so there is no credential to
    accidentally serialize into a model request or progress event.
    """

    user: UserProfile
    holdings: HoldingsService
    watchlist: WatchlistService
    portfolio: PortfolioService
    market: MarketService
    asset_detail: Optional[AssetDetailService] = None
    news: Optional[NewsService] = None
    run_analyst: Optional[AnalystFn] = None


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    # Optional product-facing label.  Tool descriptions and schemas remain
    # model-facing; the UI receives only this small allow-listed metadata.
    public_label: Optional[str] = None
    # Mutating tools are checked against request cancellation immediately
    # before execution and participate in request idempotency handling.
    mutating: bool = False


@dataclass
class ToolExecution:
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    ok: bool
    tool_call_id: str = ""


@dataclass
class ToolRegistry:
    _tools: dict[str, ToolSpec] = field(default_factory=dict)

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def public_tool_metadata(self, name: str) -> Optional[dict[str, str]]:
        """Return the only tool metadata that may cross the API boundary.

        Unknown/model-invented tool names are intentionally rejected rather
        than echoed.  This prevents arbitrary model text from becoming a UI
        event and keeps arguments/results out of the public contract.
        """
        spec = self._tools.get(name)
        if spec is None:
            return None
        label = (spec.public_label or _PUBLIC_TOOL_LABELS.get(spec.name) or "").strip()
        if not label:
            return None
        return {"name": spec.name, "label": label}

    def is_mutating(self, name: str) -> bool:
        spec = self._tools.get(name)
        return bool(spec and spec.mutating)

    def openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
            for spec in self._tools.values()
        ]

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        ctx: ToolContext,
        *,
        tool_call_id: str = "",
        max_chars: int = 8000,
    ) -> ToolExecution:
        spec = self._tools.get(name)
        if spec is None:
            result = {"ok": False, "error": f"Unknown tool: {name}"}
            return ToolExecution(
                name=name,
                arguments=arguments or {},
                result=result,
                ok=False,
                tool_call_id=tool_call_id,
            )
        try:
            raw = spec.handler(arguments or {}, ctx)
            if not isinstance(raw, dict):
                raw = {"ok": True, "result": raw}
            elif "ok" not in raw:
                raw = {"ok": True, **raw}
        except Exception as exc:  # noqa: BLE001 — tool errors become model-visible JSON
            raw = {"ok": False, "error": str(getattr(exc, "detail", None) or exc)}
        clipped = _clip_result(raw, max_chars)
        return ToolExecution(
            name=name,
            arguments=arguments or {},
            result=clipped,
            ok=bool(clipped.get("ok")),
            tool_call_id=tool_call_id,
        )


def _clip_result(result: dict[str, Any], max_chars: int) -> dict[str, Any]:
    try:
        encoded = json.dumps(result, default=str)
    except TypeError:
        encoded = json.dumps({"ok": result.get("ok", True), "error": "unserializable tool result"})
        result = json.loads(encoded)
    if len(encoded) <= max_chars:
        return result
    return {
        "ok": result.get("ok", True),
        "truncated": True,
        "preview": encoded[: max(0, max_chars - 80)],
    }


__all__ = [
    "AnalystFn",
    "ToolContext",
    "ToolExecution",
    "ToolHandler",
    "ToolRegistry",
    "ToolSpec",
]


# This is deliberately a closed list.  Adding a tool requires consciously
# deciding what short, non-sensitive label can be shown to signed-in users.
_PUBLIC_TOOL_LABELS: dict[str, str] = {
    "search_assets": "Searching assets",
    "add_holding": "Updating holdings",
    "remove_holding": "Updating holdings",
    "list_holdings": "Reading holdings",
    "get_portfolio": "Reading portfolio",
    "get_quote": "Checking a quote",
    "analyze_asset": "Analyzing an asset",
    "analyze_portfolio": "Analyzing portfolio",
    "get_news": "Reading market news",
    "add_watchlist": "Updating watchlist",
    "remove_watchlist": "Updating watchlist",
}
