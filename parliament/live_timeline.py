"""Convert MCP tool results into showcase timeline events."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from parliament.state import reset_worlds, register_world
from parliament.tools import list_specialists
from parliament.worlds import build_world, shipped_task_specs

TRAINED_POLICY_ID = "targeted_oracle"
TRAINED_POLICY_LABEL = "Trained Speaker (Live)"
SPEAKER_MODEL = "parliament-qwen36-35b-clean"


def _task_row(world_id: str) -> dict[str, Any]:
    for row in shipped_task_specs():
        if str(row["world_id"]) == world_id:
            return row
    raise KeyError(f"Unknown world_id: {world_id}")


def _parse_tool_payload(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    content = getattr(result, "content", None) or []
    chunks: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            chunks.append(str(block.get("text", "")))
        else:
            text = getattr(block, "text", None)
            if text:
                chunks.append(str(text))
    raw = "".join(chunks).strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "error": raw}
    return parsed if isinstance(parsed, dict) else {"ok": True, "content": parsed}


def _tool_basename(name: str) -> str:
    if "__" in name:
        return name.rsplit("__", 1)[-1]
    if name.startswith("mcp__"):
        return name.split("__")[-1]
    return name


def make_preview(world_id: str) -> dict[str, Any]:
    row = _task_row(world_id)
    reset_worlds()
    world = build_world(
        world_id=str(row["world_id"]),
        domain=str(row["domain"]),
        difficulty=str(row["difficulty"]),
        seed=int(row["seed"]),
    )
    register_world(world)
    specialists = list_specialists(world.world_id)["specialists"]
    session_start = {
        "index": 0,
        "type": "session_start",
        "payload": {
            "narrative": world.narrative,
            "specialists": specialists,
            "budget_total": world.token_budget,
            "max_interactions": world.max_interactions,
        },
    }
    return {
        "meta": {
            "world_id": world.world_id,
            "domain": world.domain,
            "difficulty": world.difficulty,
            "policy_id": TRAINED_POLICY_ID,
            "policy_label": TRAINED_POLICY_LABEL,
            "speaker_model": SPEAKER_MODEL,
            "generated_at": datetime.now(UTC).isoformat(),
            "live": True,
        },
        "world": {
            "world_id": world.world_id,
            "domain": world.domain,
            "difficulty": world.difficulty,
            "narrative": world.narrative,
            "token_budget": world.token_budget,
            "max_interactions": world.max_interactions,
            "decision_options": world.decision_options,
            "root_cause_options": world.root_cause_options,
        },
        "reward": {
            "reward": 0.0,
            "subscores": {},
            "metadata": {},
        },
        "timeline": [session_start],
        "final_record": {
            "budget_used": 0,
            "budget_remaining": world.token_budget,
            "testimony": [],
        },
    }


def event_from_tool_call(
    *,
    index: int,
    tool_name: str,
    arguments: dict[str, Any],
    result: Any,
    specialists_by_id: dict[str, dict[str, Any]],
    interactions_used: int,
) -> tuple[dict[str, Any], int]:
    tool = _tool_basename(tool_name)
    payload = _parse_tool_payload(result)
    ok = bool(payload.get("ok", not getattr(result, "isError", False)))
    message = str(payload.get("error") or payload.get("message") or ("ok" if ok else "error"))

    budget_total = payload.get("budget_total")
    budget_remaining = payload.get("remaining_budget", payload.get("budget_remaining"))
    budget_used = None
    if isinstance(budget_total, int) and isinstance(budget_remaining, int):
        budget_used = budget_total - budget_remaining
    elif isinstance(payload.get("budget_used"), int):
        budget_used = int(payload["budget_used"])

    max_interactions = payload.get("max_interactions")
    testimony = None
    verdict = None

    if ok and tool in {"grant_floor", "cross_examine"}:
        specialist_id = str(payload.get("specialist_id") or arguments.get("specialist_id") or "")
        card = specialists_by_id.get(specialist_id, {})
        testimony = {
            "id": str(payload.get("testimony_id") or f"t-{index}"),
            "specialist_id": specialist_id,
            "specialist_name": str(card.get("name") or specialist_id or "specialist"),
            "role": str(card.get("role") or ""),
            "mode": "cross_exam" if tool == "cross_examine" else "floor",
            "question": arguments.get("question") if tool == "cross_examine" else None,
            "visible_text": str(payload.get("visible_text") or ""),
            "token_count": int(payload.get("used_tokens") or arguments.get("token_budget") or 0),
        }
        interactions_used += 1
    elif ok and tool == "submit_verdict":
        verdict = payload.get("verdict")
        if isinstance(verdict, dict):
            verdict = {
                "decision": str(verdict.get("decision", "")),
                "confidence": float(verdict.get("confidence", 0)),
                "root_cause": str(verdict.get("root_cause", "")),
                "citation_ids": list(verdict.get("citation_ids") or verdict.get("citations") or []),
                "rationale": str(verdict.get("rationale", "")),
            }

    if tool == "view_record" and ok:
        budget_used = payload.get("budget_used", budget_used)
        budget_remaining = payload.get("budget_remaining", budget_remaining)
        max_interactions = payload.get("max_interactions", max_interactions)
        interactions_used = int(payload.get("interactions_used") or interactions_used)

    event = {
        "index": index,
        "type": "tool_call",
        "tool": tool,
        "ok": ok,
        "message": message,
        "args": arguments,
        "budget_used": budget_used,
        "budget_remaining": budget_remaining,
        "budget_total": budget_total,
        "interactions_used": interactions_used,
        "max_interactions": max_interactions,
        "testimony_added": testimony,
        "verdict": verdict,
    }
    return event, interactions_used


def reward_from_grade(raw: dict[str, Any], reward: float) -> dict[str, Any]:
    info = raw.get("info") if isinstance(raw.get("info"), dict) else {}
    metadata = info.get("metadata") if isinstance(info.get("metadata"), dict) else {}
    subscores = info.get("subscores") if isinstance(info.get("subscores"), dict) else {}
    if not subscores:
        nested = raw.get("subscores")
        if isinstance(nested, list):
            subscores = {
                str(item.get("name")): float(item.get("score", 0))
                for item in nested
                if isinstance(item, dict) and item.get("name")
            }
        elif isinstance(nested, dict):
            subscores = {str(k): float(v) for k, v in nested.items()}
    return {
        "reward": float(reward),
        "subscores": {str(k): float(v) for k, v in subscores.items()},
        "metadata": metadata,
    }


def final_record_from_view(view_payload: dict[str, Any] | None, fallback_budget: int) -> dict[str, Any]:
    if not view_payload:
        return {"budget_used": 0, "budget_remaining": fallback_budget, "testimony": []}
    testimony = view_payload.get("testimony")
    return {
        "budget_used": int(view_payload.get("budget_used") or 0),
        "budget_remaining": int(
            view_payload.get("budget_remaining")
            or max(fallback_budget - int(view_payload.get("budget_used") or 0), 0)
        ),
        "testimony": testimony if isinstance(testimony, list) else [],
    }
