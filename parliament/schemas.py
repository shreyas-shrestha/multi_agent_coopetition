"""Prompt and schema helpers."""

from __future__ import annotations

import json

from parliament.models import World


FINAL_VERDICT_SCHEMA = {
    "decision": "<one of the listed decision options>",
    "confidence": 0.0,
    "root_cause": "<one of the listed root-cause options>",
    "citation_ids": ["T1", "T2"],
    "rationale": "short explanation grounded in cited testimony",
}


def task_prompt(world: World) -> str:
    """Build the visible task prompt for the Speaker."""

    schema = json.dumps(FINAL_VERDICT_SCHEMA, indent=2)
    decisions = ", ".join(world.decision_options)
    roots = ", ".join(world.root_cause_options)
    tools = "\n".join(
        [
            "- list_specialists(world_id)",
            "- grant_floor(world_id, specialist_id, token_budget)",
            "- cross_examine(world_id, specialist_id, question, token_budget)",
            "- view_record(world_id)",
            "- submit_verdict(world_id, decision, confidence, root_cause, citation_ids, rationale)",
        ]
    )
    return f"""You are the Speaker of a context-window parliament.

World ID: {world.world_id}

Domain narrative:
{world.narrative}

Decision options: {decisions}
Root-cause options: {roots}

Official-record token budget: {world.token_budget}
Maximum evidence-gathering interactions: {world.max_interactions}

Tools:
{tools}

Public bids are cheap, but specialists may be biased, noisy, overconfident, or underconfident.
Detailed testimony consumes the official-record budget. Decide who receives floor time, how many
tokens to spend, when to cross-examine, and when to stop. Use targeted cross-examination when a
generic public bid is not enough.

Your score depends on making a correct evidence-backed decision under limited context. The final
verdict should cite testimony IDs from the official record that support the decision and root cause.

Submit the verdict with submit_verdict, then finish with the same JSON:

{schema}
"""

