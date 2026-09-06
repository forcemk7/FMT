/**
 * Dashboard Best players (CA) / Best talent (PA ≤20).
 * Pool = owned managed-club players including loaned-out.
 */

import type { LivePlayer } from "./adapters";

const TALENT_AGE_MAX = 20;
const DEFAULT_LIMIT = 8;

export type SquadAbilityRank = {
  player: LivePlayer;
  ca: number | null;
  pa: number | null;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** Owned by managed club (includes outgoing loans). */
export function isOwnedManagedPlayer(
  player: Pick<LivePlayer, "clubId">,
  managedClubId: string | null | undefined,
): boolean {
  return Boolean(managedClubId) && player.clubId === managedClubId;
}

function byName(a: LivePlayer, b: LivePlayer): number {
  return a.name.localeCompare(b.name);
}

/** Highest CA on owned club roster (loans included). */
export function rankBestPlayers(
  players: LivePlayer[],
  managedClubId: string | null | undefined,
  limit = DEFAULT_LIMIT,
): SquadAbilityRank[] {
  const rows: SquadAbilityRank[] = [];
  for (const player of players) {
    if (!isOwnedManagedPlayer(player, managedClubId)) continue;
    const ca = player.currentAbility;
    if (!isFiniteNumber(ca)) continue;
    rows.push({
      player,
      ca,
      pa: isFiniteNumber(player.potentialAbility) ? player.potentialAbility : null,
    });
  }
  rows.sort((a, b) => {
    const caDiff = (b.ca ?? 0) - (a.ca ?? 0);
    if (caDiff !== 0) return caDiff;
    return byName(a.player, b.player);
  });
  return rows.slice(0, Math.max(0, limit));
}

/** Highest PA among owned players age ≤ 20 (FT + loans included). */
export function rankBestTalent(
  players: LivePlayer[],
  managedClubId: string | null | undefined,
  limit = DEFAULT_LIMIT,
): SquadAbilityRank[] {
  const rows: SquadAbilityRank[] = [];
  for (const player of players) {
    if (!isOwnedManagedPlayer(player, managedClubId)) continue;
    if (!isFiniteNumber(player.age) || (player.age as number) > TALENT_AGE_MAX) continue;
    const pa = player.potentialAbility;
    if (!isFiniteNumber(pa)) continue;
    rows.push({
      player,
      ca: isFiniteNumber(player.currentAbility) ? player.currentAbility : null,
      pa,
    });
  }
  rows.sort((a, b) => {
    const paDiff = (b.pa ?? 0) - (a.pa ?? 0);
    if (paDiff !== 0) return paDiff;
    return byName(a.player, b.player);
  });
  return rows.slice(0, Math.max(0, limit));
}
