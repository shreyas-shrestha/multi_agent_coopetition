import type { PolicyId, ReplayBundle, TimelineEvent } from "./types";

const orchestratorUrl = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL?.replace(/\/$/, "") ?? "";

export function isLivePolicy(policy: PolicyId): boolean {
  return policy === "targeted_oracle" && Boolean(orchestratorUrl);
}

export function orchestratorBaseUrl(): string {
  return orchestratorUrl;
}

export async function loadLivePreview(worldId: string): Promise<ReplayBundle> {
  const base = orchestratorBaseUrl();
  if (!base) throw new Error("NEXT_PUBLIC_ORCHESTRATOR_URL is not configured");
  const response = await fetch(`${base}/api/worlds/${encodeURIComponent(worldId)}/preview`);
  if (!response.ok) {
    throw new Error(`Live preview failed (${response.status})`);
  }
  return response.json();
}

export type LiveStreamHandlers = {
  onTimeline: (event: TimelineEvent) => void;
  onComplete: (payload: {
    reward: ReplayBundle["reward"];
    final_record: ReplayBundle["final_record"];
    meta?: Record<string, unknown>;
  }) => void;
  onError: (message: string) => void;
};

export function openLiveHearingStream(
  worldId: string,
  handlers: LiveStreamHandlers,
): EventSource {
  const base = orchestratorBaseUrl();
  const url = `${base}/api/hearing/stream?world_id=${encodeURIComponent(worldId)}`;
  const source = new EventSource(url);

  source.addEventListener("timeline", (message) => {
    try {
      const event = JSON.parse((message as MessageEvent<string>).data) as TimelineEvent;
      handlers.onTimeline(event);
    } catch (error) {
      handlers.onError(error instanceof Error ? error.message : "Malformed timeline event");
    }
  });

  source.addEventListener("complete", (message) => {
    try {
      const payload = JSON.parse((message as MessageEvent<string>).data) as {
        reward: ReplayBundle["reward"];
        final_record: ReplayBundle["final_record"];
        meta?: Record<string, unknown>;
      };
      handlers.onComplete(payload);
      source.close();
    } catch (error) {
      handlers.onError(error instanceof Error ? error.message : "Malformed completion event");
      source.close();
    }
  });

  source.addEventListener("error", (message) => {
    if (message instanceof MessageEvent && message.data) {
      try {
        const payload = JSON.parse(message.data) as { message?: string };
        handlers.onError(payload.message ?? "Live hearing failed");
      } catch {
        handlers.onError("Live hearing failed");
      }
      source.close();
      return;
    }
    if (source.readyState === EventSource.CLOSED) return;
    handlers.onError("Live hearing connection lost");
    source.close();
  });

  return source;
}
