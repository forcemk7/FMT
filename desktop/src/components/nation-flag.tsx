"use client";

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { badgeObjectFit } from "@/domain/badge-fit";

type NationFlagResult = { found: boolean; nationId: string; dataUrl: string | null };
const cache = new Map<string, string | null>();
const RETRY_MS = [400, 1200, 2800, 5000];

export function clearNationFlagMemoryCache() {
  cache.clear();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("fmt-flags-updated"));
  }
}

export function NationFlag({
  nationId,
  name,
  size = "sm",
}: {
  nationId: string;
  name: string;
  size?: "sm" | "md";
}) {
  const [source, setSource] = useState<string | null | undefined>(() => {
    if (cache.has(nationId)) return cache.get(nationId);
    if (typeof window !== "undefined" && !("__TAURI_INTERNALS__" in window)) return null;
    return undefined;
  });
  const [fit, setFit] = useState<"contain" | "cover">("contain");

  useEffect(() => {
    if (!("__TAURI_INTERNALS__" in window)) {
      cache.set(nationId, null);
      setSource(null);
      return;
    }

    let active = true;
    let timers: number[] = [];

    const apply = (next: string | null) => {
      cache.set(nationId, next);
      if (active) {
        setFit("contain");
        setSource(next);
      }
    };

    const load = (attempt: number) => {
      const hit = cache.get(nationId);
      if (hit) {
        if (active) setSource(hit);
        return;
      }
      invoke<NationFlagResult>("nation_flag_data", { nationId })
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
                cache.delete(nationId);
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
      cache.delete(nationId);
      if (active) setSource(undefined);
      load(0);
    };
    window.addEventListener("fmt-flags-updated", onUpdate);
    return () => {
      active = false;
      timers.forEach((id) => window.clearTimeout(id));
      window.removeEventListener("fmt-flags-updated", onUpdate);
    };
  }, [nationId]);

  if (!source) {
    return (
      <span className={`nation-flag nation-flag-${size} nation-flag-empty`} aria-hidden="true" />
    );
  }
  return (
    <span className={`nation-flag nation-flag-${size}`}>
      <img
        src={source}
        alt={`${name} flag from FM nation ID ${nationId}`}
        data-fit={fit}
        onLoad={(event) => {
          const img = event.currentTarget;
          setFit(badgeObjectFit(img.naturalWidth, img.naturalHeight));
        }}
      />
    </span>
  );
}
