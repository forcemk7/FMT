import type { LiveClubTeam, LivePlayer } from "@/domain/adapters";

/** GM Sell lane: PA − CA at or below this (CA≈PA). */
export const MOVE_ON_HEADROOM_MAX = 8;
/** GM Loan lane: last age (inclusive) still in development range. */
export const GM_DEVELOPMENT_AGE_MAX = 24;

export type GmAdvice = "sell" | "loan";

export type SquadUnit = "firstTeam" | "under19s" | "reserves";

/** All players employed by the managed club (any squad unit; includes loans). */
export function countClubEmployees(
  players: Array<Pick<LivePlayer, "clubId">>,
  managedClubId: string | null | undefined,
): number {
  if (!managedClubId) return 0;
  return players.filter((player) => player.clubId === managedClubId).length;
}

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

/** At-club player on a specific FM team object roster. */
export function isAtClubTeamPlayer(
  player: Pick<LivePlayer, "clubId" | "loanedOut" | "loanedIn" | "squadTeamUid">,
  managedClubId: string | null | undefined,
  teamUid: string | null | undefined,
): boolean {
  if (!managedClubId || !teamUid || player.clubId !== managedClubId) return false;
  if (player.loanedOut === true) return false;
  if (player.loanedIn === true) return false;
  return player.squadTeamUid === teamUid;
}

/** Any managed-club player on a team roster (at club, loaned in, or loaned out). */
export function isOnClubTeamRosterPlayer(
  player: Pick<LivePlayer, "clubId" | "squadTeamUid">,
  managedClubId: string | null | undefined,
  teamUid: string | null | undefined,
): boolean {
  if (!managedClubId || !teamUid || player.clubId !== managedClubId) return false;
  return player.squadTeamUid === teamUid;
}

export type SquadRosterStatus = "atClub" | "loanedIn" | "loanedOut";

export function squadRosterStatus(
  player: Pick<LivePlayer, "clubId" | "loanedOut" | "loanedIn">,
  managedClubId: string | null | undefined,
): SquadRosterStatus | null {
  if (!managedClubId || player.clubId !== managedClubId) return null;
  if (player.loanedOut === true) return "loanedOut";
  if (player.loanedIn === true) return "loanedIn";
  return "atClub";
}

export type SquadTeamRosterCounts = {
  atClub: number;
  loanedIn: number;
  loanedOut: number;
};

/** Loaded players on a team tab = filter totals (not raw Team.Players vector length). */
export function squadTeamLoadedCount(counts: SquadTeamRosterCounts): number {
  return counts.atClub + counts.loanedIn + counts.loanedOut;
}

export function countSquadTeamRoster(
  players: Array<
    Pick<LivePlayer, "clubId" | "loanedOut" | "loanedIn" | "squadTeamUid">
  >,
  managedClubId: string | null | undefined,
  teamUid: string | null | undefined,
): SquadTeamRosterCounts {
  const counts: SquadTeamRosterCounts = { atClub: 0, loanedIn: 0, loanedOut: 0 };
  for (const player of players) {
    if (!isOnClubTeamRosterPlayer(player, managedClubId, teamUid)) continue;
    const status = squadRosterStatus(player, managedClubId);
    if (status === "atClub") counts.atClub += 1;
    else if (status === "loanedIn") counts.loanedIn += 1;
    else if (status === "loanedOut") counts.loanedOut += 1;
  }
  return counts;
}

export const ALL_SQUAD_ROSTER_STATUSES: readonly SquadRosterStatus[] = [
  "atClub",
  "loanedIn",
  "loanedOut",
];

/** True when the player's roster status is one of the enabled Squad filters. */
export function playerMatchesSquadRosterFilters(
  player: Pick<LivePlayer, "clubId" | "loanedOut" | "loanedIn">,
  managedClubId: string | null | undefined,
  enabled: ReadonlySet<SquadRosterStatus>,
): boolean {
  const status = squadRosterStatus(player, managedClubId);
  return status != null && enabled.has(status);
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
export function countClubEmployeesOnLoan(
  players: Array<Pick<LivePlayer, "clubId" | "loanedOut">>,
  managedClubId: string | null | undefined,
): number {
  if (!managedClubId) return 0;
  return players.filter(
    (player) => player.clubId === managedClubId && player.loanedOut === true,
  ).length;
}

/** Managed-club player at any squad unit (excludes outgoing loans). */
export function isAtClubEmployee(
  player: Pick<LivePlayer, "clubId" | "loanedOut">,
  managedClubId: string | null | undefined,
): boolean {
  if (!managedClubId || player.clubId !== managedClubId) return false;
  return player.loanedOut !== true;
}

export function countClubEmployeesAtClub(
  players: Array<Pick<LivePlayer, "clubId" | "loanedOut">>,
  managedClubId: string | null | undefined,
): number {
  if (!managedClubId) return 0;
  return players.filter((player) => isAtClubEmployee(player, managedClubId)).length;
}

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

/** Manager senior squad team uid (First Team), else first `firstTeam` unit. */
export function seniorSquadTeamUid(
  clubTeams: Array<Pick<LiveClubTeam, "teamUid" | "isManagerTeam" | "squadUnit">>,
): string | null {
  const manager = clubTeams.find((team) => team.isManagerTeam);
  if (manager?.teamUid) return manager.teamUid;
  const first = clubTeams.find((team) => team.squadUnit === "firstTeam");
  return first?.teamUid ?? null;
}

/**
 * At-club players on the senior/manager team — reference pool for HoYD/GM median CA
 * (pipeline toward First Team, not diluted by UTeams/reserves).
 */
export function seniorAtClubPlayers<
  T extends Pick<LivePlayer, "clubId" | "loanedOut" | "loanedIn" | "squadTeamUid">,
>(
  players: T[],
  managedClubId: string | null | undefined,
  clubTeams: Array<Pick<LiveClubTeam, "teamUid" | "isManagerTeam" | "squadUnit">>,
): T[] {
  const teamUid = seniorSquadTeamUid(clubTeams);
  if (!teamUid) return [];
  return players.filter((player) =>
    isAtClubTeamPlayer(player, managedClubId, teamUid),
  );
}

/**
 * GM advice vs senior-team median CA (pipeline toward First Team).
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
 * HoYD groom prospect vs senior-team median CA.
 * High PA for this club’s First Team bar with room left to develop; youth only (≤24).
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
  const { primary, secondary } = playerPositionParts(player);
  if (primary === "—") return "—";
  if (!secondary) return primary;
  return `${primary} (${secondary})`;
}

/** Primary / secondary parts for stacked facts-strip display. */
export function playerPositionParts(
  player: Pick<LivePlayer, "positions" | "secondaryPositions">,
): { primary: string; secondary: string | null } {
  const primaryList = player.positions ?? [];
  if (!primaryList.length) return { primary: "—", secondary: null };
  const primary = primaryList.join(" / ");
  const secondaryList = player.secondaryPositions ?? [];
  if (!secondaryList.length) return { primary, secondary: null };
  return { primary, secondary: secondaryList.join(" / ") };
}

const POSITION_CODE_GROUP: Record<string, PositionGroup> = {
  GK: "Goalkeepers",
  SW: "Centre-backs",
  DC: "Centre-backs",
  CB: "Centre-backs",
  DL: "Full-backs / wing-backs",
  DR: "Full-backs / wing-backs",
  LB: "Full-backs / wing-backs",
  RB: "Full-backs / wing-backs",
  WBL: "Full-backs / wing-backs",
  WBR: "Full-backs / wing-backs",
  DM: "Defensive midfielders",
  DMC: "Defensive midfielders",
  MC: "Central midfielders",
  CM: "Central midfielders",
  AMC: "Attacking midfielders",
  AM: "Attacking midfielders",
  ML: "Wingers",
  MR: "Wingers",
  AML: "Wingers",
  AMR: "Wingers",
  LW: "Wingers",
  RW: "Wingers",
  ST: "Strikers",
  CF: "Strikers",
};

const GROUP_MATCH_ORDER: PositionGroup[] = [
  "Goalkeepers",
  "Centre-backs",
  "Full-backs / wing-backs",
  "Defensive midfielders",
  "Central midfielders",
  "Attacking midfielders",
  "Wingers",
  "Strikers",
];

function collectPositionCodes(
  values: Array<string | null | undefined>,
): string[] {
  const seen = new Set<string>();
  const codes: string[] = [];
  for (const value of values) {
    const code = value?.trim().toUpperCase();
    if (!code || seen.has(code)) continue;
    seen.add(code);
    codes.push(code);
  }
  return codes;
}

function primaryPositionCodesForGrouping(
  player: Pick<LivePlayer, "positions" | "bestCalculatedPosition">,
): string[] {
  return collectPositionCodes([
    player.bestCalculatedPosition,
    ...(player.positions ?? []),
  ]);
}

function positionCodesForGrouping(
  player: Pick<LivePlayer, "positions" | "secondaryPositions" | "bestCalculatedPosition">,
): string[] {
  const primary = primaryPositionCodesForGrouping(player);
  if (primary.length > 0) return primary;
  return collectPositionCodes(player.secondaryPositions ?? []);
}

function groupForPositionCode(code: string): PositionGroup | null {
  return POSITION_CODE_GROUP[code] ?? null;
}

/** Group by best position slot only; secondaries are display-only unless no primary exists. */
export function groupPlayerPosition(
  player: Pick<LivePlayer, "positions" | "secondaryPositions" | "bestCalculatedPosition">,
): PositionGroup {
  const codes = positionCodesForGrouping(player);
  for (const group of GROUP_MATCH_ORDER) {
    if (codes.some((code) => groupForPositionCode(code) === group)) {
      return group;
    }
  }
  return "Utility / other players";
}

/** FMScout TeamType → default squad tab label (or map reminder). */
export function teamTypeDisplayLabel(teamType: number | null | undefined): string | null {
  switch (teamType) {
    case 0:
      return "First Team";
    case 1:
      return "Reserves";
    case 2:
      return "A";
    case 3:
      return "B";
    case 9:
      return "Under 23s";
    case 10:
      return "Under 21s";
    case 11:
      return "Under 19s";
    case 12:
      return "Under 18s";
    case 13:
      return "C";
    case 14:
      return "Amateur";
    case 15:
      return "II";
    case 16:
      return "Team 2";
    case 17:
      return "Team 3";
    case 18:
      return "Under 20s";
    case 21:
    case 22:
      return "Youth";
    case 30:
      return "Dutch Reserves";
    default:
      if (typeof teamType === "number") return `Map TeamType ${teamType}`;
      return null;
  }
}

/** PGE Affiliation Type byte (wrapper +0x30) → label or map reminder. */
export function affiliationTypeDisplayLabel(
  affiliationType: number | null | undefined,
  affiliationTypeLabel?: string | null,
): string | null {
  if (affiliationTypeLabel?.trim()) return affiliationTypeLabel.trim();
  if (typeof affiliationType !== "number") return null;
  switch (affiliationType) {
    case 0x01:
      return "Normal Affiliated Club";
    case 0x08:
      return "II Club";
    case 0x10:
      return "Good Relations";
    case 0x11:
      return "Likely Friendly";
    default:
      return `Map AffiliationType 0x${affiliationType.toString(16).padStart(2, "0").toUpperCase()}`;
  }
}

/**
 * Squad tab / Settings display name.
 * Managed club teams → TeamType labels; affiliated teams → team shortName.
 */
export function squadTeamDisplayName(
  team: Pick<
    LiveClubTeam,
    | "name"
    | "shortName"
    | "teamUid"
    | "teamType"
    | "affiliationType"
    | "affiliationTypeLabel"
  >,
  _managedClubName?: string | null,
): string {
  const isAffiliate = typeof team.affiliationType === "number";
  if (isAffiliate) {
    const short = team.shortName?.trim();
    if (short) return short;
    const trimmed = team.name.trim();
    if (trimmed) return trimmed;
    const fromAffiliation = affiliationTypeDisplayLabel(
      team.affiliationType,
      team.affiliationTypeLabel,
    );
    if (fromAffiliation) return fromAffiliation;
    return `Map TeamType (?): uid-${team.teamUid}`;
  }

  const fromAffiliation = affiliationTypeDisplayLabel(
    team.affiliationType,
    team.affiliationTypeLabel,
  );
  if (fromAffiliation?.startsWith("Map AffiliationType")) return fromAffiliation;
  const fromType = teamTypeDisplayLabel(team.teamType);
  if (fromType) return fromType;
  if (fromAffiliation) return fromAffiliation;
  const trimmed = team.name.trim();
  if (trimmed) return `Map TeamType (?): ${trimmed}`;
  return `Map TeamType (?): uid-${team.teamUid}`;
}

/** Player profile Club fact — prefer the player's team shortName. */
export function playerTeamDisplayName(
  player: Pick<LivePlayer, "squadTeamUid" | "clubName" | "clubId">,
  clubTeams: Array<Pick<LiveClubTeam, "teamUid" | "shortName" | "name">>,
  clubs: Array<{ id: string; name: string }>,
): string | null {
  const teamUid = player.squadTeamUid?.trim();
  if (teamUid) {
    const team = clubTeams.find((item) => item.teamUid === teamUid);
    const short = team?.shortName?.trim();
    if (short) return short;
    const teamName = team?.name?.trim();
    if (teamName) return teamName;
  }
  const clubName = player.clubName?.trim();
  if (clubName) return clubName;
  const clubId = player.clubId?.trim();
  if (clubId) {
    const club = clubs.find((item) => item.id === clubId);
    const name = club?.name?.trim();
    if (name) return name;
  }
  return null;
}

/**
 * Squad desk tab label — display name + loaded roster size
 * (at club + on loan + loaned out). Raw Team.Players `rosterLen` stays in Settings.
 */
export function squadTeamTabLabel(
  team: Pick<
    LiveClubTeam,
    | "name"
    | "shortName"
    | "teamUid"
    | "teamType"
    | "affiliationType"
    | "affiliationTypeLabel"
  >,
  managedClubName?: string | null,
  rosterCounts?: SquadTeamRosterCounts | null,
): string {
  const name = squadTeamDisplayName(team, managedClubName);
  if (!rosterCounts) return name;
  return `${name} (${squadTeamLoadedCount(rosterCounts)})`;
}

const SQUAD_UNIT_SORT: Record<SquadUnit, number> = {
  firstTeam: 0,
  under19s: 1,
  reserves: 2,
};

export function sortClubTeamsForSquadDesk(teams: LiveClubTeam[]): LiveClubTeam[] {
  return [...teams].sort((left, right) => {
    const unit = SQUAD_UNIT_SORT[left.squadUnit] - SQUAD_UNIT_SORT[right.squadUnit];
    if (unit !== 0) return unit;
    if (right.rosterLen !== left.rosterLen) return right.rosterLen - left.rosterLen;
    return squadTeamDisplayName(left).localeCompare(squadTeamDisplayName(right));
  });
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
