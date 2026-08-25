"use client";

import type { LiveFootballSnapshot } from "@/domain/adapters";
import { LiveDataState } from "@/components/live-data-state";

/** Orphaned GlassScout shell — not routed from FMTApp. */
export function DashboardScreen({
  snapshot,
  checking,
  onRefresh,
}: {
  snapshot: LiveFootballSnapshot;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
}) {
  return (
    <main className="screen">
      <LiveDataState snapshot={snapshot} title="Dashboard" checking={checking} onRefresh={onRefresh} />
      <p className="section-kicker">Use Squad — Dashboard is not part of the FMT club desk.</p>
    </main>
  );
}
