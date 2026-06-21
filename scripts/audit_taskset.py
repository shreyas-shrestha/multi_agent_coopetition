from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parliament.policies import loud_capture, random_policy, targeted_oracle, uniform_floor
from parliament.scenarios import SCENARIOS
from parliament.scoring import detect_public_leakage
from parliament.state import reset_worlds
from parliament.worlds import build_world, shipped_task_specs


EXPECTED_TASKS = 500
EXPECTED_DOMAIN_COUNT = 50
EXPECTED_DIFFICULTIES = {"easy": 170, "medium": 170, "hard": 160}
STRATEGY_TARGETS = {
    "targeted_oracle_min": 0.82,
    "loud_capture_max": 0.45,
    "uniform_floor_margin_over_loud": 0.15,
}
GENERIC_BANNED_PHRASES = {
    "urgent issue",
    "important signal",
    "some metric",
    "various problems",
}


def _world_for(row: dict[str, object]):
    return build_world(
        domain=str(row["domain"]),
        difficulty=str(row["difficulty"]),
        seed=int(row["seed"]),
        world_id=str(row["world_id"]),
    )


def _run_policy(policy, row: dict[str, object]):
    reset_worlds()
    return policy(_world_for(row))


def _failures_for_worlds(rows: list[dict[str, object]]) -> list[str]:
    failures: list[str] = []
    worlds = [_world_for(row) for row in rows]
    domain_counts = Counter(world.domain for world in worlds)
    difficulty_counts = Counter(world.difficulty for world in worlds)

    if len(rows) != EXPECTED_TASKS:
        failures.append(f"expected {EXPECTED_TASKS} task rows, found {len(rows)}")
    for domain, count in domain_counts.items():
        if count != EXPECTED_DOMAIN_COUNT:
            failures.append(f"domain {domain} has {count} rows, expected {EXPECTED_DOMAIN_COUNT}")
    if difficulty_counts != EXPECTED_DIFFICULTIES:
        failures.append(f"difficulty counts {dict(difficulty_counts)} != {EXPECTED_DIFFICULTIES}")

    by_domain: dict[str, list] = defaultdict(list)
    for world in worlds:
        by_domain[world.domain].append(world)
        if detect_public_leakage(world):
            failures.append(f"public leakage detected in {world.world_id}")
        if not world.required_fact_ids:
            failures.append(f"{world.world_id} has no required facts")
        for fact in world.facts.values():
            lowered = fact.text.lower()
            if any(phrase in lowered for phrase in GENERIC_BANNED_PHRASES):
                failures.append(f"generic prose phrase in {world.world_id}: {fact.text}")
        owners = {fid for sp in world.specialists.values() for fid in sp.private_fact_ids}
        missing = set(world.facts) - owners
        if missing:
            failures.append(f"{world.world_id} has unowned fact ids {sorted(missing)}")

    template_texts: Counter[str] = Counter()
    for scenarios in SCENARIOS.values():
        for scenario in scenarios:
            for _role, text, _weight, _cluster in [
                *scenario.required,
                *scenario.supporting,
                *scenario.decoys,
            ]:
                template_texts[text] += 1
    duplicates = [text for text, count in template_texts.items() if count > 1]
    if duplicates:
        failures.append(f"duplicate fact text count {len(duplicates)}")

    for domain, domain_worlds in by_domain.items():
        decisions = {world.truth_decision for world in domain_worlds}
        roots = {world.truth_root_cause for world in domain_worlds}
        if len(decisions) < 3:
            failures.append(f"domain {domain} has only {len(decisions)} truth decisions")
        if len(roots) < 6:
            failures.append(f"domain {domain} has only {len(roots)} root causes")
        quiet_key = 0
        loud_decoy = 0
        cross_exam = 0
        floor_solvable = 0
        for world in domain_worlds:
            if world.metadata.get("requires_cross_exam"):
                cross_exam += 1
            if world.metadata.get("direct_floor_solvable"):
                floor_solvable += 1
            for specialist in world.specialists.values():
                owns_required = bool(set(specialist.private_fact_ids) & set(world.required_fact_ids))
                owns_decoy_only = (
                    bool(set(specialist.private_fact_ids) & set(world.decoy_fact_ids)) and not owns_required
                )
                if specialist.persona_policy == "underconfident_expert" and owns_required:
                    quiet_key += 1
                if specialist.persona_policy == "verbose_lobbyist" and owns_decoy_only:
                    loud_decoy += 1
        if quiet_key < 8:
            failures.append(f"domain {domain} has weak quiet-key coverage: {quiet_key}")
        if loud_decoy < 8:
            failures.append(f"domain {domain} has weak loud-decoy coverage: {loud_decoy}")
        if cross_exam < 12:
            failures.append(f"domain {domain} has weak cross-exam coverage: {cross_exam}")
        if floor_solvable < 12:
            failures.append(f"domain {domain} has weak floor-solvable coverage: {floor_solvable}")

    return failures


def _strategy_summary(rows: list[dict[str, object]]) -> tuple[dict[str, list[float]], list[str]]:
    failures: list[str] = []
    policy_map = {
        "loud_capture": loud_capture,
        "uniform_floor": uniform_floor,
        "targeted_oracle": targeted_oracle,
        "random": random_policy,
    }
    scores = {
        name: [float(_run_policy(policy, row).reward) for row in rows]
        for name, policy in policy_map.items()
    }
    means = {name: mean(values) for name, values in scores.items()}
    if means["targeted_oracle"] < STRATEGY_TARGETS["targeted_oracle_min"]:
        failures.append(f"targeted_oracle mean {means['targeted_oracle']:.3f} below target")
    if means["loud_capture"] > STRATEGY_TARGETS["loud_capture_max"]:
        failures.append(f"loud_capture mean {means['loud_capture']:.3f} above target")
    if means["uniform_floor"] <= means["loud_capture"] + STRATEGY_TARGETS["uniform_floor_margin_over_loud"]:
        failures.append("uniform_floor does not clear loud_capture by required margin")
    if pstdev(scores["random"]) <= 0.05:
        failures.append("random policy reward spread is degenerate")
    return scores, failures


def main() -> int:
    rows = shipped_task_specs()
    failures = _failures_for_worlds(rows)
    scores, strategy_failures = _strategy_summary(rows)
    failures.extend(strategy_failures)

    summary = {
        "task_count": len(rows),
        "domains": Counter(str(row["domain"]) for row in rows),
        "difficulties": Counter(str(row["difficulty"]) for row in rows),
        "strategy_means": {name: round(mean(values), 3) for name, values in scores.items()},
        "strategy_stddev": {name: round(pstdev(values), 3) for name, values in scores.items()},
        "failures": failures,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
