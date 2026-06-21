from __future__ import annotations

from statistics import mean

from parliament.policies import loud_capture, random_policy, targeted_oracle, uniform_floor
from parliament.state import reset_worlds
from parliament.worlds import build_world, shipped_task_specs


def _run(policy, row):
    reset_worlds()
    world = build_world(
        domain=str(row["domain"]),
        difficulty=str(row["difficulty"]),
        seed=int(row["seed"]),
        world_id=str(row["world_id"]),
    )
    return policy(world)


def test_strategy_reward_separation() -> None:
    rows = shipped_task_specs()
    scores = {}
    for name, policy in {
        "loud_capture": loud_capture,
        "uniform_floor": uniform_floor,
        "targeted_oracle": targeted_oracle,
        "random": random_policy,
    }.items():
        scores[name] = [float(_run(policy, row).reward) for row in rows]

    means = {name: mean(values) for name, values in scores.items()}
    assert means["targeted_oracle"] > 0.80
    assert means["loud_capture"] < 0.45
    assert means["targeted_oracle"] > means["uniform_floor"] > means["loud_capture"]
    assert means["targeted_oracle"] > means["random"]

