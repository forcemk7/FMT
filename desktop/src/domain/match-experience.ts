/**
 * Match experience: same-primary-position CA ranks across loaded clubTeams.
 */

import type { LiveClubTeam, LivePlayer } from "./adapters";
import { sortClubTeamsForSquadDesk, squadTeamDisplayName } from "./live-data";

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
 * One card per loaded clubTeam: primary-position peers ranked by CA,
 * with the focus player always included (injected when not on that roster).
 */
export function buildMatchExperienceCards(
  focus: LivePlayer,
  players: LivePlayer[],
  clubTeams: LiveClubTeam[],
  managedClubName?: string | null,
  positionOverride?: string | null,
): MatchExperienceCard[] {
  const position =
    positionOverride?.trim() || matchExperiencePosition(focus);
  if (!position) return [];

  const teams = sortClubTeamsForSquadDesk(clubTeams);
  return teams.map((team) => {
    const onRoster = players.filter(
      (player) =>
        player.squadTeamUid === team.teamUid &&
        hasPrimaryPosition(player, position),
    );
    const focusOnRoster = onRoster.some((player) => player.id === focus.id);
    const pool: LivePlayer[] = focusOnRoster
      ? onRoster
      : [...onRoster, focus];

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
      position,
      focusRank,
      rows,
    };
  });
}
