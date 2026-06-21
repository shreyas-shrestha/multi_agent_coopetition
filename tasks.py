"""Concrete task rows for the Context Window Parliament HUD environment."""

from __future__ import annotations

from typing import Any

from env import context_parliament, env  # noqa: F401
from parliament.worlds import TASKSET_NAME, shipped_task_specs

TASK_ROWS = shipped_task_specs()

try:
    from hud import Taskset  # type: ignore
except Exception:  # pragma: no cover - optional in local unit tests
    Taskset = None  # type: ignore[assignment]

def _build_tasks() -> list[Any]:
    built: list[Any] = []
    if env is None:
        return built
    for row in TASK_ROWS:
        item = context_parliament(**row)
        item.slug = str(row["world_id"])
        built.append(item)
    return built


_built_tasks = _build_tasks()

try:
    taskset = Taskset(TASKSET_NAME, _built_tasks) if Taskset is not None else _built_tasks
except TypeError:
    taskset = _built_tasks
