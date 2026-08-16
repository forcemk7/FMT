/** Managed First Team identity + roster from a career .fm save. */

/** 1–20 attribute, or null when not yet extracted / unknown. */
export type AttrValue = number | null;

export const TECHNICAL_KEYS = [
  "corners",
  "crossing",
  "dribbling",
  "finishing",
  "firstTouch",
  "freeKickTaking",
  "heading",
  "longShots",
  "longThrows",
  "marking",
  "passing",
  "penaltyTaking",
  "tackling",
  "technique",
] as const;

export const GOALKEEPING_KEYS = [
  "aerialReach",
  "commandOfArea",
  "communication",
  "eccentricity",
  "handling",
  "kicking",
  "oneOnOnes",
  "punchingTendency",
  "reflexes",
  "rushingOutTendency",
  "throwing",
] as const;

export const MENTAL_KEYS = [
  "aggression",
  "anticipation",
  "bravery",
  "composure",
  "concentration",
  "decisions",
  "determination",
  "flair",
  "leadership",
  "offTheBall",
  "positioning",
  "teamwork",
  "vision",
  "workRate",
] as const;

export const PHYSICAL_KEYS = [
  "acceleration",
  "agility",
  "balance",
  "jumpingReach",
  "naturalFitness",
  "pace",
  "stamina",
  "strength",
] as const;

/**
 * SI Real Time Editor ≈ Player Attributes > General:
 * personality pack + Ada/Vers + remaining HAs (roadmap).
 * Det/Lea live under mental only — not mirrored here.
 */
export const GENERAL_KEYS = [
  "adaptability",
  "ambition",
  "consistency",
  "controversy",
  "dirtiness",
  "importantMatches",
  "injuryProneness",
  "loyalty",
  "pressure",
  "professionalism",
  "sportsmanship",
  "temperament",
  "versatility",
] as const;

export type TechnicalKey = (typeof TECHNICAL_KEYS)[number];
export type GoalkeepingKey = (typeof GOALKEEPING_KEYS)[number];
export type MentalKey = (typeof MENTAL_KEYS)[number];
export type PhysicalKey = (typeof PHYSICAL_KEYS)[number];
export type GeneralKey = (typeof GENERAL_KEYS)[number];

export type TechnicalAttributes = Partial<Record<TechnicalKey, AttrValue>>;
export type GoalkeepingAttributes = Partial<Record<GoalkeepingKey, AttrValue>>;
export type MentalAttributes = Partial<Record<MentalKey, AttrValue>>;
export type PhysicalAttributes = Partial<Record<PhysicalKey, AttrValue>>;
export type GeneralAttributes = Partial<Record<GeneralKey, AttrValue>>;

export type PlayerAttributes = {
  technical?: TechnicalAttributes | null;
  goalkeeping?: GoalkeepingAttributes | null;
  mental?: MentalAttributes | null;
  physical?: PhysicalAttributes | null;
  general?: GeneralAttributes | null;
};

export type PositionRatingKey =
  | "gk"
  | "dl"
  | "dc"
  | "dr"
  | "wbl"
  | "wbr"
  | "dm"
  | "ml"
  | "mc"
  | "mr"
  | "aml"
  | "amc"
  | "amr"
  | "st";

export type PositionRatings = Partial<Record<PositionRatingKey, AttrValue>>;

export type PlayerPositions = {
  preferred?: string | null;
  leftFoot?: AttrValue;
  rightFoot?: AttrValue;
  ratings?: PositionRatings | null;
};

/** Dynamics > Captains */
export type CaptaincyRole = "captain" | "viceCaptain";

/** Dynamics > Hierarchy */
export type HierarchyRole =
  | "teamLeader"
  | "highlyInfluential"
  | "influential"
  | "other"
  | "na";

/**
 * Dynamics > Social Groups — secondary labels may rename once binary confirms.
 */
export type SocialGroupId =
  | "core"
  | "secondaryA"
  | "secondaryB"
  | "secondaryC"
  | "other";

/** Training > Units */
export type TrainingUnitId = "goalkeeping" | "defending" | "attacking";

export type PlayerDynamics = {
  captaincy?: CaptaincyRole | null;
  hierarchy?: HierarchyRole | null;
  socialGroup?: SocialGroupId | null;
  /** Index in that social list; 0 = highest in-group. Null if group unknown. */
  socialRank?: number | null;
};

export type PlayerTraining = {
  unit?: TrainingUnitId | null;
};

/** Binary / extract debug offsets — not display data. */
export type PlayerExtractMeta = {
  doubleUidAbs?: number | null;
  personalityPackAbs?: number | null;
  attrCardAbs?: number | null;
  kind?: "gk" | "outfield" | string | null;
  /** Number of CA change-points retained on attributeHistory. */
  historyPoints?: number | null;
};

/**
 * Derived view for personality × media / HAS (not stored).
 * Det/Lea from mental; pack traits from general.
 */
export type PersonalitySignals = {
  determination: AttrValue;
  leadership: AttrValue;
  ambition: AttrValue;
  controversy: AttrValue;
  loyalty: AttrValue;
  pressure: AttrValue;
  professionalism: AttrValue;
  sportsmanship: AttrValue;
  temperament: AttrValue;
};

/**
 * One CA snapshot change-point (oldest → newest via `index`).
 * `date` is ISO when calendar mapping is locked; otherwise null and the UI
 * uses ordinal `index` on the X-axis.
 */
export type AttributeHistoryPoint = {
  index: number;
  date?: string | null;
  gap?: number | null;
  snapshotU16?: number | null;
  b23?: number | null;
  kind?: "gk" | "outfield" | string | null;
  technical?: TechnicalAttributes | null;
  goalkeeping?: GoalkeepingAttributes | null;
  mental?: MentalAttributes | null;
  physical?: PhysicalAttributes | null;
  /** FMT-side HA pack snapshots (not present on CA strip points). */
  general?: GeneralAttributes | null;
};

export type FirstTeamPlayer = {
  jobId: number;
  uid: number;
  name: string;
  /**
   * Database population for regen_only personalities (Mercenary, etc.).
   * Distinct from `_extract.kind` (gk | outfield attr layout).
   */
  kind?: "REAL" | "NEWGEN" | "UNKNOWN";
  /** Current Ability 1–200 when resolved from person-double CAPA core. */
  ca?: number | null;
  /** Potential Ability 1–200 when resolved. */
  pa?: number | null;
  /** Source of truth for age — derive age from extract `gameDate`. */
  dateOfBirth?: string | null;
  nation?: string | null;
  secondNation?: string | null;
  positions?: PlayerPositions | null;
  dynamics?: PlayerDynamics | null;
  training?: PlayerTraining | null;
  attributes?: PlayerAttributes | null;
  /**
   * CA attribute evolution (technical / GK / mental / physical).
   * Not personality/general HAs — those need a separate history locus.
   */
  attributeHistory?: AttributeHistoryPoint[] | null;
  /**
   * Loan / not-at-club status when known from the save.
   * - loanedOut: still on our squad list, playing elsewhere → badge = loan club
   * - loanedIn: at our club on loan → badge = parent club
   * - atClub: contracted and present (no badge)
   */
  loan?: PlayerLoan | null;
  _extract?: PlayerExtractMeta | null;
};

/** Parent / loan club as shown on Player Report → Contract. */
export type PlayerLoanStatus = "atClub" | "loanedOut" | "loanedIn";

export type PlayerLoan = {
  status: PlayerLoanStatus;
  /** Club currently employing the player on the pitch (loan destination). */
  loanClubId?: number | null;
  /** Contract parent club (owning club). */
  parentClubId?: number | null;
  loanClubName?: string | null;
  parentClubName?: string | null;
};

export type FirstTeamExtract = {
  savePath: string;
  saveName: string;
  /** Club Site UniqueID (primary display ID). */
  clubId: number;
  /** First Team subunit teamId used for squad job lists. */
  teamId: number;
  clubName: string;
  clubNameShort?: string | null;
  /** In-game date of the save when known (for age-from-DOB). */
  gameDate?: string | null;
  /** Identity human tag: 00950e01 native FM26, 00950e02 continue FM24. */
  tagHex?: string | null;
  /** Upload path (T096): identity only — no FT/II/U19/HA/loans. */
  metaOnly?: boolean;
  players: FirstTeamPlayer[];
  /** Reserves / II squad when discovered from parent short name. */
  reserves?: ReservesSquadExtract | null;
  /** U19 squad when discovered from parent short name. */
  u19?: U19SquadExtract | null;
  listAbs?: number;
  countHeader?: number;
  discovery?: Record<string, unknown>;
  elapsedMs: number;
  decompressedBytes?: number;
};

/** Reserves (II) squad discovered via locked catalog + team-body join. */
export type ReservesSquadExtract = {
  iiName: string;
  /** II affiliate clubId (not parent club Site ID). */
  clubId: number;
  teamId?: number | null;
  listAbs?: number;
  countHeader?: number;
  players: FirstTeamPlayer[];
  capaResolved?: number;
  discovery?: Record<string, unknown>;
};

/** U19 squad discovered via locked mid-file name → colocated job-list. */
export type U19SquadExtract = {
  u19Name: string;
  listAbs?: number;
  countHeader?: number;
  players: FirstTeamPlayer[];
  capaResolved?: number;
  discovery?: Record<string, unknown>;
};

/** Favourite-club scout hit (save-wide). */
export type FavouredClubScoutPlayer = {
  uid: number;
  name?: string | null;
  /** Relation strength; currently locked samples are 100. */
  affinity: number;
  /** Current Ability 1–200 when resolved from person-double CAPA core. */
  ca?: number | null;
  /** Potential Ability 1–200 when resolved. */
  pa?: number | null;
};

/**
 * Players who list the managed club as favoured (`4e 64 01 03 02 <clubId>`).
 * Filter out First Team UIDs client-side when a Squad extract is loaded.
 */
export type FavouredClubScoutExtract = {
  savePath: string;
  saveName: string;
  clubId: number;
  clubName?: string | null;
  clubNameShort?: string | null;
  managerName?: string | null;
  query: "favoured_club";
  affinity: number;
  motif?: string;
  players: FavouredClubScoutPlayer[];
  hitCount?: number;
  anchoredCount?: number;
  elapsedMs: number;
  decompressedBytes?: number;
};

export const JOB_ID_LO = 100_000;
export const JOB_ID_HI = 800_000;
export const UID_LO = 1_900_000_000;
export const UID_HI = 2_100_000_000;

/** Build the HAS / combo view from stored nests (single source of truth). */
export function personalitySignalsFromAttributes(
  attributes: PlayerAttributes | null | undefined,
): PersonalitySignals | null {
  if (!attributes) return null;
  const mental = attributes.mental;
  const general = attributes.general;
  if (!mental && !general) return null;
  return {
    determination: mental?.determination ?? null,
    leadership: mental?.leadership ?? null,
    ambition: general?.ambition ?? null,
    controversy: general?.controversy ?? null,
    loyalty: general?.loyalty ?? null,
    pressure: general?.pressure ?? null,
    professionalism: general?.professionalism ?? null,
    sportsmanship: general?.sportsmanship ?? null,
    temperament: general?.temperament ?? null,
  };
}

export function hasPersonalitySignals(
  signals: PersonalitySignals | null | undefined,
): boolean {
  if (!signals) return false;
  return Object.values(signals).some((v) => v != null && Number.isFinite(v));
}

/**
 * Age in whole years at `gameDate` (ISO `YYYY-MM-DD` or Date-parseable).
 * Returns null when DOB or game date is missing/invalid.
 */
export function ageFromDateOfBirth(
  dateOfBirth: string | null | undefined,
  gameDate: string | null | undefined,
): number | null {
  if (!dateOfBirth || !gameDate) return null;
  const dob = new Date(dateOfBirth);
  const asOf = new Date(gameDate);
  if (Number.isNaN(dob.getTime()) || Number.isNaN(asOf.getTime())) return null;
  let age = asOf.getFullYear() - dob.getFullYear();
  const month = asOf.getMonth() - dob.getMonth();
  if (month < 0 || (month === 0 && asOf.getDate() < dob.getDate())) age -= 1;
  if (age < 0 || age > 80) return null;
  return age;
}
