"use client";

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

type ClubLogoResult = { found: boolean; clubId: string; dataUrl: string | null };
const cache = new Map<string, string | null>();
const RETRY_MS = [400, 1200, 2800, 5000];

export function clearClubLogoMemoryCache() {
  cache.clear();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("fmt-logos-updated"));
  }
}

export function ClubLogo({
  clubId,
  name,
  size = "md",
}: {
  clubId: string;
  name: string;
  size?: "sm" | "md" | "lg";
}) {
  const [source, setSource] = useState<string | null | undefined>(() => {
    if (cache.has(clubId)) return cache.get(clubId);
    if (typeof window !== "undefined" && !("__TAURI_INTERNALS__" in window)) return null;
    return undefined;
  });

  useEffect(() => {
    if (!("__TAURI_INTERNALS__" in window)) {
      cache.set(clubId, null);
      setSource(null);
      return;
    }

    let active = true;
    let timers: number[] = [];

    const apply = (next: string | null) => {
      cache.set(clubId, next);
      if (active) setSource(next);
    };

    const load = (attempt: number) => {
      const hit = cache.get(clubId);
      if (hit) {
        if (active) setSource(hit);
        return;
      }
      invoke<ClubLogoResult>("club_logo_data", { clubId })
        .then((result) => {
          if (!active) return;
          const next = result.found && result.dataUrl ? result.dataUrl : null;
          if (next) {
            apply(next);
            return;
          }
          if (attempt < RETRY_MS.length) {
            timers.push(
              window.setTimeout(() => {
                cache.delete(clubId);
                load(attempt + 1);
              }, RETRY_MS[attempt]),
            );
          } else {
            apply(null);
          }
        })
        .catch(() => {
          if (!active) return;
          apply(null);
        });
    };

    load(0);
    const onUpdate = () => {
      cache.delete(clubId);
      if (active) setSource(undefined);
      load(0);
    };
    window.addEventListener("fmt-logos-updated", onUpdate);
    return () => {
      active = false;
      timers.forEach((id) => window.clearTimeout(id));
      window.removeEventListener("fmt-logos-updated", onUpdate);
    };
  }, [clubId]);

  if (!source) {
    return (
      <span className={`club-logo club-logo-${size} club-logo-empty`} aria-hidden="true" />
    );
  }
  return (
    <span className={`club-logo club-logo-${size}`}>
      <span className="badge-media">
        <img src={source} alt={`${name} badge from FM club ID ${clubId}`} />
      </span>
    </span>
  );
}
