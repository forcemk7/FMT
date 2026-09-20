"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { LiveFootballSnapshot } from "@/domain/adapters";
import { cn } from "@/lib/utils";

/** Empty / not-ready desk — structure stays; this fills the data hole only. */
export function LiveDataState({
  snapshot,
  title,
  checking,
  onRefresh,
  compact = false,
}: {
  snapshot: LiveFootballSnapshot;
  title: string;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
  compact?: boolean;
}) {
  const status = snapshot.status;
  const fmRunning = status.processDetected;
  const failure =
    status.failureStage && status.failureStage !== "none"
      ? status.failureStage.replaceAll("_", " ")
      : null;
  const usefulMessage =
    status.message &&
    status.message !== "Diagnostics have not run yet." &&
    !status.message.toLowerCase().includes("have not run")
      ? status.message
      : null;

  if (checking) {
    return (
      <section
        className={cn("live-data-state", compact ? "is-compact" : "is-empty")}
        aria-busy="true"
        aria-label={`Loading ${title}`}
      >
        {compact ? <p>Loading live data…</p> : null}
      </section>
    );
  }

  const hasSignal = fmRunning || Boolean(failure) || Boolean(usefulMessage);

  if (!hasSignal && !compact) {
    return <section className="live-data-state is-empty" aria-label={`${title} empty`} />;
  }

  return (
    <section
      className={cn("live-data-state", compact && "is-compact")}
      role="status"
      aria-live="polite"
    >
      <div>
        {fmRunning && !failure ? (
          <>
            <h1>FM26 is running</h1>
            <p>{usefulMessage ?? "Save is open — load when you want the squad desk."}</p>
          </>
        ) : failure ? (
          <>
            <h1>{title} could not load</h1>
            <p>{usefulMessage ?? failure}</p>
          </>
        ) : (
          <>
            <h1>{compact ? "No live squad yet" : title}</h1>
            <p>{usefulMessage ?? "Use Load Data in the header when Football Manager 26 has a career save open."}</p>
          </>
        )}
      </div>
      <div className="live-data-state-actions">
        <Button onClick={onRefresh}>
          <RefreshCw data-icon="inline-start" />
          Load Data
        </Button>
      </div>
    </section>
  );
}
