"""Deterministic specialist testimony backends."""

from __future__ import annotations

from typing import Literal, Protocol

from parliament.models import FactAtom, Specialist, SpecialistTurn, TestimonyBlock, World
from parliament.parsing import extract_tags, token_count, trim_to_token_budget


class SpecialistBackend(Protocol):
    """Interface for testimony generation backends."""

    def generate_testimony(
        self,
        world: World,
        specialist: Specialist,
        mode: Literal["floor", "cross_exam"],
        token_budget: int,
        question: str | None = None,
    ) -> TestimonyBlock:
        """Generate a testimony block without mutating the official record."""


class DeterministicSpecialistBackend:
    """Stateful deterministic testimony generator."""

    def generate_testimony(
        self,
        world: World,
        specialist: Specialist,
        mode: Literal["floor", "cross_exam"],
        token_budget: int,
        question: str | None = None,
    ) -> TestimonyBlock:
        question = question.strip() if question else None
        testimony_id = world.next_testimony_id()
        repeated_question = bool(
            question
            and any(turn.question and turn.question.lower() == question.lower() for turn in specialist.previous_turns)
        )
        if repeated_question:
            return self._repeat_response(world, specialist, mode, token_budget, question)

        candidates = [
            (self._fact_score(world, specialist, world.facts[fid], mode, token_budget, question), world.facts[fid])
            for fid in specialist.private_fact_ids
        ]
        candidates.sort(key=lambda item: (-item[0], item[1].id))

        visible_parts: list[str] = []
        hidden_fact_ids: list[str] = []
        hidden_cluster_ids: list[str] = []
        root_cause_tags: set[str] = set()
        relevant_tokens = 0
        decoy_tokens = 0
        fluff_tokens = 0
        duplicate_tokens = 0
        used = 0

        intro = self._intro(specialist, mode, question)
        if intro:
            intro_tokens = token_count(intro)
            if intro_tokens <= max(12, token_budget // 4):
                visible_parts.append(intro)
                used += intro_tokens
                fluff_tokens += intro_tokens

        for score, fact in candidates:
            if score < self._minimum_score(specialist, mode, token_budget, question):
                continue
            sentence = self._fact_sentence(specialist, fact, mode, question)
            sentence_tokens = token_count(sentence)
            if sentence_tokens > token_budget:
                sentence = trim_to_token_budget(sentence, token_budget)
                sentence_tokens = token_count(sentence)
            if used + sentence_tokens > token_budget:
                continue
            visible_parts.append(sentence)
            used += sentence_tokens
            hidden_fact_ids.append(fact.id)
            hidden_cluster_ids.append(fact.cluster_id)
            root_cause_tags |= fact.root_cause_tags
            if fact.kind in {"required", "supporting"}:
                relevant_tokens += sentence_tokens
            elif fact.kind == "decoy":
                decoy_tokens += sentence_tokens
            else:
                fluff_tokens += sentence_tokens
            if fact.id in specialist.revealed_fact_ids or self._cluster_seen(world, fact.cluster_id):
                duplicate_tokens += sentence_tokens
            if self._enough_evidence(specialist, mode, token_budget, len(hidden_fact_ids), used):
                break

        if not visible_parts or not hidden_fact_ids:
            fallback = self._fallback(specialist, mode, token_budget, question)
            visible_parts.append(fallback)
            fluff_tokens += token_count(fallback)

        visible_text = trim_to_token_budget(" ".join(visible_parts), token_budget)
        actual = token_count(visible_text)
        attributed = relevant_tokens + decoy_tokens + fluff_tokens
        if attributed < actual:
            fluff_tokens += actual - attributed
        elif attributed > actual:
            over = attributed - actual
            fluff_tokens = max(0, fluff_tokens - over)

        return TestimonyBlock(
            id=testimony_id,
            specialist_id=specialist.id,
            mode=mode,
            question=question,
            visible_text=visible_text,
            token_count=actual,
            hidden_fact_ids=hidden_fact_ids,
            hidden_cluster_ids=hidden_cluster_ids,
            relevant_tokens=relevant_tokens,
            decoy_tokens=decoy_tokens,
            fluff_tokens=fluff_tokens,
            duplicate_tokens=duplicate_tokens,
            root_cause_tags=root_cause_tags,
        )

    def _fact_score(
        self,
        world: World,
        specialist: Specialist,
        fact: FactAtom,
        mode: str,
        token_budget: int,
        question: str | None,
    ) -> float:
        qtags = extract_tags(question)
        role_tags = extract_tags(specialist.role)
        truth_tags = extract_tags(world.truth_root_cause)
        overlap = len(qtags & fact.tags)
        root_overlap = len(qtags & truth_tags & fact.tags)
        kind_base = {"required": 6.0, "supporting": 4.0, "decoy": 2.0, "fluff": 0.5}[fact.kind]
        score = kind_base + fact.weight + 0.4 * len(role_tags & fact.tags)
        if fact.id not in specialist.revealed_fact_ids:
            score += 1.5
        else:
            score -= 5.0
        if self._cluster_seen(world, fact.cluster_id):
            score -= 1.5

        if mode == "cross_exam":
            score += 2.4 * overlap + 2.0 * root_overlap
            if token_budget >= fact.token_value_hint + 10:
                score += 0.8
        else:
            score += 0.2 * overlap

        persona = specialist.persona_policy
        if persona == "honest_dense":
            if fact.kind in {"required", "supporting"}:
                score += 2.0
            score -= 0.5 if fact.kind == "decoy" else 0.0
        elif persona == "underconfident_expert":
            if mode == "floor" and token_budget < max(70, specialist.requested_tokens):
                if fact.kind == "required":
                    score -= 5.5
                else:
                    score += 0.7
            elif mode == "cross_exam" and overlap >= 1 and token_budget >= 45:
                score += 4.5 if fact.kind in {"required", "supporting"} else 0.0
        elif persona == "verbose_lobbyist":
            if fact.kind == "decoy":
                score += 5.0
            elif fact.kind == "required":
                score -= 1.8
            score += 0.3 * specialist.verbosity
        elif persona == "strategic_biased":
            if mode == "floor" and fact.kind == "required":
                score -= 4.5
            if mode == "cross_exam" and (overlap >= 2 or root_overlap >= 1) and token_budget >= 55:
                score += 5.0
            elif fact.kind == "decoy":
                score += 1.2
        elif persona == "noisy_observer":
            if fact.kind == "decoy":
                score += 1.0
            score += 0.7 * overlap
        elif persona == "skeptic":
            if fact.kind in {"supporting", "required"}:
                score += 0.8
            if {"sample", "pipeline", "contract", "risk", "metrics"} & fact.tags:
                score += 1.2
            if fact.kind == "decoy":
                score -= 0.4

        return score

    def _minimum_score(
        self,
        specialist: Specialist,
        mode: str,
        token_budget: int,
        question: str | None,
    ) -> float:
        if mode == "cross_exam":
            return 4.0
        if specialist.persona_policy == "underconfident_expert" and token_budget < 55:
            return 4.5
        if specialist.persona_policy == "strategic_biased":
            return 4.7
        return 3.2

    def _enough_evidence(
        self,
        specialist: Specialist,
        mode: str,
        token_budget: int,
        fact_count: int,
        used: int,
    ) -> bool:
        if fact_count <= 0:
            return False
        if mode == "cross_exam":
            return fact_count >= (2 if token_budget >= 90 else 1)
        if specialist.persona_policy == "verbose_lobbyist":
            return fact_count >= (3 if token_budget >= 120 else 2)
        if specialist.persona_policy == "honest_dense":
            return fact_count >= (3 if token_budget >= 100 else 2)
        return fact_count >= 2 or used > token_budget * 0.75

    def _intro(self, specialist: Specialist, mode: str, question: str | None) -> str:
        if specialist.persona_policy == "verbose_lobbyist":
            return f"{specialist.role} framing: the headline looks urgent, but I will separate examples from proof."
        if specialist.persona_policy == "underconfident_expert" and mode == "floor":
            return f"{specialist.role} caveat: my signal is not loud in the public summaries."
        if mode == "cross_exam" and question:
            return "Answering the targeted question directly:"
        return ""

    def _fact_sentence(
        self,
        specialist: Specialist,
        fact: FactAtom,
        mode: str,
        question: str | None,
    ) -> str:
        if specialist.persona_policy == "verbose_lobbyist":
            return f"Example from {specialist.role}: {fact.text}"
        if specialist.persona_policy == "strategic_biased" and mode == "floor":
            return f"Context I am comfortable putting on record: {fact.text}"
        if specialist.persona_policy == "skeptic":
            return f"Caveat from {specialist.role}: {fact.text}"
        if mode == "cross_exam":
            return f"On that point, {fact.text}"
        return f"{specialist.role} evidence: {fact.text}"

    def _fallback(
        self,
        specialist: Specialist,
        mode: str,
        token_budget: int,
        question: str | None,
    ) -> str:
        if mode == "cross_exam":
            text = (
                f"{specialist.role} cannot add a new concrete fact on that exact question from the "
                "available record. The prior testimony is the best supported version."
            )
        elif specialist.persona_policy == "underconfident_expert":
            text = (
                f"{specialist.role} sees a weak-looking signal but needs a more specific question or "
                "more floor time before naming a concrete measurement."
            )
        elif specialist.persona_policy == "strategic_biased":
            text = (
                f"{specialist.role} gives general context and recommends caution about overreacting, "
                "without putting a decisive measurement on the record."
            )
        else:
            text = (
                f"{specialist.role} has no additional concrete fact that fits the requested budget."
            )
        return trim_to_token_budget(text, token_budget)

    def _repeat_response(
        self,
        world: World,
        specialist: Specialist,
        mode: str,
        token_budget: int,
        question: str | None,
    ) -> TestimonyBlock:
        text = trim_to_token_budget(
            f"{specialist.role} has already answered that question. Repeating it adds no new "
            "official evidence beyond the same cluster of prior testimony.",
            token_budget,
        )
        actual = token_count(text)
        previous_clusters = [
            cluster
            for turn in specialist.previous_turns
            for fid in turn.revealed_fact_ids
            for cluster in [world.facts[fid].cluster_id]
        ]
        return TestimonyBlock(
            id=world.next_testimony_id(),
            specialist_id=specialist.id,
            mode=mode,  # type: ignore[arg-type]
            question=question,
            visible_text=text,
            token_count=actual,
            hidden_fact_ids=[],
            hidden_cluster_ids=previous_clusters[:1],
            relevant_tokens=0,
            decoy_tokens=0,
            fluff_tokens=actual,
            duplicate_tokens=actual,
            root_cause_tags=set(),
        )

    @staticmethod
    def _cluster_seen(world: World, cluster_id: str) -> bool:
        return any(cluster_id in block.hidden_cluster_ids for block in world.official_record)


class LLMSpecialistBackend:
    """Future LLM-backed specialist backend.

    A later version can give each specialist's private facts and persona to an LLM
    subagent. The output would still need post-hoc fact attribution because the
    deterministic scorer requires hidden fact IDs, clusters, and token attribution.
    Nested HUD subagent rollouts could eventually replace these scripted specialists,
    while preserving the same official-record and reward interfaces.
    """

    def generate_testimony(
        self,
        world: World,
        specialist: Specialist,
        mode: Literal["floor", "cross_exam"],
        token_budget: int,
        question: str | None = None,
    ) -> TestimonyBlock:
        raise NotImplementedError("LLMSpecialistBackend is a documented stub for future work.")


DEFAULT_BACKEND = DeterministicSpecialistBackend()


def apply_testimony_to_specialist(specialist: Specialist, block: TestimonyBlock, token_budget: int) -> None:
    """Update specialist state after a testimony block is appended."""

    specialist.revealed_fact_ids.update(block.hidden_fact_ids)
    specialist.previous_turns.append(
        SpecialistTurn(
            testimony_id=block.id,
            mode=block.mode,
            question=block.question,
            token_budget=token_budget,
            revealed_fact_ids=list(block.hidden_fact_ids),
            visible_text=block.visible_text,
        )
    )

