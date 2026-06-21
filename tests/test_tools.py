from __future__ import annotations

from copy import deepcopy

from parliament.state import register_world, reset_worlds
from parliament.tools import cross_examine, grant_floor, submit_verdict, view_record
from parliament.worlds import build_shipped_worlds, build_world


def _register(world):
    reset_worlds()
    return register_world(world)


def _find_cross_exam_world():
    for world in build_shipped_worlds():
        for specialist in world.specialists.values():
            if (
                specialist.persona_policy in {"underconfident_expert", "strategic_biased"}
                and set(specialist.private_fact_ids) & set(world.required_fact_ids)
            ):
                return world, specialist.id
    raise AssertionError("no cross-exam world found")


def test_budget_enforced_and_denied_call_does_not_mutate_record() -> None:
    world = _register(build_world(domain="incident_response", difficulty="easy", seed=11, world_id="budget"))
    first = grant_floor(world.world_id, next(iter(world.specialists)), 80)
    assert first["ok"]
    before_len = len(world.official_record)
    before_budget = world.budget_used
    denied = cross_examine(
        world.world_id,
        next(iter(world.specialists)),
        "What exact metric proves the root cause?",
        world.budget_remaining + 1,
    )
    assert not denied["ok"]
    assert len(world.official_record) == before_len
    assert world.budget_used == before_budget


def test_multi_turn_stateful_and_deterministic() -> None:
    world_a = _register(build_world(domain="product_rollback", difficulty="medium", seed=2, world_id="det-a"))
    specialist_id = "metrics"
    result_a1 = grant_floor(world_a.world_id, specialist_id, 80)
    result_a2 = cross_examine(
        world_a.world_id,
        specialist_id,
        "What concrete cohort evidence mentions mobile copy or completion?",
        80,
    )

    world_b = _register(build_world(domain="product_rollback", difficulty="medium", seed=2, world_id="det-b"))
    result_b1 = grant_floor(world_b.world_id, specialist_id, 80)
    result_b2 = cross_examine(
        world_b.world_id,
        specialist_id,
        "What concrete cohort evidence mentions mobile copy or completion?",
        80,
    )
    assert result_a1["visible_text"] == result_b1["visible_text"]
    assert result_a2["visible_text"] == result_b2["visible_text"]

    world_c = _register(build_world(domain="product_rollback", difficulty="medium", seed=2, world_id="det-c"))
    q1 = cross_examine(world_c.world_id, specialist_id, "What evidence concerns mobile cohorts?", 80)
    q2 = cross_examine(world_c.world_id, specialist_id, "What evidence concerns revenue lag?", 80)
    assert q1["visible_text"] != q2["visible_text"]
    repeated = cross_examine(world_c.world_id, specialist_id, "What evidence concerns revenue lag?", 80)
    assert repeated["ok"]
    assert not world_c.official_record[-1].hidden_fact_ids
    assert world_c.official_record[-1].duplicate_tokens > 0


def test_cross_examination_can_surface_hidden_fact_that_short_floor_misses() -> None:
    base_world, specialist_id = _find_cross_exam_world()
    world = _register(deepcopy(base_world))
    specialist = world.specialists[specialist_id]
    short = grant_floor(world.world_id, specialist_id, 35)
    assert short["ok"]
    short_required = set(world.official_record[-1].hidden_fact_ids) & set(world.required_fact_ids)

    target_fact = next(fid for fid in specialist.private_fact_ids if fid in world.required_fact_ids)
    fact = world.facts[target_fact]
    direct = cross_examine(
        world.world_id,
        specialist_id,
        f"What concrete evidence about {world.truth_root_cause} and {fact.short_text} do you have?",
        95,
    )
    assert direct["ok"]
    direct_required = set(world.official_record[-1].hidden_fact_ids) & set(world.required_fact_ids)
    assert not short_required
    assert direct_required


def test_submit_verdict_validation_and_invalid_citations_recorded() -> None:
    world = _register(build_world(domain="investment_committee", difficulty="easy", seed=12, world_id="verdict"))
    assert not submit_verdict(world.world_id, "bogus", 0.5, world.truth_root_cause, [], "x")["ok"]
    assert not submit_verdict(world.world_id, world.truth_decision, 0.5, "bogus", [], "x")["ok"]
    assert not submit_verdict(world.world_id, world.truth_decision, 1.5, world.truth_root_cause, [], "x")["ok"]
    ok = submit_verdict(
        world.world_id,
        world.truth_decision,
        0.5,
        world.truth_root_cause,
        ["T404"],
        "invalid citations are scored later",
    )
    assert ok["ok"]
    assert world.final_verdict is not None
    assert world.final_verdict.citations == ["T404"]
    assert world.hearing_closed
    record = view_record(world.world_id)
    assert record["hearing_closed"]

