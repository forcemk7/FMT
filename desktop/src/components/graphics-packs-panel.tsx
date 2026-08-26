"use client";

import { useEffect, useState } from "react";
import { Images } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";

type GraphicsPackEntry = {
  name: string;
  kind: "Faces" | "Logos" | string;
};

type GraphicsStatusPayload = {
  packs: GraphicsPackEntry[];
  graphicsExists: boolean;
};

export function GraphicsPacksPanel() {
  const [status, setStatus] = useState<GraphicsStatusPayload | null>(null);

  useEffect(() => {
    if (!("__TAURI_INTERNALS__" in window)) return;
    let cancelled = false;
    void invoke<GraphicsStatusPayload>("graphics_status")
      .then((next) => {
        if (!cancelled) setStatus(next);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  if (!("__TAURI_INTERNALS__" in window)) {
    return null;
  }

  const packs = status?.packs ?? [];
  const ready = Boolean(status?.graphicsExists && packs.length);

  return (
    <article>
      <Images aria-hidden="true" />
      <div>
        <strong>Graphics</strong>
        {!status ? (
          <span>Checking…</span>
        ) : packs.length ? (
          <ul className="settings-face-pills">
            {packs.map((pack) => (
              <li key={`${pack.kind}:${pack.name}`}>
                <b data-kind={pack.kind}>{pack.kind}</b>
                {pack.name}
              </li>
            ))}
          </ul>
        ) : (
          <span>No packs found</span>
        )}
      </div>
      <b>{!status ? "…" : ready ? `${packs.length} pack${packs.length === 1 ? "" : "s"}` : "None"}</b>
    </article>
  );
}
