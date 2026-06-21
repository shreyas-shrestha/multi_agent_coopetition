"""Modal web orchestrator for live Context Window Parliament hearings."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import modal

ROOT = Path(__file__).resolve().parent
REMOTE_ROOT = "/root/context-window-parliament"
HUD_SECRET = "context-window-parliament-hud"
TRAINED_MODEL = "parliament-qwen36-35b-clean"

app = modal.App("context-window-parliament-orchestrator")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "fastmcp>=2.0",
        "hud-python==0.6.6",
        "fastapi[standard]==0.115.6",
        "anthropic>=0.40",
    )
    .add_local_dir(ROOT / "parliament", f"{REMOTE_ROOT}/parliament", copy=True)
    .add_local_dir(ROOT / "controller", f"{REMOTE_ROOT}/controller", copy=True)
    .add_local_dir(ROOT / "environment", f"{REMOTE_ROOT}/environment", copy=True)
    .add_local_file(ROOT / "env.py", f"{REMOTE_ROOT}/env.py", copy=True)
    .add_local_file(ROOT / "tasks.py", f"{REMOTE_ROOT}/tasks.py", copy=True)
    .add_local_file(ROOT / ".hud_eval.toml", f"{REMOTE_ROOT}/.hud_eval.toml", copy=True)
    .workdir(REMOTE_ROOT)
)


def _configure_runtime() -> None:
    os.environ.setdefault("PARLIAMENT_SPECIALIST_BACKEND", "llm")
    os.environ.setdefault("PARLIAMENT_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name(HUD_SECRET, required_keys=["HUD_API_KEY", "ANTHROPIC_API_KEY"])],
    timeout=60,
)
def secret_check() -> dict[str, bool]:
    return {
        "hud_configured": bool(os.environ.get("HUD_API_KEY")),
        "anthropic_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


@app.function(
    image=image,
    secrets=[modal.Secret.from_name(HUD_SECRET, required_keys=["HUD_API_KEY", "ANTHROPIC_API_KEY"])],
    timeout=900,
    scaledown_window=3600,
    min_containers=1,
    max_containers=4,
)
@modal.concurrent(max_inputs=8)
@modal.asgi_app()
def web() -> Any:
    import asyncio

    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse

    from parliament.live_runner import run_live_hearing
    from parliament.live_timeline import SPEAKER_MODEL, make_preview

    _configure_runtime()

    api = FastAPI(title="Context Window Parliament Orchestrator")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.get("/health")
    async def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "speaker_model": TRAINED_MODEL,
            "specialist_model": os.environ.get("PARLIAMENT_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            "hud_configured": bool(os.environ.get("HUD_API_KEY")),
            "anthropic_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
        }

    @api.get("/api/worlds/{world_id}/preview")
    async def preview(world_id: str) -> JSONResponse:
        try:
            return JSONResponse(make_preview(world_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @api.get("/api/hearing/stream")
    async def hearing_stream(
        world_id: str = Query(..., min_length=1),
        max_steps: int = Query(100, ge=10, le=150),
    ) -> StreamingResponse:
        try:
            make_preview(world_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        async def emit(event: dict[str, Any]) -> None:
            await queue.put(event)

        async def runner() -> None:
            try:
                await run_live_hearing(world_id, emit, max_steps=max_steps)
            except Exception as exc:  # noqa: BLE001 - surface to client stream
                await queue.put({"type": "hearing_error", "message": str(exc)})
            finally:
                await queue.put(None)

        asyncio.create_task(runner())

        async def event_source():
            yield f"event: meta\ndata: {json.dumps({'speaker_model': SPEAKER_MODEL, 'world_id': world_id})}\n\n"
            yield f"event: ping\ndata: {json.dumps({'status': 'started'})}\n\n"
            await asyncio.sleep(0)
            while True:
                item = await queue.get()
                if item is None:
                    break
                raw_type = str(item.get("type", "timeline"))
                if raw_type == "complete":
                    sse_type = "complete"
                elif raw_type == "hearing_error":
                    sse_type = "hearing_error"
                else:
                    sse_type = "timeline"
                yield f"event: {sse_type}\ndata: {json.dumps(item)}\n\n"

        return StreamingResponse(
            event_source(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return api
