"""Parsing and deterministic approximate token utilities."""

from __future__ import annotations

import re

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?%?(?:ms|s|x|k|m|gb|mb)?", re.IGNORECASE)

STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "me",
    "more",
    "not",
    "of",
    "on",
    "or",
    "our",
    "please",
    "should",
    "show",
    "tell",
    "than",
    "that",
    "the",
    "their",
    "there",
    "this",
    "to",
    "was",
    "we",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
    "you",
}

SYNONYMS = {
    "android": "mobile",
    "ios": "mobile",
    "phone": "mobile",
    "latency": "mobile_latency",
    "slow": "mobile_latency",
    "frozen": "mobile_latency",
    "copy": "onboarding_copy",
    "wording": "onboarding_copy",
    "instrumentation": "data_bug",
    "tracking": "data_bug",
    "pipeline": "data_bug",
    "holiday": "seasonality",
    "seasonal": "seasonality",
    "lock": "database_lock_contention",
    "locks": "database_lock_contention",
    "cache": "cache_thundering_herd",
    "herd": "cache_thundering_herd",
    "frontend": "frontend_regression",
    "browser": "frontend_regression",
    "third": "third_party_api",
    "vendor": "third_party_api",
    "metrics": "bad_metrics_pipeline",
    "churn": "hidden_churn",
    "retention": "hidden_churn",
    "growth": "durable_growth",
    "margin": "margin_problem",
    "legal": "legal_risk",
    "contract": "legal_risk",
    "misreporting": "founder_misreporting",
    "market": "market_pull",
}


def token_count(text: str) -> int:
    """Return a deterministic approximate token count."""

    return len(TOKEN_RE.findall(text or ""))


def tokens(text: str) -> list[str]:
    """Return regex tokens used by the budget model."""

    return TOKEN_RE.findall(text or "")


def trim_to_token_budget(text: str, budget: int) -> str:
    """Trim text at a deterministic token boundary."""

    if budget <= 0:
        return ""
    parts = tokens(text)
    if len(parts) <= budget:
        return text.strip()
    trimmed = parts[:budget]
    out: list[str] = []
    for part in trimmed:
        if out and re.match(r"\w", part) and re.match(r"\w", out[-1][-1]):
            out.append(" ")
        elif out and part not in ".,;:!?)]}" and out[-1] not in "([{":
            out.append(" ")
        out.append(part)
    return "".join(out).strip()


def extract_tags(text: str | None) -> set[str]:
    """Extract rough semantic tags from a prompt, fact, or role string."""

    raw = re.findall(r"[A-Za-z][A-Za-z0-9_/-]*", (text or "").lower())
    tags: set[str] = set()
    for item in raw:
        for part in re.split(r"[_/-]+", item):
            if len(part) > 2 and part not in STOPWORDS:
                tags.add(SYNONYMS.get(part, part))
        if "_" in item:
            tags.add(item)
    for source, target in SYNONYMS.items():
        if source in tags:
            tags.add(target)
    return tags


def exact_numeric_markers(text: str) -> set[str]:
    """Return exact numeric evidence markers that must not appear in public bids."""

    return set(NUMBER_RE.findall(text or ""))

