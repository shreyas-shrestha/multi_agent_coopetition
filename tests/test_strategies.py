from __future__ import annotations

from collections import defaultdict
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
    assert means["targeted_oracle"] >= 0.82
    assert means["loud_capture"] < 0.45
    assert means["uniform_floor"] > means["loud_capture"] + 0.15
    assert means["targeted_oracle"] > means["uniform_floor"] > means["loud_capture"]
    assert means["targeted_oracle"] > means["random"]


def test_strategy_reward_separation_by_domain_and_difficulty() -> None:
    rows = shipped_task_specs()
    targeted_by_domain: dict[str, list[float]] = defaultdict(list)
    loud_by_domain: dict[str, list[float]] = defaultdict(list)
    targeted_by_difficulty: dict[str, list[float]] = defaultdict(list)
    loud_by_difficulty: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        targeted = float(_run(targeted_oracle, row).reward)
        loud = float(_run(loud_capture, row).reward)
        targeted_by_domain[str(row["domain"])].append(targeted)
        loud_by_domain[str(row["domain"])].append(loud)
        targeted_by_difficulty[str(row["difficulty"])].append(targeted)
        loud_by_difficulty[str(row["difficulty"])].append(loud)

    for domain in targeted_by_domain:
        assert mean(targeted_by_domain[domain]) >= 0.78, domain
        assert mean(loud_by_domain[domain]) <= 0.52, domain
    for difficulty in targeted_by_difficulty:
        assert mean(targeted_by_difficulty[difficulty]) >= 0.78, difficulty
        assert mean(loud_by_difficulty[difficulty]) <= 0.52, difficulty
