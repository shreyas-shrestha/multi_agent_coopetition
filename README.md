# All I Have Is Attention

**Context Window Parliament** is a multi-agent evaluation environment where a **Speaker** must allocate scarce context-window budget among specialists who hold private evidence. Public bids are free but unreliable; decisive facts only enter the official record through paid floor time or targeted cross-examination.

The project ships:

- A **HUD v6 environment** with 500 deterministic worlds and a structured reward model
- **Baseline policies** and local simulation for strategy comparison
- **GRPO training** hooks against HUD eval traces
- A **Modal live orchestrator** for real-time hearings (trained Speaker + LLM specialists)
- A **static Next.js showcase** ([All I Have Is Attention](showcase/)) with replay and live modes

---

## Table of contents

- [Why this environment](#why-this-environment)
- [How a hearing works](#how-a-hearing-works)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Environment variables](#environment-variables)
- [HUD integration](#hud-integration)
- [MCP tools](#mcp-tools)
- [Worlds and task generation](#worlds-and-task-generation)
- [Reward model](#reward-model)
- [Baseline policies](#baseline-policies)
- [Training](#training)
- [Showcase UI](#showcase-ui)
- [Modal deployment](#modal-deployment)
- [Scripts and diagnostics](#scripts-and-diagnostics)
- [Testing](#testing)
- [Future work](#future-work)

---

## Why this environment

Generic debate benchmarks do not stress **attention allocation**. Here the Speaker must decide:

- **Who** gets context-window space
- **How much** to spend on each interaction
- **Which questions** to ask under cross-examination
- **When** to stop gathering evidence
- **Which testimony IDs** support the final verdict

Specialists are LLM-prompted (or deterministic in offline mode). They are stateful: responses depend on persona, private facts, question wording, token budget, prior turns, world difficulty, and seed. The same world can yield many trajectories because the Speaker controls ordering, questions, spend, and stopping time.

Hidden fact attribution is validated **deterministically** — the reward model grades evidence and citations, not prose quality alone.

---

## How a hearing works

```text
┌─────────────┐     public bids (free)      ┌──────────────────┐
│  Speaker    │ ◄────────────────────────── │  Specialists     │
│  (LLM)      │                             │  (LLM / scripted)│
└──────┬──────┘                             └────────▲─────────┘
       │                                               │
       │  grant_floor / cross_examine (costs tokens)   │
       └───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────┐     submit_verdict      ┌─────────────┐
│  Official record │ ───────────────────────►│  Scorer     │
│  (token budget)  │                         │  (hidden)   │
└──────────────────┘                         └─────────────┘
```

1. The Speaker calls `list_specialists` to see public cards (name, role, bid, claimed priority).
2. The Speaker spends **official-record tokens** via `grant_floor` or `cross_examine`.
3. Testimony enters the visible record; hidden fact IDs are tracked server-side.
4. The Speaker calls `view_record` to inspect budget and testimony.
5. The Speaker calls `submit_verdict` with decision, root cause, confidence, citations, and rationale.
6. The environment scores against hidden ground truth.

Default token budget is **500** with a cap on evidence-gathering interactions (typically **10**).

---

## Architecture

| Layer | Role |
|-------|------|
| `parliament/` | Core models, worlds, scenarios, tools, scoring, policies, live runner |
| `controller/` | MCP tool wiring for HUD |
| `environment/` | In-process MCP server |
| `env.py` | HUD `Environment` definition and lifecycle hooks |
| `tasks.py` | 500 concrete HUD task rows |
| `modal_orchestrator.py` | FastAPI + SSE live hearing API on Modal |
| `modal_benchmark.py` | Batch HUD eval runner on Modal |
| `showcase/` | Next.js static export — replay JSON + live SSE client |
| `train_step.py` | GRPO training step from HUD eval traces |

**Live hearing stack**

```text
Vercel (static Next.js)
    │  NEXT_PUBLIC_ORCHESTRATOR_URL
    ▼
Modal orchestrator (FastAPI SSE)
    │  HUD Gateway
    ├── Speaker: parliament-qwen36-35b-clean
    └── Specialists: Claude Haiku (ANTHROPIC_API_KEY on Modal)
```

---

## Repository layout

```text
parliament/
  models.py          # World, Specialist, Verdict, FactAtom
  scenarios.py       # Domain narratives, scenario families, 500-world specs
  worlds.py          # Deterministic world builder
  facts.py           # Hidden / visible fact atoms
  specialists.py     # LLM + deterministic specialist backends
  tools.py           # grant_floor, cross_examine, view_record, submit_verdict
  scoring.py         # Deterministic reward decomposition
  policies.py        # targeted_oracle, loud_capture, uniform_floor baselines
  live_runner.py     # HUD rollout + streaming timeline for live hearings
  live_timeline.py   # Tool results → showcase timeline JSON
  state.py           # In-memory world registry
  schemas.py         # Speaker system prompt

controller/
  tools.py           # FastMCP tool registration

environment/
  server.py          # MCP server process

showcase/
  app/               # Next.js app (static export)
  exporter/          # Replay JSON generator from Python worlds
  public/replays/    # Bundled replay bundles

scripts/
  simulate_strategies.py
  audit_taskset.py
  diagnose_live_hearing.py

tests/               # Pytest suite (scoring, tools, worlds, leakage, strategies)

env.py               # HUD environment entrypoint
tasks.py             # HUD taskset (500 rows)
modal_orchestrator.py
modal_benchmark.py
train_step.py
```

---

## Quick start

### Python environment

Requires **Python 3.11+**. Recommended: [uv](https://github.com/astral-sh/uv).

```bash
# Install dependencies
uv sync   # or: pip install -e .

# Run tests
uv run pytest -q

# Compare baseline strategies (no API keys required)
uv run python scripts/simulate_strategies.py

# Audit the 500-world taskset
uv run python scripts/audit_taskset.py
```

Typical strategy separation from simulation:

```text
targeted_oracle  > uniform_floor > loud_capture
targeted_oracle  > random
loud_capture     below 0.45 mean reward
targeted_oracle  above 0.80 mean reward
uniform_floor    clears loud_capture by > 0.15
```

### Showcase (local)

```bash
# Regenerate replay JSON from Python worlds (optional)
python showcase/exporter/export_replays.py
python showcase/exporter/export_strategy_summary.py

cd showcase
npm install
npm run dev
```

Open the dev server (default Next.js port). The default docket is **`incident-response-medium-004`**.

For **live hearings** locally, copy `showcase/app/.env.example` to `showcase/app/.env.local` and set `NEXT_PUBLIC_ORCHESTRATOR_URL` to your deployed Modal orchestrator URL.

---

## Environment variables

### Specialist LLMs (local eval / Modal)

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | — | Enables LLM specialist testimony |
| `PARLIAMENT_SPECIALIST_BACKEND` | `auto` | `auto`, `llm`, or `deterministic` |
| `PARLIAMENT_ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | Specialist model |
| `ANTHROPIC_BASE_URL` | — | Optional API base override |
| `ANTHROPIC_VERSION` | — | Optional API version header |
| `PARLIAMENT_ANTHROPIC_TIMEOUT` | — | Optional request timeout (seconds) |

`auto` uses LLM specialists when `ANTHROPIC_API_KEY` is set; otherwise deterministic stubs run offline.

### HUD platform

| Variable | Purpose |
|----------|---------|
| `HUD_API_KEY` | Required for HUD eval, deploy, sync, and live Speaker inference via Gateway |

### Showcase (Vercel / local)

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_ORCHESTRATOR_URL` | Modal orchestrator base URL for live hearings |

**Never** put `HUD_API_KEY` or `ANTHROPIC_API_KEY` in Vercel — keep them in Modal secrets only.

### Diagnostics

| Variable | Default |
|----------|---------|
| `ORCHESTRATOR_URL` | Modal web URL |
| `WORLD_ID` | `incident-response-medium-004` |

---

## HUD integration

| Setting | Value |
|---------|-------|
| Environment name | `context-window-parliament` |
| Task template | `context_parliament` |
| Taskset name | `context-window-parliament-mvp` |
| Shipped worlds | **500** |

The HUD scaffold pattern:

- `Environment(name="context-window-parliament")` in `env.py`
- Async generator task templates with two yields
- `FastMCP` tools via `Capability.mcp(...)`
- `@env.initialize` starts the in-process MCP server on a free port
- `@env.shutdown` cancels the MCP server task

```bash
# Requires HUD CLI + HUD_API_KEY
hud eval tasks.py claude
hud eval tasks.py openai_compatible --model parliament-qwen36-35b-clean --gateway
hud eval tasks.py claude --group 8
hud deploy .
hud sync tasks context-window-parliament-mvp tasks.py
```

`HUD_API_KEY` is **not** required for unit tests or local simulation.

---

## MCP tools

| Tool | Description |
|------|-------------|
| `list_specialists(world_id)` | Public specialist cards only — no hidden facts, weights, or truth |
| `grant_floor(world_id, specialist_id, token_budget)` | Spend tokens on generic floor testimony |
| `cross_examine(world_id, specialist_id, question, token_budget)` | Spend tokens on targeted testimony |
| `view_record(world_id)` | Visible testimony and budget state |
| `submit_verdict(world_id, decision, confidence, root_cause, citation_ids, rationale)` | Record final structured answer |

Public bids may be biased, noisy, or underconfident. Hidden evidence, fact IDs, relevance labels, fact weights, and ground truth are **never** returned by public tools.

---

## Worlds and task generation

**500 concrete worlds:**

- **10 domains:** product rollback, incident response, investment committee, security access review, supply chain disruption, manufacturing quality, research claim review, marketplace integrity, customer success escalation, civic program evaluation
- **3 difficulties:** easy, medium, hard
- **50 rows per domain** (170 easy / 170 medium / 160 hard overall)

Worlds are generated from deterministic scenario families — eight templates per domain with multiple truth decisions and root causes. Seeds rotate fact ownership, persona policy, loud decoys, quiet key specialists, and whether cross-examination is needed for high reward.

**Stable showcase slugs:**

| World ID | Domain | Notes |
|----------|--------|-------|
| `product-rollback-easy-001` | Product rollback | First shipped world |
| `incident-response-medium-004` | Incident response | Default showcase / live demo |
| `investment-committee-hard-005` | Investment committee | Hard tier example |
| `security-access-review-medium-168` | Security review | Third showcase preset |

Example incident narrative (`incident-response-medium-004`):

> Error rates on /recommendations spiked from 0.4% to 7.8% minutes after a recommendation-cache feature flag hit 100%. Cache misses jumped to 83% and database load followed. Cross-examine SRE, API, database, and deploy witnesses under a 500-token budget to find the root cause and choose the right mitigation.

---

## Reward model

Deterministic scoring against hidden world state:

```text
R =
  0.24 × gated_decision_accuracy
+ 0.12 × gated_root_cause_accuracy
+ 0.30 × evidence_recall
+ 0.14 × evidence_precision
+ 0.08 × non_redundancy
+ 0.07 × citation_quality
+ 0.05 × budget_discipline
− 0.10 × unsupported_claim_penalty
```

| Subscore | Meaning |
|----------|---------|
| **Gated decision / root cause** | Correct action and diagnosis; accuracy is gated by evidence recall so lucky guesses are capped |
| **Evidence recall** | Required hidden facts reached the official record |
| **Evidence precision** | Record density vs fluff |
| **Non-redundancy** | Distinct evidence clusters covered |
| **Citation quality** | Cited testimony supports required facts |
| **Budget discipline** | Context-budget compliance |
| **Unsupported claim penalty** | Hallucinated or unsupported root causes |

Root cause is scored separately from decision — the correct action and the correct causal diagnosis are different skills.

---

## Baseline policies

Non-LLM policies in `parliament/policies.py` used for simulation and replay export:

| Policy ID | Label | Behavior |
|-----------|-------|----------|
| `targeted_oracle` | Trained Speaker | Cross-examines specialists with required facts |
| `loud_capture` | Loud Capture | Prioritizes highest public bids |
| `uniform_floor` | Uniform Floor | Grants floor time broadly |

These produce deterministic replay JSON under `showcase/app/public/replays/`.

---

## Training

`train_step.py` runs one **GRPO** step on traces from a HUD eval job:

```bash
# Requires HUD_API_KEY and a completed eval job
uv run python train_step.py --job-id <hud-job-id>
```

Default model slug: `parliament-qwen36-35b-clean`. Checkpoint metadata lives in `training/checkpoints.json` and `training/checkpoints_35b.json`.

---

## Showcase UI

The **All I Have Is Attention** showcase is a static Next.js app (`showcase/app/`) with two modes:

| Mode | Trigger | Data source |
|------|---------|-------------|
| **Replay** | Default when `NEXT_PUBLIC_ORCHESTRATOR_URL` is unset | Bundled JSON in `public/replays/` |
| **Live** | `NEXT_PUBLIC_ORCHESTRATOR_URL` set + Trained Speaker policy | Modal SSE stream |

**Speaker view** — agent deliberation, parallel specialist cards, official record table, verdict panel.

**Audit view** — ground truth, reward decomposition, subscores.

### Deploy to Vercel

**Option A — app subdirectory (recommended)**

1. Import the repo in Vercel.
2. Set **Root Directory** to `showcase/app`.
3. Use the repo's `showcase/app/vercel.json` (install: `cd .. && npm ci`, build: `npm run build`).
4. Add environment variable:
   ```bash
   NEXT_PUBLIC_ORCHESTRATOR_URL=https://<workspace>--context-window-parliament-orchestrator-web.modal.run
   ```
5. Deploy. Replay mode works without env vars; live mode requires the orchestrator URL.

**Option B — CLI**

```bash
cd showcase/app
npx vercel
npx vercel --prod
```

Regenerate replay data before shipping UI changes that depend on new worlds:

```bash
python showcase/exporter/export_replays.py
python showcase/exporter/export_strategy_summary.py
cd showcase && npm run build
```

See [showcase/README.md](showcase/README.md) for additional Vercel troubleshooting notes.

---

## Modal deployment

### Live orchestrator (showcase hearings)

Exposes HTTP + SSE for real-time hearings:

```bash
uv tool install modal   # or: pip install modal
modal setup

modal secret create context-window-parliament-hud \
  HUD_API_KEY="$HUD_API_KEY" \
  ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --force

modal deploy modal_orchestrator.py
```

Endpoints:

| Route | Purpose |
|-------|---------|
| `GET /health` | Warm container, verify keys configured |
| `GET /api/worlds/{world_id}/preview` | Session start + roster JSON |
| `GET /api/hearing/stream?world_id=...` | SSE timeline + complete + keepalive pings |

Live inference:

- **Speaker:** `parliament-qwen36-35b-clean` via HUD Gateway
- **Specialists:** Claude Haiku on Modal (`ANTHROPIC_API_KEY`)

The orchestrator keeps `min_containers=1` and sends periodic SSE pings during long inference gaps.

### Benchmark runner

Batch eval of trained vs base models:

```bash
modal deploy modal_benchmark.py
modal run modal_benchmark.py --task-start 200 --task-count 30 --rollouts-per-task 2
```

Default: 30 held-out tasks, 2 rollouts each, HUD/Tinker concurrency capped at 4.

---

## Scripts and diagnostics

| Script | Purpose |
|--------|---------|
| `scripts/simulate_strategies.py` | Run baseline policies across worlds; print separation |
| `scripts/audit_taskset.py` | Validate 500-world taskset invariants |
| `scripts/diagnose_live_hearing.py` | Time SSE stream end-to-end against Modal |
| `scripts/export_showcase_data.py` | Export helper for showcase assets |
| `showcase/exporter/export_replays.py` | Generate replay JSON bundles |
| `showcase/exporter/export_strategy_summary.py` | Generate strategy summary JSON |

**Live hearing diagnostic:**

```bash
ORCHESTRATOR_URL=https://your-modal-url.modal.run \
WORLD_ID=incident-response-medium-004 \
python scripts/diagnose_live_hearing.py
```

Expect ~50–90s on a warm container for the default world (first byte delay includes Speaker + specialist inference).

---

## Testing

```bash
uv run pytest -q
```

Test coverage includes:

- World generation and taskset balance
- Tool behavior and budget accounting
- Scoring and gating logic
- No leakage of hidden facts through public tools
- Baseline strategy ordering
- LLM specialist backend (when configured)
- Training step helpers

---

## Future work

- Nested HUD subagent rollouts
- Auctions for floor time
- Reputation over repeated hearings
- Multiple Speakers or factions
- Official-record compression
- Public cache or shared memory
- Real document shards

---

## License

See repository for license terms.
