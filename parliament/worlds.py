"""Deterministic world and taskset generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from parliament.facts import make_fact
from parliament.models import FactAtom, Specialist, World
from parliament.parsing import extract_tags

TASKSET_NAME = "context-window-parliament-mvp"


@dataclass(frozen=True)
class DifficultyConfig:
    token_budget: int
    max_interactions: int
    specialist_count: int
    required_limit: int
    decoy_limit: int
    supporting_limit: int


DIFFICULTIES: dict[str, DifficultyConfig] = {
    "easy": DifficultyConfig(650, 12, 5, 3, 3, 2),
    "medium": DifficultyConfig(500, 10, 6, 4, 5, 3),
    "hard": DifficultyConfig(400, 8, 7, 5, 7, 4),
}

DOMAIN_NARRATIVES = {
    "product_rollback": "An internal product review is deciding whether to roll back Feature X after launch.",
    "incident_response": "An incident commander must diagnose a production incident and choose action.",
    "investment_committee": "An investment committee must decide whether to invest, pass, or wait.",
}

DOMAIN_SLUGS = {
    "product_rollback": "product-rollback",
    "incident_response": "incident-response",
    "investment_committee": "investment-committee",
}

DECISIONS = {
    "product_rollback": ["rollback", "do_not_rollback", "partial_rollback", "uncertain"],
    "incident_response": [
        "rollback_feature_flag",
        "scale_database",
        "patch_config",
        "disable_endpoint",
        "no_action_monitor",
        "uncertain",
    ],
    "investment_committee": ["invest", "pass", "wait_for_more_data", "uncertain"],
}

ROOT_CAUSES = {
    "product_rollback": [
        "mobile_latency",
        "onboarding_copy",
        "pricing_change",
        "data_bug",
        "seasonality",
        "unknown",
    ],
    "incident_response": [
        "database_lock_contention",
        "cache_thundering_herd",
        "frontend_regression",
        "third_party_api",
        "bad_metrics_pipeline",
        "unknown",
    ],
    "investment_committee": [
        "hidden_churn",
        "durable_growth",
        "margin_problem",
        "legal_risk",
        "founder_misreporting",
        "market_pull",
        "unknown",
    ],
}

ROLE_IDS = {
    "product_rollback": {
        "Metrics": "metrics",
        "Infra": "infra",
        "Support": "support",
        "Sales": "sales",
        "Experimentation": "experimentation",
        "Exec": "exec",
    },
    "incident_response": {
        "API": "api",
        "Database": "database",
        "Frontend": "frontend",
        "Deploy": "deploy",
        "Support": "support",
        "On-call Manager": "oncall_manager",
        "Observability/SRE": "observability",
    },
    "investment_committee": {
        "Growth": "growth",
        "Finance": "finance",
        "Customer Calls": "customer_calls",
        "Technical Diligence": "technical_diligence",
        "Legal": "legal",
        "Founder": "founder",
        "Market Analyst": "market_analyst",
    },
}


@dataclass(frozen=True)
class Scenario:
    decision: str
    root_cause: str
    required: tuple[tuple[str, str, float, str], ...]
    supporting: tuple[tuple[str, str, float, str], ...]
    decoys: tuple[tuple[str, str, float, str], ...]


PRODUCT_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "rollback",
        "mobile_latency",
        (
            ("Infra", "Mobile p95 onboarding latency rose from 610ms to 1030ms within two hours of the launch.", 1.4, "latency"),
            ("Metrics", "Activation dropped 18% on mobile cohorts while desktop activation stayed within 1% of baseline.", 1.25, "cohort"),
            ("Support", "Support tickets mentioning slow or frozen onboarding increased from 9 to 64 after launch.", 1.1, "complaints"),
            ("Experimentation", "The A/B test underrepresented Android early-user traffic by 42%, hiding the worst segment.", 1.0, "sample"),
        ),
        (
            ("Infra", "A small rollback canary restored mobile onboarding latency to 640ms for affected Android users.", 0.9, "recovery"),
            ("Metrics", "Revenue was flat in week one, so revenue lag does not disprove activation harm.", 0.45, "lag"),
        ),
        (
            ("Sales", "Enterprise demos after launch were positive and three prospects asked for broader rollout.", 0.25, "sales"),
            ("Exec", "Social mentions rose 31% after launch, mostly quoting the announcement thread.", 0.2, "social"),
            ("Sales", "The sales pipeline improved by 8%, but the deals were already in procurement before launch.", 0.2, "pipeline"),
            ("Exec", "First-week revenue was unchanged, which is too lagged to settle onboarding impact.", 0.2, "revenue"),
        ),
    ),
    Scenario(
        "do_not_rollback",
        "data_bug",
        (
            ("Metrics", "The apparent activation drop starts exactly when the tracking event renamed completed_onboarding to setup_done.", 1.35, "instrumentation"),
            ("Experimentation", "Server-side successful onboarding counts stayed within 0.7% of the pre-launch baseline.", 1.25, "server"),
            ("Support", "Complaint volume changed from 41 to 43 tickets per day, not a material launch spike.", 1.0, "complaints"),
            ("Metrics", "The dashboard pipeline shipped a schema change 17 minutes before the launch flag went live.", 1.05, "pipeline"),
        ),
        (
            ("Infra", "A 12-minute latency blip occurred in a different region and did not overlap the affected metric window.", 0.55, "latency"),
            ("Exec", "Executive review notes show no customer escalation tied to the launch date.", 0.4, "escalation"),
        ),
        (
            ("Support", "One viral post complained about onboarding, but it came from a beta build.", 0.2, "viral"),
            ("Sales", "A large prospect paused a demo for unrelated procurement review.", 0.2, "sales"),
            ("Infra", "CPU rose 6% during normal image warmup, below the alert threshold.", 0.2, "cpu"),
            ("Exec", "The CEO disliked the dashboard color change and called the rollout confusing.", 0.15, "opinion"),
        ),
    ),
    Scenario(
        "partial_rollback",
        "onboarding_copy",
        (
            ("Metrics", "The drop is concentrated among new mobile users, with a 22% fall at the permissions step.", 1.25, "cohort"),
            ("Support", "Support transcripts repeatedly quote the new permission copy as asking for permanent location access.", 1.2, "copy"),
            ("Experimentation", "Power users and returning desktop users changed by less than 2%, isolating the issue to first-run copy.", 1.0, "segment"),
            ("Metrics", "A copy-only revert for 15% of new users restored completion from 54% to 68%.", 1.2, "recovery"),
        ),
        (
            ("Infra", "Backend p95 rose from 240ms to 275ms, still below the 350ms onboarding threshold.", 0.45, "latency"),
            ("Sales", "Sales feedback was positive because demos bypassed the new-user permission step.", 0.35, "sales"),
        ),
        (
            ("Infra", "A minor backend queue warning fired twice during deploy but cleared without intervention.", 0.2, "queue"),
            ("Sales", "Enterprise buyers liked the feature concept in controlled demos.", 0.2, "sales"),
            ("Exec", "The launch announcement had the strongest click-through rate of the quarter.", 0.2, "announcement"),
            ("Support", "Desktop support threads were stable and mostly about billing questions.", 0.15, "desktop"),
        ),
    ),
    Scenario(
        "uncertain",
        "seasonality",
        (
            ("Metrics", "The launch overlapped with a holiday traffic mix shift that raised mobile share from 47% to 62%.", 1.15, "seasonality"),
            ("Experimentation", "The A/B sample has only 310 new users per arm, below the 900 needed for this variance.", 1.25, "power"),
            ("Support", "Complaints rose in one student cohort but fell among enterprise users, making the signal inconsistent.", 0.95, "cohort"),
            ("Metrics", "The strongest negative cohort is from a region that entered school holidays on the launch date.", 0.9, "holiday"),
        ),
        (
            ("Experimentation", "A limited ramp with two more weekdays would cut the confidence interval nearly in half.", 0.55, "monitor"),
            ("Infra", "Latency and error rates stayed below alert thresholds across mobile and desktop.", 0.5, "health"),
        ),
        (
            ("Sales", "One enterprise customer praised the feature during a renewal call.", 0.2, "sales"),
            ("Exec", "A single mobile cohort looks sharply negative before adjustment.", 0.2, "cohort"),
            ("Support", "Three screenshots look alarming but all came from the same campus network.", 0.15, "support"),
            ("Exec", "The board asked for a decision before the next product review.", 0.15, "deadline"),
        ),
    ),
)

INCIDENT_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "rollback_feature_flag",
        "cache_thundering_herd",
        (
            ("Deploy", "Error rate jumped from 0.4% to 7.8% exactly four minutes after the recommendation-cache flag reached 100%.", 1.25, "timing"),
            ("Observability/SRE", "Cache miss rate rose from 12% to 83% while database CPU followed 11 minutes later.", 1.25, "cache"),
            ("API", "The affected endpoint is /recommendations; checkout and account APIs stayed under 0.6% errors.", 0.95, "endpoint"),
            ("Database", "Rolling the flag back on one canary node dropped database reads by 68% in that shard.", 1.15, "recovery"),
        ),
        (
            ("Support", "Customers described slow recommendations before checkout failures, matching the upstream symptom.", 0.45, "symptom"),
            ("Database", "The lock dashboard shows waits as a downstream effect after cache misses spike.", 0.55, "downstream"),
        ),
        (
            ("Frontend", "Browser console warnings rose, but they came from an unrelated ad script.", 0.2, "console"),
            ("On-call Manager", "A database backup started near the incident, creating a normal CPU bump.", 0.2, "backup"),
            ("Support", "Several complaints mention checkout because the recommendation panel blocks page render.", 0.2, "support"),
            ("Deploy", "A harmless logging deploy finished 25 minutes earlier.", 0.15, "deploy"),
        ),
    ),
    Scenario(
        "scale_database",
        "database_lock_contention",
        (
            ("Database", "The orders table lock wait p99 increased from 35ms to 4200ms before API errors began.", 1.35, "locks"),
            ("Observability/SRE", "Database write queue depth reached 19x baseline while cache hit rate stayed normal.", 1.2, "queue"),
            ("API", "All failing requests share the order-write path; read-only endpoints remained healthy.", 1.0, "endpoint"),
            ("Database", "Adding two writer replicas reduced lock waits by 71% in the shadow test.", 1.1, "recovery"),
        ),
        (
            ("Deploy", "No feature flag changed in the 90 minutes before the first lock alert.", 0.5, "timing"),
            ("Support", "Support saw duplicate-order complaints consistent with write retries.", 0.4, "support"),
        ),
        (
            ("Frontend", "A frontend warning spiked because failed writes retried the same client callback.", 0.2, "frontend"),
            ("On-call Manager", "The incident started during a traffic surge, but API traffic was only 9% above forecast.", 0.2, "traffic"),
            ("Deploy", "A config diff looked suspicious but touched only staging.", 0.15, "config"),
            ("Support", "One region looked worse because its support queue was staffed first.", 0.15, "region"),
        ),
    ),
    Scenario(
        "patch_config",
        "third_party_api",
        (
            ("Deploy", "A config patch changed the payment-vendor timeout from 2s to 9s at 14:07.", 1.2, "config"),
            ("API", "Requests stall only when the fraud-check vendor call is in the trace span.", 1.25, "vendor"),
            ("Observability/SRE", "Internal service latency stays below 180ms until the third-party span begins.", 1.0, "trace"),
            ("Deploy", "Reverting the timeout to 2s in canary restored checkout success from 81% to 97%.", 1.2, "recovery"),
        ),
        (
            ("Support", "Customers report checkout hangs after payment details, not during product browsing.", 0.45, "support"),
            ("Database", "Database lock metrics stayed under warning thresholds during the incident.", 0.45, "database"),
        ),
        (
            ("Frontend", "A new frontend bundle emitted warnings, but sessions without vendor calls succeeded.", 0.2, "frontend"),
            ("On-call Manager", "CPU briefly rose during deploy verification.", 0.15, "cpu"),
            ("Support", "A single VIP customer blamed the redesign, but their trace shows a vendor timeout.", 0.2, "vip"),
            ("Database", "Replica lag rose to 1.2s, below the 4s alert threshold.", 0.15, "replica"),
        ),
    ),
    Scenario(
        "no_action_monitor",
        "bad_metrics_pipeline",
        (
            ("Observability/SRE", "The alert starts exactly when the metrics pipeline switched from request_count to sampled_request_count.", 1.3, "metrics"),
            ("API", "Raw gateway logs show success rate at 99.1% while the dashboard reports 88.4%.", 1.2, "logs"),
            ("Support", "Customer contacts stayed at 12 per hour, matching the normal Saturday baseline.", 0.95, "support"),
            ("Deploy", "No production binary or feature flag changed within two hours of the alert.", 1.0, "deploy"),
        ),
        (
            ("Frontend", "Synthetic browser checks stayed green across the reported outage window.", 0.45, "synthetic"),
            ("Database", "Database metrics were normal except for dashboard-derived error panels.", 0.45, "database"),
        ),
        (
            ("On-call Manager", "A single-region metric showed a dramatic dip before sampling adjustment.", 0.2, "region"),
            ("Frontend", "Console warnings increased after an ad-network script update.", 0.2, "console"),
            ("Support", "One angry customer thread was escalated twice, inflating apparent severity.", 0.15, "support"),
            ("API", "Retry volume rose 4%, consistent with a routine mobile carrier issue.", 0.15, "retry"),
        ),
    ),
)

INVESTMENT_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "invest",
        "durable_growth",
        (
            ("Growth", "Weekly retained active teams grew from 820 to 1560 over 12 weeks while signup source mix stayed stable.", 1.25, "growth"),
            ("Finance", "Net revenue retention is 128% across cohorts older than six months.", 1.15, "retention"),
            ("Customer Calls", "Seven of nine reference customers expanded seats after a paid pilot without founder involvement.", 1.05, "customers"),
            ("Market Analyst", "Three competitors raised prices while this company still won 41% of evaluated bakeoffs.", 0.95, "market"),
        ),
        (
            ("Founder", "The founder disclosed the two weak pilots and separated them from retained cohort metrics.", 0.55, "candor"),
            ("Technical Diligence", "Infrastructure cost per active team fell 23% after the March architecture change.", 0.5, "cost"),
        ),
        (
            ("Growth", "Press coverage created a vanity signup spike in week four.", 0.2, "press"),
            ("Founder", "The founder previously worked at a famous AI lab.", 0.15, "background"),
            ("Market Analyst", "A competitor announced a large fundraise.", 0.15, "competitor"),
            ("Customer Calls", "Demo feedback was enthusiastic before procurement review.", 0.15, "demo"),
        ),
    ),
    Scenario(
        "pass",
        "hidden_churn",
        (
            ("Finance", "Logo churn is 4% monthly among customers older than 90 days, double the deck's blended number.", 1.35, "churn"),
            ("Customer Calls", "Four of six churned customers cite missing workflow integrations after initial excitement.", 1.15, "customers"),
            ("Growth", "Signup growth is driven by a paid channel whose 60-day retained usage is only 18%.", 1.1, "retention"),
            ("Founder", "The founder's dashboard excludes expired pilots from churn calculations.", 1.0, "misreporting"),
        ),
        (
            ("Market Analyst", "The category has demand, but buyers compare the product against bundled incumbents.", 0.45, "market"),
            ("Technical Diligence", "The integration roadmap is feasible but would take at least two quarters.", 0.45, "roadmap"),
        ),
        (
            ("Founder", "Top-line signups grew 64% quarter over quarter.", 0.25, "signup"),
            ("Growth", "A conference demo produced 900 waitlist emails.", 0.2, "conference"),
            ("Market Analyst", "Two competitors raised large rounds last month.", 0.15, "competitor"),
            ("Customer Calls", "The happiest customer offered a glowing quote.", 0.15, "quote"),
        ),
    ),
    Scenario(
        "pass",
        "margin_problem",
        (
            ("Finance", "Gross margin is 28% after support and inference costs, not the 71% shown before allocations.", 1.35, "margin"),
            ("Technical Diligence", "Each enterprise workflow triggers 14 expensive model calls that cannot be cached safely.", 1.15, "cost"),
            ("Customer Calls", "Customers demand unlimited usage clauses that prevent passing costs through.", 1.0, "pricing"),
            ("Finance", "The largest customer is unprofitable by $38k per quarter at current utilization.", 1.05, "customer"),
        ),
        (
            ("Founder", "The founder has a plausible margin plan but it depends on an unbuilt compiler.", 0.5, "plan"),
            ("Market Analyst", "Competitors with simpler workflows report margins above 60%.", 0.4, "benchmark"),
        ),
        (
            ("Growth", "Revenue grew 19% month over month from a small base.", 0.2, "revenue"),
            ("Founder", "The demo feels polished and fast on a curated dataset.", 0.15, "demo"),
            ("Market Analyst", "The market category is hot with several acquisitions.", 0.15, "market"),
            ("Customer Calls", "One customer called the product mission-critical but negotiated the steepest discount.", 0.15, "quote"),
        ),
    ),
    Scenario(
        "wait_for_more_data",
        "legal_risk",
        (
            ("Legal", "A draft enterprise contract grants exclusivity that would block 37% of the pipeline if signed.", 1.25, "contract"),
            ("Founder", "The founder says the clause is standard, but the counterparty marked it non-negotiable.", 1.0, "founder"),
            ("Customer Calls", "Two reference customers say they need clarity on data-retention rights before expanding.", 1.0, "customers"),
            ("Finance", "The next financing milestone assumes the disputed contract closes within 45 days.", 0.95, "runway"),
        ),
        (
            ("Market Analyst", "Demand is real, but legal terms determine whether the best segment stays available.", 0.45, "market"),
            ("Technical Diligence", "The technical product does not create the legal risk; contracting does.", 0.35, "technical"),
        ),
        (
            ("Growth", "Signup growth remains strong in self-serve trials.", 0.2, "growth"),
            ("Founder", "The founder has an impressive prior exit.", 0.15, "background"),
            ("Market Analyst", "A strategic acquirer monitors the space.", 0.15, "acquirer"),
            ("Customer Calls", "A small customer praised the roadmap in a public webinar.", 0.15, "webinar"),
        ),
    ),
    Scenario(
        "pass",
        "founder_misreporting",
        (
            ("Finance", "Three revenue invoices totaling $410k were booked before signed order forms existed.", 1.35, "revenue"),
            ("Legal", "Two customer references deny agreeing to the deployment dates shown in the data room.", 1.15, "references"),
            ("Customer Calls", "A reference customer says the founder described an unpaid pilot as a production rollout.", 1.1, "pilot"),
            ("Founder", "The founder changed the cohort export after diligence questions and did not preserve the original file.", 1.0, "export"),
        ),
        (
            ("Technical Diligence", "The codebase is credible, so the issue is reporting trust rather than product feasibility.", 0.45, "technical"),
            ("Market Analyst", "Market demand exists, but governance risk overwhelms the positive signal.", 0.45, "market"),
        ),
        (
            ("Growth", "The public waitlist crossed 12k emails after press coverage.", 0.2, "waitlist"),
            ("Founder", "The founder gives a compelling product narrative.", 0.2, "story"),
            ("Market Analyst", "The company's category is in a strong funding cycle.", 0.15, "category"),
            ("Customer Calls", "One current customer loves the product and wants more features.", 0.15, "quote"),
        ),
    ),
    Scenario(
        "invest",
        "market_pull",
        (
            ("Customer Calls", "Six of eight customers built internal workarounds before finding the product, showing urgent pull.", 1.2, "pull"),
            ("Growth", "Inbound qualified pipeline grew 52% without paid campaigns after the first customer webinar.", 1.1, "pipeline"),
            ("Market Analyst", "Procurement teams named the problem a top-three 2026 budget item in 11 of 14 interviews.", 1.0, "market"),
            ("Finance", "Expansion revenue from the first three accounts covers 73% of current monthly burn.", 0.95, "expansion"),
        ),
        (
            ("Founder", "The founder gave conservative pipeline odds and corrected an overcount during diligence.", 0.5, "candor"),
            ("Technical Diligence", "The product has rough edges but no blocker for the near-term use case.", 0.4, "technical"),
        ),
        (
            ("Growth", "Press mentions rose after a competitor outage.", 0.15, "press"),
            ("Founder", "The founder has a charismatic demo style.", 0.15, "demo"),
            ("Market Analyst", "A competitor raised a large round.", 0.15, "competitor"),
            ("Legal", "A standard security review is still open.", 0.15, "security"),
        ),
    ),
)

SCENARIOS = {
    "product_rollback": PRODUCT_SCENARIOS,
    "incident_response": INCIDENT_SCENARIOS,
    "investment_committee": INVESTMENT_SCENARIOS,
}


def _select_roles(domain: str, difficulty: str, seed: int) -> list[str]:
    roles = list(ROLE_IDS[domain])
    count = DIFFICULTIES[difficulty].specialist_count
    if count >= len(roles):
        return roles
    # Rotate optional omissions so no one public role is always present or absent.
    rotated = roles[seed % len(roles) :] + roles[: seed % len(roles)]
    selected = rotated[:count]
    required_anchors = {
        "product_rollback": ["Metrics", "Infra", "Experimentation"],
        "incident_response": ["API", "Database", "Observability/SRE"],
        "investment_committee": ["Finance", "Customer Calls", "Market Analyst"],
    }[domain]
    for anchor in required_anchors:
        if anchor not in selected:
            selected[-1] = anchor
    return list(dict.fromkeys(selected))[:count]


def _safe_topic(role: str, scenario: Scenario) -> str:
    root_words = scenario.root_cause.replace("_", " ")
    if role in {"Sales", "Founder", "Exec", "On-call Manager", "Growth"}:
        return "stakeholder signal"
    if role in {"Metrics", "Observability/SRE", "Finance"}:
        return "measurement quality"
    if role in {"Infra", "Database", "API", "Technical Diligence"}:
        return "system behavior"
    if role in {"Legal"}:
        return "contract risk"
    if role in {"Experimentation"}:
        return "sample quality"
    if role in {"Support", "Customer Calls"}:
        return "user reports"
    return root_words


def _persona_for_role(domain: str, role: str, scenario: Scenario, seed: int, owns_key: bool) -> str:
    if owns_key and seed % 4 in {0, 1}:
        return "underconfident_expert"
    if role in {"Sales", "On-call Manager", "Growth"}:
        return "verbose_lobbyist"
    if role in {"Exec", "Deploy"}:
        return "strategic_biased"
    if role == "Founder":
        if scenario.root_cause in {"founder_misreporting", "hidden_churn", "legal_risk"}:
            return "strategic_biased"
        if seed % 3 == 0:
            return "honest_dense"
        return "verbose_lobbyist"
    if role in {"Experimentation", "Technical Diligence", "Legal"} and seed % 2 == 0:
        return "skeptic"
    if role in {"Support", "Customer Calls", "Frontend"}:
        return "noisy_observer"
    return "honest_dense"


def _public_bid(persona: str, role: str, scenario: Scenario, requested_tokens: int) -> tuple[str, str]:
    topic = _safe_topic(role, scenario)
    if persona == "underconfident_expert":
        return (
            f"I have a mild-looking {topic} signal that may be worth checking if budget allows. "
            f"Requesting {requested_tokens} tokens.",
            "low",
        )
    if persona == "verbose_lobbyist":
        return (
            f"My lane has a high-priority story and I can give concrete examples. "
            f"Requesting {requested_tokens} tokens.",
            "high",
        )
    if persona == "strategic_biased":
        return (
            f"I can explain the decision context and risks from my seat, though some details are sensitive. "
            f"Requesting {requested_tokens} tokens.",
            "high",
        )
    if persona == "skeptic":
        return (
            f"I can test whether the obvious explanation survives caveats and sampling checks. "
            f"Requesting {requested_tokens} tokens.",
            "medium",
        )
    if persona == "noisy_observer":
        return (
            f"I saw mixed {topic} signals, including some anecdotes that may or may not generalize. "
            f"Requesting {requested_tokens} tokens.",
            "medium",
        )
    return (
        f"I can summarize structured {topic} evidence without claiming certainty from the public bid. "
        f"Requesting {requested_tokens} tokens.",
        "medium",
    )


def _requested_tokens(persona: str, difficulty: str, seed: int) -> int:
    base = {"easy": 82, "medium": 94, "hard": 107}[difficulty]
    if persona == "verbose_lobbyist":
        return base + 41 + (seed % 3) * 13
    if persona == "underconfident_expert":
        return base - 27
    if persona == "strategic_biased":
        return base + 14
    return base


def _add_facts(
    *,
    domain: str,
    scenario: Scenario,
    difficulty: str,
    selected_roles: list[str],
) -> tuple[dict[str, FactAtom], dict[str, list[str]], list[str], list[str], list[str]]:
    cfg = DIFFICULTIES[difficulty]
    facts: dict[str, FactAtom] = {}
    by_role: dict[str, list[str]] = {role: [] for role in selected_roles}
    required_ids: list[str] = []
    supporting_ids: list[str] = []
    decoy_ids: list[str] = []

    def assign(role: str, fact_id: str) -> None:
        stable = sum(ord(ch) for ch in f"{role}:{fact_id}")
        owner = role if role in by_role else selected_roles[stable % len(selected_roles)]
        by_role[owner].append(fact_id)

    for idx, (role, text, weight, cluster) in enumerate(scenario.required[: cfg.required_limit], 1):
        fact_id = f"F{idx}"
        facts[fact_id] = make_fact(
            fact_id=fact_id,
            text=text,
            domain=domain,
            root_cause=scenario.root_cause,
            kind="required",
            weight=weight,
            role=role,
            cluster_id=f"{scenario.root_cause}:{cluster}",
        )
        required_ids.append(fact_id)
        assign(role, fact_id)

    for idx, (role, text, weight, cluster) in enumerate(scenario.supporting[: cfg.supporting_limit], 1):
        fact_id = f"S{idx}"
        facts[fact_id] = make_fact(
            fact_id=fact_id,
            text=text,
            domain=domain,
            root_cause=scenario.root_cause,
            kind="supporting",
            weight=weight,
            role=role,
            cluster_id=f"{scenario.root_cause}:{cluster}",
        )
        supporting_ids.append(fact_id)
        assign(role, fact_id)

    for idx, (role, text, weight, cluster) in enumerate(scenario.decoys[: cfg.decoy_limit], 1):
        fact_id = f"D{idx}"
        facts[fact_id] = make_fact(
            fact_id=fact_id,
            text=text,
            domain=domain,
            root_cause=scenario.root_cause,
            kind="decoy",
            weight=weight,
            role=role,
            cluster_id=f"decoy:{cluster}",
            extra_tags=extract_tags(role),
        )
        decoy_ids.append(fact_id)
        assign(role, fact_id)

    return facts, by_role, required_ids, supporting_ids, decoy_ids


def build_world(
    *,
    domain: str,
    difficulty: str,
    seed: int,
    world_id: str | None = None,
    variant: int | None = None,
) -> World:
    """Build a deterministic generated world."""

    if domain not in SCENARIOS:
        raise ValueError(f"Unknown domain: {domain}")
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"Unknown difficulty: {difficulty}")
    scenarios = SCENARIOS[domain]
    scenario = scenarios[(variant if variant is not None else seed) % len(scenarios)]
    cfg = DIFFICULTIES[difficulty]
    selected_roles = _select_roles(domain, difficulty, seed)
    facts, by_role, required_ids, supporting_ids, decoy_ids = _add_facts(
        domain=domain,
        scenario=scenario,
        difficulty=difficulty,
        selected_roles=selected_roles,
    )
    key_fact = required_ids[0] if required_ids else None
    specialists: dict[str, Specialist] = {}
    for role in selected_roles:
        owns_key = key_fact in by_role.get(role, [])
        persona = _persona_for_role(domain, role, scenario, seed, owns_key)
        requested = _requested_tokens(persona, difficulty, seed)
        bid, priority = _public_bid(persona, role, scenario, requested)
        role_id = ROLE_IDS[domain][role]
        specialists[role_id] = Specialist(
            id=role_id,
            name=role,
            role=role,
            persona_policy=persona,  # type: ignore[arg-type]
            public_bid=bid,
            requested_tokens=requested,
            claimed_priority=priority,
            private_fact_ids=by_role.get(role, []),
            bias_target="avoid_bad_news" if persona == "strategic_biased" else None,
            verbosity=1.35 if persona == "verbose_lobbyist" else 0.8 if persona == "honest_dense" else 1.0,
            reliability=0.95 if persona in {"honest_dense", "underconfident_expert"} else 0.75,
        )

    wid = world_id or f"{DOMAIN_SLUGS[domain]}-{difficulty}-{seed:03d}"
    return World(
        world_id=wid,
        seed=seed,
        domain=domain,
        difficulty=difficulty,
        narrative=DOMAIN_NARRATIVES[domain],
        token_budget=cfg.token_budget if difficulty != "hard" else cfg.token_budget + (seed % 3) * 10,
        max_interactions=cfg.max_interactions,
        decision_options=list(DECISIONS[domain]),
        root_cause_options=list(ROOT_CAUSES[domain]),
        truth_decision=scenario.decision,
        truth_root_cause=scenario.root_cause,
        facts=facts,
        required_fact_ids=required_ids,
        supporting_fact_ids=supporting_ids,
        decoy_fact_ids=decoy_ids,
        specialists=specialists,
        metadata={
            "requires_cross_exam": any(
                sp.persona_policy in {"underconfident_expert", "strategic_biased"}
                and any(fid in required_ids for fid in sp.private_fact_ids)
                for sp in specialists.values()
            ),
            "direct_floor_solvable": seed % 4 in {2, 3},
            "scenario_root": scenario.root_cause,
        },
    )


DOMAIN_BUILDERS: dict[str, Callable[..., World]] = {
    "product_rollback": build_world,
    "incident_response": build_world,
    "investment_committee": build_world,
}


def _task_seed_for(domain: str, difficulty: str, ordinal: int) -> int:
    domain_offset = {"product_rollback": 100, "incident_response": 200, "investment_committee": 300}[domain]
    diff_offset = {"easy": 10, "medium": 20, "hard": 30}[difficulty]
    return domain_offset + diff_offset + ordinal


def shipped_task_specs() -> list[dict[str, object]]:
    """Return the 36 concrete shipped task rows."""

    required_first = [
        ("product_rollback", "easy", 1, "product-rollback-easy-001"),
        ("product_rollback", "medium", 2, "product-rollback-medium-002"),
        ("product_rollback", "hard", 3, "product-rollback-hard-003"),
        ("incident_response", "medium", 4, "incident-response-medium-004"),
        ("investment_committee", "hard", 5, "investment-committee-hard-005"),
    ]
    rows: list[dict[str, object]] = [
        {"domain": d, "difficulty": diff, "seed": seed, "world_id": slug}
        for d, diff, seed, slug in required_first
    ]
    seen_keys = {(d, diff, seed) for d, diff, seed, _ in required_first}
    counts: dict[tuple[str, str], int] = {}
    for d, diff, _seed, _slug in required_first:
        counts[(d, diff)] = counts.get((d, diff), 0) + 1

    idx = 6
    for domain in ("product_rollback", "incident_response", "investment_committee"):
        for difficulty in ("easy", "medium", "hard"):
            ordinal = 1
            while counts.get((domain, difficulty), 0) < 4:
                seed = _task_seed_for(domain, difficulty, ordinal)
                ordinal += 1
                if (domain, difficulty, seed) in seen_keys:
                    continue
                slug = f"{DOMAIN_SLUGS[domain]}-{difficulty}-{idx:03d}"
                rows.append({"domain": domain, "difficulty": difficulty, "seed": seed, "world_id": slug})
                seen_keys.add((domain, difficulty, seed))
                counts[(domain, difficulty)] = counts.get((domain, difficulty), 0) + 1
                idx += 1
    return rows


def build_shipped_worlds() -> list[World]:
    """Build all shipped worlds."""

    return [
        build_world(
            domain=str(row["domain"]),
            difficulty=str(row["difficulty"]),
            seed=int(row["seed"]),
            world_id=str(row["world_id"]),
        )
        for row in shipped_task_specs()
    ]


def iter_worlds(rows: Iterable[dict[str, object]] | None = None) -> Iterable[World]:
    """Yield worlds from task rows."""

    for row in rows or shipped_task_specs():
        yield build_world(
            domain=str(row["domain"]),
            difficulty=str(row["difficulty"]),
            seed=int(row["seed"]),
            world_id=str(row["world_id"]),
        )
