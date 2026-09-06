/**
 * Dashboard Best players (CA) / Best talent (PA ≤20).
 * Pool = owned managed-club players including loaned-out.
 */

import type { LiveClubTeam, LivePlayer } from "./adapters";
import {
  matchExperienceTeamBand,
  matchExperienceTeamLabel,
} from "./match-experience";

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

function resolveClubName(
  clubId: string | null | undefined,
  clubTeams: LiveClubTeam[],
  clubs: Array<{ id: string; name: string }>,
  fallback?: string | null,
): string | null {
  const trimmed = fallback?.trim();
  if (trimmed) return trimmed;
  const id = clubId?.trim();
  if (!id) return null;
  const fromClubs = clubs.find((club) => club.id === id)?.name?.trim();
  if (fromClubs) return fromClubs;
  const fromTeam = clubTeams.find((team) => team.clubId === id)?.clubName?.trim();
  return fromTeam || null;
}

/**
 * Actual clubTeam for ability peeks: `{clubName} {teamType}`.
 * Loaned-out → destination First Team when loaded.
 */
export function dashClubTeamSpellout(
  player: LivePlayer,
  clubTeams: LiveClubTeam[],
  clubs: Array<{ id: string; name: string }> = [],
): string | null {
  if (player.loanedOut === true) {
    const loanId = player.loanClubId?.trim() || null;
    const first =
      clubTeams.find(
        (team) => team.clubId === loanId && matchExperienceTeamBand(team) === 0,
      ) ?? clubTeams.find((team) => team.clubId === loanId);
    const clubName = resolveClubName(loanId, clubTeams, clubs, player.loanClubName);
    if (clubName && first) return `${clubName} ${matchExperienceTeamLabel(first)}`;
    if (clubName) return `${clubName} First Team`;
    return null;
  }

  const teamUid = player.squadTeamUid?.trim();
  const team = teamUid
    ? clubTeams.find((item) => item.teamUid === teamUid)
    : undefined;
  if (!team) return null;
  const clubName = resolveClubName(
    team.clubId,
    clubTeams,
    clubs,
    team.clubName ?? player.clubName,
  );
  const type = matchExperienceTeamLabel(team);
  return clubName ? `${clubName} ${type}` : type;
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
