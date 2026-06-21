"""Scenario library for deterministic Context Window Parliament worlds."""

from __future__ import annotations

from dataclasses import dataclass

TASKSET_NAME = "context-window-parliament-mvp"
TASKS_PER_DOMAIN = 50
DIFFICULTY_TARGETS = {"easy": 17, "medium": 17, "hard": 16}


@dataclass(frozen=True)
class DifficultyConfig:
    token_budget: int
    max_interactions: int
    specialist_count: int
    required_limit: int
    decoy_limit: int
    supporting_limit: int


@dataclass(frozen=True)
class Scenario:
    decision: str
    root_cause: str
    required: tuple[tuple[str, str, float, str], ...]
    supporting: tuple[tuple[str, str, float, str], ...]
    decoys: tuple[tuple[str, str, float, str], ...]


@dataclass(frozen=True)
class ScenarioSpec:
    decision: str
    root_cause: str
    subject: str
    metric: str
    population: str
    trigger: str
    remedy: str
    decoy: str
    window: str
    before: str
    after: str
    control: str
    sample: str
    recovery: str


DIFFICULTIES: dict[str, DifficultyConfig] = {
    "easy": DifficultyConfig(650, 12, 5, 3, 3, 2),
    "medium": DifficultyConfig(500, 10, 6, 4, 5, 3),
    "hard": DifficultyConfig(400, 8, 7, 5, 7, 4),
}

DOMAIN_ORDER = (
    "product_rollback",
    "incident_response",
    "investment_committee",
    "security_access_review",
    "supply_chain_disruption",
    "manufacturing_quality",
    "research_claim_review",
    "marketplace_integrity",
    "customer_success_escalation",
    "civic_program_evaluation",
)

DOMAIN_NARRATIVES = {
    "product_rollback": "An internal product review is deciding whether to roll back Feature X after launch.",
    "incident_response": "An incident commander must diagnose a production incident and choose action.",
    "investment_committee": "An investment committee must decide whether to invest, pass, or wait.",
    "security_access_review": "A security review board must decide how to respond to an access anomaly.",
    "supply_chain_disruption": "An operations team must identify why a customer shipment plan is failing.",
    "manufacturing_quality": "A manufacturing cell must diagnose a quality excursion before the next production run.",
    "research_claim_review": "A review committee must decide whether a research claim is reliable enough to act on.",
    "marketplace_integrity": "A marketplace integrity team must respond to suspicious platform behavior.",
    "customer_success_escalation": "A customer-success escalation room must choose the right recovery action.",
    "civic_program_evaluation": "A civic program board must decide whether a pilot should continue, pause, or change.",
}

DOMAIN_SLUGS = {
    "product_rollback": "product-rollback",
    "incident_response": "incident-response",
    "investment_committee": "investment-committee",
    "security_access_review": "security-access-review",
    "supply_chain_disruption": "supply-chain-disruption",
    "manufacturing_quality": "manufacturing-quality",
    "research_claim_review": "research-claim-review",
    "marketplace_integrity": "marketplace-integrity",
    "customer_success_escalation": "customer-success-escalation",
    "civic_program_evaluation": "civic-program-evaluation",
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
    "security_access_review": [
        "disable_account",
        "revoke_role",
        "revoke_token",
        "block_oauth_app",
        "close_false_positive",
        "rotate_secret",
        "monitor",
        "uncertain",
    ],
    "supply_chain_disruption": [
        "expedite_supplier_rework",
        "hold_for_customs",
        "revise_forecast",
        "book_backup_carrier",
        "reroute_port",
        "allocate_material",
        "recount_warehouse",
        "fix_labeling",
        "uncertain",
    ],
    "manufacturing_quality": [
        "stop_line",
        "quarantine_batch",
        "recalibrate_sensor",
        "retrain_shift",
        "replace_packaging",
        "adjust_environment",
        "replace_fixture",
        "fix_labels",
        "uncertain",
    ],
    "research_claim_review": [
        "reject_claim",
        "revise_claim",
        "replicate_before_launch",
        "accept_claim",
        "audit_dataset",
        "uncertain",
    ],
    "marketplace_integrity": [
        "ban_seller_ring",
        "tighten_fraud_rules",
        "reverse_policy_action",
        "remove_fake_reviews",
        "monitor_seasonal_spike",
        "rate_limit_scraping",
        "review_chargebacks",
        "uncertain",
    ],
    "customer_success_escalation": [
        "ship_fix",
        "correct_billing",
        "rewrite_docs",
        "schedule_training",
        "renegotiate_scope",
        "wait_for_vendor",
        "repair_import",
        "uncertain",
    ],
    "civic_program_evaluation": [
        "continue_program",
        "redesign_outreach",
        "pause_for_measurement",
        "tighten_eligibility",
        "fix_reporting",
        "scale_program",
        "uncertain",
    ],
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
    "security_access_review": [
        "phishing_compromise",
        "overbroad_role",
        "orphaned_token",
        "oauth_app_abuse",
        "false_positive_alert",
        "contractor_offboarding",
        "secret_leak",
        "impossible_travel",
        "unknown",
    ],
    "supply_chain_disruption": [
        "supplier_quality",
        "customs_hold",
        "demand_forecast_error",
        "carrier_capacity",
        "port_congestion",
        "material_shortage",
        "warehouse_miscount",
        "regulatory_labeling",
        "unknown",
    ],
    "manufacturing_quality": [
        "machine_drift",
        "material_batch",
        "sensor_calibration",
        "operator_training",
        "packaging_defect",
        "environmental_condition",
        "test_fixture_wear",
        "labeling_mixup",
        "unknown",
    ],
    "research_claim_review": [
        "sampling_bias",
        "measurement_artifact",
        "confounder",
        "data_leakage",
        "genuine_effect",
        "underpowered_study",
        "annotation_bias",
        "protocol_deviation",
        "unknown",
    ],
    "marketplace_integrity": [
        "bot_ring",
        "seller_collusion",
        "payment_fraud",
        "policy_misclassification",
        "review_brigading",
        "seasonal_spike",
        "inventory_scrape",
        "chargeback_abuse",
        "unknown",
    ],
    "customer_success_escalation": [
        "integration_mismatch",
        "billing_misconfiguration",
        "documentation_gap",
        "product_bug",
        "contract_scope_confusion",
        "adoption_training_gap",
        "vendor_outage",
        "data_import_error",
        "unknown",
    ],
    "civic_program_evaluation": [
        "selection_bias",
        "implementation_fidelity",
        "demand_shift",
        "measurement_lag",
        "true_impact",
        "reporting_artifact",
        "outreach_gap",
        "eligibility_confusion",
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
    "security_access_review": {
        "Identity": "identity",
        "SOC Analyst": "soc_analyst",
        "App Owner": "app_owner",
        "HR Ops": "hr_ops",
        "Network": "network",
        "Compliance": "compliance",
        "Vendor Manager": "vendor_manager",
    },
    "supply_chain_disruption": {
        "Quality": "quality",
        "Logistics": "logistics",
        "Demand Planning": "demand_planning",
        "Warehouse": "warehouse",
        "Supplier Manager": "supplier_manager",
        "Regulatory": "regulatory",
        "Finance": "finance",
    },
    "manufacturing_quality": {
        "Line Engineer": "line_engineer",
        "Quality Lab": "quality_lab",
        "Maintenance": "maintenance",
        "Shift Lead": "shift_lead",
        "Packaging": "packaging",
        "Process Control": "process_control",
        "Supplier Quality": "supplier_quality",
    },
    "research_claim_review": {
        "Statistician": "statistician",
        "Principal Investigator": "principal_investigator",
        "Field Coordinator": "field_coordinator",
        "Data Engineer": "data_engineer",
        "Reviewer": "reviewer",
        "Sponsor": "sponsor",
        "Ethics Lead": "ethics_lead",
    },
    "marketplace_integrity": {
        "Trust & Safety": "trust_safety",
        "Payments": "payments",
        "Seller Ops": "seller_ops",
        "Customer Support": "customer_support",
        "Search Ranking": "search_ranking",
        "Growth": "growth",
        "Legal Policy": "legal_policy",
    },
    "customer_success_escalation": {
        "Solutions Engineer": "solutions_engineer",
        "Support Lead": "support_lead",
        "Billing Ops": "billing_ops",
        "Product Manager": "product_manager",
        "Docs Lead": "docs_lead",
        "Account Manager": "account_manager",
        "Vendor Liaison": "vendor_liaison",
    },
    "civic_program_evaluation": {
        "Data Analyst": "data_analyst",
        "Field Office": "field_office",
        "Program Manager": "program_manager",
        "Community Liaison": "community_liaison",
        "Finance Auditor": "finance_auditor",
        "Eligibility Lead": "eligibility_lead",
        "External Evaluator": "external_evaluator",
    },
}

ANCHOR_ROLES = {
    "product_rollback": ["Metrics", "Infra", "Experimentation"],
    "incident_response": ["API", "Database", "Observability/SRE"],
    "investment_committee": ["Finance", "Customer Calls", "Market Analyst"],
    "security_access_review": ["Identity", "SOC Analyst", "Compliance"],
    "supply_chain_disruption": ["Quality", "Logistics", "Demand Planning"],
    "manufacturing_quality": ["Line Engineer", "Quality Lab", "Process Control"],
    "research_claim_review": ["Statistician", "Data Engineer", "Reviewer"],
    "marketplace_integrity": ["Trust & Safety", "Payments", "Search Ranking"],
    "customer_success_escalation": ["Solutions Engineer", "Support Lead", "Billing Ops"],
    "civic_program_evaluation": ["Data Analyst", "Field Office", "External Evaluator"],
}

ROLE_TENDENCIES = {
    "Sales": "loud",
    "On-call Manager": "loud",
    "Growth": "loud",
    "Vendor Manager": "loud",
    "Finance": "loud",
    "Packaging": "loud",
    "Sponsor": "loud",
    "Account Manager": "loud",
    "Community Liaison": "loud",
    "Exec": "strategic",
    "Deploy": "strategic",
    "Founder": "strategic_when_bad",
    "App Owner": "strategic",
    "Supplier Manager": "strategic",
    "Maintenance": "strategic",
    "Principal Investigator": "strategic",
    "Seller Ops": "strategic",
    "Product Manager": "strategic",
    "Program Manager": "strategic",
    "Experimentation": "skeptic",
    "Technical Diligence": "skeptic",
    "Legal": "skeptic",
    "HR Ops": "skeptic",
    "Regulatory": "skeptic",
    "Quality Lab": "skeptic",
    "Data Engineer": "skeptic",
    "Search Ranking": "skeptic",
    "Billing Ops": "skeptic",
    "Finance Auditor": "skeptic",
    "Support": "noisy",
    "Customer Calls": "noisy",
    "Frontend": "noisy",
    "SOC Analyst": "noisy",
    "Warehouse": "noisy",
    "Shift Lead": "noisy",
    "Field Coordinator": "noisy",
    "Customer Support": "noisy",
    "Support Lead": "noisy",
    "Field Office": "noisy",
}

ROLE_TOPICS = {
    "Sales": "stakeholder signal",
    "Founder": "founder signal",
    "Exec": "executive context",
    "On-call Manager": "incident coordination",
    "Growth": "growth signal",
    "Metrics": "measurement quality",
    "Observability/SRE": "measurement quality",
    "Finance": "financial evidence",
    "Infra": "system behavior",
    "Database": "system behavior",
    "API": "system behavior",
    "Technical Diligence": "technical risk",
    "Legal": "contract risk",
    "Experimentation": "sample quality",
    "Support": "user reports",
    "Customer Calls": "customer evidence",
    "Identity": "access evidence",
    "SOC Analyst": "alert evidence",
    "App Owner": "application ownership",
    "HR Ops": "offboarding records",
    "Network": "network telemetry",
    "Compliance": "audit evidence",
    "Vendor Manager": "vendor context",
    "Quality": "supplier evidence",
    "Logistics": "shipment evidence",
    "Demand Planning": "forecast evidence",
    "Warehouse": "inventory records",
    "Supplier Manager": "supplier context",
    "Regulatory": "labeling evidence",
    "Line Engineer": "line telemetry",
    "Quality Lab": "lab evidence",
    "Maintenance": "maintenance context",
    "Shift Lead": "shift observations",
    "Packaging": "packaging signal",
    "Process Control": "process data",
    "Supplier Quality": "material evidence",
    "Statistician": "statistical evidence",
    "Principal Investigator": "study context",
    "Field Coordinator": "field observations",
    "Data Engineer": "dataset integrity",
    "Reviewer": "review evidence",
    "Sponsor": "stakeholder signal",
    "Ethics Lead": "protocol evidence",
    "Trust & Safety": "platform evidence",
    "Payments": "payment evidence",
    "Seller Ops": "seller context",
    "Customer Support": "buyer reports",
    "Search Ranking": "ranking evidence",
    "Legal Policy": "policy evidence",
    "Solutions Engineer": "integration evidence",
    "Support Lead": "ticket evidence",
    "Billing Ops": "billing evidence",
    "Product Manager": "product context",
    "Docs Lead": "documentation evidence",
    "Account Manager": "account context",
    "Vendor Liaison": "vendor context",
    "Data Analyst": "program measurement",
    "Field Office": "field reports",
    "Program Manager": "program context",
    "Community Liaison": "participant reports",
    "Finance Auditor": "audit evidence",
    "Eligibility Lead": "eligibility records",
    "External Evaluator": "evaluation evidence",
}


def _s(
    decision: str,
    root: str,
    required: tuple[tuple[str, str, float, str], ...],
    supporting: tuple[tuple[str, str, float, str], ...],
    decoys: tuple[tuple[str, str, float, str], ...],
) -> Scenario:
    return Scenario(decision, root, required, supporting, decoys)


PRODUCT_BASE: tuple[Scenario, ...] = (
    _s(
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
    _s(
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
    _s(
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
    _s(
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


INCIDENT_BASE: tuple[Scenario, ...] = (
    _s(
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
    _s(
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
    _s(
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
    _s(
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


INVESTMENT_BASE: tuple[Scenario, ...] = (
    _s(
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
    _s(
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
    _s(
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
    _s(
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
    _s(
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
    _s(
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

DOMAIN_FACT_ROLES = {
    "product_rollback": (
        ("Metrics", "Experimentation", "Support", "Infra"),
        ("Exec", "Infra"),
        ("Sales", "Exec", "Sales", "Support"),
    ),
    "incident_response": (
        ("Observability/SRE", "API", "Support", "Database"),
        ("Deploy", "Database"),
        ("On-call Manager", "Frontend", "Support", "Deploy"),
    ),
    "investment_committee": (
        ("Finance", "Customer Calls", "Market Analyst", "Technical Diligence"),
        ("Founder", "Legal"),
        ("Growth", "Founder", "Market Analyst", "Customer Calls"),
    ),
    "security_access_review": (
        ("Identity", "SOC Analyst", "Network", "Compliance"),
        ("HR Ops", "Identity"),
        ("Vendor Manager", "App Owner", "SOC Analyst", "HR Ops"),
    ),
    "supply_chain_disruption": (
        ("Quality", "Logistics", "Demand Planning", "Warehouse"),
        ("Regulatory", "Quality"),
        ("Finance", "Supplier Manager", "Logistics", "Warehouse"),
    ),
    "manufacturing_quality": (
        ("Line Engineer", "Quality Lab", "Process Control", "Supplier Quality"),
        ("Maintenance", "Quality Lab"),
        ("Packaging", "Shift Lead", "Maintenance", "Supplier Quality"),
    ),
    "research_claim_review": (
        ("Statistician", "Data Engineer", "Reviewer", "Field Coordinator"),
        ("Ethics Lead", "Statistician"),
        ("Sponsor", "Principal Investigator", "Field Coordinator", "Reviewer"),
    ),
    "marketplace_integrity": (
        ("Trust & Safety", "Payments", "Search Ranking", "Customer Support"),
        ("Legal Policy", "Trust & Safety"),
        ("Growth", "Seller Ops", "Customer Support", "Payments"),
    ),
    "customer_success_escalation": (
        ("Solutions Engineer", "Support Lead", "Billing Ops", "Docs Lead"),
        ("Product Manager", "Solutions Engineer"),
        ("Account Manager", "Vendor Liaison", "Support Lead", "Product Manager"),
    ),
    "civic_program_evaluation": (
        ("Data Analyst", "Field Office", "External Evaluator", "Eligibility Lead"),
        ("Finance Auditor", "Data Analyst"),
        ("Community Liaison", "Program Manager", "Field Office", "Finance Auditor"),
    ),
}


def _generated_scenario(domain: str, spec: ScenarioSpec) -> Scenario:
    required_roles, supporting_roles, decoy_roles = DOMAIN_FACT_ROLES[domain]
    root_words = spec.root_cause.replace("_", " ")
    return Scenario(
        spec.decision,
        spec.root_cause,
        (
            (
                required_roles[0],
                f"{spec.subject} {spec.metric} moved from {spec.before} to {spec.after} during {spec.window}, and the rows share {root_words} markers.",
                1.35,
                "metric",
            ),
            (
                required_roles[1],
                f"The {spec.population} slice shows the same {root_words} pattern after {spec.trigger}, while {spec.control} stayed within 2% of baseline.",
                1.2,
                "cohort",
            ),
            (
                required_roles[2],
                f"A blind audit of {spec.subject} found the decisive anomaly only when the team filtered for {root_words} rather than the public headline.",
                1.05,
                "audit",
            ),
            (
                required_roles[3],
                f"When the team tried {spec.remedy}, the affected slice improved from {spec.after} to {spec.recovery} without moving the unaffected controls.",
                1.15,
                "recovery",
            ),
        ),
        (
            (
                supporting_roles[0],
                f"The operational timeline rules out {spec.decoy} because its timestamp lands outside {spec.window}.",
                0.5,
                "timing",
            ),
            (
                supporting_roles[1],
                f"The smallest safe intervention is {spec.remedy}, which addresses {root_words} without broad collateral changes.",
                0.45,
                "scope",
            ),
        ),
        (
            (
                decoy_roles[0],
                f"A visible stakeholder dashboard for {spec.subject} highlighted {spec.decoy}, but that panel aggregates unaffected and affected records together.",
                0.2,
                "headline",
            ),
            (
                decoy_roles[1],
                f"A senior reviewer flagged a noisy anecdote about {spec.decoy} near {spec.subject}, but the anecdote came from a case outside the decision window.",
                0.2,
                "anecdote",
            ),
            (
                decoy_roles[2],
                f"The broad weekly report changed by 6%, but it uses a lagging denominator and cannot isolate {spec.population}.",
                0.15,
                "lag",
            ),
            (
                decoy_roles[3],
                f"One {spec.subject} escalation looked severe because it was copied into three queues, not because {root_words} repeated.",
                0.15,
                "duplicate",
            ),
        ),
    )


PRODUCT_EXTRA_SPECS = (
    ScenarioSpec("partial_rollback", "pricing_change", "Checkout funnel", "trial-start conversion", "new self-serve teams", "the price-card copy swap", "price-card revert", "enterprise pipeline optimism", "the first 36 hours", "31%", "19%", "returning users", "420", "30%"),
    ScenarioSpec("do_not_rollback", "unknown", "Launch guardrail", "weighted activation", "low-volume invite cohorts", "the general launch", "two-day holdout extension", "sales chatter", "the weekend ramp", "58%", "55%", "desktop cohorts", "260", "57%"),
    ScenarioSpec("rollback", "mobile_latency", "Android onboarding", "crash-free start rate", "Android 13 devices", "the image prefetch change", "prefetch rollback", "social launch traffic", "six launch hours", "97%", "82%", "iOS devices", "390", "96%"),
    ScenarioSpec("do_not_rollback", "data_bug", "Activation dashboard", "completed setup count", "instrumented mobile events", "the warehouse backfill", "dashboard parser fix", "support screenshots", "the metric replay", "44%", "28%", "server-side completions", "510", "43%"),
)

INCIDENT_EXTRA_SPECS = (
    ScenarioSpec("disable_endpoint", "frontend_regression", "Checkout browser", "client error rate", "Safari sessions", "the bundle minifier change", "disable the new endpoint shim", "database CPU", "the first 22 minutes", "0.9%", "9.4%", "Chrome sessions", "680", "1.1%"),
    ScenarioSpec("uncertain", "unknown", "Incident timeline", "customer-visible failure rate", "multi-region traffic", "the overlapping deploy window", "extend monitoring with canaries", "backup traffic", "the first hour", "1.1%", "2.0%", "synthetic checks", "340", "1.4%"),
    ScenarioSpec("rollback_feature_flag", "cache_thundering_herd", "Search service", "origin read burst", "personalized search calls", "the cache-key rollout", "cache-key rollback", "frontend warning banner", "18 minutes", "14x", "61x", "anonymous search calls", "720", "16x"),
    ScenarioSpec("patch_config", "third_party_api", "Fraud-check trace", "checkout stall rate", "high-value orders", "the vendor retry patch", "retry budget patch", "replica lag", "29 minutes", "3%", "26%", "low-value orders", "450", "4%"),
)

INVESTMENT_EXTRA_SPECS = (
    ScenarioSpec("invest", "durable_growth", "Expansion cohort", "paid-seat retention", "teams past month four", "the usage-based packaging change", "standardize the expansion plan", "press-driven signup spike", "the last 10 weeks", "72%", "91%", "new trial teams", "64", "93%"),
    ScenarioSpec("wait_for_more_data", "legal_risk", "Enterprise diligence", "blocked-pipeline share", "regulated customers", "the draft data-rights clause", "delay signing until the clause clears", "founder charisma", "the contract redline", "4%", "29%", "self-serve customers", "18", "6%"),
)

NEW_DOMAIN_SPECS = {
    "security_access_review": (
        ScenarioSpec("disable_account", "phishing_compromise", "Login telemetry", "risky session score", "finance-admin sessions", "the credential-harvest email", "disable the user and reset sessions", "VPN maintenance", "41 minutes", "0.08", "0.91", "engineering sessions", "74", "0.12"),
        ScenarioSpec("revoke_role", "overbroad_role", "Permission audit", "privileged-action rate", "temporary analyst accounts", "the emergency role grant", "revoke the broad role", "new dashboard rollout", "two business days", "3%", "46%", "standard analyst accounts", "52", "5%"),
        ScenarioSpec("revoke_token", "orphaned_token", "Token inventory", "stale-token calls", "retired automation jobs", "the owner team migration", "revoke the orphaned token", "scanner noise", "the overnight batch", "11", "318", "active jobs", "89", "9"),
        ScenarioSpec("block_oauth_app", "oauth_app_abuse", "OAuth consent logs", "sensitive-scope grants", "sales workspace users", "the external calendar plugin", "block the OAuth app", "SSO certificate rotation", "four hours", "2%", "37%", "engineering users", "97", "3%"),
        ScenarioSpec("close_false_positive", "false_positive_alert", "Alert triage", "impossible-login flags", "traveling executives", "the geolocation vendor update", "close the alert and tune geolocation", "contractor offboarding", "the Monday sync", "6", "83", "device-bound sessions", "116", "8"),
        ScenarioSpec("disable_account", "contractor_offboarding", "Access review", "post-end-date logins", "contractor accounts", "the missed offboarding feed", "disable the contractor accounts", "phishing email", "the weekly roster import", "0", "27", "employee accounts", "61", "1"),
        ScenarioSpec("rotate_secret", "secret_leak", "Repository scan", "credential-use attempts", "build tokens", "the copied sample config", "rotate the leaked secret", "OAuth approval queue", "the commit window", "0", "144", "deploy keys", "38", "2"),
        ScenarioSpec("monitor", "impossible_travel", "Device history", "travel-speed alerts", "regional sales logins", "the mobile carrier routing change", "monitor with device binding", "phishing report", "the carrier outage", "4", "79", "hardware-key sessions", "93", "7"),
    ),
    "supply_chain_disruption": (
        ScenarioSpec("expedite_supplier_rework", "supplier_quality", "Inbound inspection", "reject rate", "motor assemblies", "the supplier process change", "expedite supplier rework", "carrier delay rumor", "three receiving shifts", "1.8%", "18.6%", "alternate supplier lots", "210", "2.4%"),
        ScenarioSpec("hold_for_customs", "customs_hold", "Broker queue", "clearance dwell time", "EU-bound pallets", "the tariff-code mismatch", "hold for customs correction", "warehouse staffing", "the port scan", "9h", "74h", "domestic pallets", "84", "11h"),
        ScenarioSpec("revise_forecast", "demand_forecast_error", "Forecast ledger", "shortage variance", "enterprise bundles", "the promotion uplift miss", "revise the forecast allocation", "supplier quality complaints", "the launch week", "4%", "31%", "consumer bundles", "125", "6%"),
        ScenarioSpec("book_backup_carrier", "carrier_capacity", "Tender history", "load rejection rate", "westbound refrigerated loads", "the carrier capacity freeze", "book backup carrier lanes", "customs paperwork", "two dispatch waves", "7%", "52%", "dry-van loads", "63", "9%"),
        ScenarioSpec("reroute_port", "port_congestion", "Container trace", "berth wait time", "priority container group", "the terminal labor slowdown", "reroute through the alternate port", "supplier rework notice", "five vessel calls", "18h", "96h", "air-freight orders", "48", "22h"),
        ScenarioSpec("allocate_material", "material_shortage", "Material ledger", "uncovered build quantity", "grade-B resin jobs", "the upstream resin outage", "allocate scarce material to committed orders", "demand planning optimism", "the build freeze", "120", "1840", "grade-A resin jobs", "57", "210"),
        ScenarioSpec("recount_warehouse", "warehouse_miscount", "Inventory cycle count", "phantom-on-hand units", "slot C17 inventory", "the bin transfer miss", "recount the warehouse slots", "carrier capacity chatter", "the overnight wave", "12", "740", "slot C18 inventory", "99", "18"),
        ScenarioSpec("fix_labeling", "regulatory_labeling", "Compliance review", "label exception rate", "medical accessory cartons", "the translated label file", "fix the regulatory label", "port congestion", "the packaging release", "0.6%", "24%", "domestic cartons", "156", "0.8%"),
    ),
    "manufacturing_quality": (
        ScenarioSpec("stop_line", "machine_drift", "Line telemetry", "dimension drift", "station 4 housings", "the worn spindle offset", "stop the line for spindle calibration", "operator schedule", "two production lots", "0.04mm", "0.42mm", "station 2 housings", "320", "0.05mm"),
        ScenarioSpec("quarantine_batch", "material_batch", "Incoming material", "fracture rate", "lot M7 brackets", "the resin batch swap", "quarantine the material batch", "packaging scuffs", "the tensile test", "1.1%", "16.8%", "lot M6 brackets", "144", "1.4%"),
        ScenarioSpec("recalibrate_sensor", "sensor_calibration", "Sensor trace", "false reject rate", "vision-inspected labels", "the camera calibration drift", "recalibrate the sensor", "operator retraining", "the morning shift", "3%", "38%", "manual inspection", "260", "4%"),
        ScenarioSpec("retrain_shift", "operator_training", "Work-instruction audit", "missed torque sequence", "new second-shift operators", "the unannounced fixture change", "retrain the shift on the torque sequence", "material batch rumor", "four shift handoffs", "2%", "27%", "first-shift operators", "88", "3%"),
        ScenarioSpec("replace_packaging", "packaging_defect", "Damage log", "corner crush rate", "export cartons", "the thinner insert rollout", "replace the packaging insert", "machine drift", "three outbound waves", "0.7%", "19%", "domestic cartons", "110", "1.0%"),
        ScenarioSpec("adjust_environment", "environmental_condition", "Clean-room monitor", "humidity excursion rate", "adhesive cure samples", "the dehumidifier failure", "adjust the environment controls", "test fixture wear", "two curing cycles", "42%", "68%", "sealed samples", "75", "45%"),
        ScenarioSpec("replace_fixture", "test_fixture_wear", "Gauge study", "measurement repeatability error", "fixture B tests", "the worn locating pin", "replace the test fixture", "labeling mixup", "the gauge repeatability run", "3%", "22%", "fixture A tests", "92", "4%"),
        ScenarioSpec("fix_labels", "labeling_mixup", "Traceability scan", "wrong-label rate", "small-carton SKUs", "the printer template swap", "fix the label template", "supplier quality alert", "the packaging cell changeover", "0.2%", "15%", "large-carton SKUs", "180", "0.4%"),
    ),
    "research_claim_review": (
        ScenarioSpec("revise_claim", "sampling_bias", "Cohort table", "effect estimate", "urban clinic participants", "the recruitment channel change", "reweight and revise the claim", "annotation backlog", "the enrollment window", "4.1", "8.9", "rural participants", "640", "4.6"),
        ScenarioSpec("reject_claim", "measurement_artifact", "Instrument log", "signal amplitude", "assay plate B", "the detector firmware update", "rerun with calibrated measurement", "seasonal uptake", "the assay batch", "0.12", "0.48", "assay plate A", "216", "0.14"),
        ScenarioSpec("replicate_before_launch", "confounder", "Covariate audit", "reported lift", "high-baseline sites", "the concurrent coaching program", "replicate after blocking the confounder", "data leak rumor", "the intervention month", "2%", "11%", "matched control sites", "38", "3%"),
        ScenarioSpec("audit_dataset", "data_leakage", "Feature lineage", "validation accuracy", "holdout rows", "the post-outcome feature join", "audit the dataset join", "underpowered sample", "the model freeze", "61%", "94%", "pre-join validation rows", "510", "63%"),
        ScenarioSpec("accept_claim", "genuine_effect", "Pre-registered endpoint", "outcome improvement", "randomized treatment group", "the intervention exposure", "accept the claim with monitoring", "measurement artifact", "the locked analysis", "3%", "17%", "placebo group", "724", "16%"),
        ScenarioSpec("uncertain", "underpowered_study", "Power analysis", "minimum detectable effect", "rare-event subgroup", "the early stop", "collect another wave before launch", "sponsor enthusiasm", "the interim readout", "6%", "19%", "primary cohort", "42", "8%"),
        ScenarioSpec("revise_claim", "annotation_bias", "Label audit", "positive-label rate", "expert-reviewed examples", "the single-rater annotation batch", "relabel with blinded reviewers", "protocol deviation", "the annotation sprint", "24%", "58%", "double-rated examples", "300", "27%"),
        ScenarioSpec("reject_claim", "protocol_deviation", "Trial log", "excluded-session share", "treated schools", "the unapproved schedule change", "reject the claim until protocol-compliant data exists", "selection bias", "the field visit", "5%", "33%", "control schools", "57", "7%"),
    ),
    "marketplace_integrity": (
        ScenarioSpec("ban_seller_ring", "bot_ring", "Account graph", "linked-account density", "new electronics sellers", "the shared automation script", "ban the seller ring", "seasonal sale spike", "the flash-sale window", "2.1", "18.4", "legacy sellers", "230", "2.4"),
        ScenarioSpec("ban_seller_ring", "seller_collusion", "Pricing graph", "synchronized price moves", "refurbished-camera sellers", "the private reseller channel", "ban the colluding sellers", "inventory scrape", "six pricing intervals", "4%", "67%", "unrelated camera sellers", "96", "5%"),
        ScenarioSpec("tighten_fraud_rules", "payment_fraud", "Payments ledger", "failed-auth retry rate", "gift-card orders", "the card-testing burst", "tighten fraud rules for the segment", "review brigading", "the midnight batch", "3%", "44%", "credit-card orders", "188", "5%"),
        ScenarioSpec("reverse_policy_action", "policy_misclassification", "Policy queue", "false enforcement rate", "handmade accessory sellers", "the taxonomy classifier update", "reverse the policy action", "payment fraud chatter", "two moderation waves", "1%", "29%", "mass-produced sellers", "140", "2%"),
        ScenarioSpec("remove_fake_reviews", "review_brigading", "Review graph", "coordinated-review share", "new home-goods listings", "the off-platform campaign", "remove the fake reviews", "seasonal demand", "four review bursts", "6%", "53%", "older listings", "275", "8%"),
        ScenarioSpec("monitor_seasonal_spike", "seasonal_spike", "Traffic model", "organic conversion", "holiday gift searches", "the seasonal event", "monitor without enforcement", "seller collusion", "the holiday week", "9%", "26%", "control categories", "310", "24%"),
        ScenarioSpec("rate_limit_scraping", "inventory_scrape", "Bot telemetry", "inventory-page hit rate", "limited-edition listings", "the scraper job", "rate limit inventory scraping", "policy misclassification", "the product drop", "120/min", "1480/min", "standard listings", "160", "180/min"),
        ScenarioSpec("review_chargebacks", "chargeback_abuse", "Dispute ledger", "repeat-chargeback rate", "digital voucher buyers", "the abuse forum post", "review chargebacks before refunds", "payment gateway outage", "the refund window", "1.4%", "22%", "physical goods buyers", "102", "2.0%"),
    ),
    "customer_success_escalation": (
        ScenarioSpec("ship_fix", "integration_mismatch", "API trace", "sync failure rate", "customer ERP exports", "the field-mapping mismatch", "ship the integration adapter fix", "training attendance", "the nightly sync", "2%", "41%", "CSV imports", "86", "3%"),
        ScenarioSpec("correct_billing", "billing_misconfiguration", "Invoice audit", "overbilled-seat share", "annual-plan renewals", "the entitlement rule change", "correct the billing configuration", "vendor outage", "the renewal run", "0.5%", "18%", "monthly plans", "124", "0.7%"),
        ScenarioSpec("rewrite_docs", "documentation_gap", "Search logs", "failed help-query rate", "new admin users", "the renamed setup flow", "rewrite the setup docs", "product bug report", "the onboarding week", "9%", "36%", "experienced admins", "410", "11%"),
        ScenarioSpec("ship_fix", "product_bug", "Session replay", "save-error rate", "teams using bulk edits", "the validation regression", "ship the product fix", "contract scope dispute", "the release day", "1.2%", "33%", "single-edit teams", "152", "2%"),
        ScenarioSpec("renegotiate_scope", "contract_scope_confusion", "Contract review", "out-of-scope request share", "premium-support tickets", "the ambiguous service exhibit", "renegotiate scope language", "documentation gap", "the escalation queue", "6%", "42%", "standard tickets", "65", "8%"),
        ScenarioSpec("schedule_training", "adoption_training_gap", "Usage cohort", "unused-seat share", "new regional team", "the skipped enablement session", "schedule targeted training", "billing issue", "the first 30 days", "12%", "49%", "trained teams", "210", "16%"),
        ScenarioSpec("wait_for_vendor", "vendor_outage", "Vendor status", "external API failure rate", "accounts using the payment connector", "the vendor incident", "wait for vendor recovery and communicate", "data import error", "the outage window", "0.8%", "31%", "native billing accounts", "78", "1.1%"),
        ScenarioSpec("repair_import", "data_import_error", "Import audit", "missing-record rate", "legacy CRM imports", "the date-format parser", "repair the import parser", "product bug", "the migration batch", "2%", "28%", "new CRM imports", "98", "3%"),
    ),
    "civic_program_evaluation": (
        ScenarioSpec("redesign_outreach", "selection_bias", "Enrollment table", "eligible-participant share", "online applicants", "the digital-only outreach", "redesign outreach before scaling", "reporting artifact", "the enrollment month", "33%", "71%", "walk-in applicants", "540", "38%"),
        ScenarioSpec("continue_program", "implementation_fidelity", "Field checklist", "completed-service dose", "sites with trained staff", "the coaching protocol", "continue with fidelity checks", "demand shift", "the first quarter", "41%", "84%", "untrained sites", "46", "80%"),
        ScenarioSpec("pause_for_measurement", "demand_shift", "Service logs", "walk-in volume", "downtown offices", "the transit route change", "pause for a new demand baseline", "eligibility confusion", "six service weeks", "180/week", "64/week", "neighborhood offices", "72", "170/week"),
        ScenarioSpec("pause_for_measurement", "measurement_lag", "Reporting calendar", "verified outcome lag", "late-reporting clinics", "the claims reconciliation delay", "pause until measurement catches up", "selection bias", "the reconciliation cycle", "12 days", "54 days", "same-day reports", "88", "14 days"),
        ScenarioSpec("scale_program", "true_impact", "Matched comparison", "employment placement rate", "eligible participants", "the coaching pilot", "scale the program with monitoring", "reporting artifact", "the six-month readout", "18%", "39%", "waitlist comparison", "620", "37%"),
        ScenarioSpec("fix_reporting", "reporting_artifact", "Dashboard audit", "duplicate-success count", "multi-service participants", "the case-management export", "fix reporting before deciding", "implementation fidelity", "the monthly export", "2%", "24%", "single-service participants", "330", "3%"),
        ScenarioSpec("redesign_outreach", "outreach_gap", "Contact log", "unreached eligible share", "non-English households", "the English-only mailer", "redesign outreach materials", "budget rumor", "the outreach wave", "16%", "58%", "English-speaking households", "210", "20%"),
        ScenarioSpec("tighten_eligibility", "eligibility_confusion", "Eligibility review", "ineligible-enrollment share", "self-attested applicants", "the unclear income screen", "tighten eligibility guidance", "measurement lag", "the intake sprint", "3%", "27%", "verified applicants", "154", "4%"),
    ),
}


def _generated(domain: str, specs: tuple[ScenarioSpec, ...]) -> tuple[Scenario, ...]:
    return tuple(_generated_scenario(domain, spec) for spec in specs)


SCENARIOS: dict[str, tuple[Scenario, ...]] = {
    "product_rollback": PRODUCT_BASE + _generated("product_rollback", PRODUCT_EXTRA_SPECS),
    "incident_response": INCIDENT_BASE + _generated("incident_response", INCIDENT_EXTRA_SPECS),
    "investment_committee": INVESTMENT_BASE + _generated("investment_committee", INVESTMENT_EXTRA_SPECS),
    **{domain: _generated(domain, specs) for domain, specs in NEW_DOMAIN_SPECS.items()},
}
