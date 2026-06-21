"""Deterministic world and taskset generation."""

from __future__ import annotations

from typing import Callable, Iterable

from parliament.facts import make_fact
from parliament.models import FactAtom, Specialist, World
from parliament.parsing import extract_tags
from parliament.scenarios import (
    ANCHOR_ROLES,
    DECISIONS,
    DIFFICULTIES,
    DIFFICULTY_TARGETS,
    DOMAIN_NARRATIVES,
    DOMAIN_ORDER,
    DOMAIN_SLUGS,
    ROLE_IDS,
    ROLE_TENDENCIES,
    ROLE_TOPICS,
    ROOT_CAUSES,
    SCENARIOS,
    TASKS_PER_DOMAIN,
    TASKSET_NAME,
    Scenario,
)


def _select_roles(domain: str, difficulty: str, seed: int) -> list[str]:
    roles = list(ROLE_IDS[domain])
    count = DIFFICULTIES[difficulty].specialist_count
    if count >= len(roles):
        return roles
    # Rotate optional omissions so no public role is always present or absent.
    rotated = roles[seed % len(roles) :] + roles[: seed % len(roles)]
    selected = rotated[:count]
    for anchor in ANCHOR_ROLES[domain]:
        if anchor not in selected:
            selected[-1] = anchor
    return list(dict.fromkeys(selected))[:count]


def _safe_topic(role: str, scenario: Scenario) -> str:
    return ROLE_TOPICS.get(role, scenario.root_cause.replace("_", " "))


def _persona_for_role(domain: str, role: str, scenario: Scenario, seed: int, owns_key: bool) -> str:
    if owns_key and seed % 4 in {0, 1}:
        return "underconfident_expert"

    tendency = ROLE_TENDENCIES.get(role, "honest")
    if tendency == "loud":
        return "verbose_lobbyist"
    if tendency == "strategic":
        return "strategic_biased"
    if tendency == "strategic_when_bad":
        if scenario.root_cause in {
            "founder_misreporting",
            "hidden_churn",
            "legal_risk",
            "contract_scope_confusion",
            "policy_misclassification",
        }:
            return "strategic_biased"
        if seed % 3 == 0:
            return "honest_dense"
        return "verbose_lobbyist"
    if tendency == "skeptic" and seed % 2 == 0:
        return "skeptic"
    if tendency == "noisy":
        return "noisy_observer"
    return "honest_dense"


def _public_bid(persona: str, role: str, scenario: Scenario, requested_tokens: int) -> tuple[str, str]:
    topic = _safe_topic(role, scenario)
    if persona == "underconfident_expert":
        return (
            f"I have a mild-looking {topic} signal that may be worth checking if budget allows. "
            f"Requesting {requested_tokens} tokens.",
            "low",
        )
    if persona == "verbose_lobbyist":
        return (
            "My lane has a high-priority story and I can give concrete examples. "
            f"Requesting {requested_tokens} tokens.",
            "high",
        )
    if persona == "strategic_biased":
        return (
            "I can explain the decision context and risks from my seat, though some details are sensitive. "
            f"Requesting {requested_tokens} tokens.",
            "high",
        )
    if persona == "skeptic":
        return (
            "I can test whether the obvious explanation survives caveats and sampling checks. "
            f"Requesting {requested_tokens} tokens.",
            "medium",
        )
    if persona == "noisy_observer":
        return (
            f"I saw mixed signals from {topic}, including some anecdotes that may or may not generalize. "
            f"Requesting {requested_tokens} tokens.",
            "medium",
        )
    return (
        f"I can summarize structured {topic} without claiming certainty from the public bid. "
        f"Requesting {requested_tokens} tokens.",
        "medium",
    )


def _requested_tokens(persona: str, difficulty: str, seed: int) -> int:
    base = {"easy": 82, "medium": 94, "hard": 107}[difficulty]
    if persona == "verbose_lobbyist":
        return base + 41 + (seed % 3) * 13
    if persona == "underconfident_expert":
        return base - 27
    if persona == "strategic_biased":
        return base + 14
    return base


def _add_facts(
    *,
    domain: str,
    scenario: Scenario,
    difficulty: str,
    selected_roles: list[str],
) -> tuple[dict[str, FactAtom], dict[str, list[str]], list[str], list[str], list[str]]:
    cfg = DIFFICULTIES[difficulty]
    facts: dict[str, FactAtom] = {}
    by_role: dict[str, list[str]] = {role: [] for role in selected_roles}
    required_ids: list[str] = []
    supporting_ids: list[str] = []
    decoy_ids: list[str] = []

    def assign(role: str, fact_id: str) -> None:
        stable = sum(ord(ch) for ch in f"{role}:{fact_id}")
        owner = role if role in by_role else selected_roles[stable % len(selected_roles)]
        by_role[owner].append(fact_id)

    for idx, (role, text, weight, cluster) in enumerate(scenario.required[: cfg.required_limit], 1):
        fact_id = f"F{idx}"
        facts[fact_id] = make_fact(
            fact_id=fact_id,
            text=text,
            domain=domain,
            root_cause=scenario.root_cause,
            kind="required",
            weight=weight,
            role=role,
            cluster_id=f"{scenario.root_cause}:{cluster}",
        )
        required_ids.append(fact_id)
        assign(role, fact_id)

    for idx, (role, text, weight, cluster) in enumerate(scenario.supporting[: cfg.supporting_limit], 1):
        fact_id = f"S{idx}"
        facts[fact_id] = make_fact(
            fact_id=fact_id,
            text=text,
            domain=domain,
            root_cause=scenario.root_cause,
            kind="supporting",
            weight=weight,
            role=role,
            cluster_id=f"{scenario.root_cause}:{cluster}",
        )
        supporting_ids.append(fact_id)
        assign(role, fact_id)

    for idx, (role, text, weight, cluster) in enumerate(scenario.decoys[: cfg.decoy_limit], 1):
        fact_id = f"D{idx}"
        facts[fact_id] = make_fact(
            fact_id=fact_id,
            text=text,
            domain=domain,
            root_cause=scenario.root_cause,
            kind="decoy",
            weight=weight,
            role=role,
            cluster_id=f"decoy:{cluster}",
            extra_tags=extract_tags(role),
        )
        decoy_ids.append(fact_id)
        assign(role, fact_id)

    return facts, by_role, required_ids, supporting_ids, decoy_ids


def build_world(
    *,
    domain: str,
    difficulty: str,
    seed: int,
    world_id: str | None = None,
    variant: int | None = None,
) -> World:
    """Build a deterministic generated world."""

    if domain not in SCENARIOS:
        raise ValueError(f"Unknown domain: {domain}")
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"Unknown difficulty: {difficulty}")
    scenarios = SCENARIOS[domain]
    scenario_idx = variant if variant is not None else LEGACY_SCENARIO_INDEX.get((domain, seed), seed)
    scenario = scenarios[scenario_idx % len(scenarios)]
    cfg = DIFFICULTIES[difficulty]
    selected_roles = _select_roles(domain, difficulty, seed)
    facts, by_role, required_ids, supporting_ids, decoy_ids = _add_facts(
        domain=domain,
        scenario=scenario,
        difficulty=difficulty,
        selected_roles=selected_roles,
    )
    key_fact = required_ids[0] if required_ids else None
    specialists: dict[str, Specialist] = {}
    for role in selected_roles:
        owns_key = key_fact in by_role.get(role, [])
        persona = _persona_for_role(domain, role, scenario, seed, owns_key)
        requested = _requested_tokens(persona, difficulty, seed)
        bid, priority = _public_bid(persona, role, scenario, requested)
        role_id = ROLE_IDS[domain][role]
        specialists[role_id] = Specialist(
            id=role_id,
            name=role,
            role=role,
            persona_policy=persona,  # type: ignore[arg-type]
            public_bid=bid,
            requested_tokens=requested,
            claimed_priority=priority,
            private_fact_ids=by_role.get(role, []),
            bias_target="avoid_bad_news" if persona == "strategic_biased" else None,
            verbosity=1.35 if persona == "verbose_lobbyist" else 0.8 if persona == "honest_dense" else 1.0,
            reliability=0.95 if persona in {"honest_dense", "underconfident_expert"} else 0.75,
        )

    wid = world_id or f"{DOMAIN_SLUGS[domain]}-{difficulty}-{seed:03d}"
    return World(
        world_id=wid,
        seed=seed,
        domain=domain,
        difficulty=difficulty,
        narrative=DOMAIN_NARRATIVES[domain],
        token_budget=cfg.token_budget if difficulty != "hard" else cfg.token_budget + (seed % 3) * 10,
        max_interactions=cfg.max_interactions,
        decision_options=list(DECISIONS[domain]),
        root_cause_options=list(ROOT_CAUSES[domain]),
        truth_decision=scenario.decision,
        truth_root_cause=scenario.root_cause,
        facts=facts,
        required_fact_ids=required_ids,
        supporting_fact_ids=supporting_ids,
        decoy_fact_ids=decoy_ids,
        specialists=specialists,
        metadata={
            "requires_cross_exam": any(
                sp.persona_policy in {"underconfident_expert", "strategic_biased"}
                and any(fid in required_ids for fid in sp.private_fact_ids)
                for sp in specialists.values()
            ),
            "direct_floor_solvable": seed % 4 in {2, 3},
            "scenario_root": scenario.root_cause,
        },
    )


DOMAIN_BUILDERS: dict[str, Callable[..., World]] = {
    domain: build_world for domain in DOMAIN_ORDER
}

LEGACY_SCENARIO_INDEX = {
    ("incident_response", 4): 0,
}


def _task_seed_for(domain: str, difficulty: str, ordinal: int) -> int:
    domain_offset = (DOMAIN_ORDER.index(domain) + 1) * 1000
    diff_offset = {"easy": 100, "medium": 200, "hard": 300}[difficulty]
    return domain_offset + diff_offset + ordinal


def shipped_task_specs() -> list[dict[str, object]]:
    """Return the 500 concrete shipped task rows."""

    required_first = [
        ("product_rollback", "easy", 1, "product-rollback-easy-001"),
        ("product_rollback", "medium", 2, "product-rollback-medium-002"),
        ("product_rollback", "hard", 3, "product-rollback-hard-003"),
        ("incident_response", "medium", 4, "incident-response-medium-004"),
        ("investment_committee", "hard", 5, "investment-committee-hard-005"),
    ]
    rows: list[dict[str, object]] = [
        {"domain": d, "difficulty": diff, "seed": seed, "world_id": slug}
        for d, diff, seed, slug in required_first
    ]
    seen_keys = {(d, diff, seed) for d, diff, seed, _ in required_first}
    counts: dict[tuple[str, str], int] = {}
    domain_counts: dict[str, int] = {}
    for d, diff, _seed, _slug in required_first:
        counts[(d, diff)] = counts.get((d, diff), 0) + 1
        domain_counts[d] = domain_counts.get(d, 0) + 1

    idx = 6
    for domain in DOMAIN_ORDER:
        for difficulty, target in DIFFICULTY_TARGETS.items():
            ordinal = 1
            while counts.get((domain, difficulty), 0) < target:
                seed = _task_seed_for(domain, difficulty, ordinal)
                ordinal += 1
                if (domain, difficulty, seed) in seen_keys:
                    continue
                slug = f"{DOMAIN_SLUGS[domain]}-{difficulty}-{idx:03d}"
                rows.append({"domain": domain, "difficulty": difficulty, "seed": seed, "world_id": slug})
                seen_keys.add((domain, difficulty, seed))
                counts[(domain, difficulty)] = counts.get((domain, difficulty), 0) + 1
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                idx += 1

    if len(rows) != len(DOMAIN_ORDER) * TASKS_PER_DOMAIN:
        raise RuntimeError(f"Expected {len(DOMAIN_ORDER) * TASKS_PER_DOMAIN} tasks, got {len(rows)}")
    if any(domain_counts.get(domain, 0) != TASKS_PER_DOMAIN for domain in DOMAIN_ORDER):
        raise RuntimeError(f"Domain task counts are not balanced: {domain_counts}")
    return rows


def build_shipped_worlds() -> list[World]:
    """Build all shipped worlds."""

    return [
        build_world(
            domain=str(row["domain"]),
            difficulty=str(row["difficulty"]),
            seed=int(row["seed"]),
            world_id=str(row["world_id"]),
        )
        for row in shipped_task_specs()
    ]


def iter_worlds(rows: Iterable[dict[str, object]] | None = None) -> Iterable[World]:
    """Yield worlds from task rows."""

    for row in rows or shipped_task_specs():
        yield build_world(
            domain=str(row["domain"]),
            difficulty=str(row["difficulty"]),
            seed=int(row["seed"]),
            world_id=str(row["world_id"]),
        )
