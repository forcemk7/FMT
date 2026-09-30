import { getVersion } from "@tauri-apps/api/app";
import { useSyncExternalStore } from "react";
import { getPreferences } from "@/domain/preferences";

/**
 * T290 — minimal functional telemetry (install/launch → load → outcome).
 * Posts directly to Supabase's REST API with a public anon key (write-only
 * via RLS — see FMT/scrum/tickets/T290-minimal-functional-telemetry.md for
 * the table/policy). Read from NEXT_PUBLIC_SUPABASE_URL/ANON_KEY in
 * .env.local (see .env.example) rather than hardcoded here, so the real
 * values never need to go through source review. Missing/empty env is a
 * deliberate no-op, not a bug: every send silently skips instead of
 * throwing, so this file is safe to build against with no .env.local at all.
 */
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

type EventType = "launch" | "load_attempt" | "load_outcome";
type Outcome = "success" | "failure";

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/** Last event actually posted this session, for Settings > Diagnostics. */
export type LastSent = {
  at: Date;
  data: string;
  ok: boolean;
  httpStatus: number | null;
};

let lastSent: LastSent | null = null;
const listeners = new Set<() => void>();

function recordSent(entry: LastSent): void {
  lastSent = entry;
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useLastSent(): LastSent | null {
  return useSyncExternalStore(subscribe, () => lastSent, () => null);
}

export function isTelemetryConfigured(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY) && isTauri();
}

let cachedAppVersion: string | null = null;

async function resolveAppVersion(): Promise<string | null> {
  if (cachedAppVersion) return cachedAppVersion;
  if (!isTauri()) return null;
  try {
    cachedAppVersion = await getVersion();
  } catch {
    cachedAppVersion = null;
  }
  return cachedAppVersion;
}

async function postEvent(payload: {
  event_type: EventType;
  outcome?: Outcome;
  failure_reason?: string | null;
}): Promise<void> {
  if (!isTelemetryConfigured()) return;
  const anonId = getPreferences().telemetryId;
  if (!anonId) return;
  const appVersion = await resolveAppVersion();
  // anon_id has its own Settings cell; show everything else exactly as sent.
  const shown = {
    event_type: payload.event_type,
    outcome: payload.outcome ?? null,
    failure_reason: payload.failure_reason ?? null,
    app_version: appVersion ?? "unknown",
  };
  const body = { anon_id: anonId, ...shown };
  const data = JSON.stringify(shown);
  try {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        Prefer: "return=minimal",
      },
      body: JSON.stringify(body),
    });
    recordSent({ at: new Date(), data, ok: response.ok, httpStatus: response.status });
  } catch {
    // Telemetry must never surface an error to the user or block whatever it's reporting on.
    recordSent({ at: new Date(), data, ok: false, httpStatus: null });
  }
}

let launchSent = false;

/** Fire once per app run. "Install" is derived later as this anon_id's first-ever launch row. */
export function reportLaunch(): void {
  if (launchSent) return;
  launchSent = true;
  void postEvent({ event_type: "launch" });
}

let lastLoadResult: { outcome: Outcome; failureReason: string | null } | null = null;

/**
 * Reports one load attempt + its outcome, throttled to only send when the
 * outcome (or failure reason) differs from the last one sent this session.
 * T274's heartbeat poll retries a failing load roughly every 8s — without
 * this throttle, one stuck install would flood identical rows.
 */
export function reportLoadResult(outcome: Outcome, failureReason: string | null): void {
  if (
    lastLoadResult &&
    lastLoadResult.outcome === outcome &&
    lastLoadResult.failureReason === failureReason
  ) {
    return;
  }
  lastLoadResult = { outcome, failureReason };
  // Sequential so "last sent" is deterministically the outcome row.
  void (async () => {
    await postEvent({ event_type: "load_attempt" });
    await postEvent({ event_type: "load_outcome", outcome, failure_reason: failureReason });
  })();
}
