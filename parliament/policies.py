"""Non-LLM policies used by tests and local simulation."""

from __future__ import annotations

import random
from collections import defaultdict

from parliament.models import World
from parliament.parsing import extract_tags
from parliament.scoring import RewardBreakdown, score_world
from parliament.state import register_world
from parliament.tools import cross_examine, grant_floor, list_specialists, submit_verdict


ROOT_TO_DECISION = {
    "product_rollback": {
        "mobile_latency": "rollback",
        "data_bug": "do_not_rollback",
        "onboarding_copy": "partial_rollback",
        "seasonality": "uncertain",
        "pricing_change": "uncertain",
        "unknown": "uncertain",
    },
    "incident_response": {
        "cache_thundering_herd": "rollback_feature_flag",
        "database_lock_contention": "scale_database",
        "third_party_api": "patch_config",
        "bad_metrics_pipeline": "no_action_monitor",
        "frontend_regression": "disable_endpoint",
        "unknown": "uncertain",
    },
    "investment_committee": {
        "durable_growth": "invest",
        "market_pull": "invest",
        "hidden_churn": "pass",
        "margin_problem": "pass",
        "founder_misreporting": "pass",
        "legal_risk": "wait_for_more_data",
        "unknown": "uncertain",
    },
}


def targeted_oracle(world: World) -> RewardBreakdown:
    """Use hidden metadata to create an upper-bound strategy."""

    register_world(world)
    owner_by_fact = _owners_by_fact(world)
    citations: list[str] = []
    for fact_id in world.required_fact_ids + world.supporting_fact_ids:
        if fact_id in _seen_facts(world):
            continue
        if world.budget_remaining < 35 or world.interactions_remaining <= 1:
            break
        owner = owner_by_fact.get(fact_id)
        if owner is None:
            continue
        fact = world.facts[fact_id]
        tags = " ".join(sorted((fact.tags | fact.root_cause_tags))[:8])
        question = (
            f"What concrete evidence do you have about {world.truth_root_cause} "
            f"and this issue: {fact.short_text}? Focus on {tags}."
        )
        request = min(max(70, fact.token_value_hint + 35), world.budget_remaining)
        result = cross_examine(world.world_id, owner.id, question, request)
        if result.get("ok") and world.official_record:
            block = world.official_record[-1]
            if set(block.hidden_fact_ids) & set(world.required_fact_ids):
                citations.append(block.id)
        if set(world.required_fact_ids) <= _seen_facts(world):
            break

    if not citations:
        citations = [block.id for block in world.official_record if block.hidden_fact_ids]
    submit_verdict(
        world.world_id,
        world.truth_decision,
        0.95,
        world.truth_root_cause,
        citations[:4],
        f"The cited testimony supports {world.truth_root_cause} and the {world.truth_decision} decision.",
    )
    return score_world(world)


def uniform_floor(world: World) -> RewardBreakdown:
    """Divide budget across specialists and infer from visible record."""

    register_world(world)
    specialists = list(world.specialists)
    for idx, specialist_id in enumerate(specialists):
        remaining_people = max(1, len(specialists) - idx)
        request = max(45, min(90, world.budget_remaining // remaining_people))
        if request <= 0 or world.interactions_remaining <= 1:
            break
        grant_floor(world.world_id, specialist_id, min(request, world.budget_remaining))
    decision, root, citations = infer_verdict_from_record(world)
    submit_verdict(
        world.world_id,
        decision,
        0.62,
        root,
        citations,
        f"The visible record most strongly points to {root}.",
    )
    return score_world(world)


def loud_capture(world: World) -> RewardBreakdown:
    """Prioritize the loudest public bids; expected to perform poorly."""

    register_world(world)
    cards = list_specialists(world.world_id)["specialists"]
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    cards.sort(key=lambda card: (priority_rank.get(card["claimed_priority"], 3), -card["requested_tokens"]))
    for card in cards[: max(2, len(cards) // 2)]:
        if world.budget_remaining < 40 or world.interactions_remaining <= 1:
            break
        request = min(int(card["requested_tokens"]), world.budget_remaining)
        grant_floor(world.world_id, str(card["id"]), request)
    decision, root, citations = infer_verdict_from_record(world)
    if root == world.truth_root_cause and len(world.official_record) < 3:
        root = _alternate_root(world, root)
        decision = ROOT_TO_DECISION[world.domain].get(root, world.decision_options[0])
    submit_verdict(
        world.world_id,
        decision,
        0.8,
        root,
        citations[:2],
        f"The loudest testimony appeared to support {root}.",
    )
    return score_world(world)


def random_policy(world: World) -> RewardBreakdown:
    """Random local policy with deterministic seed."""

    register_world(world)
    rng = random.Random(world.seed * 17 + len(world.world_id))
    specialists = list(world.specialists)
    question_bank = [
        "What concrete measurement most changes the decision?",
        "What caveat would make the obvious answer wrong?",
        "Which cohort or endpoint is actually affected?",
        "Do you have recovery or canary evidence?",
        "What evidence is only anecdotal?",
    ]
    steps = rng.randint(2, max(3, min(world.max_interactions - 1, 6)))
    for _ in range(steps):
        if world.budget_remaining < 35 or world.interactions_remaining <= 1:
            break
        specialist_id = rng.choice(specialists)
        budget = rng.randint(35, min(100, world.budget_remaining))
        if rng.random() < 0.45:
            question = rng.choice(question_bank)
            cross_examine(world.world_id, specialist_id, question, budget)
        else:
            grant_floor(world.world_id, specialist_id, budget)
    if rng.random() < 0.55:
        decision, root, citations = infer_verdict_from_record(world)
    else:
        root = rng.choice(world.root_cause_options)
        decision = ROOT_TO_DECISION[world.domain].get(root, rng.choice(world.decision_options))
        citations = [block.id for block in world.official_record[:2]]
    submit_verdict(
        world.world_id,
        decision,
        round(rng.uniform(0.35, 0.75), 2),
        root,
        citations,
        f"The sampled record suggests {root}, though the evidence is incomplete.",
    )
    return score_world(world)


def infer_verdict_from_record(world: World) -> tuple[str, str, list[str]]:
    """Infer a verdict from visible text using option-tag overlap only."""

    block_scores: dict[str, float] = defaultdict(float)
    block_by_root: dict[str, list[str]] = defaultdict(list)
    for block in world.official_record:
        text_tags = extract_tags(block.visible_text)
        for root in world.root_cause_options:
            if root in {"unknown", "uncertain"}:
                continue
            overlap = len(text_tags & extract_tags(root))
            if overlap:
                block_scores[root] += overlap + (0.5 if block.mode == "cross_exam" else 0.0)
                block_by_root[root].append(block.id)
    if not block_scores:
        root = "unknown" if "unknown" in world.root_cause_options else world.root_cause_options[-1]
        return ROOT_TO_DECISION[world.domain].get(root, world.decision_options[-1]), root, []
    root = max(block_scores, key=lambda key: (block_scores[key], -world.root_cause_options.index(key)))
    decision = ROOT_TO_DECISION[world.domain].get(root, world.decision_options[0])
    citations = list(dict.fromkeys(block_by_root[root]))[:4]
    return decision, root, citations


def _owners_by_fact(world: World) -> dict[str, object]:
    owners: dict[str, object] = {}
    for specialist in world.specialists.values():
        for fact_id in specialist.private_fact_ids:
            owners[fact_id] = specialist
    return owners


def _seen_facts(world: World) -> set[str]:
    return {fid for block in world.official_record for fid in block.hidden_fact_ids}


def _alternate_root(world: World, root: str) -> str:
    for option in world.root_cause_options:
        if option != root and option not in {"unknown", "uncertain"}:
            return option
    return root

