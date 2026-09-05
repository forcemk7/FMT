"use client";

import { useEffect, useState } from "react";
import { UserRound } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { whenFmtCosmeticsReady, isFmtCosmeticsReady } from "@/domain/cosmetics-ready";
import { cn } from "@/lib/utils";

type PlayerFaceResult = {
  found: boolean;
  playerId: string;
  dataUrl: string | null;
  source: "fm-unique-id" | "fallback";
};

const faceCache = new Map<string, string | null>();
const RETRY_MS = [400, 1200, 2800, 5000, 9000];

export function clearPlayerFaceMemoryCache() {
  faceCache.clear();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("fmt-faces-updated"));
  }
}

export function PlayerFace({ playerId, name, size = "md", highResolution = false }: {
  playerId: string;
  name: string;
  size?: "sm" | "md" | "lg";
  highResolution?: boolean;
}) {
  // Prefer portraits everywhere — icon packs are incomplete; backend still accepts icon=false.
  const useIcon = false;
  const cacheKey = `${playerId}:${useIcon ? "icon" : "portrait"}`;
  const [source, setSource] = useState<string | null | undefined>(() => {
    if (faceCache.has(cacheKey)) return faceCache.get(cacheKey);
    if (typeof window !== "undefined" && !("__TAURI_INTERNALS__" in window)) return null;
    return undefined;
  });

  useEffect(() => {
    if (!("__TAURI_INTERNALS__" in window)) {
      faceCache.set(cacheKey, null);
      setSource(null);
      return;
    }

    let active = true;
    const timers: number[] = [];

    const apply = (next: string | null) => {
      faceCache.set(cacheKey, next);
      if (active) setSource(next);
    };

    const load = (attempt: number) => {
      const hit = faceCache.get(cacheKey);
      if (hit) {
        if (active) setSource(hit);
        return;
      }
      invoke<PlayerFaceResult>("player_face_data", { playerId, icon: useIcon })
        .then((result) => {
          if (!active) return;
          const next = result.found && result.dataUrl ? result.dataUrl : null;
          if (next) {
            apply(next);
            return;
          }
          // Soft miss while background warm copies into face-cache — retry a few times.
          if (attempt < RETRY_MS.length) {
            timers.push(
              window.setTimeout(() => {
                faceCache.delete(cacheKey);
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

    const onUpdate = () => {
      faceCache.delete(cacheKey);
      if (active) setSource(undefined);
      load(0);
    };

    const startLoad = () => {
      load(0);
    };

    window.addEventListener("fmt-faces-updated", onUpdate);
    if (isFmtCosmeticsReady()) {
      startLoad();
    } else {
      whenFmtCosmeticsReady(startLoad);
    }

    return () => {
      active = false;
      timers.forEach((id) => window.clearTimeout(id));
      window.removeEventListener("fmt-faces-updated", onUpdate);
    };
  }, [cacheKey, playerId, useIcon]);

  return (
    <span className={cn("player-face", `player-face-${size}`)} title={`${name} · FM ID ${playerId}`}>
      {source ? <img src={source} alt={`${name} portrait`} /> : <UserRound aria-label="No player face available" />}
    </span>
  );
}
