"""HUD v6 environment for Context Window Parliament.

The current blank scaffold keeps the Environment and tool capability in env.py,
while tasks.py instantiates concrete task rows. The core parliament logic lives
in the parliament package so tests and simulations can run without HUD.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
from typing import Any

from controller.tools import mcp
from parliament.schemas import task_prompt
from parliament.scoring import score_world
from parliament.state import register_world
from parliament.worlds import build_world

try:
    from hud import Environment  # type: ignore
    from hud.capabilities import Capability  # type: ignore
except Exception:  # pragma: no cover - local tests can run without HUD
    Environment = None  # type: ignore[assignment]
    Capability = None  # type: ignore[assignment]

env = Environment(name="context-window-parliament") if Environment is not None else None

_MCP_PORT: int = 0
_MCP_SERVER_TASK: asyncio.Task[Any] | None = None


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _listening(host: str, port: int, timeout: float = 10.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            socket.create_connection((host, port), timeout=0.2).close()
            return
        except OSError:
            await asyncio.sleep(0.1)
    raise RuntimeError(f"parliament MCP server never came up on {host}:{port}")


if env is not None and mcp is not None and Capability is not None:

    @env.initialize
    async def _up() -> None:
        global _MCP_PORT, _MCP_SERVER_TASK
        if _MCP_SERVER_TASK is None:
            _MCP_PORT = _free_port()
            _MCP_SERVER_TASK = asyncio.create_task(
                mcp.run_async(
                    transport="http",
                    host="127.0.0.1",
                    port=_MCP_PORT,
                    show_banner=False,
                )
            )
            await _listening("127.0.0.1", _MCP_PORT)
        env.add_capability(
            Capability.mcp(
                name="parliament-tools",
                url=f"http://127.0.0.1:{_MCP_PORT}/mcp",
            )
        )

    @env.shutdown
    async def _down() -> None:
        global _MCP_SERVER_TASK
        if _MCP_SERVER_TASK is not None:
            _MCP_SERVER_TASK.cancel()
            with contextlib.suppress(BaseException):
                await _MCP_SERVER_TASK
            _MCP_SERVER_TASK = None

    @env.template(id="context_parliament")
    async def context_parliament(
        world_id: str,
        domain: str,
        difficulty: str,
        seed: int,
    ) -> Any:
        """Run one context-window parliament hearing."""

        world = build_world(
            world_id=world_id,
            domain=domain,
            difficulty=difficulty,
            seed=seed,
        )
        register_world(world)
        answer = yield task_prompt(world)
        yield score_world(world, answer).to_hud_result()
else:

    async def context_parliament(
        world_id: str,
        domain: str,
        difficulty: str,
        seed: int,
    ) -> Any:
        """Placeholder when HUD is not installed."""

        raise RuntimeError("hud-python is required to run HUD tasks")

