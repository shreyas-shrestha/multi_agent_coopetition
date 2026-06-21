#!/usr/bin/env python3
"""Time a live hearing SSE stream and print per-event gaps."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get(
    "ORCHESTRATOR_URL",
    "https://shreyas-shrestha--context-window-parliament-orchestrator-web.modal.run",
).rstrip("/")
WORLD = os.environ.get("WORLD_ID", "incident-response-medium-004")


def timed_get(path: str, label: str) -> float:
    t0 = time.perf_counter()
    with urllib.request.urlopen(f"{BASE}{path}", timeout=120) as response:
        payload = response.read()
    elapsed = time.perf_counter() - t0
    print(f"{label}: {elapsed:.2f}s ({len(payload)} bytes)")
    if path == "/health":
        print(" ", payload.decode("utf-8", errors="replace"))
    return elapsed


def stream_hearing() -> int:
    url = f"{BASE}/api/hearing/stream?world_id={WORLD}&max_steps=30"
    print(f"\nStreaming {url}")
    t0 = time.perf_counter()
    last = t0
    events = 0
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    try:
        with urllib.request.urlopen(req, timeout=900) as response:
            buffer = b""
            while True:
                chunk = response.read(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n\n" in buffer:
                    block, buffer = buffer.split(b"\n\n", 1)
                    text = block.decode("utf-8", errors="replace")
                    if not text.strip():
                        continue
                    now = time.perf_counter()
                    gap = now - last
                    last = now
                    event_type = None
                    data = None
                    for line in text.splitlines():
                        if line.startswith("event:"):
                            event_type = line.split(":", 1)[1].strip()
                        elif line.startswith("data:"):
                            data = line.split(":", 1)[1].strip()
                    if event_type == "meta":
                        print(f"  meta at {now - t0:.2f}s")
                        continue
                    if not data:
                        continue
                    payload = json.loads(data)
                    if event_type == "hearing_error":
                        print(f"  ERROR at {now - t0:.2f}s: {payload.get('message')}")
                        return 1
                    if event_type == "complete":
                        reward = payload.get("reward", {}).get("reward")
                        elapsed = payload.get("meta", {}).get("elapsed_s")
                        print(
                            f"  complete at {now - t0:.2f}s "
                            f"reward={reward} backend_elapsed={elapsed}s"
                        )
                        return 0
                    tool = payload.get("tool") or payload.get("type")
                    idx = payload.get("index")
                    backend_elapsed = payload.get("elapsed_s")
                    events += 1
                    extra = f" backend={backend_elapsed}s" if backend_elapsed else ""
                    print(f"  +{gap:.2f}s  t={now - t0:6.2f}s  #{idx} {tool}{extra}")
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"stream failed after {time.perf_counter() - t0:.2f}s: {exc}")
        return 1
    print(f"stream ended without complete ({events} events)")
    return 1


def main() -> int:
    print(f"Orchestrator: {BASE}")
    timed_get("/health", "health")
    timed_get("/health", "health (warm)")
    timed_get(f"/api/worlds/{WORLD}/preview", "preview")
    return stream_hearing()


if __name__ == "__main__":
    raise SystemExit(main())
