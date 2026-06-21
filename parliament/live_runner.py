"""Run one live parliament hearing via HUD rollout and stream timeline events."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import mcp.types as mcp_types
from hud.agents.openai_compatible import OpenAIChatAgent
from hud.agents.types import OpenAIChatConfig
from hud.eval.run import rollout
from hud.eval.runtime import LocalRuntime
from hud.types import MCPToolCall, MCPToolResult

from parliament.live_timeline import (
    SPEAKER_MODEL,
    TRAINED_POLICY_ID,
    TRAINED_POLICY_LABEL,
    event_from_tool_call,
    final_record_from_view,
    make_preview,
    reward_from_grade,
)
from tasks import _built_tasks

REPO_ROOT = Path(__file__).resolve().parents[1]
EventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]

# Live demo: skip training-only gateway flags and cap generation length for latency.
LIVE_COMPLETION_KWARGS = {
    "tool_choice": "required",
    "max_tokens": 512,
    "temperature": 0.4,
    "extra_body": {
        "chat_template_kwargs": {"enable_thinking": False},
    },
}


def _configure_specialists() -> None:
    os.environ.setdefault("PARLIAMENT_SPECIALIST_BACKEND", "llm")
    os.environ.setdefault("PARLIAMENT_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


def _require_hud_api_key() -> None:
    if not os.environ.get("HUD_API_KEY"):
        raise RuntimeError(
            "HUD_API_KEY is not configured on the Modal orchestrator. "
            "Run: modal secret create context-window-parliament-hud "
            "HUD_API_KEY=$HUD_API_KEY ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY --force"
        )


def _task_for_world(world_id: str) -> Any:
    for task in _built_tasks:
        slug = getattr(task, "slug", None)
        if slug == world_id:
            return task
    raise KeyError(f"No task registered for world_id={world_id!r}")


def _arguments(call: MCPToolCall) -> dict[str, Any]:
    if isinstance(call.arguments, dict):
        return call.arguments
    return {}


class StreamingOpenAIChatAgent(OpenAIChatAgent):
    def __init__(
        self,
        config: OpenAIChatConfig,
        *,
        on_tool_complete: Callable[[int, MCPToolCall, MCPToolResult], Awaitable[None]],
    ) -> None:
        super().__init__(config)
        self._on_tool_complete = on_tool_complete
        self._timeline_index = 1

    async def _dispatch_call(self, call: MCPToolCall, state: Any) -> MCPToolResult:
        result = await super()._dispatch_call(call, state)
        await self._on_tool_complete(self._timeline_index, call, result)
        self._timeline_index += 1
        return result


async def run_live_hearing(
    world_id: str,
    on_event: EventCallback,
    *,
    max_steps: int = 100,
) -> dict[str, Any]:
    _configure_specialists()
    _require_hud_api_key()
    preview = make_preview(world_id)
    specialists = preview["timeline"][0]["payload"]["specialists"]
    specialists_by_id = {str(item["id"]): item for item in specialists}
    started = time.perf_counter()
    await _emit(on_event, preview["timeline"][0])

    interactions_used = 0
    last_view: dict[str, Any] | None = None
    last_verdict: dict[str, Any] | None = None

    async def handle_tool(index: int, call: MCPToolCall, result: MCPToolResult) -> None:
        nonlocal interactions_used, last_view, last_verdict
        elapsed = time.perf_counter() - started
        event, interactions_used = event_from_tool_call(
            index=index,
            tool_name=call.name,
            arguments=_arguments(call),
            result=result,
            specialists_by_id=specialists_by_id,
            interactions_used=interactions_used,
        )
        event["elapsed_s"] = round(elapsed, 2)
        if event["tool"] == "view_record" and event.get("ok"):
            from parliament.live_timeline import _parse_tool_payload

            last_view = _parse_tool_payload(result)
        if event.get("verdict"):
            last_verdict = event["verdict"]
        await _emit(on_event, event)

    agent = StreamingOpenAIChatAgent(
        OpenAIChatConfig(
            model=SPEAKER_MODEL,
            max_steps=max_steps,
            completion_kwargs=LIVE_COMPLETION_KWARGS,
        ),
        on_tool_complete=handle_tool,
    )

    task = _task_for_world(world_id)
    run = await rollout(task, agent, runtime=LocalRuntime(REPO_ROOT / "env.py"))

    reward_block = reward_from_grade(run.evaluation or {}, run.reward)
    final_record = final_record_from_view(last_view, int(preview["world"]["token_budget"]))
    complete = {
        "type": "complete",
        "meta": {
            **preview["meta"],
            "trace_id": run.trace_id,
            "job_id": run.job_id,
            "elapsed_s": round(time.perf_counter() - started, 2),
        },
        "reward": reward_block,
        "final_record": final_record,
        "verdict": last_verdict,
        "status": run.trace.status or "completed",
    }
    await _emit(on_event, complete)

    return {
        **preview,
        "meta": {
            **preview["meta"],
            "policy_id": TRAINED_POLICY_ID,
            "policy_label": TRAINED_POLICY_LABEL,
            "trace_id": run.trace_id,
            "job_id": run.job_id,
            "live": True,
        },
        "reward": reward_block,
        "final_record": final_record,
    }


async def _emit(callback: EventCallback, payload: dict[str, Any]) -> None:
    maybe = callback(payload)
    if asyncio.iscoroutine(maybe):
        await maybe
