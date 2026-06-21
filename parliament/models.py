"""Dataclasses for the Context Window Parliament environment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

FactKind = Literal["required", "supporting", "decoy", "fluff"]
PersonaPolicy = Literal[
    "honest_dense",
    "underconfident_expert",
    "verbose_lobbyist",
    "strategic_biased",
    "noisy_observer",
    "skeptic",
]
TestimonyMode = Literal["floor", "cross_exam"]


@dataclass(slots=True)
class FactAtom:
    id: str
    text: str
    short_text: str
    domain: str
    tags: set[str]
    cluster_id: str
    root_cause_tags: set[str]
    kind: FactKind
    weight: float
    token_value_hint: int
    leak_guard_phrases: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SpecialistTurn:
    testimony_id: str
    mode: TestimonyMode
    question: str | None
    token_budget: int
    revealed_fact_ids: list[str]
    visible_text: str


@dataclass(slots=True)
class Specialist:
    id: str
    name: str
    role: str
    persona_policy: PersonaPolicy
    public_bid: str
    requested_tokens: int
    claimed_priority: str
    private_fact_ids: list[str]
    bias_target: str | None = None
    verbosity: float = 1.0
    reliability: float = 1.0
    revealed_fact_ids: set[str] = field(default_factory=set)
    previous_turns: list[SpecialistTurn] = field(default_factory=list)

    def public_card(self, token_used: int) -> dict[str, Any]:
        """Return the public specialist card visible to the Speaker."""

        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "public_bid": self.public_bid,
            "claimed_priority": self.claimed_priority,
            "requested_tokens": self.requested_tokens,
            "has_spoken": bool(self.previous_turns),
            "times_heard": len(self.previous_turns),
            "total_tokens_used": token_used,
        }


@dataclass(slots=True)
class TestimonyBlock:
    id: str
    specialist_id: str
    mode: TestimonyMode
    question: str | None
    visible_text: str
    token_count: int
    hidden_fact_ids: list[str]
    hidden_cluster_ids: list[str]
    relevant_tokens: int
    decoy_tokens: int
    fluff_tokens: int
    duplicate_tokens: int
    root_cause_tags: set[str]

    def visible_dict(self, specialist: Specialist) -> dict[str, Any]:
        """Return the public official-record representation."""

        return {
            "id": self.id,
            "specialist_id": self.specialist_id,
            "specialist_name": specialist.name,
            "role": specialist.role,
            "mode": self.mode,
            "question": self.question,
            "visible_text": self.visible_text,
            "token_count": self.token_count,
        }


@dataclass(slots=True)
class Verdict:
    decision: str
    confidence: float
    root_cause: str
    citations: list[str]
    rationale: str

    def normalized(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "root_cause": self.root_cause,
            "citation_ids": list(self.citations),
            "rationale": self.rationale,
        }


@dataclass(slots=True)
class ToolCallLog:
    tool: str
    ok: bool
    message: str
    args: dict[str, Any]
    record_len_before: int
    record_len_after: int


@dataclass(slots=True)
class World:
    world_id: str
    seed: int
    domain: str
    difficulty: str
    narrative: str
    token_budget: int
    max_interactions: int
    decision_options: list[str]
    root_cause_options: list[str]
    truth_decision: str
    truth_root_cause: str
    facts: dict[str, FactAtom]
    required_fact_ids: list[str]
    supporting_fact_ids: list[str]
    decoy_fact_ids: list[str]
    specialists: dict[str, Specialist]
    official_record: list[TestimonyBlock] = field(default_factory=list)
    final_verdict: Verdict | None = None
    interaction_count: int = 0
    hearing_closed: bool = False
    call_log: list[ToolCallLog] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def budget_used(self) -> int:
        return sum(block.token_count for block in self.official_record)

    @property
    def budget_remaining(self) -> int:
        return max(0, self.token_budget - self.budget_used)

    @property
    def interactions_remaining(self) -> int:
        return max(0, self.max_interactions - self.interaction_count)

    def next_testimony_id(self) -> str:
        return f"T{len(self.official_record) + 1}"

    def close_if_exhausted(self) -> None:
        if self.budget_remaining <= 0 or self.interaction_count >= self.max_interactions:
            self.hearing_closed = True


@dataclass(slots=True)
class RewardBreakdown:
    reward: float
    subscores: dict[str, float]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "reward": self.reward,
            "subscores": dict(self.subscores),
            "metadata": dict(self.metadata),
        }

    def to_hud_result(self) -> Any:
        """Return a HUD EvaluationResult when available, otherwise a plain float."""

        try:
            from hud.agents.types import EvaluationResult, SubScore  # type: ignore
        except Exception:
            try:
                from hud import EvaluationResult, SubScore  # type: ignore
            except Exception:
                return self.reward

        hud_subscores = [
            SubScore(name=name, score=value, weight=0.0)
            for name, value in self.subscores.items()
        ]
        try:
            return EvaluationResult(
                reward=self.reward,
                score=self.reward,
                subscores=hud_subscores,
                metadata=self.metadata,
            )
        except TypeError:
            return EvaluationResult(
                reward=self.reward,
                subscores=hud_subscores,
                metadata=self.metadata,
            )

