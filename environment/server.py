"""Compatibility entrypoint for serving the HUD environment."""

from __future__ import annotations

import asyncio

from tasks import env


async def main() -> None:
    if env is None:
        raise RuntimeError("hud-python is not installed")
    await env.serve()


if __name__ == "__main__":
    asyncio.run(main())

