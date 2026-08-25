"use client";

import { useEffect, useState } from "react";
import { Check, Database, Download, LockKeyhole, RefreshCw, ShieldCheck } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import type { LiveConnectorStatus } from "@/domain/adapters";
import { windowsInstallerUrl } from "@/domain/distribution";
import { cn } from "@/lib/utils";

const loadStageLabels: Record<string, string> = {
  detecting_fm26: "Detecting FM26…",
  validating_active_save: "Validating active save…",
  reading_managed_club: "Reading managed club…",
  loading_managed_squad: "Loading managed squad…",
  indexing_player_database: "Indexing wider player database…",
  building_visibility_index: "Building scouting-knowledge index…",
  ready: "Ready",
};

function readable(value: string | null | undefined) {
  if (!value) return "None";
  return value.replaceAll("_", " ").replaceAll("-", " ");
}

export function StartupScreen({
  onConnect,
  onEnter,
}: {
  onConnect: () => Promise<LiveConnectorStatus>;
  onEnter: (status: LiveConnectorStatus) => void;
}) {
  // SSR and the first client paint must match. Detect Tauri only after mount.
  const [runtime, setRuntime] = useState<"pending" | "desktop" | "web">("pending");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<LiveConnectorStatus | null>(null);
  const [loadStage, setLoadStage] = useState("detecting_fm26");
  const desktopRuntime = runtime === "desktop";

  useEffect(() => {
    setRuntime(
      typeof window !== "undefined" && "__TAURI_INTERNALS__" in window ? "desktop" : "web",
    );
  }, []);

  useEffect(() => {
    if (!desktopRuntime) return;
    let remove: (() => void) | null = null;
    void import("@tauri-apps/api/event")
      .then(({ listen }) => listen<string>("fmt-load-progress", (event) => {
        setLoadStage(event.payload);
      }))
      .then((unlisten) => {
        remove = unlisten;
      });
    return () => remove?.();
  }, [desktopRuntime]);

  const loadActiveSave = async () => {
    setLoading(true);
    setLoadStage("detecting_fm26");
    try {
      const next = await onConnect();
      setStatus(next);
      if (next.state === "connected") onEnter(next);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="startup-screen live-startup">
      <div className="startup-brand">
        <span className="brand-mark"><span /></span>
        <span><strong>FMT</strong><small>club desk</small></span>
      </div>

      <section className="live-start-card">
        {runtime === "pending" ? (
          <>
            <span className="live-start-icon"><Database /></span>
            <p className="section-kicker">Live FM26 connection</p>
            <h1>Starting FMT…</h1>
            <p>Preparing the live connector UI.</p>
            <Button disabled>
              <RefreshCw data-icon="inline-start" className="spin" />
              Starting…
            </Button>
          </>
        ) : (
          <>
            <span className="live-start-icon">{desktopRuntime ? <Database /> : <ShieldCheck />}</span>
            <p className="section-kicker">Live FM26 connection</p>
            <h1>{desktopRuntime ? "Load your active FM26 save" : "Install FMT for Windows"}</h1>
            <p>
              {desktopRuntime
                ? "Open FM26 and load your save, then start a read-only scan. Your club squad loads first; the wider player index continues in the background."
                : "FMT reads the active FM26 game through its Windows desktop connector."}
            </p>
            {desktopRuntime ? (
              <Button onClick={loadActiveSave} disabled={loading}>
                {loading ? <RefreshCw data-icon="inline-start" className="spin" /> : <Database data-icon="inline-start" />}
                {loading ? loadStageLabels[loadStage] ?? "Reading active save…" : "Load Active Save"}
              </Button>
            ) : (
              <a className={cn(buttonVariants({ size: "lg" }), "setup-download")} href={windowsInstallerUrl}>
                <Download data-icon="inline-start" />Download FMT for Windows
              </a>
            )}
          </>
        )}
        <div className="live-start-trust">
          <span><Check />Active game only</span>
          <span><LockKeyhole />Read-only access</span>
          <span><ShieldCheck />No simulated players</span>
        </div>
        {status && status.state !== "connected" ? (
          <div className="load-failure" role="alert">
            <strong>{status.message}</strong>
            <span>Failed stage: {readable(status.failureStage)}</span>
            <span>Last successful read: {readable(status.lastSuccessfulRead)}</span>
            <span>Memory access: {readable(status.memoryAccess)}</span>
          </div>
        ) : null}
      </section>
    </main>
  );
}
