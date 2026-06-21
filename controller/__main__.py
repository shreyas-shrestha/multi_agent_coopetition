"""Run the MCP controller directly for local debugging."""

from __future__ import annotations

import asyncio

from controller.tools import mcp


async def main() -> None:
    if mcp is None:
        raise RuntimeError("fastmcp is not installed")
    await mcp.run_async(transport="http", host="127.0.0.1", port=8765, show_banner=True)


if __name__ == "__main__":
    asyncio.run(main())

