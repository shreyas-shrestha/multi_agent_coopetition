"""FastMCP tool declarations for HUD, backed by parliament.tools."""

from __future__ import annotations

from typing import Any

from parliament import tools as core_tools

try:
    from fastmcp import FastMCP
except Exception:  # pragma: no cover - exercised only without optional dependency
    FastMCP = None  # type: ignore[assignment]

mcp = FastMCP(name="context-window-parliament") if FastMCP is not None else None


def _tool(func: Any) -> Any:
    return mcp.tool(func) if mcp is not None else func


@_tool
async def list_specialists(world_id: str) -> dict[str, Any]:
    """Return public specialist cards for a world."""

    return core_tools.list_specialists(world_id)


@_tool
async def grant_floor(world_id: str, specialist_id: str, token_budget: int) -> dict[str, Any]:
    """Grant official-record floor time to a specialist."""

    return core_tools.grant_floor(world_id, specialist_id, token_budget)


@_tool
async def cross_examine(
    world_id: str,
    specialist_id: str,
    question: str,
    token_budget: int,
) -> dict[str, Any]:
    """Ask a targeted cross-examination question."""

    return core_tools.cross_examine(world_id, specialist_id, question, token_budget)


@_tool
async def view_record(world_id: str) -> dict[str, Any]:
    """Return the visible official record."""

    return core_tools.view_record(world_id)


@_tool
async def submit_verdict(
    world_id: str,
    decision: str,
    confidence: float,
    root_cause: str,
    citation_ids: list[str],
    rationale: str,
) -> dict[str, Any]:
    """Submit the final structured verdict."""

    return core_tools.submit_verdict(
        world_id,
        decision,
        confidence,
        root_cause,
        citation_ids,
        rationale,
    )

