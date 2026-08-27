import type { LivePlayer } from "@/domain/adapters";

/** GM Sell lane: PA − CA at or below this (CA≈PA). */
export const MOVE_ON_HEADROOM_MAX = 8;

export type GmAdvice = "sell" | "loan";

/** Managed-club players available for match squads (excludes outgoing loans). */
export function isAtClubSquadPlayer(
  player: Pick<LivePlayer, "clubId" | "loanedOut">,
  managedClubId: string | null | undefined,
): boolean {
  if (!managedClubId || player.clubId !== managedClubId) return false;
  return player.loanedOut !== true;
}

/** Managed-club players currently out on loan (Squad honesty complement). */
export function isLoanedOutSquadPlayer(
  player: Pick<LivePlayer, "clubId" | "loanedOut">,
  managedClubId: string | null | undefined,
): boolean {
  if (!managedClubId || player.clubId !== managedClubId) return false;
  return player.loanedOut === true;
}

/** Mean CA of players with finite currentAbility; null if none. */
export function squadAverageCA(
  players: Array<Pick<LivePlayer, "currentAbility">>,
): number | null {
  let sum = 0;
  let count = 0;
  for (const player of players) {
    const ca = player.currentAbility;
    if (typeof ca !== "number" || !Number.isFinite(ca)) continue;
    sum += ca;
    count += 1;
  }
  if (!count) return null;
  return sum / count;
}

/**
 * GM advice vs this club’s squad average CA.
 * Sell: PA below avg and CA≈PA. Loan: PA at/above avg but CA still below avg.
 */
export function gmAdvice(
  player: Pick<LivePlayer, "currentAbility" | "potentialAbility">,
  avgCA: number,
): GmAdvice | null {
  const ca = player.currentAbility;
  const pa = player.potentialAbility;
  if (typeof ca !== "number" || typeof pa !== "number") return null;
  if (!Number.isFinite(ca) || !Number.isFinite(pa) || !Number.isFinite(avgCA)) return null;
  if (pa < avgCA && pa - ca <= MOVE_ON_HEADROOM_MAX) return "sell";
  if (pa >= avgCA && ca < avgCA) return "loan";
  return null;
}

export const positionGroups = [
  "Goalkeepers",
  "Centre-backs",
  "Full-backs / wing-backs",
  "Defensive midfielders",
  "Central midfielders",
  "Attacking midfielders",
  "Wingers",
  "Strikers",
  "Utility / other players",
] as const;

export type PositionGroup = (typeof positionGroups)[number];

/** Best slot(s), with secondaries in parentheses — e.g. `DC (DM / MC)`. */
export function formatPlayerPositions(
  player: Pick<LivePlayer, "positions" | "secondaryPositions">,
): string {
  const primary = player.positions ?? [];
  if (!primary.length) return "—";
  const head = primary.join(" / ");
  const secondary = player.secondaryPositions ?? [];
  if (!secondary.length) return head;
  return `${head} (${secondary.join(" / ")})`;
}

/** Group by best (primary) position only — not secondary slots. */
export function groupPlayerPosition(player: LivePlayer): PositionGroup {
  const positions = player.positions.map((position) => position.toUpperCase());
  if (positions.some((position) => /\bGK\b/.test(position))) return "Goalkeepers";
  if (positions.some((position) => /\bDC\b|\bCB\b/.test(position))) return "Centre-backs";
  if (positions.some((position) => /\bDL\b|\bDR\b|\bLB\b|\bRB\b|\bWB/.test(position))) return "Full-backs / wing-backs";
  if (positions.some((position) => /\bDM\b|\bDMC\b/.test(position))) return "Defensive midfielders";
  if (positions.some((position) => /\bMC\b|\bCM\b/.test(position))) return "Central midfielders";
  if (positions.some((position) => /\bAMC\b|\bAM\b/.test(position))) return "Attacking midfielders";
  if (positions.some((position) => /\bAML\b|\bAMR\b|\bLW\b|\bRW\b/.test(position))) return "Wingers";
  if (positions.some((position) => /\bST\b|\bCF\b/.test(position))) return "Strikers";
  return "Utility / other players";
}

export function groupSquad(players: LivePlayer[]) {
  const grouped = new Map<PositionGroup, LivePlayer[]>(
    positionGroups.map((group) => [group, []]),
  );
  for (const player of players) {
    grouped.get(groupPlayerPosition(player))?.push(player);
  }
  return grouped;
}

export type FavoriteRecord = {
  playerId: string;
  note: string;
};

export function toggleFavorite(records: FavoriteRecord[], playerId: string): FavoriteRecord[] {
  return records.some((record) => record.playerId === playerId)
    ? records.filter((record) => record.playerId !== playerId)
    : [...records, { playerId, note: "" }];
}

export function updateFavoriteNote(records: FavoriteRecord[], playerId: string, note: string): FavoriteRecord[] {
  return records.map((record) => record.playerId === playerId ? { ...record, note } : record);
}

export function resolveFavorites(records: FavoriteRecord[], players: LivePlayer[]) {
  const playersById = new Map(players.map((player) => [player.id, player]));
  return records.flatMap((record) => {
    const player = playersById.get(record.playerId);
    return player ? [{ player, note: record.note }] : [];
  });
}
