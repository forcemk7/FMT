import type { LivePlayer } from "@/domain/adapters";

/** GM Sell lane: PA − CA at or below this (CA≈PA). */
export const MOVE_ON_HEADROOM_MAX = 8;
/** GM Loan lane: last age (inclusive) still in development range. */
export const GM_DEVELOPMENT_AGE_MAX = 24;

export type GmAdvice = "sell" | "loan";

export type SquadUnit = "firstTeam" | "under19s" | "reserves";

/** Managed-club players available for match squads (excludes outgoing loans). */
export function isAtClubSquadPlayer(
  player: Pick<LivePlayer, "clubId" | "loanedOut" | "squadUnit">,
  managedClubId: string | null | undefined,
  squadUnit: SquadUnit = "firstTeam",
): boolean {
  if (!managedClubId || player.clubId !== managedClubId) return false;
  if (player.loanedOut === true) return false;
  const unit = player.squadUnit ?? "firstTeam";
  return unit === squadUnit;
}

export function countAtClubSquadUnit(
  players: Array<Pick<LivePlayer, "clubId" | "loanedOut" | "squadUnit">>,
  managedClubId: string | null | undefined,
  squadUnit: SquadUnit,
): number {
  return players.filter((player) =>
    isAtClubSquadPlayer(player, managedClubId, squadUnit),
  ).length;
}

/** Managed-club players currently out on loan (Squad honesty complement). */
export function isLoanedOutSquadPlayer(
  player: Pick<LivePlayer, "clubId" | "loanedOut">,
  managedClubId: string | null | undefined,
): boolean {
  if (!managedClubId || player.clubId !== managedClubId) return false;
  return player.loanedOut === true;
}

/** Median CA of players with finite currentAbility; null if none. */
export function squadMedianCA(
  players: Array<Pick<LivePlayer, "currentAbility">>,
): number | null {
  const values: number[] = [];
  for (const player of players) {
    const ca = player.currentAbility;
    if (typeof ca === "number" && Number.isFinite(ca)) values.push(ca);
  }
  if (!values.length) return null;
  values.sort((a, b) => a - b);
  const mid = Math.floor(values.length / 2);
  if (values.length % 2 === 1) return values[mid]!;
  return (values[mid - 1]! + values[mid]!) / 2;
}

/**
 * GM advice vs this club’s squad median CA.
 * Sell: PA below ref and CA≈PA, or past dev age with CA far below PA (decline).
 * Loan: in dev range (≤24) with CA far below PA — high PA youth below ref, or CA still below ref.
 */
export function gmAdvice(
  player: Pick<LivePlayer, "currentAbility" | "potentialAbility" | "age">,
  refCA: number,
): GmAdvice | null {
  const ca = player.currentAbility;
  const pa = player.potentialAbility;
  const age = player.age;
  if (typeof ca !== "number" || typeof pa !== "number") return null;
  if (!Number.isFinite(ca) || !Number.isFinite(pa) || !Number.isFinite(refCA)) return null;
  const headroom = pa - ca;
  const nearPA = headroom <= MOVE_ON_HEADROOM_MAX;
  const farFromPA = headroom > MOVE_ON_HEADROOM_MAX;
  const inDev =
    typeof age === "number" && Number.isFinite(age) && age <= GM_DEVELOPMENT_AGE_MAX;
  const pastDev =
    typeof age === "number" && Number.isFinite(age) && age > GM_DEVELOPMENT_AGE_MAX;

  if (pa < refCA && nearPA) return "sell";

  if (pa >= refCA && ca < refCA && pastDev && farFromPA) return "sell";

  if (inDev && farFromPA) {
    if (pa < refCA) return "loan";
    if (pa >= refCA && ca < refCA) return "loan";
  }

  return null;
}

/**
 * HoYD groom prospect vs squad median CA.
 * High PA for this club with room left to develop; youth only (≤24).
 */
export function isHoydProspect(
  player: Pick<LivePlayer, "currentAbility" | "potentialAbility" | "age">,
  refCA: number,
): boolean {
  const ca = player.currentAbility;
  const pa = player.potentialAbility;
  const age = player.age;
  if (typeof ca !== "number" || typeof pa !== "number") return false;
  if (!Number.isFinite(ca) || !Number.isFinite(pa) || !Number.isFinite(refCA)) return false;
  if (typeof age !== "number" || !Number.isFinite(age) || age > GM_DEVELOPMENT_AGE_MAX) return false;
  if (pa < refCA) return false;
  return pa - ca > MOVE_ON_HEADROOM_MAX;
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
