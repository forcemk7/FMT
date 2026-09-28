import { getVersion } from "@tauri-apps/api/app";
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
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY || !isTauri()) return;
  const anonId = getPreferences().telemetryId;
  if (!anonId) return;
  const appVersion = await resolveAppVersion();
  try {
    await fetch(`${SUPABASE_URL}/rest/v1/events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        Prefer: "return=minimal",
      },
      body: JSON.stringify({
        anon_id: anonId,
        event_type: payload.event_type,
        outcome: payload.outcome ?? null,
        failure_reason: payload.failure_reason ?? null,
        app_version: appVersion ?? "unknown",
      }),
    });
  } catch {
    // Telemetry must never surface an error to the user or block whatever it's reporting on.
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
  void postEvent({ event_type: "load_attempt" });
  void postEvent({ event_type: "load_outcome", outcome, failure_reason: failureReason });
}
