import type { LiveFootballSnapshot } from "@/domain/adapters";

export const LOAD_STAGE_LABELS: Record<string, string> = {
  detecting_fm26: "Detecting FM26…",
  validating_active_save: "Validating active save…",
  reading_managed_club: "Reading managed club…",
  loading_managed_squad: "Loading managed squad…",
  loading_club_teams: "Loading club teams…",
  ready: "Ready",
  collect_snapshot: "Collecting live snapshot…",
};

export function loadStageLabel(stage: string) {
  return LOAD_STAGE_LABELS[stage] ?? stage.replaceAll("_", " ");
}

export function shellLoadLabel(
  snapshot: LiveFootballSnapshot,
  checking: boolean,
  loadStage?: string | null,
) {
  const connected = snapshot.status.state === "connected";
  const needsLoad = !connected;
  const club = snapshot.clubs.find((item) => item.id === snapshot.managedClubId);
  const totalPlayers =
    snapshot.status.clubEmployees > 0
      ? snapshot.status.clubEmployees
      : snapshot.status.managedSquadPlayers;

  if (checking) {
    return loadStage ? loadStageLabel(loadStage) : "Loading…";
  }
  if (needsLoad) return "Load Data";
  return `${club?.name ?? "Synced"} · ${totalPlayers} players`;
}

/** Single line matching the shell header load button. */
export function shellStatusLine(
  snapshot: LiveFootballSnapshot,
  checking = false,
  loadStage?: string | null,
) {
  return shellLoadLabel(snapshot, checking, loadStage);
}

/** Headline shown on empty desks (LiveDataState). */
export function liveDeskHeadline(snapshot: LiveFootballSnapshot, deskTitle: string) {
  const status = snapshot.status;
  const fmRunning = status.processDetected;
  const failure =
    status.failureStage && status.failureStage !== "none"
      ? status.failureStage.replaceAll("_", " ")
      : null;
  const usefulMessage =
    status.message &&
    status.message !== "Diagnostics have not run yet." &&
    !status.message.toLowerCase().includes("have not run")
      ? status.message
      : null;

  if (fmRunning && !failure) {
    return usefulMessage ?? "Save is open — load when you want the squad desk.";
  }
  if (failure) {
    return usefulMessage ?? failure;
  }
  return usefulMessage ?? "Use Load Data in the header when Football Manager 26 has a career save open.";
}

let lastMirrored = "";

export async function mirrorToTerminal(message: string) {
  const line = message.trim();
  if (!line || line === lastMirrored) return;
  lastMirrored = line;
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) return;
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("fmt_terminal_log", { message: line });
  } catch {
    // ignore — browser preview or connector unavailable
  }
}

export function resetTerminalMirror() {
  lastMirrored = "";
}
