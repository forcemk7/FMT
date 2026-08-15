/** Roster types + empty seed (fixture players removed from UI). */

export type {
  AttrValue,
  AttributeHistoryPoint,
  CaptaincyRole,
  FirstTeamPlayer,
  GeneralAttributes,
  GoalkeepingAttributes,
  HierarchyRole,
  MentalAttributes,
  PersonalitySignals,
  PhysicalAttributes,
  PlayerAttributes,
  PlayerDynamics,
  PlayerExtractMeta,
  PlayerPositions,
  PlayerTraining,
  PositionRatings,
  SocialGroupId,
  TechnicalAttributes,
  TrainingUnitId,
} from "../shared/save/types.ts";

export {
  GENERAL_KEYS,
  GOALKEEPING_KEYS,
  MENTAL_KEYS,
  PHYSICAL_KEYS,
  TECHNICAL_KEYS,
  ageFromDateOfBirth,
  hasPersonalitySignals,
  personalitySignalsFromAttributes,
} from "../shared/save/types.ts";

import type {
  AttributeHistoryPoint,
  FirstTeamPlayer,
  PersonalitySignals,
  PlayerAttributes,
  PlayerLoan,
  PlayerLoanStatus,
} from "../shared/save/types.ts";
import {
  ageFromDateOfBirth,
  hasPersonalitySignals,
  personalitySignalsFromAttributes,
} from "../shared/save/types.ts";

export type { PlayerLoan, PlayerLoanStatus } from "../shared/save/types.ts";

/**
 * Empirical UID split for this FM26 career DB (see extract-first-team-fast.py).
 * REAL fixtures sit below; NEWGENs at/above. Used when extract omits `kind`.
 */
export const NEWGEN_UID_FLOOR = 2_002_000_000;

export function populationKindFromUid(
  uid: number | null | undefined,
): "REAL" | "NEWGEN" | "UNKNOWN" {
  if (uid == null || !Number.isFinite(uid) || uid <= 0) return "UNKNOWN";
  return uid >= NEWGEN_UID_FLOOR ? "NEWGEN" : "REAL";
}

function normalizePopulationKind(
  raw: unknown,
  uid: number | null | undefined,
): "REAL" | "NEWGEN" | "UNKNOWN" {
  if (raw === "REAL" || raw === "NEWGEN" || raw === "UNKNOWN") return raw;
  return populationKindFromUid(uid);
}

function normalizePlayerLoan(raw: unknown): PlayerLoan | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const status = o.status;
  if (status !== "atClub" && status !== "loanedOut" && status !== "loanedIn") {
    return null;
  }
  const num = (v: unknown): number | null =>
    typeof v === "number" && Number.isFinite(v) ? v : null;
  const str = (v: unknown): string | null =>
    typeof v === "string" && v.trim() ? v.trim() : null;
  return {
    status,
    loanClubId: num(o.loanClubId),
    parentClubId: num(o.parentClubId),
    loanClubName: str(o.loanClubName),
    parentClubName: str(o.parentClubName),
  };
}

export type RosterPlayer = FirstTeamPlayer & {
  personIndex?: number;
  kind?: "REAL" | "NEWGEN" | "UNKNOWN";
  /** @deprecated legacy shorthand — prefer attributes.mental */
  pos?: string;
  club?: string;
  notes?: string;
  source?: "fixture" | "save";
};

/** Legacy flattened personality blob (pre-attributes.general). */
type LegacyPersonalityAttributes = {
  determination?: number | null;
  leadership?: number | null;
  ambition?: number | null;
  controversy?: number | null;
  loyalty?: number | null;
  pressure?: number | null;
  professionalism?: number | null;
  sportsmanship?: number | null;
  temperament?: number | null;
};

type LegacyHiddenAttributes = {
  adaptability?: number | null;
  consistency?: number | null;
  dirtiness?: number | null;
  importantMatches?: number | null;
  injuryProneness?: number | null;
  versatility?: number | null;
};

/** Loose shape accepted from API / older localStorage. */
export type LegacyRosterPlayer = RosterPlayer & {
  age?: number | null;
  det?: number;
  lea?: number;
  /** Slim subunit persist (pre full RosterPlayer). */
  determination?: number | null;
  leadership?: number | null;
  doubleUidAbs?: number | null;
  personalityPackAbs?: number | null;
  personalityAttributes?: LegacyPersonalityAttributes | null;
  hiddenAttributes?: LegacyHiddenAttributes | null;
  attributes?: (PlayerAttributes & { _meta?: Record<string, unknown> }) | null;
};

/**
 * Normalize API / legacy localStorage players into the current model.
 * Drops stored age; Det/Lea stay under mental; pack under general.
 */
export function normalizeRosterPlayer(raw: LegacyRosterPlayer): RosterPlayer {
  const legacyPa = raw.personalityAttributes;
  const legacyHa = raw.hiddenAttributes;
  const incoming = raw.attributes ?? null;

  let attributes: PlayerAttributes | null = incoming
    ? {
        technical: incoming.technical ?? null,
        goalkeeping: incoming.goalkeeping ?? null,
        mental: incoming.mental ?? null,
        physical: incoming.physical ?? null,
        general: incoming.general ?? null,
      }
    : null;

  // Strip accidental FT/Pas under GK if an older extract put them there.
  if (attributes?.goalkeeping) {
    const { firstTouch: _ft, passing: _pas, ...gkRest } = attributes.goalkeeping as {
      firstTouch?: number | null;
      passing?: number | null;
    } & Record<string, number | null | undefined>;
    attributes = { ...attributes, goalkeeping: gkRest };
  }

  if (legacyPa || legacyHa) {
    const mental = {
      ...(attributes?.mental ?? {}),
      ...(legacyPa?.determination != null
        ? { determination: legacyPa.determination }
        : {}),
      ...(legacyPa?.leadership != null ? { leadership: legacyPa.leadership } : {}),
    };
    const general = {
      ...(attributes?.general ?? {}),
      ...(legacyHa?.adaptability != null
        ? { adaptability: legacyHa.adaptability }
        : {}),
      ...(legacyHa?.consistency != null
        ? { consistency: legacyHa.consistency }
        : {}),
      ...(legacyHa?.dirtiness != null ? { dirtiness: legacyHa.dirtiness } : {}),
      ...(legacyHa?.importantMatches != null
        ? { importantMatches: legacyHa.importantMatches }
        : {}),
      ...(legacyHa?.injuryProneness != null
        ? { injuryProneness: legacyHa.injuryProneness }
        : {}),
      ...(legacyHa?.versatility != null
        ? { versatility: legacyHa.versatility }
        : {}),
      ...(legacyPa?.ambition != null ? { ambition: legacyPa.ambition } : {}),
      ...(legacyPa?.controversy != null
        ? { controversy: legacyPa.controversy }
        : {}),
      ...(legacyPa?.loyalty != null ? { loyalty: legacyPa.loyalty } : {}),
      ...(legacyPa?.pressure != null ? { pressure: legacyPa.pressure } : {}),
      ...(legacyPa?.professionalism != null
        ? { professionalism: legacyPa.professionalism }
        : {}),
      ...(legacyPa?.sportsmanship != null
        ? { sportsmanship: legacyPa.sportsmanship }
        : {}),
      ...(legacyPa?.temperament != null
        ? { temperament: legacyPa.temperament }
        : {}),
    };
    attributes = {
      ...(attributes ?? {}),
      mental: Object.keys(mental).length ? mental : attributes?.mental ?? null,
      general: Object.keys(general).length
        ? general
        : attributes?.general ?? null,
    };
  }

  // Legacy top-level det/lea shortcuts (+ slim subunit determination/leadership)
  const slimDet = raw.determination;
  const slimLea = raw.leadership;
  if (
    raw.det != null ||
    raw.lea != null ||
    slimDet != null ||
    slimLea != null
  ) {
    attributes = {
      ...(attributes ?? {}),
      mental: {
        ...(attributes?.mental ?? {}),
        ...(raw.det != null ? { determination: raw.det } : {}),
        ...(raw.lea != null ? { leadership: raw.lea } : {}),
        ...(slimDet != null && attributes?.mental?.determination == null
          ? { determination: slimDet }
          : {}),
        ...(slimLea != null && attributes?.mental?.leadership == null
          ? { leadership: slimLea }
          : {}),
      },
    };
  }

  const extract = raw._extract ?? {
    doubleUidAbs: raw.doubleUidAbs ?? null,
    personalityPackAbs: raw.personalityPackAbs ?? null,
    attrCardAbs:
      typeof incoming?._meta?.cardAbs === "number"
        ? incoming._meta.cardAbs
        : null,
    kind:
      incoming?._meta?.kind === "gk" || incoming?._meta?.kind === "outfield"
        ? incoming._meta.kind
        : null,
  };

  return {
    jobId: raw.jobId ?? 0,
    uid: raw.uid,
    name: raw.name,
    dateOfBirth: raw.dateOfBirth ?? null,
    nation: raw.nation ?? null,
    secondNation: raw.secondNation ?? null,
    positions: raw.positions ?? null,
    dynamics: raw.dynamics ?? null,
    training: raw.training ?? null,
    attributes,
    attributeHistory: Array.isArray(
      (raw as { attributeHistory?: AttributeHistoryPoint[] | null })
        .attributeHistory,
    )
      ? (raw as { attributeHistory: AttributeHistoryPoint[] }).attributeHistory
      : null,
    loan: normalizePlayerLoan(
      (raw as { loan?: unknown }).loan ??
        (incoming as { loan?: unknown } | null)?.loan,
    ),
    ca:
      raw.ca != null && Number.isFinite(Number(raw.ca)) ? Number(raw.ca) : null,
    pa:
      raw.pa != null && Number.isFinite(Number(raw.pa)) ? Number(raw.pa) : null,
    _extract: extract,
    personIndex: raw.personIndex,
    kind: normalizePopulationKind(raw.kind, raw.uid),
    pos: raw.pos,
    club: raw.club,
    notes: raw.notes,
    source: raw.source,
  };
}

export function rosterPersonalitySignals(
  player: RosterPlayer,
): PersonalitySignals | null {
  const base = personalitySignalsFromAttributes(player.attributes);
  // Mentor / HAS Det·Lea must match Attributes tip. Live CA cards can be wrong
  // (foreign Det=20 decoys) while attributeHistory keeps the Progress Report strip.
  const tipMental = player.attributeHistory?.at(-1)?.mental;
  if (!base && tipMental == null) return null;
  return {
    determination:
      tipMental?.determination ?? base?.determination ?? null,
    leadership: tipMental?.leadership ?? base?.leadership ?? null,
    ambition: base?.ambition ?? null,
    controversy: base?.controversy ?? null,
    loyalty: base?.loyalty ?? null,
    pressure: base?.pressure ?? null,
    professionalism: base?.professionalism ?? null,
    sportsmanship: base?.sportsmanship ?? null,
    temperament: base?.temperament ?? null,
  };
}

export function rosterHasPersonalityData(player: RosterPlayer): boolean {
  return hasPersonalitySignals(rosterPersonalitySignals(player));
}

export function rosterPlayerAge(
  player: RosterPlayer,
  gameDate?: string | null,
): number | null {
  return ageFromDateOfBirth(player.dateOfBirth, gameDate ?? null);
}
