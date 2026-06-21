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

tasks: list[Any] = []
if env is not None:
    for row in TASK_ROWS:
        task = context_parliament(**row)
        task.slug = str(row["world_id"])
        tasks.append(task)

try:
    taskset = Taskset(TASKSET_NAME, tasks) if Taskset is not None else tasks
except TypeError:
    taskset = tasks
