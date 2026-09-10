"use client";

import { useEffect, useState } from "react";
import { ChevronDown, Images } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";

type GraphicsPackEntry = {
  name: string;
  kind: "Faces" | "Logos" | string;
  path?: string;
};

type GraphicsStatusPayload = {
  packs: GraphicsPackEntry[];
  graphicsPath?: string;
};

export type GraphicsPacksStatus = {
  packs: GraphicsPackEntry[];
  graphicsPath?: string;
  loading: boolean;
};

function packPath(pack: GraphicsPackEntry, graphicsRoot?: string) {
  const direct = pack.path?.trim();
  if (direct) return direct;
  const root = graphicsRoot?.trim().replace(/[\\/]+$/, "");
  if (root) return `${root}\\${pack.name}`;
  return "Path unavailable";
}

/** Pack list body for Settings → Graphics (no outer expand). */
export function GraphicsPacksBody({ status }: { status: GraphicsPacksStatus | null }) {
  const packs = status?.packs ?? [];
  const graphicsRoot = status?.graphicsPath;

  return (
    <div className="read-pipeline-grid graphics-pack-grid">
      {!status || status.loading ? (
        <article data-state="pending">
          <span>…</span>
          <strong>Reading graphics folder</strong>
          <p>Checking FM26 graphics packs.</p>
        </article>
      ) : packs.length ? (
        packs.map((pack) => {
          const path = packPath(pack, graphicsRoot);
          return (
            <article key={`${pack.kind}:${pack.name}:${path}`} data-kind={pack.kind}>
              <span>{pack.kind}</span>
              <strong>{pack.name}</strong>
              <code className="graphics-pack-path">{path}</code>
            </article>
          );
        })
      ) : (
        <article data-state="pending">
          <span>None</span>
          <strong>No graphics packs found</strong>
          <p>Install face or logo packs under your FM26 graphics folder, then reopen Settings.</p>
        </article>
      )}
    </div>
  );
}

export function useGraphicsPacksStatus(): GraphicsPacksStatus | null {
  const [status, setStatus] = useState<GraphicsPacksStatus | null>(null);

  useEffect(() => {
    if (!("__TAURI_INTERNALS__" in window)) return;
    let cancelled = false;
    setStatus({ packs: [], graphicsPath: undefined, loading: true });
    void invoke<GraphicsStatusPayload>("graphics_status")
      .then((next) => {
        if (!cancelled) {
          setStatus({
            packs: next.packs ?? [],
            graphicsPath: next.graphicsPath,
            loading: false,
          });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus({ packs: [], graphicsPath: undefined, loading: false });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!("__TAURI_INTERNALS__" in window)) return null;
  return status;
}

/** @deprecated Prefer Settings → Graphics + GraphicsPacksBody. Kept for any leftover imports. */
export function GraphicsPacksPanel() {
  const status = useGraphicsPacksStatus();
  if (!status && !("__TAURI_INTERNALS__" in window)) return null;
  return (
    <details className="settings-expand" id="graphics-packs">
      <summary>
        <Images aria-hidden="true" />
        <div>
          <strong>Graphics</strong>
          <span>Player faces and club logos from your FM26 graphics folder.</span>
        </div>
        <span className="settings-expand-meta">
          <b>{!status || status.loading ? "…" : status.packs.length ? `${status.packs.length} packs` : "None"}</b>
          <ChevronDown className="settings-expand-chevron" aria-hidden="true" />
        </span>
      </summary>
      <div className="settings-expand-body">
        <GraphicsPacksBody status={status} />
      </div>
    </details>
  );
}
