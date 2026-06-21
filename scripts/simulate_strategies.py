from __future__ import annotations

import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parliament.policies import loud_capture, random_policy, targeted_oracle, uniform_floor
from parliament.state import reset_worlds
from parliament.worlds import build_world, shipped_task_specs


POLICIES = {
    "loud_capture": loud_capture,
    "uniform_floor": uniform_floor,
    "targeted_oracle": targeted_oracle,
    "random": random_policy,
}


def run_policy(policy, row):
    reset_worlds()
    world = build_world(
        domain=str(row["domain"]),
        difficulty=str(row["difficulty"]),
        seed=int(row["seed"]),
        world_id=str(row["world_id"]),
    )
    return policy(world)


def main() -> None:
    rows = shipped_task_specs()
    print(
        "Strategy          Mean Reward   Decision   RootCause   Recall   Precision   "
        "Redundancy   Citation   Tokens"
    )
    for name, policy in POLICIES.items():
        results = [run_policy(policy, row) for row in rows]
        print(
            f"{name:<17} "
            f"{mean(result.reward for result in results):>10.3f}   "
            f"{mean(result.subscores['gated_decision_accuracy'] for result in results):>8.3f}   "
            f"{mean(result.subscores['gated_root_cause_accuracy'] for result in results):>9.3f}   "
            f"{mean(result.subscores['evidence_recall'] for result in results):>6.3f}   "
            f"{mean(result.subscores['evidence_precision'] for result in results):>9.3f}   "
            f"{mean(result.subscores['non_redundancy'] for result in results):>10.3f}   "
            f"{mean(result.subscores['citation_quality'] for result in results):>8.3f}   "
            f"{mean(result.metadata['budget_used'] for result in results):>6.1f}"
        )


if __name__ == "__main__":
    main()
