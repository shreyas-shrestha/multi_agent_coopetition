from __future__ import annotations

import json

from parliament.specialists import LLMSpecialistBackend, apply_testimony_to_specialist
from parliament.state import register_world, reset_worlds
from parliament.worlds import build_world


class FakeLLMClient:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self.payloads = list(payloads)
        self.calls: list[dict[str, object]] = []

    def complete(self, *, system: str, user: str, max_tokens: int) -> str:
        self.calls.append({"system": system, "user": user, "max_tokens": max_tokens})
        return json.dumps(self.payloads.pop(0))


def _world():
    reset_worlds()
    return register_world(
        build_world(domain="product_rollback", difficulty="medium", seed=2, world_id="llm")
    )


def test_llm_backend_builds_scored_testimony_from_attributed_fact() -> None:
    world = _world()
    specialist = world.specialists["metrics"]
    fact_id = specialist.private_fact_ids[0]
    fact = world.facts[fact_id]
    client = FakeLLMClient(
        [
            {
                "visible_text": f"Metrics evidence: {fact.text}",
                "fact_ids": [fact_id, "not-a-real-fact"],
            }
        ]
    )
    backend = LLMSpecialistBackend(client=client, fallback_on_error=False)

    block = backend.generate_testimony(world, specialist, "floor", 90)

    assert len(client.calls) == 1
    assert block.visible_text == f"Metrics evidence: {fact.text}"
    assert block.hidden_fact_ids == [fact_id]
    assert block.hidden_cluster_ids == [fact.cluster_id]
    assert block.token_count <= 90
    assert block.relevant_tokens + block.decoy_tokens + block.fluff_tokens == block.token_count


def test_llm_backend_strips_hidden_fact_ids_from_visible_text() -> None:
    world = _world()
    specialist = world.specialists["metrics"]
    fact_id = specialist.private_fact_ids[0]
    fact = world.facts[fact_id]
    client = FakeLLMClient(
        [
            {
                "visible_text": f"{fact_id}: {fact.text}",
                "fact_ids": [fact_id],
            }
        ]
    )
    backend = LLMSpecialistBackend(client=client, fallback_on_error=False)

    block = backend.generate_testimony(world, specialist, "floor", 90)

    assert fact_id not in block.visible_text
    assert fact.text in block.visible_text
    assert block.hidden_fact_ids == [fact_id]


def test_llm_backend_trims_visible_text_to_requested_budget() -> None:
    world = _world()
    specialist = world.specialists["metrics"]
    fact_id = specialist.private_fact_ids[0]
    fact = world.facts[fact_id]
    visible_text = " ".join([fact.text] * 10)
    client = FakeLLMClient([{"visible_text": visible_text, "fact_ids": [fact_id]}])
    backend = LLMSpecialistBackend(client=client, fallback_on_error=False)

    block = backend.generate_testimony(world, specialist, "floor", 30)

    assert block.token_count <= 30
    assert block.hidden_fact_ids == [fact_id]


def test_llm_backend_uses_repeat_response_without_calling_client_again() -> None:
    world = _world()
    specialist = world.specialists["metrics"]
    fact_id = specialist.private_fact_ids[0]
    fact = world.facts[fact_id]
    question = "What concrete metric changes the decision?"
    client = FakeLLMClient(
        [{"visible_text": f"On that point, {fact.text}", "fact_ids": [fact_id]}]
    )
    backend = LLMSpecialistBackend(client=client, fallback_on_error=False)

    first = backend.generate_testimony(world, specialist, "cross_exam", 90, question)
    world.official_record.append(first)
    apply_testimony_to_specialist(specialist, first, 90)
    repeated = backend.generate_testimony(world, specialist, "cross_exam", 90, question)

    assert len(client.calls) == 1
    assert repeated.hidden_fact_ids == []
    assert repeated.duplicate_tokens > 0

