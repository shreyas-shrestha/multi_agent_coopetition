"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { loadReplayIndex } from "@/lib/replay";
import { isLivePolicy } from "@/lib/live";
import {
  useSessionStream,
  type LiveEventRow,
} from "@/hooks/useSessionStream";
import type {
  PolicyId,
  ReplayBundle,
  ReplayIndex,
  SpecialistCard,
  TestimonyVisible,
  TimelineEvent,
} from "@/lib/types";

type ViewMode = "speaker" | "audit";
type PlaybackState = "complete" | "running" | "paused";
type Tone = "green" | "yellow" | "blue" | "neutral";

const DEFAULT_WORLD = "incident-response-medium-004";
const DEFAULT_POLICY: PolicyId = "targeted_oracle";
const BRAND_NAME = "All I Have Is Attention";

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
  arrow: "\u2192",
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

function replayVerdict(events: TimelineEvent[]) {
  return events.find((event) => event.verdict)?.verdict ?? null;
}

function resolveVisibleVerdict(
  visibleEvents: TimelineEvent[],
  liveMode: boolean,
  liveEvents: LiveEventRow[],
  bundleVerdict?: NonNullable<TimelineEvent["verdict"]> | null,
): NonNullable<TimelineEvent["verdict"]> | null {
  const fromTimeline = replayVerdict(visibleEvents);
  if (fromTimeline) return fromTimeline;
  if (!liveMode) return null;
  const fromRows = liveEvents.findLast((row) => row.verdict)?.verdict;
  if (fromRows) return fromRows;
  return bundleVerdict ?? null;
}

function liveRowToEvent(row: LiveEventRow): TimelineEvent {
  const toolKey = row.tool.replace(/ /g, "_").toLowerCase();
  return {
    index: row.eventIndex,
    type: "tool_call",
    tool: toolKey,
    ok: true,
    message: row.decisionLog,
    args: row.args,
    budget_used: row.budgetUsed,
    budget_remaining: row.budgetRemaining,
    testimony_added: row.testimony,
    verdict: row.verdict,
  };
}

function liveAgentPrompt(
  phase: string,
  liveEvents: LiveEventRow[],
  activeEvent: TimelineEvent | undefined,
  world: ReplayBundle["world"] | undefined,
): string {
  if (phase === "running" && liveEvents.length === 0) {
    return "Speaker is deliberating — first tool call in progress (typically 10–30s)…";
  }
  const last = liveEvents.at(-1);
  if (phase === "running" && last) {
    if (last.testimony) {
      const question =
        last.question ??
        (typeof last.args?.question === "string" ? last.args.question : undefined);
      if (question) {
        return `Main agent cross-examining ${last.testimony.specialist_name}: ${question}`;
      }
      return `Main agent recorded floor testimony from ${last.testimony.specialist_name}.`;
    }
    if (last.verdict) {
      return `Main agent submitted verdict: ${compact(last.verdict.decision)}.`;
    }
    return `Running ${last.tool.replace(/_/g, " ")} — planning next move…`;
  }
  return promptFor(activeEvent, world);
}

function resolveVisibleTestimony(
  visibleEvents: TimelineEvent[],
  liveMode: boolean,
  liveEvents: LiveEventRow[],
): TestimonyVisible[] {
  const fromTimeline = visibleEvents
    .map((event) => event.testimony_added)
    .filter((item): item is TestimonyVisible => Boolean(item));
  if (fromTimeline.length > 0 || !liveMode) return fromTimeline;
  return liveEvents
    .filter((row) => row.testimony)
    .map((row) => row.testimony!);
}

function liveTimelineEvents(bundle: ReplayBundle, liveEvents: LiveEventRow[]): TimelineEvent[] {
  const sessionStart = bundle.timeline[0];
  const streamed = liveEvents.map(liveRowToEvent);
  return sessionStart ? [sessionStart, ...streamed] : streamed;
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

function latestBySource(testimony: TestimonyVisible[]) {
  const map: Record<string, TestimonyVisible> = {};
  for (const block of testimony) {
    map[block.specialist_id] = block;
  }
  return map;
}

const DOCUMENT_SETS: Record<string, string[]> = {
  incident_response: [
    "Support tickets",
    "On-call notes",
    "Metrics board",
    "API traces",
    "Database counters",
    "Frontend sessions",
  ],
  product_rollback: [
    "Experiment notes",
    "Customer feedback",
    "Flag history",
    "Release logs",
    "Analytics chart",
    "QA transcript",
  ],
  security_access_review: [
    "Access requests",
    "Identity audit",
    "SIEM events",
    "Policy exceptions",
    "Admin logs",
    "Reviewer notes",
  ],
};

function documentForSource(
  source: SpecialistCard,
  index: number,
  domain: string | undefined,
) {
  const labels = DOCUMENT_SETS[domain ?? ""] ?? [
    "Source document",
    "Operator notes",
    "Measurement log",
    "Trace excerpt",
  ];
  return {
    id: `D${String(index + 1).padStart(2, "0")}`,
    label: labels[index % labels.length],
    detail: source.public_bid.replace(/^I can summarize /, "").replace(/^I have /, ""),
  };
}

function eventDelay(event: TimelineEvent | undefined) {
  if (!event) return 1900;
  if (event.verdict) return 4600;
  if (event.testimony_added) return 5200;
  return 2100;
}

function promptFor(event: TimelineEvent | undefined, world?: ReplayBundle["world"]) {
  if (!event) {
    return "Replay loaded. Press Replay to watch the main agent dispatch targeted questions through the source documents.";
  }
  if (event.type === "session_start") {
    return `Main agent opens ${event.payload?.specialists?.length ?? 0} source lanes for ${world?.world_id ?? "the docket"} and fans out document traversal.`;
  }
  if (event.verdict) {
    return `Main agent synthesizes ${compact(event.verdict.decision)} from compact citations ${event.verdict.citation_ids.join(", ")}.`;
  }
  if (event.testimony_added) {
    const question =
      typeof event.args?.question === "string"
        ? event.args.question
        : `Cross-examining ${event.testimony_added.specialist_name}.`;
    return `Main agent queries ${event.testimony_added.specialist_name}: ${question}`;
  }
  return `${event.tool ?? "tool_call"} completed.`;
}

function useTypewriter(text: string, active: boolean) {
  const [typed, setTyped] = useState(text);

  useEffect(() => {
    if (!active) {
      setTyped(text);
      return;
    }
    let index = 0;
    setTyped("");
    const timer = window.setInterval(() => {
      index += Math.max(1, Math.round(text.length / 96));
      setTyped(text.slice(0, index));
      if (index >= text.length) window.clearInterval(timer);
    }, 64);
    return () => window.clearInterval(timer);
  }, [active, text]);

  return typed;
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

function AgentFlow({
  event,
  typedPrompt,
  playback,
  settled = false,
}: {
  event: TimelineEvent | undefined;
  typedPrompt: string;
  playback: PlaybackState;
  settled?: boolean;
}) {
  const testimony = event?.testimony_added;
  const verdict = event?.verdict;
  const target = verdict
    ? "Verdict"
    : testimony?.specialist_name ?? (event?.type === "session_start" ? "Roster" : "Record");
  const status =
    settled || playback === "complete"
      ? "complete"
      : playback === "running"
        ? "streaming"
        : playback === "paused"
          ? "paused"
          : "complete";

  return (
    <section className={`cvp-agent-flow cvp-agent-flow-${status}`} data-testid="agent-flow">
      <div className="cvp-agent-kicker">
        <span>{GLYPH.verdict} Main Agent</span>
        <em>{status}</em>
      </div>
      <div className="cvp-agent-route">
        <span>Planner</span>
        <i>{GLYPH.arrow}</i>
        <span>{target}</span>
        <i>{GLYPH.arrow}</i>
        <span>{verdict ? "Token-efficient answer" : "Compact record"}</span>
      </div>
      <p>
        {typedPrompt}
        {playback === "running" && !settled && <b aria-hidden="true" />}
      </p>
    </section>
  );
}

function ParallelInterrogation({
  specialists,
  testimony,
  activeId,
  playback,
  world,
  settled = false,
}: {
  specialists: SpecialistCard[];
  testimony: TestimonyVisible[];
  activeId: string | null;
  playback: PlaybackState;
  world: ReplayBundle["world"];
  settled?: boolean;
}) {
  const sampled = useMemo(() => sampledBySource(testimony), [testimony]);
  const latest = useMemo(() => latestBySource(testimony), [testimony]);
  const max = Math.max(
    1,
    ...specialists.map((source) =>
      Math.max(source.requested_tokens, sampled[source.id]?.tokens ?? 0),
    ),
  );
  const activeTraversal = !settled && (playback === "running" || playback === "paused");

  return (
    <section className="cvp-parallel-panel">
      <div className="cvp-parallel-head">
        <h3>{GLYPH.timeline} INTERROGATION TIMELINE</h3>
        <span>{settled ? "hearing complete" : activeTraversal ? "parallel traversal" : "replay trace"}</span>
      </div>

      <div className="cvp-subagent-grid" data-testid="subagent-grid">
        {specialists.map((source, index) => {
          const block = latest[source.id];
          const pulled = sampled[source.id]?.tokens ?? 0;
          const active = !settled && activeId === source.id;
          const state = active
            ? "reporting"
            : block
              ? "returned"
              : activeTraversal
                ? "traversing"
                : "queued";
          const document = documentForSource(source, index, world.domain);

          return (
            <article className={`cvp-subagent-card ${state}`} data-state={state} key={source.id}>
              <div className="cvp-subagent-head">
                <span>{source.name}</span>
                <em>{state}</em>
              </div>
              <p>{block?.visible_text ?? block?.question ?? source.public_bid}</p>
              <div className="cvp-subagent-footer">
                <span>{document.id}</span>
                <span>{block ? `${block.token_count}t returned` : `${source.requested_tokens}t bid`}</span>
              </div>
              <div className="cvp-subagent-bar" aria-hidden="true">
                <i style={{ width: `${(source.requested_tokens / max) * 100}%` }} />
                <b style={{ width: `${(pulled / max) * 100}%` }} />
              </div>
            </article>
          );
        })}
      </div>

      <div className="cvp-doc-layer">
        <div className="cvp-parallel-head">
          <h3>{GLYPH.source} EVIDENCE SOURCES</h3>
          <span>documents traversed by subagents</span>
        </div>
        <div className="cvp-doc-grid">
          {specialists.map((source, index) => {
            const block = latest[source.id];
            const active = !settled && activeId === source.id;
            const state = active ? "active" : block ? "visited" : activeTraversal ? "scanning" : "idle";
            const document = documentForSource(source, index, world.domain);

            return (
              <article className={`cvp-doc-card ${state}`} data-state={state} key={source.id}>
                <span>{document.id}</span>
                <strong>{document.label}</strong>
                <p>{block?.visible_text ?? document.detail}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function SourceActivity({
  specialists,
  testimony,
  activeId,
}: {
  specialists: SpecialistCard[];
  testimony: TestimonyVisible[];
  activeId: string | null;
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
          const active = activeId === source.id;
          return (
            <div
              className={`cvp-source-row${active ? " active" : ""}`}
              data-active={active ? "true" : "false"}
              key={source.id}
            >
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

function TimelinePanel({
  events,
  activeIndex,
  playback,
}: {
  events: TimelineEvent[];
  activeIndex: number | null;
  playback: PlaybackState;
}) {
  const calls = events.filter((event) => event.type === "tool_call");
  return (
    <article className="cvp-timeline-panel">
      <h3>{GLYPH.timeline} INTERROGATION TIMELINE</h3>
      <div className="cvp-timeline" data-testid="timeline">
        {calls.length === 0 && (
          <p className="cvp-empty">
            {playback === "running"
              ? "Speaker is scanning public cards..."
              : "Replay the hearing to reveal the tool calls."}
          </p>
        )}
        {calls.map((event) => {
          const testimony = event.testimony_added;
          const verdict = event.verdict;
          const active = activeIndex === event.index && playback !== "complete";
          return (
            <div
              className={`cvp-timeline-row${active ? " active" : ""}`}
              data-active={active ? "true" : "false"}
              key={event.index}
            >
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
  emptyMessage = "No testimony has entered the official record yet.",
}: {
  testimony: TestimonyVisible[];
  citationIds: string[];
  audit: boolean;
  emptyMessage?: string;
}) {
  const citations = new Set(citationIds);
  return (
    <div className="cvp-record-table" data-testid="record-table">
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
          {testimony.length === 0 && (
            <tr className="cvp-empty-row">
              <td colSpan={5}>{emptyMessage}</td>
            </tr>
          )}
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
    </div>
  );
}

function SpeakerRightPanel({
  events,
  verdict,
  currentEvent,
  typedPrompt,
  playback,
  liveDeliberating = false,
  hearingComplete = false,
}: {
  events: TimelineEvent[];
  verdict: NonNullable<TimelineEvent["verdict"]> | null;
  currentEvent: TimelineEvent | undefined;
  typedPrompt: string;
  playback: PlaybackState;
  liveDeliberating?: boolean;
  hearingComplete?: boolean;
}) {
  const activity = events
    .filter((event) => event.type === "tool_call")
    .slice(-5)
    .reverse();

  return (
    <>
      <section className="cvp-right-section cvp-output">
        <h2>{verdict ? `${GLYPH.verdict} MAIN AGENT OUTPUT` : `${GLYPH.timeline} LIVE AGENT TRACE`}</h2>
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
          <>
            <div className="cvp-output-decision">
              {hearingComplete
                ? "Hearing Complete"
                : playback === "complete"
                  ? "Ready To Replay"
                  : liveDeliberating
                    ? "Deliberating"
                    : "Gathering Evidence"}
            </div>
            <p>{typedPrompt}</p>
            <div className="cvp-citation-row">
              <span className={`cvp-pill ${playback === "running" ? "green" : "neutral"}`}>
                {playback}
              </span>
              {currentEvent?.testimony_added && (
                <span className="cvp-pill blue">{currentEvent.testimony_added.specialist_name}</span>
              )}
            </div>
          </>
        )}
      </section>

      <section className="cvp-right-section cvp-recent">
        <h2>{GLYPH.timeline} TOOL ACTIVITY</h2>
        {activity.length === 0 && <p className="cvp-empty">No tool calls yet.</p>}
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
  const [mode, setMode] = useState<ViewMode>("speaker");
  const [playback, setPlayback] = useState<PlaybackState>("complete");
  const [playhead, setPlayhead] = useState<number | null>(null);
  const [autoplay, setAutoplay] = useState(false);

  const liveMode = isLivePolicy(DEFAULT_POLICY);
  const session = useSessionStream(worldId, DEFAULT_POLICY);
  const bundle = session.bundle;
  const loadError =
    session.error ??
    (session.phase === "loading" ? "Loading hearing…" : null);

  useEffect(() => {
    loadReplayIndex().then(setCatalog).catch((error) => {
      console.error(error);
    });
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("view");
    if (requested === "audit" || requested === "speaker") {
      setMode(requested);
    }
    setAutoplay(params.get("autoplay") === "1");
  }, []);

  useEffect(() => {
    setPlayback("complete");
    setPlayhead(null);
  }, [worldId]);

  const startReplay = useCallback(() => {
    if (!bundle || liveMode) return;
    setPlayhead(0);
    setPlayback("running");
  }, [bundle, liveMode]);

  useEffect(() => {
    if (bundle && autoplay && !liveMode) {
      startReplay();
      setAutoplay(false);
    }
  }, [autoplay, bundle, liveMode, startReplay]);

  useEffect(() => {
    if (liveMode || !bundle || playback !== "running") return;
    const events = bundle.timeline;
    const maxIndex = events.at(-1)?.index ?? 0;
    const current = events.find((event) => event.index === playhead);

    if ((playhead ?? 0) >= maxIndex) {
      const done = window.setTimeout(() => {
        setPlayback("complete");
      }, eventDelay(current));
      return () => window.clearTimeout(done);
    }

    const timer = window.setTimeout(() => {
      setPlayhead((currentHead) => Math.min(maxIndex, (currentHead ?? 0) + 1));
    }, eventDelay(current));
    return () => window.clearTimeout(timer);
  }, [bundle, liveMode, playhead, playback]);

  useEffect(() => {
    if (!liveMode || !bundle) return;
    if (session.phase === "running" || session.phase === "complete") {
      const events = liveTimelineEvents(bundle, session.liveEvents);
      const latest = events.at(-1)?.index ?? 0;
      setPlayhead(latest);
      setPlayback(session.phase === "complete" ? "complete" : "running");
    }
  }, [liveMode, bundle, session.liveEvents, session.phase]);

  const togglePlayback = () => {
    if (!bundle) return;
    if (liveMode) {
      if (session.phase === "running") return;
      if (session.canStart) session.start();
      return;
    }
    if (playback === "running") {
      setPlayback("paused");
      return;
    }
    if (playback === "paused") {
      setPlayback("running");
      return;
    }
    startReplay();
  };

  const preset = catalog?.presets.find((item) => item.world_id === worldId);
  const allEvents = liveMode
    ? bundle
      ? liveTimelineEvents(bundle, session.liveEvents)
      : []
    : (bundle?.timeline ?? []);
  const visibleEvents =
    liveMode || playhead == null
      ? allEvents
      : allEvents.filter((event) => event.index <= playhead);
  const visibleTestimony = resolveVisibleTestimony(
    visibleEvents,
    liveMode,
    session.liveEvents,
  );
  const hasRecordTokens = visibleTestimony.length > 0;
  const visibleVerdict = resolveVisibleVerdict(
    visibleEvents,
    liveMode,
    session.liveEvents,
    bundle?.verdict,
  );
  const activeEvent = liveMode
    ? ([...allEvents].reverse().find((event) => event.testimony_added || event.verdict) ??
      allEvents.at(-1))
    : playhead == null
      ? undefined
      : allEvents.find((event) => event.index === playhead);
  const activeSpecialistId =
    liveMode && session.activeSpecialistId
      ? session.activeSpecialistId
      : (activeEvent?.testimony_added?.specialist_id ?? null);
  const agentPrompt = liveMode
    ? liveAgentPrompt(session.phase, session.liveEvents, activeEvent, bundle?.world)
    : promptFor(activeEvent, bundle?.world);
  const typedReplayPrompt = useTypewriter(agentPrompt, playback === "running" && !liveMode);
  const displayPrompt = liveMode ? agentPrompt : typedReplayPrompt;
  const specialists = liveMode
    ? session.specialists
    : (bundle?.timeline[0]?.payload?.specialists ?? []);
  const citationIds = visibleVerdict?.citation_ids ?? [];
  const lastBudgetEvent = [...visibleEvents]
    .reverse()
    .find((event) => event.budget_used !== undefined);
  const budgetUsed = liveMode
    ? hasRecordTokens
      ? session.budgetUsed
      : 0
    : Number(lastBudgetEvent?.budget_used ?? 0);
  const budgetTotal = bundle?.world.token_budget ?? 500;
  const budgetRemaining = liveMode
    ? hasRecordTokens
      ? session.budgetRemaining
      : budgetTotal
    : Math.max(0, budgetTotal - budgetUsed);
  const interactions = liveMode
    ? hasRecordTokens
      ? session.interactionsUsed
      : 0
    : visibleEvents.filter((event) => event.testimony_added).length;
  const liveDeliberating = liveMode && session.phase === "running" && !hasRecordTokens;
  const hearingSettled = Boolean(visibleVerdict) || (liveMode && session.phase === "complete");
  const replayLabel = liveMode
    ? session.phase === "running"
      ? "RUNNING…"
      : "START SESSION ▶"
    : playback === "running"
      ? "PAUSE"
      : playback === "paused"
        ? "RESUME"
        : "REPLAY";

  const speakerMetrics = [
    {
      icon: GLYPH.source,
      label: "EVIDENCE INPUTS",
      value: String(specialists.length),
      status: liveDeliberating ? "opening cards" : playback === "running" ? "cards open" : "public cards",
      tone: "green" as Tone,
    },
    {
      icon: GLYPH.record,
      label: "RECORD TOKENS",
      value: hasRecordTokens
        ? `${budgetUsed}/${budgetTotal}`
        : liveDeliberating
          ? "Interviewing"
          : "—",
      status: hasRecordTokens
        ? `${budgetRemaining} left`
        : liveDeliberating
          ? "awaiting testimony"
          : "not started",
      tone: "blue" as Tone,
    },
    {
      icon: GLYPH.timeline,
      label: "INTERROGATIONS",
      value: hasRecordTokens || !liveMode ? String(interactions) : liveDeliberating ? "Asking" : "—",
      status: liveDeliberating
        ? "speaker planning"
        : `${bundle?.world.max_interactions ?? 0} max`,
      tone: "yellow" as Tone,
    },
    {
      icon: GLYPH.verdict,
      label: "FINAL ANSWER",
      value: visibleVerdict ? shortOption(visibleVerdict.decision) : "Pending",
      status: visibleVerdict
        ? `${Math.round(visibleVerdict.confidence * 100)}% confidence`
        : liveMode && session.phase === "complete"
          ? `score ${bundle?.reward.reward.toFixed(2) ?? "—"}`
          : playback === "running"
            ? liveDeliberating
              ? "deliberating"
              : "synthesizing"
            : "ready",
      tone: visibleVerdict ? "green" as Tone : "neutral" as Tone,
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
      <section className="cvp-main-panel">
        <header className="cvp-topbar">
          <div className="cvp-brand-row cvp-brand-row-inline">
            <div className="cvp-brand-mark" aria-hidden="true">
              {GLYPH.mark}
            </div>
            <div>
              <div className="cvp-brand-name cvp-brand-name-long">{BRAND_NAME}</div>
              <p>context window</p>
            </div>
          </div>

          <div className="cvp-topbar-controls">
            <label className="cvp-search">
              <span aria-hidden="true">{GLYPH.search}</span>
              <select
                value={worldId}
                onChange={(event) => setWorldId(event.target.value)}
                aria-label="Replay docket"
                disabled={session.locked}
              >
                {catalog?.presets.map((item) => (
                  <option value={item.world_id} key={item.world_id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <ViewToggle mode={mode} onChange={setMode} />
          </div>
        </header>

        <section className="cvp-problem">
          <div>
            <h1>{preset?.label ?? BRAND_NAME}</h1>
            <p>{bundle?.world.narrative ?? loadError ?? "Loading hearing…"}</p>
          </div>
          <div className="cvp-problem-meta">
            <span>{bundle?.world.world_id ?? worldId}</span>
            <span>{bundle ? titleize(bundle.world.domain) : liveMode ? "Live" : "Replay"}</span>
            <span>{bundle ? titleize(bundle.world.difficulty) : "Loading"}</span>
            {liveMode && (
              <span className="cvp-live-badge">HUD Gateway + Haiku</span>
            )}
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
                <h2>{mode === "speaker" ? "Agent Deliberation" : "Scoring Internals"}</h2>
                <p>
                  {mode === "speaker"
                    ? "Main-agent fan-out, parallel subagent traversal, and compact record synthesis"
                    : "Ground-truth comparison and reward decomposition"}
                </p>
              </div>
              <div className="cvp-section-head-actions">
                <button
                  type="button"
                  data-testid="replay-button"
                  onClick={togglePlayback}
                  disabled={liveMode && (!session.canStart || session.locked)}
                >
                  {replayLabel}
                </button>
                {liveMode && (
                  <button
                    type="button"
                    className="cvp-reset-button"
                    onClick={session.dismiss}
                    disabled={session.locked}
                  >
                    Reset
                  </button>
                )}
              </div>
            </div>

            {mode === "speaker" ? (
              <>
                <AgentFlow
                  event={activeEvent}
                  typedPrompt={displayPrompt}
                  playback={playback}
                  settled={hearingSettled}
                />
                <ParallelInterrogation
                  specialists={specialists}
                  testimony={visibleTestimony}
                  activeId={activeSpecialistId}
                  playback={playback}
                  world={bundle.world}
                  settled={hearingSettled}
                />
              </>
            ) : (
              <div className="cvp-stats-grid cvp-audit-grid">
                <>
                  <ScoreBars bundle={bundle} />
                  <TokenBuckets bundle={bundle} />
                </>
              </div>
            )}
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
          <RecordTable
            testimony={visibleTestimony}
            citationIds={citationIds}
            audit={mode === "audit"}
            emptyMessage={
              liveDeliberating
                ? "Speaker is interviewing specialists — testimony will appear here once generated."
                : "No testimony has entered the official record yet."
            }
          />
        </section>
      </section>

      <aside className="cvp-right-panel">
        <button className="cvp-edge-pill" type="button" aria-label="Panel handle" />
        {bundle ? (
          mode === "speaker" ? (
            <SpeakerRightPanel
              events={visibleEvents}
              verdict={visibleVerdict}
              currentEvent={activeEvent}
              typedPrompt={displayPrompt}
              playback={playback}
              liveDeliberating={liveDeliberating}
              hearingComplete={liveMode && session.phase === "complete" && !visibleVerdict}
            />
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
