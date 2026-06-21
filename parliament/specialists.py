"""Specialist testimony backends."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Literal, Protocol

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


class LLMClient(Protocol):
    """Minimal text-generation client used by LLM-backed specialists."""

    def complete(self, *, system: str, user: str, max_tokens: int) -> str:
        """Return a text completion."""


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
    """LLM-backed specialist backend with deterministic hidden attribution."""

    def __init__(
        self,
        client: LLMClient | None = None,
        fallback_backend: SpecialistBackend | None = None,
        fallback_on_error: bool = True,
    ) -> None:
        self.client = client or AnthropicMessagesClient.from_env()
        self.fallback_backend = fallback_backend or DeterministicSpecialistBackend()
        self.fallback_on_error = fallback_on_error

    def generate_testimony(
        self,
        world: World,
        specialist: Specialist,
        mode: Literal["floor", "cross_exam"],
        token_budget: int,
        question: str | None = None,
    ) -> TestimonyBlock:
        question = question.strip() if question else None
        if self._is_repeated_question(specialist, question):
            return self.fallback_backend.generate_testimony(
                world, specialist, mode, token_budget, question
            )

        try:
            raw = self.client.complete(
                system=_llm_system_prompt(),
                user=_llm_user_prompt(world, specialist, mode, token_budget, question),
                max_tokens=max(128, min(2048, token_budget * 3)),
            )
            payload = _parse_llm_payload(raw)
            block = _block_from_llm_payload(
                world=world,
                specialist=specialist,
                mode=mode,
                token_budget=token_budget,
                question=question,
                payload=payload,
            )
        except Exception:
            if not self.fallback_on_error:
                raise
            return self.fallback_backend.generate_testimony(
                world, specialist, mode, token_budget, question
            )

        if block.visible_text and block.hidden_fact_ids:
            return block
        if self.fallback_on_error:
            return self.fallback_backend.generate_testimony(
                world, specialist, mode, token_budget, question
            )
        return block

    @staticmethod
    def _is_repeated_question(specialist: Specialist, question: str | None) -> bool:
        return bool(
            question
            and any(
                turn.question and turn.question.lower() == question.lower()
                for turn in specialist.previous_turns
            )
        )


class AnthropicMessagesClient:
    """Small stdlib client for Anthropic's Messages API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
        base_url: str = "https://api.anthropic.com",
        anthropic_version: str = "2023-06-01",
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for LLM specialists.")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.anthropic_version = anthropic_version
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> AnthropicMessagesClient:
        return cls(
            api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            model=os.environ.get("PARLIAMENT_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
            anthropic_version=os.environ.get("ANTHROPIC_VERSION", "2023-06-01"),
            timeout=float(os.environ.get("PARLIAMENT_ANTHROPIC_TIMEOUT", "60")),
        )

    def complete(self, *, system: str, user: str, max_tokens: int) -> str:
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        request = urllib.request.Request(
            f"{self.base_url}/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "anthropic-version": self.anthropic_version,
                "content-type": "application/json",
                "x-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic Messages API error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Anthropic Messages API request failed: {exc}") from exc

        content = data.get("content", [])
        parts = [
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        text = "\n".join(part for part in parts if part).strip()
        if not text:
            raise RuntimeError("Anthropic Messages API returned no text content.")
        return text


def _llm_system_prompt() -> str:
    return (
        "You are a private expert witness inside a context-window parliament environment. "
        "Answer only as the named specialist, using only the private facts supplied in the "
        "user message and your persona instructions. Return exactly one JSON object with keys "
        "visible_text and fact_ids. visible_text is the public testimony the Speaker sees. "
        "fact_ids is a private list of supplied fact IDs that directly support visible_text. "
        "Never put fact IDs in visible_text. Do not invent facts, measurements, citations, "
        "decision options, or root causes that are not supplied."
    )


def _llm_user_prompt(
    world: World,
    specialist: Specialist,
    mode: Literal["floor", "cross_exam"],
    token_budget: int,
    question: str | None,
) -> str:
    facts = [
        {
            "id": fid,
            "kind": world.facts[fid].kind,
            "text": world.facts[fid].text,
        }
        for fid in specialist.private_fact_ids
    ]
    prior_turns = [
        {
            "mode": turn.mode,
            "question": turn.question,
            "visible_text": turn.visible_text,
            "revealed_fact_ids": turn.revealed_fact_ids,
        }
        for turn in specialist.previous_turns
    ]
    payload = {
        "world_id": world.world_id,
        "domain": world.domain,
        "mode": mode,
        "question": question,
        "token_budget": token_budget,
        "specialist": {
            "name": specialist.name,
            "role": specialist.role,
            "persona_policy": specialist.persona_policy,
            "public_bid": specialist.public_bid,
            "claimed_priority": specialist.claimed_priority,
            "requested_tokens": specialist.requested_tokens,
            "bias_target": specialist.bias_target,
            "verbosity": specialist.verbosity,
            "reliability": specialist.reliability,
        },
        "prior_turns": prior_turns,
        "private_facts": facts,
        "output_contract": {
            "visible_text": f"At most {token_budget} approximate tokens. No fact IDs.",
            "fact_ids": "Only IDs from private_facts that directly support visible_text.",
        },
    }
    return json.dumps(payload, sort_keys=True)


def _parse_llm_payload(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        parsed = None
        for index, char in enumerate(raw):
            if char != "{":
                continue
            try:
                candidate, _end = decoder.raw_decode(raw[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                parsed = candidate
        if parsed is None:
            raise ValueError("LLM specialist response did not contain a JSON object.")
    if not isinstance(parsed, dict):
        raise ValueError("LLM specialist response must be a JSON object.")
    return parsed


def _block_from_llm_payload(
    *,
    world: World,
    specialist: Specialist,
    mode: Literal["floor", "cross_exam"],
    token_budget: int,
    question: str | None,
    payload: dict[str, Any],
) -> TestimonyBlock:
    visible_text = _strip_fact_ids(str(payload.get("visible_text", "")), world)
    visible_text = trim_to_token_budget(visible_text, token_budget)
    actual = token_count(visible_text)
    fact_ids = _valid_attributed_fact_ids(payload, world, specialist, visible_text)
    token_buckets = _token_buckets_for_facts(world, fact_ids, actual)
    duplicate_tokens = _duplicate_tokens_for_facts(world, specialist, fact_ids, actual)
    root_cause_tags: set[str] = set()
    for fid in fact_ids:
        root_cause_tags |= world.facts[fid].root_cause_tags

    return TestimonyBlock(
        id=world.next_testimony_id(),
        specialist_id=specialist.id,
        mode=mode,
        question=question,
        visible_text=visible_text,
        token_count=actual,
        hidden_fact_ids=fact_ids,
        hidden_cluster_ids=[world.facts[fid].cluster_id for fid in fact_ids],
        relevant_tokens=token_buckets["relevant"],
        decoy_tokens=token_buckets["decoy"],
        fluff_tokens=token_buckets["fluff"],
        duplicate_tokens=duplicate_tokens,
        root_cause_tags=root_cause_tags,
    )


def _strip_fact_ids(text: str, world: World) -> str:
    cleaned = text
    for fact_id in sorted(world.facts, key=len, reverse=True):
        cleaned = re.sub(
            rf"(?<![A-Za-z0-9_]){re.escape(fact_id)}(?![A-Za-z0-9_])",
            "",
            cleaned,
        )
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def _valid_attributed_fact_ids(
    payload: dict[str, Any],
    world: World,
    specialist: Specialist,
    visible_text: str,
) -> list[str]:
    supplied = payload.get("fact_ids", [])
    if not isinstance(supplied, list):
        supplied = []
    private = set(specialist.private_fact_ids)
    valid: list[str] = []
    for item in supplied:
        fact_id = str(item)
        if fact_id not in private or fact_id not in world.facts or fact_id in valid:
            continue
        if _fact_supported_by_visible_text(world.facts[fact_id], visible_text):
            valid.append(fact_id)
    return valid


def _fact_supported_by_visible_text(fact: FactAtom, visible_text: str) -> bool:
    if not visible_text:
        return False
    lowered = visible_text.lower()
    if fact.text.lower() in lowered or fact.short_text.lower() in lowered:
        return True
    markers = [
        marker.lower()
        for marker in fact.leak_guard_phrases
        if marker and marker != fact.id
    ]
    if markers and any(marker in lowered for marker in markers):
        return True
    visible_tags = extract_tags(visible_text)
    overlap = visible_tags & fact.tags
    return len(overlap) >= min(4, max(2, len(fact.tags) // 4))


def _token_buckets_for_facts(world: World, fact_ids: list[str], actual: int) -> dict[str, int]:
    if actual <= 0:
        return {"relevant": 0, "decoy": 0, "fluff": 0}
    if not fact_ids:
        return {"relevant": 0, "decoy": 0, "fluff": actual}

    weights = [max(1, world.facts[fid].token_value_hint) for fid in fact_ids]
    total_weight = sum(weights)
    assigned = 0
    buckets = {"relevant": 0, "decoy": 0, "fluff": 0}
    for index, (fid, weight) in enumerate(zip(fact_ids, weights)):
        if index == len(fact_ids) - 1:
            share = actual - assigned
        else:
            share = round(actual * weight / total_weight)
            assigned += share
        fact = world.facts[fid]
        if fact.kind in {"required", "supporting"}:
            buckets["relevant"] += share
        elif fact.kind == "decoy":
            buckets["decoy"] += share
        else:
            buckets["fluff"] += share
    return buckets


def _duplicate_tokens_for_facts(
    world: World,
    specialist: Specialist,
    fact_ids: list[str],
    actual: int,
) -> int:
    if actual <= 0 or not fact_ids:
        return 0
    duplicate_count = sum(
        1
        for fid in fact_ids
        if fid in specialist.revealed_fact_ids
        or DeterministicSpecialistBackend._cluster_seen(world, world.facts[fid].cluster_id)
    )
    return round(actual * duplicate_count / len(fact_ids))


_DEFAULT_BACKEND: SpecialistBackend | None = None


def get_default_backend() -> SpecialistBackend:
    """Return the configured specialist backend."""

    global _DEFAULT_BACKEND
    if _DEFAULT_BACKEND is not None:
        return _DEFAULT_BACKEND

    backend = os.environ.get("PARLIAMENT_SPECIALIST_BACKEND", "auto").lower()
    if backend == "deterministic":
        _DEFAULT_BACKEND = DeterministicSpecialistBackend()
    elif backend == "llm" or (backend == "auto" and os.environ.get("ANTHROPIC_API_KEY")):
        _DEFAULT_BACKEND = LLMSpecialistBackend()
    elif backend == "auto":
        _DEFAULT_BACKEND = DeterministicSpecialistBackend()
    else:
        raise RuntimeError(
            "PARLIAMENT_SPECIALIST_BACKEND must be one of: auto, deterministic, llm."
        )
    return _DEFAULT_BACKEND


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
