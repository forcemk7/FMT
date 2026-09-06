/**
 * Match experience: same-primary-position CA ranks across loaded clubTeams.
 */

import type { LiveClubTeam, LivePlayer } from "./adapters";
import { squadTeamDisplayName } from "./live-data";

/** Visible rows per card — fixed height, scroll within card when longer. */
export const MATCH_EXPERIENCE_PAGE_SIZE = 5;

export type MatchExperienceRow = {
  playerId: string;
  name: string;
  currentAbility: number | null;
  rank: number;
  isFocus: boolean;
  isOnRoster: boolean;
};

export type MatchExperienceCard = {
  teamUid: string;
  teamLabel: string;
  position: string;
  focusRank: number | null;
  /** Same-pos players actually on this roster (excludes projected-only inject). */
  rosterPeerCount: number;
  rows: MatchExperienceRow[];
};

/** Best single position code for competition compare. */
export function matchExperiencePosition(
  player: Pick<LivePlayer, "bestCalculatedPosition" | "positions">,
): string | null {
  const best = player.bestCalculatedPosition?.trim();
  if (best) return best;
  const primary = player.positions?.[0]?.trim();
  return primary || null;
}

function hasPrimaryPosition(
  player: Pick<LivePlayer, "positions">,
  position: string,
): boolean {
  return (player.positions ?? []).some(
    (code) => code.trim().toUpperCase() === position.toUpperCase(),
  );
}

function caSortKey(value: number | null | undefined): number {
  return typeof value === "number" && Number.isFinite(value) ? value : -Infinity;
}

/**
 * Sort: managed Senior → Under N → 2nd/II → Normal aff Senior → Normal aff Under N.
 */
export function sortClubTeamsForMatchExperience(
  teams: LiveClubTeam[],
): LiveClubTeam[] {
  return [...teams].sort((left, right) => {
    const band = matchExperienceTeamBand(left) - matchExperienceTeamBand(right);
    if (band !== 0) return band;
    if (right.rosterLen !== left.rosterLen) return right.rosterLen - left.rosterLen;
    return squadTeamDisplayName(left).localeCompare(squadTeamDisplayName(right));
  });
}

/** Band index for Match experience ladder (lower = higher on ladder). */
export function matchExperienceTeamBand(
  team: Pick<LiveClubTeam, "squadUnit" | "affiliationType" | "teamType">,
): number {
  const aff = team.affiliationType;
  const normal = aff === 0x01;
  const iiOrSatellite =
    aff === 0x08 || (typeof aff === "number" && aff !== 0x01);

  if (normal) {
    if (team.squadUnit === "firstTeam" || team.teamType === 0) return 3;
    if (team.squadUnit === "under19s") return 4;
    return 5;
  }

  // Managed club sides + II Club / NPL satellite (treated as 2nd side).
  if (!iiOrSatellite && team.squadUnit === "firstTeam") return 0;
  if (!iiOrSatellite && team.squadUnit === "under19s") return 1;
  // Managed reserves, II Club, other affiliate reserves → "2nd club team"
  return 2;
}

/**
 * One card for a clubTeam at a chosen primary position.
 * Returns null when nobody on that roster plays the position (hide empty cards).
 */
export function buildMatchExperienceCard(
  focus: LivePlayer,
  players: LivePlayer[],
  team: LiveClubTeam,
  position: string,
  managedClubName?: string | null,
): MatchExperienceCard | null {
  const pos = position.trim();
  if (!pos) return null;

  const onRoster = players.filter(
    (player) =>
      player.squadTeamUid === team.teamUid && hasPrimaryPosition(player, pos),
  );
  if (onRoster.length === 0) return null;

  const focusOnRoster = onRoster.some((player) => player.id === focus.id);
  const pool: LivePlayer[] = focusOnRoster ? onRoster : [...onRoster, focus];

  const sorted = [...pool].sort((left, right) => {
    const ca = caSortKey(right.currentAbility) - caSortKey(left.currentAbility);
    if (ca !== 0) return ca;
    return left.name.localeCompare(right.name);
  });

  let focusRank: number | null = null;
  const rows: MatchExperienceRow[] = sorted.map((player, index) => {
    const rank = index + 1;
    const isFocus = player.id === focus.id;
    if (isFocus) focusRank = rank;
    return {
      playerId: player.id,
      name: player.name,
      currentAbility: player.currentAbility ?? null,
      rank,
      isFocus,
      isOnRoster: player.squadTeamUid === team.teamUid,
    };
  });

  return {
    teamUid: team.teamUid,
    teamLabel: squadTeamDisplayName(team, managedClubName),
    position: pos,
    focusRank,
    rosterPeerCount: onRoster.length,
    rows,
  };
}

/**
 * Cards for all loaded clubTeams. `positionByTeamUid` overrides default per card.
 * Empty same-pos rosters are omitted.
 */
export function buildMatchExperienceCards(
  focus: LivePlayer,
  players: LivePlayer[],
  clubTeams: LiveClubTeam[],
  managedClubName?: string | null,
  positionByTeamUid?: Record<string, string | null | undefined>,
  defaultPosition?: string | null,
): MatchExperienceCard[] {
  const fallback =
    defaultPosition?.trim() || matchExperiencePosition(focus);
  if (!fallback) return [];

  const teams = sortClubTeamsForMatchExperience(clubTeams);
  const cards: MatchExperienceCard[] = [];
  for (const team of teams) {
    const override = positionByTeamUid?.[team.teamUid]?.trim();
    const position = override || fallback;
    const card = buildMatchExperienceCard(
      focus,
      players,
      team,
      position,
      managedClubName,
    );
    if (card) cards.push(card);
  }
  return cards;
}

/**
 * Slice start so `focusRank` (1-based) sits in a PAGE_SIZE window.
 * Prefer centering the focus player when the list is longer than the page.
 */
export function matchExperienceWindowStart(
  rowCount: number,
  focusRank: number | null,
  pageSize: number = MATCH_EXPERIENCE_PAGE_SIZE,
): number {
  if (rowCount <= pageSize) return 0;
  if (focusRank == null || focusRank < 1) return 0;
  const focusIndex = focusRank - 1;
  const ideal = focusIndex - Math.floor((pageSize - 1) / 2);
  return Math.max(0, Math.min(ideal, rowCount - pageSize));
}
