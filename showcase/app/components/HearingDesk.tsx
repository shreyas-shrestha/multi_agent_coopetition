"use client";

import { CompareTab } from "@/components/CompareTab";
import { TrainingTab } from "@/components/TrainingTab";
import { DocketBriefing } from "@/components/posthog/DocketBriefing";
import { EvidenceSourcePanel } from "@/components/posthog/EvidenceSourcePanel";
import { LiveRecordTable } from "@/components/posthog/LiveRecordTable";
import { ParliamentShell } from "@/components/posthog/ParliamentShell";
import { TokenAnalyticsPanel } from "@/components/posthog/TokenAnalyticsPanel";
import { TransferOverlay } from "@/components/posthog/TransferOverlay";
import { useSessionStream } from "@/hooks/useSessionStream";
import { isLivePolicy, orchestratorBaseUrl } from "@/lib/live";
import { loadReplayIndex } from "@/lib/replay";
import type { PolicyId, ReplayIndex } from "@/lib/types";
import { useEffect, useState } from "react";

const DEFAULT_WORLD = "incident-response-medium-004";
const DEFAULT_POLICY: PolicyId = "targeted_oracle";

type Tab = "hearing" | "compare" | "training";
type Stage = "briefing" | "desk";

export default function HearingDeskPage() {
  const [tab, setTab] = useState<Tab>("hearing");
  const [stage, setStage] = useState<Stage>("briefing");
  const [catalog, setCatalog] = useState<ReplayIndex | null>(null);
  const [worldId, setWorldId] = useState(DEFAULT_WORLD);
  const [policy, setPolicy] = useState<PolicyId>(DEFAULT_POLICY);

  const session = useSessionStream(worldId, policy);
  const liveMode = isLivePolicy(policy);
  const orchestrator = orchestratorBaseUrl();

  useEffect(() => {
    loadReplayIndex().then(setCatalog).catch(console.error);
  }, []);

  const preset = catalog?.presets.find((p) => p.world_id === worldId);
  const policyMeta = catalog?.policies.find((p) => p.id === policy);

  const toolbar =
    stage === "desk" ? (
      <div className="cvp-desk-toolbar">
        <span className="mono">
          {liveMode ? "LIVE" : "REPLAY"} · {session.policyLabel}
        </span>
        <div className="cvp-desk-actions">
          <button type="button" disabled={!session.canStart} onClick={session.start}>
            {session.phase === "running" ? "Running…" : "Start session ▶"}
          </button>
          <button type="button" disabled={session.phase === "running"} onClick={session.dismiss}>
            Reset
          </button>
          <button type="button" onClick={() => setStage("briefing")}>
            Change docket
          </button>
        </div>
      </div>
    ) : null;

  return (
    <ParliamentShell
      tab={tab}
      onTabChange={setTab}
      windowTitle={stage === "briefing" ? "Convene a hearing" : preset?.label ?? "Hearing desk"}
      windowSubtitle={
        stage === "briefing"
          ? "Pick a docket and Speaker — nothing runs until you start the session."
          : `${session.bundle?.world.domain.replaceAll("_", " ") ?? "world"} · ${session.bundle?.world.difficulty ?? ""}`
      }
      windowBadge={
        liveMode ? (
          <span className="cvp-live-badge mono">HUD · {orchestrator ? "Modal live" : "offline"}</span>
        ) : (
          <span className="cvp-live-badge mono">Replay</span>
        )
      }
      toolbar={toolbar}
    >
      {tab === "compare" && (
        <CompareTab
          replayAs={(nextPolicy) => {
            setPolicy(nextPolicy);
            setTab("hearing");
            setStage("briefing");
          }}
        />
      )}
      {tab === "training" && <TrainingTab />}
      {tab === "hearing" && stage === "briefing" && catalog && (
        <DocketBriefing
          catalog={catalog}
          world={worldId}
          policy={policy}
          narrative={session.bundle?.world.narrative}
          tokenBudget={session.bundle?.world.token_budget}
          maxInteractions={session.bundle?.world.max_interactions}
          onWorldChange={setWorldId}
          onPolicyChange={setPolicy}
          onConvene={() => setStage("desk")}
          loading={session.phase === "loading"}
        />
      )}
      {tab === "hearing" && stage === "desk" && session.bundle && (
        <div className="cvp-hearing-desk">
          <EvidenceSourcePanel
            bundle={session.bundle}
            specialists={session.specialists}
            visibleIds={session.visibleSpecialistIds}
            activeId={session.activeSpecialistId}
            sampledMap={session.sampledMap}
            phase={session.phase}
          />
          <LiveRecordTable
            events={session.liveEvents}
            phase={session.phase}
            expandedId={session.expandedId}
            onToggle={(id) =>
              session.setExpandedId(session.expandedId === id ? null : id)
            }
            waiting={session.phase === "running" && session.liveEvents.length === 0}
          />
          <TokenAnalyticsPanel
            bundle={session.bundle}
            phase={session.phase}
            budgetUsed={session.budgetUsed}
            budgetTotal={session.bundle.world.token_budget}
            budgetRemaining={session.budgetRemaining}
            interactionsUsed={session.interactionsUsed}
            maxInteractions={session.bundle.world.max_interactions}
            naiveStack={session.naiveTokenStack}
          />
          <TransferOverlay transfer={session.transfer} />
          {(session.error || session.phase === "error") && (
            <div className="cvp-hearing-error">{session.error ?? "Hearing failed"}</div>
          )}
          {liveMode && (
            <p className="cvp-hearing-note mono">
              Specialists: Anthropic Haiku · Speaker: parliament-qwen36-35b-clean via HUD Gateway
            </p>
          )}
          {!liveMode && policyMeta && (
            <p className="cvp-hearing-note mono">{policyMeta.subtitle}</p>
          )}
        </div>
      )}
      {tab === "hearing" && stage === "desk" && !session.bundle && (
        <p className="cvp-hearing-note">{session.error ?? "Loading hearing…"}</p>
      )}
    </ParliamentShell>
  );
}
