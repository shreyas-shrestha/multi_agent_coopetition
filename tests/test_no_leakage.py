from __future__ import annotations

import json
import re

from parliament.schemas import task_prompt
from parliament.state import register_world, reset_worlds
from parliament.tools import list_specialists, view_record
from parliament.worlds import build_world


def test_public_list_does_not_leak_private_metadata() -> None:
    reset_worlds()
    world = register_world(
        build_world(domain="product_rollback", difficulty="hard", seed=3, world_id="leak-check")
    )
    result = list_specialists(world.world_id)
    assert result["ok"]
    blob = json.dumps(result, sort_keys=True)
    for fact in world.facts.values():
        assert fact.id not in blob
        for phrase in fact.leak_guard_phrases:
            assert re.search(rf"(?<![A-Za-z0-9_]){re.escape(phrase)}(?![A-Za-z0-9_])", blob) is None
    assert world.truth_decision not in blob
    assert world.truth_root_cause not in blob


def test_task_prompt_has_no_oracle_solution() -> None:
    world = build_world(domain="incident_response", difficulty="medium", seed=4, world_id="prompt-check")
    prompt = task_prompt(world)
    for fact in world.facts.values():
        assert fact.id not in prompt
        assert fact.text not in prompt
    assert f"truth_decision: {world.truth_decision}" not in prompt
    assert f"truth_root_cause: {world.truth_root_cause}" not in prompt


def test_view_record_does_not_return_hidden_fact_ids() -> None:
    reset_worlds()
    world = register_world(
        build_world(domain="investment_committee", difficulty="medium", seed=7, world_id="record-check")
    )
    result = view_record(world.world_id)
    blob = json.dumps(result, sort_keys=True)
    for fact_id in world.facts:
        assert fact_id not in blob
    assert "hidden_fact_ids" not in blob
    assert "relevant_tokens" not in blob
