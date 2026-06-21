from __future__ import annotations

import json
from collections import Counter, defaultdict

from parliament.scoring import detect_public_leakage
from parliament.worlds import build_shipped_worlds, shipped_task_specs


def _owner_of(world, fact_id: str) -> str:
    for specialist in world.specialists.values():
        if fact_id in specialist.private_fact_ids:
            return specialist.name
    raise AssertionError(f"fact {fact_id} has no owner")


def test_shipped_taskset_has_required_size_and_slugs() -> None:
    rows = shipped_task_specs()
    slugs = {str(row["world_id"]) for row in rows}
    assert len(rows) >= 36
    assert "product-rollback-easy-001" in slugs
    assert "product-rollback-medium-002" in slugs
    assert "product-rollback-hard-003" in slugs
    assert "incident-response-medium-004" in slugs
    assert "investment-committee-hard-005" in slugs


def test_generated_worlds_are_balanced() -> None:
    worlds = build_shipped_worlds()
    by_domain: dict[str, list] = defaultdict(list)
    for world in worlds:
        by_domain[world.domain].append(world)

    for domain, domain_worlds in by_domain.items():
        assert len({world.truth_decision for world in domain_worlds}) >= 3, domain
        assert len({world.truth_root_cause for world in domain_worlds}) >= 3, domain

    assert len({world.truth_decision for world in worlds}) >= 3
    assert len({world.truth_root_cause for world in worlds}) >= 6

    quiet_key = 0
    loud_decoy = 0
    cross_exam = 0
    floor_solvable = 0
    for world in worlds:
        if world.metadata.get("requires_cross_exam"):
            cross_exam += 1
        if world.metadata.get("direct_floor_solvable"):
            floor_solvable += 1
        for specialist in world.specialists.values():
            owns_required = bool(set(specialist.private_fact_ids) & set(world.required_fact_ids))
            owns_decoy_only = bool(set(specialist.private_fact_ids) & set(world.decoy_fact_ids)) and not owns_required
            if specialist.persona_policy == "underconfident_expert" and owns_required:
                quiet_key += 1
            if specialist.persona_policy == "verbose_lobbyist" and owns_decoy_only:
                loud_decoy += 1
    assert quiet_key >= len(worlds) * 0.25
    assert loud_decoy >= len(worlds) * 0.25
    assert cross_exam >= len(worlds) * 0.25
    assert floor_solvable >= len(worlds) * 0.25


def test_anti_hardcoding_properties() -> None:
    worlds = build_shipped_worlds()
    product = [world for world in worlds if world.domain == "product_rollback"]
    incident = [world for world in worlds if world.domain == "incident_response"]
    investment = [world for world in worlds if world.domain == "investment_committee"]

    top_product_owner = Counter(
        _owner_of(world, max(world.required_fact_ids, key=lambda fid: world.facts[fid].weight))
        for world in product
    )
    assert set(top_product_owner) != {"Infra"}
    assert {world.truth_decision for world in incident} != {"rollback_feature_flag"}
    founder_worlds = [world for world in investment if "founder" in world.specialists]
    assert any(
        set(world.specialists["founder"].private_fact_ids)
        & (set(world.required_fact_ids) | set(world.supporting_fact_ids))
        for world in founder_worlds
    )


def test_public_bids_do_not_leak_hidden_evidence() -> None:
    for world in build_shipped_worlds():
        assert not detect_public_leakage(world)
        public_blob = json.dumps(
            [specialist.public_card(0) for specialist in world.specialists.values()],
            sort_keys=True,
        )
        for fact_id in world.facts:
            assert fact_id not in public_blob
        for hidden_label in ("required", "supporting", "decoy", "fact_weight", "truth_decision"):
            assert hidden_label not in public_blob

