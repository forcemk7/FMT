/**
 * Dashboard Match experience opportunities — upward First-team #1/#2 glances.
 */

import type { LiveClubTeam, LiveFootballSnapshot, LivePlayer } from "./adapters";
import { isAtClubEmployee } from "./live-data";
import {
  buildMatchExperienceCards,
  matchExperiencePosition,
  matchExperienceTeamBand,
  type MatchExperienceCard,
} from "./match-experience";

export const MATCH_EXPERIENCE_OPPORTUNITY_RANK_MAX = 2;

export type MatchExperienceOpportunity = {
  player: LivePlayer;
  position: string;
  focusRank: number;
  fromTeamLabel: string;
  fromClubName: string;
  toTeamLabel: string;
  toClubName: string;
  toTeamUid: string;
};

function teamByUid(
  clubTeams: LiveClubTeam[],
  teamUid: string | null | undefined,
): LiveClubTeam | null {
  const uid = teamUid?.trim();
  if (!uid) return null;
  return clubTeams.find((team) => team.teamUid === uid) ?? null;
}

function isUpwardCandidate(
  player: LivePlayer,
  clubTeams: LiveClubTeam[],
  managedClubId: string | null | undefined,
): boolean {
  if (!isAtClubEmployee(player, managedClubId)) return false;
  if (player.loanedOut === true) return false;
  const current = teamByUid(clubTeams, player.squadTeamUid);
  if (!current) return false;
  return matchExperienceTeamBand(current) > 0;
}

function bestFirstUpgrade(
  cards: MatchExperienceCard[],
  managedClubId?: string | null,
): MatchExperienceCard | null {
  const upgrades = cards.filter(
    (card) =>
      card.band === 0 &&
      !card.isFocusCurrentTeam &&
      card.focusRank != null &&
      card.focusRank >= 1 &&
      card.focusRank <= MATCH_EXPERIENCE_OPPORTUNITY_RANK_MAX,
  );
  if (!upgrades.length) return null;
  const managed = managedClubId?.trim() || null;
  return [...upgrades].sort((left, right) => {
    const rank = (left.focusRank ?? 99) - (right.focusRank ?? 99);
    if (rank !== 0) return rank;
    const leftHome = managed && left.clubId === managed ? 0 : 1;
    const rightHome = managed && right.clubId === managed ? 0 : 1;
    if (leftHome !== rightHome) return leftHome - rightHome;
    const strength = right.maxSamePosCa - left.maxSamePosCa;
    if (strength !== 0) return strength;
    return left.teamUid.localeCompare(right.teamUid);
  })[0]!;
}

/**
 * Players on Reserves / Under N / Youth who would be #1 or #2 same-pos on a First Team.
 */
export function rankMatchExperienceOpportunities(
  snapshot: Pick<
    LiveFootballSnapshot,
    "players" | "clubTeams" | "managedClubId" | "clubs"
  >,
  limit: number = 8,
): MatchExperienceOpportunity[] {
  const clubTeams = snapshot.clubTeams ?? [];
  if (!clubTeams.length || limit <= 0) return [];

  const candidates = snapshot.players.filter((player) =>
    isUpwardCandidate(player, clubTeams, snapshot.managedClubId),
  );

  const out: MatchExperienceOpportunity[] = [];
  for (const player of candidates) {
    const position = matchExperiencePosition(player);
    if (!position) continue;
    const cards = buildMatchExperienceCards(
      player,
      snapshot.players,
      clubTeams,
      snapshot.managedClubId,
      undefined,
      position,
      snapshot.clubs,
    );
    const current = cards.find((card) => card.isFocusCurrentTeam);
    const upgrade = bestFirstUpgrade(cards, snapshot.managedClubId);
    if (!upgrade || upgrade.focusRank == null) continue;

    out.push({
      player,
      position: upgrade.position,
      focusRank: upgrade.focusRank,
      fromTeamLabel: current?.teamLabel ?? "—",
      fromClubName: current?.clubName ?? "—",
      toTeamLabel: upgrade.teamLabel,
      toClubName: upgrade.clubName,
      toTeamUid: upgrade.teamUid,
    });
  }

  out.sort((left, right) => {
    const rank = left.focusRank - right.focusRank;
    if (rank !== 0) return rank;
    const pa =
      (right.player.potentialAbility ?? -Infinity) -
      (left.player.potentialAbility ?? -Infinity);
    if (pa !== 0) return pa;
    return left.player.name.localeCompare(right.player.name);
  });

  return out.slice(0, limit);
}
