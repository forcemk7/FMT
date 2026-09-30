import { getVersion } from "@tauri-apps/api/app";
import { useSyncExternalStore } from "react";
import { getPreferences } from "@/domain/preferences";

/**
 * T290 — minimal functional telemetry (install/launch → load → outcome).
 * Posts directly to Supabase's REST API with a publishable key (runs as the
 * anon role; write-only via RLS — see FMT/scrum/tickets/T290-minimal-functional-telemetry.md
 * for the table/policy). Read from NEXT_PUBLIC_SUPABASE_URL/PUBLISHABLE_KEY in
 * .env.local (see .env.example) rather than hardcoded here, so the real
 * values never need to go through source review. Missing/empty env is a
 * deliberate no-op, not a bug: every send silently skips instead of
 * throwing, so this file is safe to build against with no .env.local at all.
 */
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const SUPABASE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";

type EventType = "launch" | "load_attempt" | "load_outcome";
type Outcome = "success" | "failure";

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/** Last event actually posted this session, for Settings > Diagnostics. */
export type LastSent = {
  at: Date;
  eventType: EventType;
  outcome: Outcome | null;
  failureReason: string | null;
  ok: boolean;
  httpStatus: number | null;
};

const FAILURE_REASON_LABELS: Record<string, string> = {
  exact_build_match: "FM26 build not supported yet",
  open_read_only_process: "Windows denied read access to FM26",
  locate_game_module: "could not find FM26's game module",
  validate_game_module: "FM26's game module failed validation",
  entity_map: "could not read the game's data map",
  manager_signature: "could not identify the manager/save",
};

/** Plain-English line for Settings > Diagnostics; the raw codes stay in the DB row. */
export function describeLastSent(entry: LastSent): string {
  let text: string;
  if (entry.eventType === "launch") {
    text = "App launched";
  } else if (entry.eventType === "load_attempt") {
    text = "Load attempted";
  } else if (entry.outcome === "success") {
    text = "Loaded successfully";
  } else if (entry.failureReason) {
    const reason =
      FAILURE_REASON_LABELS[entry.failureReason] ?? entry.failureReason.replaceAll("_", " ");
    text = `Load failed: ${reason}`;
  } else {
    text = "Load failed";
  }
  if (entry.ok) return text;
  const why = entry.httpStatus === null ? "no connection" : `HTTP ${entry.httpStatus}`;
  return `${text} (not delivered, ${why})`;
}

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
  return Boolean(SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY) && isTauri();
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
  const body = {
    anon_id: anonId,
    event_type: payload.event_type,
    outcome: payload.outcome ?? null,
    failure_reason: payload.failure_reason ?? null,
    app_version: appVersion ?? "unknown",
  };
  const sent = {
    eventType: body.event_type,
    outcome: body.outcome,
    failureReason: body.failure_reason,
  };
  try {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Publishable keys aren't JWTs — apikey header only; Authorization: Bearer is rejected.
        apikey: SUPABASE_PUBLISHABLE_KEY,
        Prefer: "return=minimal",
      },
      body: JSON.stringify(body),
    });
    recordSent({ at: new Date(), ...sent, ok: response.ok, httpStatus: response.status });
  } catch {
    // Telemetry must never surface an error to the user or block whatever it's reporting on.
    recordSent({ at: new Date(), ...sent, ok: false, httpStatus: null });
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
