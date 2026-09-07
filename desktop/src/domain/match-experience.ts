/**
 * Match experience: same-primary-position CA ranks across loaded clubTeams.
 */

import type { LiveClubTeam, LivePlayer } from "./adapters";
import { teamTypeDisplayLabel } from "./live-data";

/** Visible rows per card — fixed height, no scrollbar (window around focus). */
export const MATCH_EXPERIENCE_PAGE_SIZE = 5;

export type MatchExperienceRow = {
  playerId: string;
  name: string;
  currentAbility: number | null;
  rank: number;
  isFocus: boolean;
  /** Competing on this team now (roster at club, or loaned *to* this club). */
  isOnRoster: boolean;
};

export type MatchExperienceCard = {
  teamUid: string;
  /** TeamType only — club identity is `clubId` logo in the UI. */
  teamLabel: string;
  /** Club UniqueID for badge; null when unread. */
  clubId: string | null;
  /** Full club/team name for tooltip / aria (not the visible title). */
  clubName: string;
  position: string;
  focusRank: number | null;
  /** Resolved players on this team (any status / position) — Squad-tab style presence. */
  teamPlayerCount: number;
  rows: MatchExperienceRow[];
  totalRows: number;
  /** Ladder band from TeamType / squadUnit (First → Reserves → Under N). */
  band: number;
  /** Max CA among same-position competitors on this card (strength sort). */
  maxSamePosCa: number;
  /** Focus player competes here now (not projected onto another ladder step). */
  isFocusCurrentTeam: boolean;
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

/** Primary + secondary codes for per-card position select. */
export function matchExperiencePositionOptions(
  player: Pick<LivePlayer, "positions" | "secondaryPositions" | "bestCalculatedPosition">,
): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  const push = (code: string | null | undefined) => {
    const trimmed = code?.trim();
    if (!trimmed) return;
    const key = trimmed.toUpperCase();
    if (seen.has(key)) return;
    seen.add(key);
    out.push(trimmed);
  };
  push(player.bestCalculatedPosition);
  for (const code of player.positions ?? []) push(code);
  for (const code of player.secondaryPositions ?? []) push(code);
  return out;
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

/** Higher youth age band first (U23 → … → U18 → Youth). */
export function underNTeamTypeSortKey(teamType: number | null | undefined): number {
  switch (teamType) {
    case 9:
      return 0; // Under 23s
    case 10:
      return 1; // Under 21s
    case 18:
      return 2; // Under 20s
    case 11:
      return 3; // Under 19s
    case 12:
      return 4; // Under 18s
    case 21:
    case 22:
      return 5; // Youth
    default:
      return 6;
  }
}

function isFeederAffiliate(
  team: Pick<LiveClubTeam, "affiliationType">,
): boolean {
  // 0x01 Normal Affiliated Club; 0x03 Schalke feeder byte (PGE label unlocked).
  return team.affiliationType === 0x01 || team.affiliationType === 0x03;
}

function isIiClubAffiliate(
  team: Pick<LiveClubTeam, "affiliationType">,
): boolean {
  return team.affiliationType === 0x08;
}

/**
 * Visible TeamType on ME cards. Club identity is the crest, not the string.
 * (Squad desk still uses `squadTeamDisplayName`.)
 */
export function matchExperienceTeamLabel(
  team: Pick<LiveClubTeam, "teamType" | "squadUnit">,
): string {
  const fromType = teamTypeDisplayLabel(team.teamType);
  if (fromType) return fromType;
  if (team.squadUnit === "firstTeam") return "First Team";
  if (team.squadUnit === "under19s") return "Under 19s";
  if (team.squadUnit === "reserves") return "Reserves";
  if (typeof team.teamType === "number") return `Map TeamType ${team.teamType}`;
  return "Map TeamType (?)";
}

/**
 * Ladder (Match experience only — does not change Squad desk):
 * 0 First Team (any club, including II First)
 * 1 Reserves / other non-youth
 * 2+ Under N / Youth (high age band first)
 *
 * Within a band, cards re-sort by max same-pos CA (see `sortMatchExperienceCards`).
 */
export function matchExperienceTeamBand(
  team: Pick<LiveClubTeam, "squadUnit" | "teamType">,
): number {
  const teamType = team.teamType ?? -1;
  if (
    team.squadUnit === "under19s" ||
    [9, 10, 11, 12, 18, 21, 22].includes(teamType)
  ) {
    return 2 + underNTeamTypeSortKey(team.teamType);
  }
  if (teamType === 0 || team.squadUnit === "firstTeam") return 0;
  return 1;
}

export function sortClubTeamsForMatchExperience(
  teams: LiveClubTeam[],
): LiveClubTeam[] {
  return [...teams].sort((left, right) => {
    const band = matchExperienceTeamBand(left) - matchExperienceTeamBand(right);
    if (band !== 0) return band;

    const leftClub = (left.clubName ?? left.name).trim();
    const rightClub = (right.clubName ?? right.name).trim();
    const byClub = leftClub.localeCompare(rightClub);
    if (byClub !== 0) return byClub;

    if (right.rosterLen !== left.rosterLen) return right.rosterLen - left.rosterLen;
    return left.teamUid.localeCompare(right.teamUid);
  });
}

/** Within TeamType band: stronger same-pos *roster* depth (max CA, focus excluded) first. */
export function sortMatchExperienceCards(
  cards: MatchExperienceCard[],
): MatchExperienceCard[] {
  return [...cards].sort((left, right) => {
    const band = left.band - right.band;
    if (band !== 0) return band;
    const strength = right.maxSamePosCa - left.maxSamePosCa;
    if (strength !== 0) return strength;
    return left.teamUid.localeCompare(right.teamUid);
  });
}

/**
 * Best ladder step for this player.
 * If already top-2 (same-pos) on Current, stay — game time is already there.
 * Else among First Team cards: lowest focusRank (ties → managed club → depth).
 */
export function pickBestMatchExperienceCard(
  cards: MatchExperienceCard[],
  managedClubId?: string | null,
): MatchExperienceCard | null {
  const current = cards.find((card) => card.isFocusCurrentTeam);
  if (
    current &&
    typeof current.focusRank === "number" &&
    current.focusRank >= 1 &&
    current.focusRank <= 2
  ) {
    return current;
  }

  const firsts = cards.filter(
    (card) => card.band === 0 && card.focusRank != null && card.focusRank >= 1,
  );
  if (!firsts.length) return current ?? null;
  const managed = managedClubId?.trim() || null;
  return [...firsts].sort((left, right) => {
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

/** All resolved players listed on this FM team object. */
export function matchExperienceResolvedPlayers(
  players: LivePlayer[],
  teamUid: string,
): LivePlayer[] {
  return players.filter((player) => player.squadTeamUid === teamUid);
}

/**
 * Infer club UniqueID for a team from its resolved players (affiliate First etc.).
 */
export function matchExperienceTeamClubId(
  teamPlayers: Array<Pick<LivePlayer, "clubId">>,
): string | null {
  for (const player of teamPlayers) {
    const id = player.clubId?.trim();
    if (id) return id;
  }
  return null;
}

/**
 * True when this player competes for game time on this team card.
 * Loaned-out players leave their parent roster; they compete on the loan
 * club's First Team when that clubTeam is loaded (no loan team uid yet).
 */
export function matchExperiencePlayerCompetesOnTeam(
  player: Pick<LivePlayer, "squadTeamUid" | "loanedOut" | "loanClubId" | "id">,
  teamUid: string,
  teamClubId: string | null,
  teamBand?: number,
): boolean {
  if (player.loanedOut === true) {
    const loanClub = player.loanClubId?.trim();
    if (!loanClub || !teamClubId) return false;
    if (loanClub !== teamClubId) return false;
    // Without loan squadTeamUid, treat destination First as the competition step.
    if (typeof teamBand === "number") return teamBand === 0;
    return true;
  }
  return player.squadTeamUid === teamUid;
}

export function buildMatchExperienceCard(
  focus: LivePlayer,
  players: LivePlayer[],
  team: LiveClubTeam,
  position: string,
  managedClubId?: string | null,
  clubs?: Array<{ id: string; name: string }>,
): MatchExperienceCard | null {
  const pos = position.trim();
  if (!pos) return null;

  const teamPlayers = matchExperienceResolvedPlayers(players, team.teamUid);
  const fromRoster = matchExperienceTeamClubId(teamPlayers);
  const fromTeam = team.clubId?.trim() || null;
  const teamClubId =
    fromTeam ??
    fromRoster ??
    (isFeederAffiliate(team) || isIiClubAffiliate(team)
      ? null
      : managedClubId?.trim() || null);
  const teamBand = matchExperienceTeamBand(team);

  const competing = players.filter((player) =>
    matchExperiencePlayerCompetesOnTeam(player, team.teamUid, teamClubId, teamBand),
  );
  // Need a loaded roster (or at least competitors) so empty shells stay hidden.
  if (teamPlayers.length === 0 && competing.length === 0) return null;

  const onRosterSamePos = competing.filter((player) =>
    hasPrimaryPosition(player, pos),
  );

  const focusCompetes = matchExperiencePlayerCompetesOnTeam(
    focus,
    team.teamUid,
    teamClubId,
    teamBand,
  );
  const focusAlreadyListed = onRosterSamePos.some((player) => player.id === focus.id);
  const pool: LivePlayer[] =
    focusCompetes && !focusAlreadyListed
      ? [...onRosterSamePos, focus]
      : focusAlreadyListed
        ? onRosterSamePos
        : [...onRosterSamePos, focus];

  const sorted = [...pool].sort((left, right) => {
    const ca = caSortKey(right.currentAbility) - caSortKey(left.currentAbility);
    if (ca !== 0) return ca;
    return left.name.localeCompare(right.name);
  });

  let focusRank: number | null = null;
  const allRows: MatchExperienceRow[] = sorted.map((player, index) => {
    const rank = index + 1;
    const isFocus = player.id === focus.id;
    if (isFocus) focusRank = rank;
    return {
      playerId: player.id,
      name: player.name,
      currentAbility: player.currentAbility ?? null,
      rank,
      isFocus,
      isOnRoster: matchExperiencePlayerCompetesOnTeam(
        player,
        team.teamUid,
        teamClubId,
        teamBand,
      ),
    };
  });

  const start = matchExperienceWindowStart(allRows.length, focusRank);
  const rows = allRows.slice(start, start + MATCH_EXPERIENCE_PAGE_SIZE);

  const clubName =
    team.clubName?.trim() ||
    (teamClubId
      ? clubs?.find((club) => club.id === teamClubId)?.name?.trim()
      : null) ||
    team.name.trim() ||
    `Map club (?): uid-${team.teamUid}`;

  // Roster depth only — including focus flattens every card when CA is elite.
  let maxSamePosCa = -Infinity;
  for (const row of allRows) {
    if (row.isFocus) continue;
    maxSamePosCa = Math.max(maxSamePosCa, caSortKey(row.currentAbility));
  }

  return {
    teamUid: team.teamUid,
    teamLabel: matchExperienceTeamLabel(team),
    clubId: teamClubId,
    clubName,
    position: pos,
    focusRank,
    teamPlayerCount: Math.max(teamPlayers.length, competing.length),
    rows,
    totalRows: allRows.length,
    band: teamBand,
    maxSamePosCa,
    isFocusCurrentTeam: focusCompetes,
  };
}

export function buildMatchExperienceCards(
  focus: LivePlayer,
  players: LivePlayer[],
  clubTeams: LiveClubTeam[],
  managedClubId?: string | null,
  positionByTeamUid?: Record<string, string | null | undefined>,
  defaultPosition?: string | null,
  clubs?: Array<{ id: string; name: string }>,
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
      managedClubId,
      clubs,
    );
    if (card) cards.push(card);
  }
  return sortMatchExperienceCards(cards);
}
