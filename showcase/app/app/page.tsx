"use client";

import { useEffect, useMemo, useState } from "react";
import { loadReplay, loadReplayIndex } from "@/lib/replay";
import type {
  PolicyId,
  ReplayBundle,
  ReplayIndex,
  SpecialistCard,
  TestimonyVisible,
  TimelineEvent,
} from "@/lib/types";

type ViewMode = "speaker" | "audit";
type Tone = "green" | "yellow" | "blue" | "neutral";

const DEFAULT_WORLD = "incident-response-medium-004";
const DEFAULT_POLICY: PolicyId = "targeted_oracle";

const GLYPH = {
  mark: "\u25c6",
  source: "\u25a6",
  record: "\u25e7",
  timeline: "\u25a3",
  verdict: "\u25cf",
  audit: "\u2726",
  bullet: "\u2022",
  search: "\u2315",
  chevron: "\u2304",
};

function titleize(value: string) {
  return value
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function compact(value: string | undefined, fallback = "Pending") {
  return titleize(value ?? fallback);
}

function shortOption(value: string | undefined) {
  const cleaned = compact(value)
    .replace("Rollback Feature Flag", "Rollback Flag")
    .replace("No Action Monitor", "Monitor")
    .replace("Wait For More Data", "Wait")
    .replace("Do Not Rollback", "No Rollback")
    .replace("Close False Positive", "Close Alert");
  if (cleaned.length <= 10) return cleaned;
  return cleaned.split(" ")[0] ?? cleaned;
}

function pct(value: number | undefined) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function replayVerdict(bundle: ReplayBundle | null) {
  return (
    bundle?.timeline.find((event) => event.verdict)?.verdict ??
    null
  );
}

function sampledBySource(testimony: TestimonyVisible[]) {
  const map: Record<string, { tokens: number; count: number }> = {};
  for (const block of testimony) {
    const current = map[block.specialist_id] ?? { tokens: 0, count: 0 };
    map[block.specialist_id] = {
      tokens: current.tokens + block.token_count,
      count: current.count + 1,
    };
  }
  return map;
}

function Metric({
  icon,
  label,
  value,
  status,
  tone = "neutral",
}: {
  icon: string;
  label: string;
  value: string;
  status: string;
  tone?: Tone;
}) {
  return (
    <article className="cvp-metric">
      <h2>
        <span aria-hidden="true">{icon}</span> {label}
      </h2>
      <div>
        <strong>{value}</strong>
        <em className={`cvp-status cvp-status-${tone}`}>
          {GLYPH.bullet} {status}
        </em>
      </div>
    </article>
  );
}

function ViewToggle({
  mode,
  onChange,
}: {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
}) {
  return (
    <div className="cvp-toggle" aria-label="View mode">
      <button
        type="button"
        className={mode === "speaker" ? "active" : undefined}
        onClick={() => {
          window.history.replaceState(null, "", "?view=speaker");
          onChange("speaker");
        }}
      >
        Speaker
      </button>
      <button
        type="button"
        className={mode === "audit" ? "active" : undefined}
        onClick={() => {
          window.history.replaceState(null, "", "?view=audit");
          onChange("audit");
        }}
      >
        Audit
      </button>
    </div>
  );
}

function SourceActivity({
  specialists,
  testimony,
}: {
  specialists: SpecialistCard[];
  testimony: TestimonyVisible[];
}) {
  const sampled = useMemo(() => sampledBySource(testimony), [testimony]);
  const max = Math.max(
    1,
    ...specialists.map((source) =>
      Math.max(source.requested_tokens, sampled[source.id]?.tokens ?? 0),
    ),
  );

  return (
    <article className="cvp-source-activity">
      <h3>{GLYPH.source} EVIDENCE SOURCES</h3>
      <div className="cvp-source-list">
        {specialists.map((source) => {
          const pulled = sampled[source.id]?.tokens ?? 0;
          return (
            <div className="cvp-source-row" key={source.id}>
              <div>
                <span>{source.name}</span>
                <small>{source.claimed_priority} bid</small>
              </div>
              <div className="cvp-source-bars">
                <i style={{ width: `${(source.requested_tokens / max) * 100}%` }} />
                <b style={{ width: `${(pulled / max) * 100}%` }} />
              </div>
              <strong>{pulled}t</strong>
            </div>
          );
        })}
      </div>
    </article>
  );
}

function TimelinePanel({ events }: { events: TimelineEvent[] }) {
  const calls = events.filter((event) => event.type === "tool_call");
  return (
    <article className="cvp-timeline-panel">
      <h3>{GLYPH.timeline} INTERROGATION TIMELINE</h3>
      <div className="cvp-timeline">
        {calls.map((event) => {
          const testimony = event.testimony_added;
          const verdict = event.verdict;
          return (
            <div className="cvp-timeline-row" key={event.index}>
              <span>{String(event.index).padStart(2, "0")}</span>
              <div>
                <strong>{event.tool}</strong>
                <p>
                  {testimony
                    ? `${testimony.specialist_name}: ${testimony.visible_text}`
                    : verdict
                      ? `Verdict: ${compact(verdict.decision)}`
                      : event.message ?? "ok"}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}

function ScoreBars({ bundle }: { bundle: ReplayBundle }) {
  return (
    <article className="cvp-score-panel">
      <h3>{GLYPH.audit} SCORING BREAKDOWN</h3>
      <div className="cvp-score-list">
        {Object.entries(bundle.reward.subscores).map(([key, value]) => (
          <div className="cvp-score-row" key={key}>
            <div>
              <span>{titleize(key)}</span>
              <strong>{pct(value)}</strong>
            </div>
            <i>
              <b style={{ width: `${Math.max(2, value * 100)}%` }} />
            </i>
          </div>
        ))}
      </div>
    </article>
  );
}

function TokenBuckets({ bundle }: { bundle: ReplayBundle }) {
  const metadata = bundle.reward.metadata;
  const relevant = Number(metadata.relevant_tokens ?? 0);
  const decoy = Number(metadata.decoy_tokens ?? 0);
  const fluff = Number(metadata.fluff_tokens ?? 0);
  const duplicate = Number(metadata.duplicate_tokens ?? 0);
  const total = Math.max(1, relevant + decoy + fluff + duplicate);
  const relevantDeg = (relevant / total) * 360;
  const decoyDeg = (decoy / total) * 360;
  const fluffDeg = (fluff / total) * 360;

  return (
    <article className="cvp-token-panel">
      <h3>{GLYPH.record} TOKEN LEDGER</h3>
      <div className="cvp-token-body">
        <div
          className="cvp-donut"
          style={{
            background: `radial-gradient(circle, #0f0f0f 0 39px, transparent 40px),
              conic-gradient(#e6e6e6 0deg ${relevantDeg}deg,
              #f0be2e ${relevantDeg}deg ${relevantDeg + decoyDeg}deg,
              #5f5f5f ${relevantDeg + decoyDeg}deg ${relevantDeg + decoyDeg + fluffDeg}deg,
              #7b6cff ${relevantDeg + decoyDeg + fluffDeg}deg 360deg)`,
          }}
          aria-hidden="true"
        />
        <ul>
          <li>
            <span className="swatch white" />
            <p>Relevant</p>
            <strong>{relevant} TOKENS</strong>
          </li>
          <li>
            <span className="swatch yellow" />
            <p>Decoy</p>
            <strong>{decoy} TOKENS</strong>
          </li>
          <li>
            <span className="swatch grey" />
            <p>Fluff</p>
            <strong>{fluff} TOKENS</strong>
          </li>
          <li>
            <span className="swatch blue" />
            <p>Duplicate</p>
            <strong>{duplicate} TOKENS</strong>
          </li>
        </ul>
      </div>
    </article>
  );
}

function RecordTable({
  testimony,
  citationIds,
  audit,
}: {
  testimony: TestimonyVisible[];
  citationIds: string[];
  audit: boolean;
}) {
  const citations = new Set(citationIds);
  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>SOURCE</th>
          <th>MODE</th>
          <th>TOKENS</th>
          <th>{audit ? "CITATION" : "TESTIMONY"}</th>
        </tr>
      </thead>
      <tbody>
        {testimony.map((block) => (
          <tr key={block.id}>
            <td>{block.id}</td>
            <td>{block.specialist_name}</td>
            <td>
              <span className={`cvp-pill ${block.mode === "cross_exam" ? "green" : "yellow"}`}>
                {block.mode === "cross_exam" ? "Cross-exam" : "Floor"}
              </span>
            </td>
            <td>{block.token_count}</td>
            <td>
              {audit ? (
                <span className={`cvp-pill ${citations.has(block.id) ? "blue" : "neutral"}`}>
                  {citations.has(block.id) ? "Cited" : "Unused"}
                </span>
              ) : (
                block.visible_text
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SpeakerRightPanel({
  bundle,
  verdict,
}: {
  bundle: ReplayBundle;
  verdict: NonNullable<TimelineEvent["verdict"]> | null;
}) {
  const activity = bundle.timeline
    .filter((event) => event.type === "tool_call")
    .slice(-5)
    .reverse();

  return (
    <>
      <section className="cvp-right-section cvp-output">
        <h2>{GLYPH.verdict} SPEAKER OUTPUT</h2>
        {verdict ? (
          <>
            <div className="cvp-output-decision">{compact(verdict.decision)}</div>
            <p>{compact(verdict.root_cause)}</p>
            <div className="cvp-citation-row">
              {verdict.citation_ids.map((id) => (
                <span className="cvp-pill blue" key={id}>
                  {id}
                </span>
              ))}
            </div>
            <blockquote>{verdict.rationale}</blockquote>
          </>
        ) : (
          <p>No verdict in replay.</p>
        )}
      </section>

      <section className="cvp-right-section cvp-recent">
        <h2>{GLYPH.timeline} TOOL ACTIVITY</h2>
        {activity.map((event) => (
          <article key={event.index}>
            <p>{event.tool}</p>
            <span>
              {event.testimony_added?.specialist_name ??
                (event.verdict ? compact(event.verdict.decision) : null) ??
                event.message}
            </span>
          </article>
        ))}
      </section>
    </>
  );
}

function AuditRightPanel({ bundle }: { bundle: ReplayBundle }) {
  const truth = bundle.world.ground_truth;
  const metadata = bundle.reward.metadata;
  return (
    <>
      <section className="cvp-right-section cvp-output">
        <h2>{GLYPH.audit} GROUND TRUTH</h2>
        <div className="cvp-output-decision">{compact(truth?.decision)}</div>
        <p>{compact(truth?.root_cause)}</p>
        <div className="cvp-citation-row">
          <span className="cvp-pill green">{bundle.reward.reward.toFixed(3)} reward</span>
          <span className="cvp-pill blue">{metadata.budget_used as number} tokens</span>
        </div>
      </section>

      <section className="cvp-right-section cvp-recent">
        <h2>{GLYPH.record} REWARD INTERNALS</h2>
        {Object.entries(bundle.reward.subscores).slice(0, 6).map(([key, value]) => (
          <article key={key}>
            <p>{titleize(key)}</p>
            <span>{pct(value)}</span>
          </article>
        ))}
      </section>
    </>
  );
}

export default function Page() {
  const [catalog, setCatalog] = useState<ReplayIndex | null>(null);
  const [worldId, setWorldId] = useState(DEFAULT_WORLD);
  const [policy, setPolicy] = useState<PolicyId>(DEFAULT_POLICY);
  const [mode, setMode] = useState<ViewMode>("speaker");
  const [bundle, setBundle] = useState<ReplayBundle | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    loadReplayIndex().then(setCatalog).catch((error) => {
      setLoadError(error instanceof Error ? error.message : "Unable to load replay index");
    });
  }, []);

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("view");
    if (requested === "audit" || requested === "speaker") {
      setMode(requested);
    }
  }, []);

  useEffect(() => {
    let active = true;
    setLoadError(null);
    loadReplay(worldId, policy)
      .then((next) => {
        if (active) setBundle(next);
      })
      .catch((error) => {
        if (active) {
          setBundle(null);
          setLoadError(error instanceof Error ? error.message : "Unable to load replay");
        }
      });
    return () => {
      active = false;
    };
  }, [worldId, policy]);

  const preset = catalog?.presets.find((item) => item.world_id === worldId);
  const verdict = replayVerdict(bundle);
  const specialists = bundle?.timeline[0]?.payload?.specialists ?? [];
  const testimony = bundle?.final_record.testimony ?? [];
  const citationIds = verdict?.citation_ids ?? [];
  const policyMeta = catalog?.policies.find((item) => item.id === policy);
  const budgetUsed = bundle?.final_record.budget_used ?? 0;
  const budgetTotal = bundle?.world.token_budget ?? 1;
  const interactions = bundle?.timeline.filter(
    (event) => event.testimony_added,
  ).length ?? 0;

  const speakerMetrics = [
    {
      icon: GLYPH.source,
      label: "EVIDENCE INPUTS",
      value: String(specialists.length),
      status: "public cards",
      tone: "green" as Tone,
    },
    {
      icon: GLYPH.record,
      label: "RECORD TOKENS",
      value: `${budgetUsed}/${budgetTotal}`,
      status: `${budgetTotal - budgetUsed} left`,
      tone: "blue" as Tone,
    },
    {
      icon: GLYPH.timeline,
      label: "INTERROGATIONS",
      value: String(interactions),
      status: `${bundle?.world.max_interactions ?? 0} max`,
      tone: "yellow" as Tone,
    },
    {
      icon: GLYPH.verdict,
      label: "FINAL ANSWER",
      value: verdict ? shortOption(verdict.decision) : "Pending",
      status: verdict ? `${Math.round(verdict.confidence * 100)}% confidence` : "no verdict",
      tone: "green" as Tone,
    },
  ];

  const auditMetrics = bundle
    ? [
        {
          icon: GLYPH.audit,
          label: "REWARD",
          value: bundle.reward.reward.toFixed(2),
          status: "deterministic",
          tone: "green" as Tone,
        },
        {
          icon: GLYPH.record,
          label: "RECALL",
          value: pct(bundle.reward.subscores.evidence_recall),
          status: "required facts",
          tone: "blue" as Tone,
        },
        {
          icon: GLYPH.source,
          label: "PRECISION",
          value: pct(bundle.reward.subscores.evidence_precision),
          status: "record density",
          tone: "yellow" as Tone,
        },
        {
          icon: GLYPH.verdict,
          label: "CITATIONS",
          value: pct(bundle.reward.subscores.citation_quality),
          status: "support quality",
          tone: "green" as Tone,
        },
      ]
    : speakerMetrics;

  return (
    <main className="cvp-desktop">
      <aside className="cvp-sidebar">
        <div className="cvp-brand-row">
          <div className="cvp-brand-mark" aria-hidden="true">
            {GLYPH.mark}
          </div>
          <div>
            <div className="cvp-brand-name">PARLIAMENT</div>
            <p>context window</p>
          </div>
        </div>

        <label className="cvp-search">
          <span aria-hidden="true">{GLYPH.search}</span>
          <select
            value={worldId}
            onChange={(event) => setWorldId(event.target.value)}
            aria-label="Replay docket"
          >
            {catalog?.presets.map((item) => (
              <option value={item.world_id} key={item.world_id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <nav className="cvp-nav-list" aria-label="Sections">
          {[
            ["Problem", GLYPH.record],
            ["Evidence Inputs", GLYPH.source],
            ["Interrogation", GLYPH.timeline],
            ["Official Record", GLYPH.record],
            ["Verdict", GLYPH.verdict],
          ].map(([label, icon], index) => (
            <a className={index === 0 ? "active" : undefined} href="#" key={label}>
              <span aria-hidden="true">{icon}</span>
              {label}
            </a>
          ))}
        </nav>

        <div className="cvp-sidebar-divider" />

        <label className="cvp-policy-select">
          <span>Speaker policy</span>
          <select
            value={policy}
            onChange={(event) => setPolicy(event.target.value as PolicyId)}
          >
            {catalog?.policies.map((item) => (
              <option value={item.id} key={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <section className="cvp-upgrade">
          <h2>{GLYPH.audit} Replay Mode</h2>
          <p>{policyMeta?.subtitle ?? "Loading replay metadata."}</p>
          <span>{bundle?.meta.policy_label ?? "Speaker"}</span>
        </section>
      </aside>

      <section className="cvp-main-panel">
        <header className="cvp-topbar">
          <p className="cvp-eyebrow">HEARING DESK</p>
          <ViewToggle mode={mode} onChange={setMode} />
        </header>

        <section className="cvp-problem">
          <div>
            <h1>{preset?.label ?? "Context Window Parliament"}</h1>
            <p>{bundle?.world.narrative ?? loadError ?? "Loading replay..."}</p>
          </div>
          <div className="cvp-problem-meta">
            <span>{bundle?.world.world_id ?? worldId}</span>
            <span>{bundle ? titleize(bundle.world.domain) : "Replay"}</span>
            <span>{bundle ? titleize(bundle.world.difficulty) : "Loading"}</span>
          </div>
        </section>

        <section className="cvp-metrics" aria-label="Summary metrics">
          {(mode === "speaker" ? speakerMetrics : auditMetrics).map((metric) => (
            <Metric {...metric} key={metric.label} />
          ))}
        </section>

        {bundle && (
          <section className="cvp-stats-card">
            <div className="cvp-section-head">
              <div>
                <h2>{mode === "speaker" ? "Attention Allocation" : "Scoring Internals"}</h2>
                <p>
                  {mode === "speaker"
                    ? "Public sources, paid testimony, and the compact official record"
                    : "Ground-truth comparison and reward decomposition"}
                </p>
              </div>
              <button type="button">
                REPLAY {GLYPH.chevron}
              </button>
            </div>

            <div className="cvp-stats-grid">
              {mode === "speaker" ? (
                <>
                  <SourceActivity specialists={specialists} testimony={testimony} />
                  <TimelinePanel events={bundle.timeline} />
                </>
              ) : (
                <>
                  <ScoreBars bundle={bundle} />
                  <TokenBuckets bundle={bundle} />
                </>
              )}
            </div>
          </section>
        )}

        <section className="cvp-record">
          <div className="cvp-record-head">
            <h2>Official Record</h2>
            <div>
              <span className="cvp-table-search">{GLYPH.search} testimony</span>
              <span className="cvp-filter">{mode === "speaker" ? "PUBLIC" : "AUDIT"}</span>
            </div>
          </div>
          <RecordTable testimony={testimony} citationIds={citationIds} audit={mode === "audit"} />
        </section>
      </section>

      <aside className="cvp-right-panel">
        <button className="cvp-edge-pill" type="button" aria-label="Panel handle" />
        {bundle ? (
          mode === "speaker" ? (
            <SpeakerRightPanel bundle={bundle} verdict={verdict} />
          ) : (
            <AuditRightPanel bundle={bundle} />
          )
        ) : (
          <section className="cvp-right-section cvp-output">
            <h2>{GLYPH.record} LOADING</h2>
            <p>{loadError ?? "Fetching replay."}</p>
          </section>
        )}
      </aside>
    </main>
  );
}
