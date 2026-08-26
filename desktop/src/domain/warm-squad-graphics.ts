import { invoke } from "@tauri-apps/api/core";
import type { LiveFootballSnapshot } from "@/domain/adapters";
import { clearClubLogoMemoryCache } from "@/components/club-logo";
import { clearNationFlagMemoryCache } from "@/components/nation-flag";
import { clearPlayerFaceMemoryCache } from "@/components/player-face";

function uniqueNumericIds(values: Array<string | null | undefined>): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const value of values) {
    const id = value?.trim() ?? "";
    if (!id || !/^\d+$/.test(id) || seen.has(id)) continue;
    seen.add(id);
    out.push(id);
  }
  return out;
}

/** Fire-and-forget: queue squad player/club/nation UIDs for background cache fill. */
export function warmSquadGraphics(snapshot: LiveFootballSnapshot) {
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) return;
  if (snapshot.status.state !== "connected" || !snapshot.players.length) return;

  const playerIds = uniqueNumericIds(snapshot.players.map((player) => player.id));
  const clubIds = uniqueNumericIds([
    snapshot.managedClubId,
    ...snapshot.players.map((player) => player.clubId),
    ...snapshot.clubs.map((club) => club.id),
  ]);
  const nationIds = uniqueNumericIds(snapshot.players.map((player) => player.nationalityId));

  if (playerIds.length) {
    void invoke("faces_update_cache", { playerIds })
      .then(() => {
        // Copy runs in the background; nudge UI after a beat so soft misses refill.
        window.setTimeout(() => clearPlayerFaceMemoryCache(), 800);
        window.setTimeout(() => clearPlayerFaceMemoryCache(), 2500);
      })
      .catch(() => undefined);
  }
  if (clubIds.length) {
    void invoke("logos_update_cache", { clubIds })
      .then(() => {
        window.setTimeout(() => clearClubLogoMemoryCache(), 800);
        window.setTimeout(() => clearClubLogoMemoryCache(), 2500);
      })
      .catch(() => undefined);
  }
  if (nationIds.length) {
    void invoke("flags_update_cache", { nationIds })
      .then(() => {
        window.setTimeout(() => clearNationFlagMemoryCache(), 800);
        window.setTimeout(() => clearNationFlagMemoryCache(), 2500);
      })
      .catch(() => undefined);
  }
}
