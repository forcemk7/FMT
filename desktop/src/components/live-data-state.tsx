"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { LiveFootballSnapshot } from "@/domain/adapters";

/** Empty / not-ready desk — show only real signals; prefer blank over filler. */
export function LiveDataState({
  snapshot,
  title,
  checking,
  onRefresh,
}: {
  snapshot: LiveFootballSnapshot;
  title: string;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
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

  const hasSignal = checking || fmRunning || Boolean(failure) || Boolean(usefulMessage);

  if (!hasSignal) {
    return <section className="live-data-state is-empty" aria-label={`${title} empty`} />;
  }

  return (
    <section className="live-data-state" role="status" aria-live="polite">
      <div>
        {checking ? (
          <>
            <h1>Loading…</h1>
            <p>Reading the active FM26 save.</p>
          </>
        ) : fmRunning && !failure ? (
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
            <h1>{title}</h1>
            {usefulMessage ? <p>{usefulMessage}</p> : null}
          </>
        )}
      </div>
      <div className="live-data-state-actions">
        <Button onClick={onRefresh} disabled={checking}>
          <RefreshCw data-icon="inline-start" className={checking ? "spin" : undefined} />
          {checking ? "Loading…" : "Load Data"}
        </Button>
      </div>
    </section>
  );
}
