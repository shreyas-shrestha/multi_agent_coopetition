"""Fact construction helpers for generated worlds."""

from __future__ import annotations

from parliament.models import FactAtom, FactKind
from parliament.parsing import exact_numeric_markers, extract_tags, token_count


def make_fact(
    *,
    fact_id: str,
    text: str,
    domain: str,
    root_cause: str,
    kind: FactKind,
    weight: float,
    role: str,
    cluster_id: str,
    extra_tags: set[str] | None = None,
) -> FactAtom:
    """Create a fact with deterministic metadata and leakage markers."""

    tags = extract_tags(text) | extract_tags(role) | extract_tags(root_cause)
    if extra_tags:
        tags |= extra_tags
    root_tags = extract_tags(root_cause)
    markers = sorted(exact_numeric_markers(text) | {fact_id})
    short = text.split(";")[0].split(".")[0].strip()
    return FactAtom(
        id=fact_id,
        text=text,
        short_text=short,
        domain=domain,
        tags=tags,
        cluster_id=cluster_id,
        root_cause_tags=root_tags,
        kind=kind,
        weight=weight,
        token_value_hint=max(12, min(45, token_count(text))),
        leak_guard_phrases=markers,
    )

