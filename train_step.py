"""Run one GRPO step on traces from a HUD eval job."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys

from hud import TrainingClient

DEFAULT_JOB_ID = "3fb30532-aad9-463b-878f-7527bd1950a2"
MODEL = "parliament-qwen4b-hackathon"
GROUP_SIZE = 8
LR = 1e-5


def fetch_trace_ids(job_id: str, *, limit: int = 500) -> list[str]:
    out = subprocess.check_output(
        ["hud", "jobs", "--json", "--limit", str(limit), job_id],
        text=True,
    )
    items = json.loads(out)
    return [
        t["id"]
        for t in items
        if t.get("id") and t.get("status") == "completed" and not t.get("error")
    ]


async def train(
    job_id: str,
    *,
    group_size: int,
    learning_rate: float,
    max_groups: int | None,
) -> None:
    trace_ids = fetch_trace_ids(job_id)
    if not trace_ids:
        raise SystemExit(f"No traces found for job {job_id}")

    n = (len(trace_ids) // group_size) * group_size
    if n == 0:
        raise SystemExit(
            f"Need at least {group_size} traces for group_size={group_size}; "
            f"job {job_id} has {len(trace_ids)}"
        )

    trace_ids = trace_ids[:n]
    if max_groups is not None:
        cap = max_groups * group_size
        trace_ids = trace_ids[:cap]
        n = len(trace_ids)
    dropped = len(fetch_trace_ids(job_id)) - n
    print(f"Job {job_id}: training on {n} traces ({n // group_size} groups)", flush=True)
    if dropped:
        print(f"Dropping {dropped} traces that do not fill a complete group", flush=True)

    client = TrainingClient(MODEL)
    result = await client.step(
        trace_ids,
        learning_rate=learning_rate,
        group_size=group_size,
    )
    print("Done.", flush=True)
    for field in ("checkpoint_id", "checkpoint_name", "mean_reward", "loss"):
        value = getattr(result, field, None)
        if value is not None:
            print(f"{field}: {value}", flush=True)
    if not any(getattr(result, field, None) for field in ("checkpoint_id", "checkpoint_name")):
        print(result, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="GRPO train step from HUD eval traces")
    parser.add_argument(
        "job_id",
        nargs="?",
        default=DEFAULT_JOB_ID,
        help="HUD eval job id containing trainable traces",
    )
    parser.add_argument("--group-size", type=int, default=GROUP_SIZE)
    parser.add_argument("--learning-rate", type=float, default=LR)
    parser.add_argument(
        "--max-groups",
        type=int,
        default=None,
        help="Cap training to this many GRPO groups (default: all complete groups)",
    )
    args = parser.parse_args()
    asyncio.run(
        train(
            args.job_id,
            group_size=args.group_size,
            learning_rate=args.learning_rate,
            max_groups=args.max_groups,
        )
    )


if __name__ == "__main__":
    main()
