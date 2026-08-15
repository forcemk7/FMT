/**
 * Mentoring group finder from age + mental / influence profile.
 *
 * FM mentoring is influence-based (not classic mentor/mentee labels). Suggestions
 * only surface overload (2 strong → 1 weaker youngling) and cascade
 * (High→Mid, High→Low, Mid→Low) groups with Determination-weighted safety.
 * Personality × media labels still inform specialize/balance package bonuses.
 */

import {
  ATTRIBUTE_LABELS,
  attributeTone,
  CHECKER_TABLE_ATTRIBUTES,
  HA_QUALITY_WEIGHTS,
  HA_VISIBLE_QUALITY_WEIGHTS,
  type AttributeTone,
  type TrackedAttribute,
} from "../domain/attributes.js";
import { loadCatalog, findPersonality, findMediaHandling } from "../catalog/lookup.js";
import { MEDIA_HANDLING } from "../data/media-handling.js";
import type {
  Catalog,
  MediaHandlingDefinition,
  PersonalityDefinition,
} from "../catalog/types.js";
import { isPersonalityMediaCompatible } from "./bands.js";
import {
  rankPersonalityMediaCombos,
  type ComboRankEntry,
  type ComboRanking,
} from "./rank-combos.js";

export type MentoringRole = "mentee" | "mentor" | "unknown";

/**
 * Stable backend / enumeration order for mentoring traits.
 * Do not use this for UI column order — see {@link MENTORING_DISPLAY_ORDER}.
 */
export const MENTORING_TRAITS = [
  "determination",
  "professionalism",
  "ambition",
  "loyalty",
  "sportsmanship",
  "controversy",
  "pressure",
  "temperament",
] as const;

export type MentoringTrait = (typeof MENTORING_TRAITS)[number];

/** @deprecated Use MENTORING_TRAITS — kept as alias for callers. */
export const PROTECTABLE_TRAITS = MENTORING_TRAITS;

export type ProtectableTrait = MentoringTrait;

/** Visible “known” mentoring attrs (Det). Rest are HA/personality hidden. */
const MENTORING_KNOWN_TRAITS: ReadonlySet<MentoringTrait> = new Set([
  "determination",
]);

/** HAS / visible weight for mentoring net-lift scoring and display ranking. */
export function mentoringTraitWeight(trait: MentoringTrait): number {
  if (trait === "determination") {
    return HA_VISIBLE_QUALITY_WEIGHTS.determination;
  }
  return HA_QUALITY_WEIGHTS[trait];
}

export function mentoringTraitIsKnown(trait: MentoringTrait): boolean {
  return MENTORING_KNOWN_TRAITS.has(trait);
}

/**
 * Mentoring matrix / board presentation order (not {@link MENTORING_TRAITS}).
 * Matches checker / HAS rank / Compare columns ({@link CHECKER_TABLE_ATTRIBUTES}),
 * omitting Leadership (not a mentoring attr).
 */
export const MENTORING_DISPLAY_ORDER: readonly MentoringTrait[] =
  CHECKER_TABLE_ATTRIBUTES.filter((attribute): attribute is MentoringTrait =>
    (MENTORING_TRAITS as readonly string[]).includes(attribute),
  );

export type MentoringTraitBand = {
  min: number;
  max: number;
  midpoint: number;
};

export type MentoringSubject = {
  id?: string;
  name?: string;
  age?: number;
  determination?: number;
  leadership?: number;
  professionalism?: number;
  ambition?: number;
  loyalty?: number;
  sportsmanship?: number;
  controversy?: number;
  pressure?: number;
  temperament?: number;
  haScore?: number;
  /** Current personality label (for ranking anchor). */
  personality?: string;
  /** Current media handling label (for ranking anchor). */
  mediaHandling?: string;
  /** Regen flag — selects the matching combo ranking table. */
  isRegen?: boolean;
  /** Estimated ranges — current combo reflection, not mentoring ceilings. */
  bands?: Partial<Record<ProtectableTrait, MentoringTraitBand>>;
};

export type MentoringCandidate = MentoringSubject & {
  id: string;
  name: string;
  /** Current Ability 1–200 when extract resolved it. Do not invent. */
  ca?: number;
  /** Potential Ability 1–200 when extract resolved it. Do not invent. */
  pa?: number;
};

/** Save-roster / board match row used by mentee scoring and package boards. */
type MentoringMatch = {
  id: string;
  name: string;
  kind: "mentor" | "mentee";
  score: number;
  age?: number;
  /** Per-trait board colors for the matched player (same 8 as mentoring boards). */
  traitTones: Record<ProtectableTrait, "good" | "work" | "neutral">;
  reasons: string[];
  /** Trait labels this mentor can polish on the mentee. */
  lifts?: string[];
  /**
   * Whether mentoring this kid is a specialize or balance path for them
   * (mentor combo sits in that lane on their board).
   */
  path?: "specialize" | "balance";
};

/**
 * Which HA ranking table(s) mentor personality packages are scored on.
 * Same personality × media can differ for regen vs real players.
 */
export type MentorRosterFilter = "mixed" | "regen" | "real";

/** In-game scouting filters derived from the catalog. */
export type MentoringPackageHint = {
  personality: string;
  /** Empty when media is not part of the scout filter. */
  mediaHandling: string;
  rank?: number;
  haScore?: number;
  tone?: AttributeTone;
  /** HA gain vs the mentee's current combo (when known). */
  haDelta?: number;
  lifts?: string[];
  /** Catalog bands prove a lift on at least one focus trait. */
  provenLift?: boolean;
  /**
   * Roster applicability:
   * - regen / real: unique card for that HA table (when HA differs)
   * - either: both tables share the same HA (no badge)
   */
  roster?: "regen" | "real" | "either";
  /** Preferred / table flag for squad matching. */
  forRegen?: boolean;
};

export type MentoringSearchProfile = {
  age: string;
  determination?: string;
  leadership?: string;
  /**
   * Default scout list. Prefer closeMatch / bestPossible / available when present.
   */
  packages: MentoringPackageHint[];
  /** Same HA-family climbs (preserve core mid; improve core and/or other traits). */
  bestPossible?: MentoringPackageHint[];
  /** Cross-family retrains that improve overall HA with bounded mid shift. */
  closeMatch?: MentoringPackageHint[];
  /** Safe combos that match players in the save (highest HA first). */
  available?: MentoringPackageHint[];
};

/** One mentor personality × media that helps without regressing protected traits. */
export type MentoringFloorOption = {
  personality: string;
  mediaHandling: string;
  rank: number;
  haScore: number;
  tone: AttributeTone;
  /** HA gain vs the mentee's current combo (when known). */
  haDelta?: number;
  /** Trait labels this package improves vs mentee mids. */
  lifts: string[];
  roster?: "regen" | "real" | "either";
  forRegen?: boolean;
};

/**
 * Safe mentor floor / climb board.
 * Options are sorted weakest→stronger; index 0 is the absolute floor.
 * When the current combo is known, the UI shows Current → Target.
 */
export type MentoringFloorBoard = {
  /** HA of the absolute floor option. */
  floorHa: number;
  /** Mentee's current personality (when known). */
  personality?: string;
  /** Mentee's current media handling (when known). */
  mediaHandling?: string;
  /** Current combo rank on the HA table (when known). */
  rank?: number;
  /** Current combo HA (when known). */
  haScore?: number;
  /** Current combo tone (when known). */
  tone?: AttributeTone;
  options: MentoringFloorOption[];
};

const AGE_GAP = 3;
/** Exclusive upper bound for classic mentee-only role (< 24). */
const YOUNG_AGE = 24;
/** Inclusive: can still receive mentoring (edge with mentor min). */
const MENTEE_MAX_AGE = 24;
/** Inclusive: old enough to lead younger players. */
const MENTOR_MIN_AGE = 21;
/**
 * Minimum mentee HA to bother mentoring — okay base worth polishing,
 * not a full personality rebuild.
 */
const MENTEE_HA_FLOOR = 9;
/** Above this, prefer tiny tweaks only (already near elite). */
export const MENTEE_HA_ELITE = 13;
/**
 * From-this-save matches shown on the scout-style board.
 * In-game mentoring groups are three players (2+1 or 1+2).
 */
const MENTORING_SLOTS = 6;
/** Exclusive upper bound for “suitable for influence” subjects (`age < 24`). */
export const MENTORING_YOUNG_AGE = YOUNG_AGE;
/** Cap group suggestions per shape (2 mentors / 2 mentees). */
const MENTORING_GROUP_SLOTS = 2;
/** How many safe mentor packages to surface in Mentor personalities. */
const FLOOR_BOARD_SLOTS = 12;

type TraitReading = {
  trait: MentoringTrait;
  value: number;
  min: number;
  max: number;
  tone: AttributeTone;
  /** Higher = more urgent to fix (low mid, or high controversy). */
  weakness: number;
};

type ScoredFloorPackage = {
  personality: PersonalityDefinition;
  media: MediaHandlingDefinition;
  entry: ComboRankEntry;
  liftScore: number;
  /** Focus traits the catalog bands prove this package can lift. */
  liftCovered: number;
  /** Package scored on the regen (true) or real-player (false) HA table. */
  forRegen: boolean;
};

const rankingCache: { regen?: ComboRanking; nonRegen?: ComboRanking } = {};
let catalogCache: Catalog | undefined;

function mentoringCatalog(): Catalog {
  catalogCache ??= loadCatalog();
  return catalogCache;
}

function comboRanking(isRegen: boolean): ComboRanking {
  if (isRegen) {
    rankingCache.regen ??= rankPersonalityMediaCombos(mentoringCatalog(), {
      isRegen: true,
    });
    return rankingCache.regen;
  }
  rankingCache.nonRegen ??= rankPersonalityMediaCombos(mentoringCatalog(), {
    isRegen: false,
  });
  return rankingCache.nonRegen;
}

function traitValue(
  subject: MentoringSubject,
  trait: ProtectableTrait,
): number | undefined {
  return subject.bands?.[trait]?.midpoint ?? subject[trait];
}

function traitBand(
  subject: MentoringSubject,
  trait: ProtectableTrait,
): MentoringTraitBand | undefined {
  const band = subject.bands?.[trait];
  if (band) return band;
  const value = subject[trait];
  if (value === undefined || !Number.isFinite(value)) return undefined;
  return { min: value, max: value, midpoint: value };
}

function traitTone(trait: ProtectableTrait, value: number): AttributeTone {
  return attributeTone(trait as TrackedAttribute, value);
}

/** How badly this mid needs work. Controversy is inverted. */
function traitWeakness(trait: MentoringTrait, value: number): number {
  return trait === "controversy" ? value : 21 - value;
}

function traitLabel(trait: ProtectableTrait): string {
  if (trait === "determination") return "Determination";
  return ATTRIBUTE_LABELS[trait as TrackedAttribute];
}

function traitDisplayIndex(trait: ProtectableTrait): number {
  const index = MENTORING_DISPLAY_ORDER.indexOf(trait);
  return index === -1 ? 999 : index;
}

function sortTraitsForDisplay<T extends { trait: ProtectableTrait }>(
  items: readonly T[],
): T[] {
  return [...items].sort(
    (a, b) =>
      traitDisplayIndex(a.trait) - traitDisplayIndex(b.trait) ||
      a.trait.localeCompare(b.trait),
  );
}

function sortTraitIdsForDisplay(
  traits: readonly ProtectableTrait[],
): ProtectableTrait[] {
  return [...traits].sort(
    (a, b) =>
      traitDisplayIndex(a) - traitDisplayIndex(b) || a.localeCompare(b),
  );
}

function labelsForDisplay(traits: readonly ProtectableTrait[]): string[] {
  return sortTraitIdsForDisplay(traits).map((trait) => traitLabel(trait));
}

/** Board colors from HA-table midpoint tones (good / bad→work / neutral). */
function mentoringBoardTones(
  subject: MentoringSubject,
): Record<ProtectableTrait, "good" | "work" | "neutral"> {
  const tones = Object.fromEntries(
    MENTORING_DISPLAY_ORDER.map((trait) => [trait, "neutral"]),
  ) as Record<ProtectableTrait, "good" | "work" | "neutral">;
  for (const reading of assessTraits(subject)) {
    if (reading.tone === "good") tones[reading.trait] = "good";
    else if (reading.tone === "bad") tones[reading.trait] = "work";
  }
  return tones;
}

/** Age → Determination → Leadership → hidden attrs (HA order). */
function formatMatchReasons(parts: {
  age?: string;
  determination?: string;
  leadership?: string;
  hidden: { trait: ProtectableTrait; text: string }[];
}): string[] {
  const reasons: string[] = [];
  if (parts.age) reasons.push(parts.age);
  if (parts.determination) reasons.push(parts.determination);
  if (parts.leadership) reasons.push(parts.leadership);
  for (const item of sortTraitsForDisplay(parts.hidden)) {
    reasons.push(item.text);
  }
  return reasons;
}

function assessTraits(subject: MentoringSubject): TraitReading[] {
  const readings: TraitReading[] = [];
  for (const trait of MENTORING_TRAITS) {
    const band = traitBand(subject, trait);
    if (!band) continue;
    readings.push({
      trait,
      value: band.midpoint,
      min: band.min,
      max: band.max,
      tone: traitTone(trait, band.midpoint),
      weakness: traitWeakness(trait, band.midpoint),
    });
  }
  return readings;
}

/**
 * Already-strong traits that a mentor must not drag down.
 * Uses mid tone and solid floors (min ≥ 14).
 */
export function protectedTraits(subject: MentoringSubject): ProtectableTrait[] {
  const protectedList: ProtectableTrait[] = [];
  for (const trait of PROTECTABLE_TRAITS) {
    const band = traitBand(subject, trait);
    if (!band) continue;
    if (trait === "controversy") {
      if (band.max <= 14 && band.midpoint < 10) protectedList.push(trait);
      continue;
    }
    if (traitTone(trait, band.midpoint) === "good" || band.min >= 14) {
      protectedList.push(trait);
    }
  }
  return protectedList;
}

/**
 * Traits to target, worst mid first.
 * Already-good mids are skipped; estimate-band tops are not mentoring ceilings.
 */
export function mentoringFocus(subject: MentoringSubject): TraitReading[] {
  return assessTraits(subject)
    .filter((r) => r.tone !== "good")
    .sort((a, b) => b.weakness - a.weakness || a.trait.localeCompare(b.trait));
}

export function mentoringRole(age?: number): MentoringRole {
  if (age === undefined || !Number.isFinite(age)) return "unknown";
  return age < YOUNG_AGE ? "mentee" : "mentor";
}

function packageBand(
  personality: PersonalityDefinition,
  media: MediaHandlingDefinition,
  trait: ProtectableTrait,
): { min: number; max: number } | undefined {
  const p = personality.bands[trait as TrackedAttribute];
  const m = media.bands[trait as TrackedAttribute];
  if (!p && !m) return undefined;
  if (!p) return { min: m!.min, max: m!.max };
  if (!m) return { min: p.min, max: p.max };
  // Keep inverted ranges (e.g. 15-12) — callers must treat min > max as impossible.
  return { min: Math.max(p.min, m.min), max: Math.min(p.max, m.max) };
}

function packageBandPossible(
  band: { min: number; max: number } | undefined,
): boolean {
  return !band || band.min <= band.max;
}

function shortMediaLabel(id: string): string {
  const row = MEDIA_HANDLING.find((m) => m.id === id);
  if (row?.styles.length) return row.styles.join(", ");
  return id;
}

function resolveMedia(label: string): MediaHandlingDefinition | undefined {
  try {
    return findMediaHandling(mentoringCatalog(), label);
  } catch {
    return MEDIA_HANDLING.find((m) => m.id === label);
  }
}

/** Current combo row on the ranking table when personality × media are known. */
function currentComboEntry(
  subject: MentoringSubject,
): ComboRankEntry | undefined {
  if (!subject.personality || !subject.mediaHandling) return undefined;
  const ranking = comboRanking(Boolean(subject.isRegen));
  return ranking.entries.find(
    (e) =>
      e.personality === subject.personality &&
      e.mediaHandling === subject.mediaHandling,
  );
}

/** HA of the player's current combo on the ranking table, else estimated HA. */
function currentHaAnchor(subject: MentoringSubject): number {
  const hit = currentComboEntry(subject);
  if (hit) return hit.haScore;
  if (subject.haScore !== undefined && Number.isFinite(subject.haScore)) {
    return subject.haScore;
  }
  return 0;
}

function liftLabelsForPackage(
  personality: PersonalityDefinition,
  media: MediaHandlingDefinition,
  focus: TraitReading[],
): string[] {
  const lifts: ProtectableTrait[] = [];
  for (const target of focus) {
    const band = packageBand(personality, media, target.trait);
    if (!band) continue;
    if (target.trait === "controversy") {
      if (band.max < target.value) lifts.push(target.trait);
      continue;
    }
    if (band.min > target.value || band.max > target.value) {
      lifts.push(target.trait);
    }
  }
  return labelsForDisplay(lifts);
}

/**
 * Band-floor safety (still uncertain in FM — mentoring is noisy).
 *
 * For every *hidden* trait we know on the mentee:
 * - positive attrs: mentor package min ≥ mentee min
 * - Controversy: mentor package max ≤ mentee max
 * Missing mentor band ⇒ unconstrained 1–20 ⇒ unsafe when the mentee has a real floor/ceiling.
 *
 * Determination is excluded here: known Det is a visible attr / scout filter
 * (mentor Det ≥ mentee Det), not a personality-package band floor.
 */
function isSafeMentorPackage(
  personality: PersonalityDefinition,
  media: MediaHandlingDefinition,
  subject: MentoringSubject,
): boolean {
  for (const trait of MENTORING_TRAITS) {
    if (trait === "determination") continue;

    const packageTraitBand = packageBand(personality, media, trait);
    if (packageTraitBand && !packageBandPossible(packageTraitBand)) {
      return false;
    }

    const menteeBand = traitBand(subject, trait);
    if (!menteeBand) continue;

    const band = packageTraitBand;
    if (trait === "controversy") {
      if (!band) {
        if (menteeBand.max < 20) return false;
        continue;
      }
      if (band.max > menteeBand.max + 0.001) return false;
      continue;
    }

    if (!band) {
      if (menteeBand.min > 1) return false;
      continue;
    }
    if (band.min + 0.001 < menteeBand.min) return false;
  }
  return true;
}

function packageLiftsFocus(
  personality: PersonalityDefinition,
  media: MediaHandlingDefinition,
  focus: TraitReading[],
): { covered: number; score: number } {
  let covered = 0;
  let score = 0;
  focus.forEach((target, index) => {
    const band = packageBand(personality, media, target.trait);
    if (!band) return;
    if (target.trait === "controversy") {
      if (band.max >= 15) return;
      const lift = target.value - band.max;
      if (lift < 0.5 && band.max >= target.value) return;
      covered += 1;
      score += Math.max(6, 18 - index * 3) + Math.min(10, Math.max(0, lift));
      return;
    }
    const midLift = band.min - target.value;
    if (midLift < 1 && band.min <= 14) {
      if (band.max <= target.value) return;
      covered += 1;
      score += 4 + Math.max(0, 12 - index * 3);
      return;
    }
    if (traitTone(target.trait, band.min) === "bad") return;
    covered += 1;
    score += Math.max(8, 22 - index * 4) + band.min + Math.min(10, midLift);
  });
  return { covered, score };
}

/**
 * Band-safe mentor packages (strict floors). Used for the floor board.
 */
function safeMentorFloorPackages(
  subject: MentoringSubject,
  focus: TraitReading[] = mentoringFocus(subject),
  roster: MentorRosterFilter = "mixed",
): ScoredFloorPackage[] {
  return scoreCatalogPackagesForRoster(
    subject,
    focus,
    (personality, media) => isSafeMentorPackage(personality, media, subject),
    roster,
  );
}

/**
 * Best-match pool: core floor strict, soft mid preserve on other bars.
 */
function bestLaneMentorPackages(
  subject: MentoringSubject,
  family: HaFamily,
  focus: TraitReading[] = mentoringFocus(subject),
  roster: MentorRosterFilter = "mixed",
): ScoredFloorPackage[] {
  return scoreCatalogPackagesForRoster(
    subject,
    focus,
    (personality, media) =>
      isSafeForBestBars(personality, media, subject, family),
    roster,
  );
}

/**
 * Close-match pool: allow core-bar dips (peak-shift), still protect other floors.
 */
function closeLaneMentorPackages(
  subject: MentoringSubject,
  family: HaFamily,
  focus: TraitReading[] = mentoringFocus(subject),
  roster: MentorRosterFilter = "mixed",
): ScoredFloorPackage[] {
  return scoreCatalogPackagesForRoster(
    subject,
    focus,
    (personality, media) =>
      isSafeMentorPackageExceptCore(personality, media, subject, family),
    roster,
  );
}

function scoreCatalogPackagesForRoster(
  subject: MentoringSubject,
  focus: TraitReading[],
  isSafe: (
    personality: PersonalityDefinition,
    media: MediaHandlingDefinition,
  ) => boolean,
  roster: MentorRosterFilter,
): ScoredFloorPackage[] {
  const modes: boolean[] =
    roster === "regen" ? [true] : roster === "real" ? [false] : [true, false];
  const scored: ScoredFloorPackage[] = [];
  for (const forRegen of modes) {
    scored.push(...scoreCatalogPackages(subject, focus, isSafe, forRegen));
  }
  scored.sort(compareScoredFloorPackages);
  return scored;
}

function compareScoredFloorPackages(
  a: ScoredFloorPackage,
  b: ScoredFloorPackage,
): number {
  return (
    a.entry.haScore - b.entry.haScore ||
    b.entry.rank - a.entry.rank ||
    b.liftCovered - a.liftCovered ||
    b.liftScore - a.liftScore ||
    a.personality.id.localeCompare(b.personality.id) ||
    a.media.id.localeCompare(b.media.id) ||
    Number(a.forRegen) - Number(b.forRegen)
  );
}

function scoreCatalogPackages(
  subject: MentoringSubject,
  focus: TraitReading[],
  isSafe: (
    personality: PersonalityDefinition,
    media: MediaHandlingDefinition,
  ) => boolean,
  forRegen: boolean,
): ScoredFloorPackage[] {
  const ranking = comboRanking(forRegen);
  const scored: ScoredFloorPackage[] = [];
  for (const entry of ranking.entries) {
    const catalog = mentoringCatalog();
    const personality = findPersonality(catalog, entry.personality);
    const media = resolveMedia(entry.mediaHandling);
    if (!personality || !media) continue;
    if (!isPersonalityMediaCompatible(personality, media)) continue;
    // Regen-only personalities only exist on the regen HA table.
    if (isRegenOnly(personality) && !forRegen) continue;
    if (!isSafe(personality, media)) continue;
    const lift = packageLiftsFocus(personality, media, focus);
    scored.push({
      personality,
      media,
      entry,
      liftScore: lift.score,
      liftCovered: lift.covered,
      forRegen,
    });
  }
  scored.sort(compareScoredFloorPackages);
  return scored;
}

/** Positive when mentor is better than subject on this trait. */
function liftTowardBetter(
  trait: MentoringTrait,
  mentorValue: number,
  subjectValue: number,
): number {
  return trait === "controversy"
    ? subjectValue - mentorValue
    : mentorValue - subjectValue;
}

/** HA from combo table, explicit score, or a mid-based estimate. */
function estimateSubjectHa(subject: MentoringSubject): number | undefined {
  const combo = currentComboEntry(subject);
  if (combo) return combo.haScore;
  if (subject.haScore !== undefined && Number.isFinite(subject.haScore)) {
    return subject.haScore;
  }

  const goods: number[] = [];
  for (const trait of [
    "professionalism",
    "ambition",
    "pressure",
    "temperament",
    "loyalty",
    "sportsmanship",
  ] as const) {
    const value = traitValue(subject, trait);
    if (value !== undefined) goods.push(value);
  }
  const controversy = traitValue(subject, "controversy");
  if (goods.length < 4 || controversy === undefined) return undefined;
  const meanGoods = goods.reduce((sum, v) => sum + v, 0) / goods.length;
  return meanGoods - controversy / 6;
}

/**
 * Traits worth a mentoring tweak (not every neutral mid).
 * Goods below 12 / Contro above 10 — room to push toward good without a rebuild.
 */
function menteePolishTargets(subject: MentoringSubject): TraitReading[] {
  return assessTraits(subject)
    .filter((r) => {
      if (r.tone === "good") return false;
      if (r.trait === "controversy") return r.value > 10 || r.tone === "bad";
      return r.value < 12;
    })
    .sort((a, b) => b.weakness - a.weakness || a.trait.localeCompare(b.trait));
}

type MenteeScoreOptions = {
  /** Skip age-gap / mentee-max gates (manual unit builder). */
  relaxAge?: boolean;
  /** Skip HA floor / rebuild-profile hard rejects (manual unit builder). */
  relaxProfile?: boolean;
};

function scoreMenteeNeedingHelp(
  candidate: MentoringCandidate,
  subject: MentoringSubject,
  options: MenteeScoreOptions = {},
): MentoringMatch | null {
  const relaxAge = Boolean(options.relaxAge);
  const relaxProfile = Boolean(options.relaxProfile);

  if (
    !relaxAge &&
    subject.age !== undefined &&
    candidate.age !== undefined &&
    candidate.age > subject.age - AGE_GAP
  ) {
    return null;
  }

  if (
    !relaxAge &&
    candidate.age !== undefined &&
    candidate.age > MENTEE_MAX_AGE
  ) {
    return null;
  }

  const ha = estimateSubjectHa(candidate);
  // Great mentors belong on kids with an okay HA base — not rebuild projects.
  if (
    !relaxProfile &&
    (ha === undefined || ha < MENTEE_HA_FLOOR)
  ) {
    return null;
  }

  const readings = assessTraits(candidate);
  const badCount = readings.filter((r) => r.tone === "bad").length;
  const goodCount = readings.filter((r) => r.tone === "good").length;
  // Too many disasters = personality rebuild, not a mentoring tweak.
  if (!relaxProfile && badCount >= 3) return null;
  if (
    !relaxProfile &&
    readings.length >= 5 &&
    goodCount === 0 &&
    badCount >= 2
  ) {
    return null;
  }

  // Soft preference only — do not void every mentor edge for high-HA /
  // multi-trait kids (that emptied Mentoring groups for Driven subjects).
  const polish = menteePolishTargets(candidate);

  const reasonParts: {
    age?: string;
    determination?: string;
    leadership?: string;
    hidden: { trait: ProtectableTrait; text: string }[];
  } = { hidden: [] };
  const lifts: ProtectableTrait[] = [];
  let weightedLift = 0;
  let weightedHarm = 0;
  let score = 0;

  // Sweet spot: okay→great (≈9–13). Below floor already rejected; above elite softens.
  if (ha !== undefined && Number.isFinite(ha)) {
    if (ha <= MENTEE_HA_ELITE) {
      score += Math.round((ha - MENTEE_HA_FLOOR) * 8 + 8);
    } else {
      score += Math.max(4, Math.round(40 - (ha - MENTEE_HA_ELITE) * 10));
    }
  }

  // Prefer a few tweaks over a laundry list.
  score += Math.max(0, 20 - Math.max(polish.length, 1) * 5);
  score += goodCount * 4;
  score -= badCount * 6;

  if (candidate.age !== undefined) {
    reasonParts.age = `${candidate.age}y`;
    if (subject.age !== undefined) {
      score += Math.min(12, (subject.age - candidate.age) * 2);
    }
  }

  // Net HAS-weighted lift: Spo +1 cannot outweigh Pro drag.
  for (const trait of MENTORING_TRAITS) {
    const menteeValue = traitValue(candidate, trait);
    const mentorValue = traitValue(subject, trait);
    if (menteeValue === undefined || mentorValue === undefined) continue;

    const weight = mentoringTraitWeight(trait);
    const lift = liftTowardBetter(trait, mentorValue, menteeValue);
    if (lift >= 2) {
      const tone = traitTone(trait, mentorValue);
      if (tone === "bad") {
        // Pulling toward a bad mentor band counts as harm.
        weightedHarm += lift * weight;
        continue;
      }
      weightedLift += lift * weight;
      lifts.push(trait);
      const text = `tweak ${traitLabel(trait)}`;
      if (trait === "determination") {
        reasonParts.determination = text;
      } else {
        reasonParts.hidden.push({ trait, text });
      }
    } else if (lift <= -2) {
      weightedHarm += -lift * weight;
    }
  }

  if (lifts.length === 0) return null;

  // Harm is charged harder so a Pro hit kills a Spo polish.
  const netWeighted = weightedLift - weightedHarm * 1.35;
  if (netWeighted < 10) return null;

  score += Math.round(netWeighted * 2);
  if (score < 18 && !relaxProfile) return null;

  const liftLabels = labelsForDisplay(lifts);
  const haLabel =
    ha !== undefined && Number.isFinite(ha)
      ? `HA ${Math.round(ha * 10) / 10}`
      : undefined;
  // Lead with traits — HA/age are context, not the decision.
  const reasons = [
    ...liftLabels.map((label) => `tweak ${label}`),
    ...(haLabel ? [haLabel] : []),
    ...formatMatchReasons(reasonParts).filter(
      (r) => !r.startsWith("tweak "),
    ),
  ].slice(0, 4);

  return {
    id: candidate.id,
    name: candidate.name,
    kind: "mentee",
    score: Math.round(score),
    ...(candidate.age !== undefined ? { age: candidate.age } : {}),
    traitTones: mentoringBoardTones(candidate),
    reasons: reasons.slice(0, 4),
    lifts: liftLabels,
  };
}

function isRegenOnly(personality: PersonalityDefinition): boolean {
  return personality.conditionals.some((rule) => rule.kind === "regen_only");
}

function mentorScoutFloors(subject: MentoringSubject): {
  age: string;
  determination: string;
  leadership: string;
} {
  const ageFloor =
    subject.age !== undefined ? subject.age + AGE_GAP : YOUNG_AGE;
  const detFloor = Math.max(15, Math.ceil(subject.determination ?? 10));
  const leadFloor = Math.max(13, Math.ceil(subject.leadership ?? 8));
  return {
    age: `${ageFloor}+`,
    determination: `${detFloor}+`,
    leadership: `${leadFloor}+`,
  };
}

function floorOptionToHint(
  row: MentoringFloorOption,
): MentoringPackageHint {
  return {
    personality: row.personality,
    mediaHandling: row.mediaHandling,
    rank: row.rank,
    haScore: row.haScore,
    tone: row.tone,
    ...(row.haDelta !== undefined ? { haDelta: row.haDelta } : {}),
    ...(row.lifts.length ? { lifts: row.lifts } : {}),
    ...(row.roster !== undefined ? { roster: row.roster } : {}),
    ...(row.forRegen !== undefined ? { forRegen: row.forRegen } : {}),
  };
}

function scoredPackageToHint(
  row: ScoredFloorPackage,
  currentHa: number,
  focus: TraitReading[],
  includeDelta: boolean,
): MentoringPackageHint {
  const provenLift = row.liftCovered > 0;
  const lifts = provenLift
    ? liftLabelsForPackage(row.personality, row.media, focus)
    : [];
  return {
    personality: row.personality.id,
    mediaHandling: shortMediaLabel(row.media.id),
    rank: row.entry.rank,
    haScore: row.entry.haScore,
    tone: row.entry.tone,
    forRegen: row.forRegen,
    roster: row.forRegen ? "regen" : "real",
    ...(includeDelta ? { haDelta: row.entry.haScore - currentHa } : {}),
    ...(lifts.length ? { lifts } : {}),
    provenLift,
  };
}

function packageHintKey(pkg: {
  personality: string;
  mediaHandling: string;
}): string {
  return `${pkg.personality}::${pkg.mediaHandling}`;
}

/** Highest HA first (better combo / rank earlier in the list). */
function sortPackagesByHaDesc(
  packages: MentoringPackageHint[],
): MentoringPackageHint[] {
  return [...packages].sort(
    (a, b) =>
      (b.haScore ?? Number.NEGATIVE_INFINITY) -
        (a.haScore ?? Number.NEGATIVE_INFINITY) ||
      (a.rank ?? Number.POSITIVE_INFINITY) -
        (b.rank ?? Number.POSITIVE_INFINITY) ||
      a.personality.localeCompare(b.personality) ||
      a.mediaHandling.localeCompare(b.mediaHandling),
  );
}

/**
 * Canonical roster label from the HA tables — not from which variants
 * happened to appear in a given mentoring bucket.
 *
 * - either: combo exists on both tables with the same HA
 * - split: both tables, different HA → keep separate Regen/Real cards
 * - regen / real: only that table has the combo
 */
type CatalogRosterKind = "either" | "split" | "regen" | "real";

function catalogRosterKind(
  personality: string,
  mediaHandling: string,
): CatalogRosterKind {
  const match = (isRegen: boolean) =>
    comboRanking(isRegen).entries.find(
      (entry) =>
        entry.personality === personality &&
        entry.mediaHandling === mediaHandling,
    );
  const regen = match(true);
  const real = match(false);
  if (regen && real) {
    return Math.abs(regen.haScore - real.haScore) < 0.05 ? "either" : "split";
  }
  if (regen) return "regen";
  if (real) return "real";
  return "split";
}

/**
 * Unify roster badges across buckets: collapse same-HA twins to Either using
 * the catalog tables, even when a list only contains one variant (e.g. Direct
 * match only found a regen mentor in the save).
 */
function collapseRosterHints(
  hints: MentoringPackageHint[],
  order: "ha-desc" | "preserve" = "ha-desc",
): MentoringPackageHint[] {
  const groups = new Map<string, MentoringPackageHint[]>();
  for (const hint of hints) {
    const key = packageHintKey(hint);
    const list = groups.get(key) ?? [];
    list.push(hint);
    groups.set(key, list);
  }

  const emitGroup = (group: MentoringPackageHint[]): MentoringPackageHint[] => {
    const head = group[0]!;
    const kind = catalogRosterKind(head.personality, head.mediaHandling);

    if (kind === "either") {
      const preferred =
        group.find((pkg) => pkg.forRegen === true) ??
        group.find((pkg) => pkg.forRegen === false) ??
        head;
      return [mergeIdenticalRosterTwins(preferred, preferred)];
    }

    if (kind === "regen" || kind === "real") {
      const primary = group[0]!;
      return [
        {
          ...primary,
          roster: kind,
          forRegen: kind === "regen",
        },
      ];
    }

    // split: one card per table variant present in this list
    const out: MentoringPackageHint[] = [];
    const seen = new Set<boolean>();
    for (const pkg of group) {
      const forRegen = Boolean(pkg.forRegen);
      if (seen.has(forRegen)) continue;
      seen.add(forRegen);
      out.push({
        ...pkg,
        roster: forRegen ? "regen" : "real",
        forRegen,
      });
    }
    return out;
  };

  if (order === "preserve") {
    const seen = new Set<string>();
    const collapsed: MentoringPackageHint[] = [];
    for (const hint of hints) {
      const key = packageHintKey(hint);
      if (seen.has(key)) continue;
      seen.add(key);
      collapsed.push(...emitGroup(groups.get(key)!));
    }
    return collapsed;
  }

  const collapsed: MentoringPackageHint[] = [];
  for (const group of groups.values()) {
    collapsed.push(...emitGroup(group));
  }
  return sortPackagesByHaDesc(collapsed);
}

/** Same personality × media, same HA on both tables → one "either" card. */
function mergeIdenticalRosterTwins(
  a: MentoringPackageHint,
  _b: MentoringPackageHint,
): MentoringPackageHint {
  return {
    personality: a.personality,
    mediaHandling: a.mediaHandling,
    ...(a.rank !== undefined ? { rank: a.rank } : {}),
    ...(a.haScore !== undefined ? { haScore: a.haScore } : {}),
    ...(a.tone !== undefined ? { tone: a.tone } : {}),
    ...(a.haDelta !== undefined ? { haDelta: a.haDelta } : {}),
    ...(a.lifts?.length ? { lifts: a.lifts } : {}),
    ...(a.provenLift !== undefined ? { provenLift: a.provenLift } : {}),
    roster: "either",
    ...(a.forRegen !== undefined ? { forRegen: a.forRegen } : {}),
  };
}

function scoredPackageKey(row: ScoredFloorPackage): string {
  return `${row.personality.id}::${shortMediaLabel(row.media.id)}::${
    row.forRegen ? "regen" : "real"
  }`;
}

function comboIdentityKey(row: ScoredFloorPackage): string {
  return `${row.personality.id}::${shortMediaLabel(row.media.id)}`;
}

/**
 * Take the top `limit` unique personality × media combos from an already-ranked
 * list, then expand each combo to include every roster variant (regen / real).
 * Stops mixed mode from filling the board with duplicate HA-table twins.
 */
function takeTopCombosWithRosterVariants(
  ranked: ScoredFloorPackage[],
  limit: number,
): ScoredFloorPackage[] {
  const variantsByCombo = new Map<string, ScoredFloorPackage[]>();
  for (const row of ranked) {
    const combo = comboIdentityKey(row);
    const list = variantsByCombo.get(combo) ?? [];
    list.push(row);
    variantsByCombo.set(combo, list);
  }

  const seen = new Set<string>();
  const out: ScoredFloorPackage[] = [];
  for (const row of ranked) {
    const combo = comboIdentityKey(row);
    if (seen.has(combo)) continue;
    seen.add(combo);
    const variants = [...(variantsByCombo.get(combo) ?? [])].sort(
      (a, b) =>
        b.entry.haScore - a.entry.haScore ||
        a.entry.rank - b.entry.rank ||
        Number(b.forRegen) - Number(a.forRegen),
    );
    out.push(...variants);
    if (seen.size >= limit) break;
  }
  return out;
}

/** Dominant HA “family”: tallest bar, or balanced (MC-style). */
type HaFamily = ProtectableTrait | "balanced";

/** Traits that form the bar chart — Determination included (visible but can be core). */
const FAMILY_TRAITS: readonly ProtectableTrait[] = [
  "determination",
  "professionalism",
  "ambition",
  "pressure",
  "temperament",
  "loyalty",
  "sportsmanship",
  "controversy",
];

function packageMidpointForTrait(
  row: ScoredFloorPackage,
  trait: ProtectableTrait,
): number | undefined {
  const band = packageBand(row.personality, row.media, trait);
  if (!band) return undefined;
  return (band.min + band.max) / 2;
}

function packageFloorTowardBetter(
  row: ScoredFloorPackage,
  trait: ProtectableTrait,
): number | undefined {
  const band = packageBand(row.personality, row.media, trait);
  if (!band) return undefined;
  return trait === "controversy" ? band.max : band.min;
}

function traitDeltaTowardBetter(
  trait: ProtectableTrait,
  mentorValue: number,
  subjectValue: number,
): number {
  return trait === "controversy"
    ? subjectValue - mentorValue
    : mentorValue - subjectValue;
}

function normalizeTraitScore(trait: ProtectableTrait, mid: number): number {
  return trait === "controversy" ? 21 - mid : mid;
}

function isCoreTrait(family: HaFamily, trait: ProtectableTrait, mid: number): boolean {
  if (family === "balanced") {
    return trait !== "controversy" && mid >= 14;
  }
  return trait === family;
}

/**
 * HA family for a mentee: tallest confident mid, or balanced when several
 * bars sit high and close (Model Citizen–style profile).
 */
function subjectHaFamily(subject: MentoringSubject): HaFamily {
  const scored = FAMILY_TRAITS.map((trait) => {
    const band = traitBand(subject, trait);
    if (!band) return null;
    const span = Math.max(0, band.max - band.min);
    const confidence = (20 - span) / 20;
    return {
      trait,
      score: normalizeTraitScore(trait, band.midpoint) + confidence * 0.75,
      mid: band.midpoint,
    };
  }).filter(
    (row): row is { trait: ProtectableTrait; score: number; mid: number } =>
      row !== null,
  );
  scored.sort((a, b) => b.score - a.score || a.trait.localeCompare(b.trait));
  if (scored.length === 0) return "balanced";

  const high = scored.filter((row) => row.score >= 14);
  if (
    high.length >= 4 &&
    high[0]!.score - high[high.length - 1]!.score <= 2.5
  ) {
    return "balanced";
  }
  return scored[0]!.trait;
}

/**
 * HA family of a mentor package from catalog floors (not personality name).
 * Model Citizen is always balanced; otherwise dominant package mid wins.
 */
function packageHaFamily(row: ScoredFloorPackage): HaFamily {
  if (row.personality.id === "Model Citizen") return "balanced";

  const scored = FAMILY_TRAITS.map((trait) => {
    const mid = packageMidpointForTrait(row, trait);
    if (mid === undefined) return null;
    return { trait, score: normalizeTraitScore(trait, mid) };
  }).filter(
    (entry): entry is { trait: ProtectableTrait; score: number } =>
      entry !== null,
  );
  scored.sort((a, b) => b.score - a.score || a.trait.localeCompare(b.trait));
  if (scored.length === 0) return "balanced";

  const high = scored.filter((row) => row.score >= 14);
  if (
    high.length >= 4 &&
    high[0]!.score - high[high.length - 1]!.score <= 2.5
  ) {
    return "balanced";
  }
  return scored[0]!.trait;
}

/**
 * Best-lane safety: core floor is strict; other bars may use mid preserve
 * (estimate mins are often soft). Determination stays a scout filter.
 */
function isSafeForBestBars(
  personality: PersonalityDefinition,
  media: MediaHandlingDefinition,
  subject: MentoringSubject,
  family: HaFamily,
): boolean {
  for (const trait of MENTORING_TRAITS) {
    if (trait === "determination") continue;

    const packageTraitBand = packageBand(personality, media, trait);
    if (packageTraitBand && !packageBandPossible(packageTraitBand)) {
      return false;
    }

    const menteeBand = traitBand(subject, trait);
    if (!menteeBand) continue;

    const band = packageTraitBand;
    const core = isCoreTrait(family, trait, menteeBand.midpoint);

    if (trait === "controversy") {
      if (!band) {
        if (menteeBand.max < 20) return false;
        continue;
      }
      if (band.max > menteeBand.max + 0.001) return false;
      continue;
    }

    if (!band) {
      // Unconstrained: only block when that bar is already tall.
      if (menteeBand.midpoint >= 14) return false;
      continue;
    }

    if (band.min + 0.001 >= menteeBand.min) continue;

    if (core) return false;

    // Soft non-core: allow if package mid still near mentee mid.
    const mentorMid = (band.min + band.max) / 2;
    if (mentorMid + 0.001 < menteeBand.midpoint - 1.5) return false;
  }
  return true;
}

/**
 * Close-lane safety: allow core-bar dips (peak-shift). Non-core floors stay
 * protected; Determination stays a scout filter.
 */
function isSafeMentorPackageExceptCore(
  personality: PersonalityDefinition,
  media: MediaHandlingDefinition,
  subject: MentoringSubject,
  family: HaFamily,
): boolean {
  for (const trait of MENTORING_TRAITS) {
    if (trait === "determination") continue;

    const packageTraitBand = packageBand(personality, media, trait);
    if (packageTraitBand && !packageBandPossible(packageTraitBand)) {
      return false;
    }

    if (family !== "balanced" && trait === family) continue;

    const menteeBand = traitBand(subject, trait);
    if (!menteeBand) continue;
    if (
      family === "balanced" &&
      trait !== "controversy" &&
      menteeBand.midpoint >= 14
    ) {
      continue;
    }

    const band = packageTraitBand;
    if (trait === "controversy") {
      if (!band) {
        if (menteeBand.max < 20) return false;
        continue;
      }
      if (band.max > menteeBand.max + 0.001) return false;
      continue;
    }

    if (!band) {
      if (menteeBand.min > 1) return false;
      continue;
    }
    if (band.min + 0.001 < menteeBand.min) return false;
  }
  return true;
}

type PackageProgressScores = {
  coreGain: number;
  otherGain: number;
  overallGain: number;
  /** True when every comparable bar is flat or up (no lowering). */
  noBarDown: boolean;
  loweredCore: boolean;
  raisedOther: boolean;
  midShift: number;
};

/**
 * Floor-based bar deltas: preserve/improve uses catalog mins (contro max),
 * matching mentoring safety rather than optimistic midpoints.
 */
function packageProgressScores(
  row: ScoredFloorPackage,
  subject: MentoringSubject,
  family: HaFamily,
): PackageProgressScores {
  let coreGain = 0;
  let otherGain = 0;
  let midShift = 0;
  let compared = 0;
  let noBarDown = true;
  let loweredCore = false;
  let raisedOther = false;

  for (const trait of FAMILY_TRAITS) {
    // Det only participates in the bar chart when it is the core family.
    if (trait === "determination" && family !== "determination") continue;

    const mentee = traitBand(subject, trait);
    if (!mentee) continue;
    const mentorFloor = packageFloorTowardBetter(row, trait);
    const mentorMid = packageMidpointForTrait(row, trait);
    const core = isCoreTrait(family, trait, mentee.midpoint);

    if (mentorFloor === undefined || mentorMid === undefined) {
      // Unconstrained: can't prove preserve on a tall bar.
      if (mentee.midpoint >= 14) noBarDown = false;
      continue;
    }

    const subjectFloor = trait === "controversy" ? mentee.max : mentee.min;
    const floorDelta = traitDeltaTowardBetter(trait, mentorFloor, subjectFloor);
    const midDelta = traitDeltaTowardBetter(trait, mentorMid, mentee.midpoint);
    midShift += Math.abs(midDelta);
    compared += 1;

    // Core: no floor drop. Other bars: mid may dip up to 1.5 (estimate noise).
    if (core) {
      if (floorDelta < -0.001) noBarDown = false;
      coreGain += floorDelta;
      if (floorDelta < -0.001) loweredCore = true;
    } else {
      if (midDelta < -1.5) noBarDown = false;
      otherGain += midDelta;
      if (midDelta > 0.05) raisedOther = true;
    }
  }

  return {
    coreGain,
    otherGain,
    overallGain: coreGain + otherGain,
    noBarDown,
    loweredCore,
    raisedOther,
    midShift: compared > 0 ? midShift / compared : 0,
  };
}

/**
 * Best matches (bar chart): same family, no bar lowers, and
 * improve core / improve rest / improve both.
 */
function isBestMatchPackage(
  row: ScoredFloorPackage,
  family: HaFamily,
  profile: PackageProgressScores,
): boolean {
  if (packageHaFamily(row) !== family) return false;
  if (!profile.noBarDown) return false;
  return profile.coreGain > 0.05 || profile.otherGain > 0.05;
}

/**
 * Close match: peak-shift / tradeoff — drop core (or shift family) while
 * raising other bars. Still a net profile gain; mid rewrite stays bounded.
 */
function isCloseMatchPackage(
  row: ScoredFloorPackage,
  family: HaFamily,
  profile: PackageProgressScores,
): boolean {
  if (packageHaFamily(row) === family) {
    // Same family but not Best: only if core dips while others rise.
    if (!profile.loweredCore || !profile.raisedOther) return false;
  }
  if (profile.overallGain <= 0.05 && !profile.raisedOther) return false;
  return profile.midShift <= 5.5;
}

function resolveCandidateCombo(
  candidate: MentoringCandidate,
): { personality: PersonalityDefinition; media: MediaHandlingDefinition } | null {
  if (!candidate.personality?.trim() || !candidate.mediaHandling?.trim()) {
    return null;
  }
  const catalog = mentoringCatalog();
  const personality = findPersonality(catalog, candidate.personality);
  const media = resolveMedia(candidate.mediaHandling);
  if (!personality || !media) return null;
  if (!isPersonalityMediaCompatible(personality, media)) return null;
  return { personality, media };
}

/**
 * One pipeline for mentee mentoring:
 * 1) all personality × media combos on the HA table(s)
 * 2) keep band-safe packages
 * 3) split into Direct match (in save), Best matches (same HA family),
 *    Close match (cross-family retrain with HA gain)
 * 4) From this save = players whose combo sits in the safe set
 */
function buildUnifiedMentorBoard(
  subject: MentoringSubject,
  candidates: MentoringCandidate[],
  focus: TraitReading[],
  roster: MentorRosterFilter = "mixed",
): {
  floor: MentoringFloorBoard;
  lookFor: MentoringSearchProfile;
  matches: MentoringMatch[];
} {
  const allSafe = safeMentorFloorPackages(subject, focus, roster);
  const current = currentComboEntry(subject);
  const currentHa = currentHaAnchor(subject);
  const includeDelta = Boolean(current) || subject.haScore !== undefined;
  const family = subjectHaFamily(subject);
  const bestLane = bestLaneMentorPackages(subject, family, focus, roster);
  const closeLane = closeLaneMentorPackages(subject, family, focus, roster);

  const climbingSafe = allSafe.filter(
    (row) => row.entry.haScore > currentHa + 0.001,
  );
  const progressionSafe = climbingSafe.length > 0 ? climbingSafe : allSafe;

  const climbingBest = bestLane.filter(
    (row) => row.entry.haScore > currentHa + 0.001,
  );
  const progressionBest = climbingBest.length > 0 ? climbingBest : bestLane;

  const climbingClose = closeLane.filter(
    (row) => row.entry.haScore > currentHa + 0.001,
  );
  const progressionClose =
    climbingClose.length > 0 ? climbingClose : closeLane;

  const profileByKey = new Map<string, PackageProgressScores>();
  for (const row of [...progressionBest, ...progressionClose]) {
    const key = scoredPackageKey(row);
    if (!profileByKey.has(key)) {
      profileByKey.set(key, packageProgressScores(row, subject, family));
    }
  }

  const bestCandidates = progressionBest.filter((row) => {
    const profile = profileByKey.get(scoredPackageKey(row));
    if (!profile) return false;
    return isBestMatchPackage(row, family, profile);
  });
  const bestPool = bestCandidates;
  const bestComboKeys = new Set(bestPool.map((row) => comboIdentityKey(row)));

  const closeCandidates = progressionClose.filter((row) => {
    if (bestComboKeys.has(comboIdentityKey(row))) return false;
    const profile = profileByKey.get(scoredPackageKey(row));
    if (!profile) return false;
    return isCloseMatchPackage(row, family, profile);
  });
  const closePool = closeCandidates;

  // Empty Best lane stays empty — don't fake "Best" with non-preserving packages.
  const bestSource = bestPool;
  const closeSource =
    closePool.length > 0
      ? closePool
      : progressionClose.filter(
          (row) => !bestComboKeys.has(comboIdentityKey(row)),
        );

  const toHint = (row: ScoredFloorPackage) =>
    scoredPackageToHint(row, currentHa, focus, includeDelta);

  const bestPossible = collapseRosterHints(
    takeTopCombosWithRosterVariants(
      [...bestSource].sort(
        (a, b) =>
          (profileByKey.get(scoredPackageKey(b))?.coreGain ?? 0) -
            (profileByKey.get(scoredPackageKey(a))?.coreGain ?? 0) ||
          (profileByKey.get(scoredPackageKey(b))?.otherGain ?? 0) -
            (profileByKey.get(scoredPackageKey(a))?.otherGain ?? 0) ||
          b.liftCovered - a.liftCovered ||
          b.entry.haScore - a.entry.haScore ||
          a.entry.rank - b.entry.rank ||
          b.liftScore - a.liftScore,
      ),
      FLOOR_BOARD_SLOTS,
    ).map(toHint),
  );

  const closeMatch = collapseRosterHints(
    takeTopCombosWithRosterVariants(
      [...closeSource].sort(
        (a, b) =>
          (profileByKey.get(scoredPackageKey(b))?.otherGain ?? 0) -
            (profileByKey.get(scoredPackageKey(a))?.otherGain ?? 0) ||
          (profileByKey.get(scoredPackageKey(b))?.overallGain ?? 0) -
            (profileByKey.get(scoredPackageKey(a))?.overallGain ?? 0) ||
          b.entry.haScore - a.entry.haScore ||
          (profileByKey.get(scoredPackageKey(a))?.midShift ?? 0) -
            (profileByKey.get(scoredPackageKey(b))?.midShift ?? 0) ||
          b.liftCovered - a.liftCovered ||
          a.entry.rank - b.entry.rank,
      ),
      FLOOR_BOARD_SLOTS,
    ).map(toHint),
  );

  // Floor board keeps weakest→stronger navigation (absolute floor first).
  const floorOptions = collapseRosterHints(
    takeTopCombosWithRosterVariants(
      progressionSafe,
      FLOOR_BOARD_SLOTS,
    ).map(toHint),
    "preserve",
  ).map((hint) => ({
    personality: hint.personality,
    mediaHandling: hint.mediaHandling,
    rank: hint.rank!,
    haScore: hint.haScore!,
    tone: hint.tone!,
    ...(hint.haDelta !== undefined ? { haDelta: hint.haDelta } : {}),
    lifts: hint.lifts ?? [],
    ...(hint.roster !== undefined ? { roster: hint.roster } : {}),
    ...(hint.forRegen !== undefined ? { forRegen: hint.forRegen } : {}),
  }));
  const floor: MentoringFloorBoard = {
    floorHa: floorOptions[0]?.haScore ?? 0,
    ...(current
      ? {
          personality: current.personality,
          mediaHandling: current.mediaHandling,
          rank: current.rank,
          haScore: current.haScore,
          tone: current.tone,
        }
      : subject.personality
        ? {
            personality: subject.personality,
            ...(subject.mediaHandling
              ? { mediaHandling: subject.mediaHandling }
              : {}),
            ...(subject.haScore !== undefined
              ? { haScore: subject.haScore }
              : {}),
          }
        : {}),
    options: floorOptions,
  };

  // Direct match: any close-lane-safe combo in the squad (includes strict-safe).
  const directByKey = new Map(
    closeLane.map((row) => [scoredPackageKey(row), row]),
  );

  const availableRows: ScoredFloorPackage[] = [];
  const availableSeen = new Set<string>();
  const matchRows: { candidate: MentoringCandidate; row: ScoredFloorPackage }[] =
    [];

  for (const candidate of candidates) {
    if (
      subject.age !== undefined &&
      candidate.age !== undefined &&
      candidate.age < subject.age + AGE_GAP
    ) {
      continue;
    }
    const combo = resolveCandidateCombo(candidate);
    if (!combo) continue;
    const forRegen = Boolean(candidate.isRegen);
    const key = `${combo.personality.id}::${shortMediaLabel(combo.media.id)}::${
      forRegen ? "regen" : "real"
    }`;
    const row = directByKey.get(key);
    if (!row) continue;
    if (!availableSeen.has(key)) {
      availableSeen.add(key);
      availableRows.push(row);
    }
    matchRows.push({ candidate, row });
  }

  const available = collapseRosterHints(availableRows.map(toHint));

  const matches: MentoringMatch[] = matchRows
    .map(({ candidate, row }) => {
      const lifts =
        row.liftCovered > 0
          ? liftLabelsForPackage(row.personality, row.media, focus)
          : [];
      return {
        id: candidate.id,
        name: candidate.name,
        kind: "mentor" as const,
        score: Math.round(row.entry.haScore * 10 + row.liftScore),
        ...(candidate.age !== undefined ? { age: candidate.age } : {}),
        traitTones: mentoringBoardTones(candidate),
        reasons: [
          `${row.personality.id} · ${shortMediaLabel(row.media.id)}`,
          ...lifts.map((label) => `Helps ${label}`),
        ].slice(0, 4),
      };
    })
    .sort(
      (a, b) =>
        b.score - a.score ||
        (b.age ?? 0) - (a.age ?? 0) ||
        a.name.localeCompare(b.name),
    )
    .slice(0, MENTORING_SLOTS);

  const floors = mentorScoutFloors(subject);
  const lookFor: MentoringSearchProfile = {
    ...floors,
    packages: closeMatch,
    closeMatch,
    bestPossible,
    available,
  };

  return { floor, lookFor, matches };
}

/** Scout filters + close-match / best-possible package buckets (no save roster). */
export function buildMentorLookForFromFloor(
  subject: MentoringSubject,
  option?: MentoringFloorOption,
  roster: MentorRosterFilter = "mixed",
): MentoringSearchProfile {
  const board = buildUnifiedMentorBoard(
    subject,
    [],
    mentoringFocus(subject),
    roster,
  );
  if (option) {
    const hint = floorOptionToHint(option);
    return {
      ...board.lookFor,
      packages: [hint],
      closeMatch: [hint],
    };
  }
  return board.lookFor;
}

function teachableTraits(subject: MentoringSubject): TraitReading[] {
  return assessTraits(subject)
    .filter((r) => r.tone === "good")
    .sort((a, b) => a.weakness - b.weakness);
}

function toMentorCandidate(subject: MentoringSubject): MentoringCandidate {
  return {
    ...subject,
    id: subject.id ?? "__self__",
    name: subject.name ?? "You",
  };
}

function packageMatchesMentorCombo(
  pkg: MentoringPackageHint,
  mentor: MentoringSubject,
): boolean {
  if (!mentor.personality?.trim()) return false;
  if (pkg.personality !== mentor.personality) return false;
  if (!pkg.mediaHandling || !mentor.mediaHandling?.trim()) return true;
  const combo = resolveCandidateCombo(toMentorCandidate(mentor));
  if (!combo) {
    return pkg.mediaHandling === mentor.mediaHandling;
  }
  return pkg.mediaHandling === shortMediaLabel(combo.media.id);
}

/**
 * Whether mentoring this kid with the subject's combo is a specialize (best)
 * or balance (close) path on the kid's board.
 */
export function menteePathUnderMentor(
  mentee: MentoringSubject,
  mentor: MentoringSubject,
  roster: MentorRosterFilter = "mixed",
): "specialize" | "balance" | null {
  const focus = mentoringFocus(mentee);
  if (focus.length === 0) return null;
  const board = buildUnifiedMentorBoard(mentee, [], focus, roster);
  const best = board.lookFor.bestPossible ?? [];
  const close =
    board.lookFor.closeMatch ?? board.lookFor.packages ?? [];
  if (best.some((pkg) => packageMatchesMentorCombo(pkg, mentor))) {
    return "specialize";
  }
  if (close.some((pkg) => packageMatchesMentorCombo(pkg, mentor))) {
    return "balance";
  }
  // Attr help without a labeled combo — treat as balance (rounding out).
  if (!mentor.personality?.trim()) return "balance";
  return null;
}

export type MentoringPairPath = "specialize" | "balance" | "avoid";

export type MentoringSquadPair = {
  mentor: MentoringCandidate;
  mentee: MentoringCandidate;
  path: MentoringPairPath;
  score: number;
  reasons: string[];
  /** Trait labels this mentor can polish on the mentee. */
  lifts: string[];
};

function joinTraitLabels(labels: readonly string[]): string {
  if (labels.length === 0) return "";
  if (labels.length === 1) return labels[0]!;
  if (labels.length === 2) return `${labels[0]} + ${labels[1]}`;
  return `${labels.slice(0, -1).join(", ")} + ${labels[labels.length - 1]}`;
}

/** Short “why this person” line focused on trait lifts. */
function formatEdgeWhy(
  edge: MentoringSquadPair,
  style: "mentor" | "mentee",
): string {
  const lifts = edge.lifts.length > 0 ? joinTraitLabels(edge.lifts) : "";
  if (style === "mentor") {
    if (lifts) return `${edge.mentor.name} lifts ${lifts}`;
    if (edge.path === "specialize") {
      return `${edge.mentor.name} matches a specialize package`;
    }
    if (edge.path === "balance") {
      return `${edge.mentor.name} helps balance the profile`;
    }
    return `${edge.mentor.name}: ${edge.reasons[0] ?? edge.path}`;
  }
  if (lifts) return `On ${edge.mentee.name}: lifts ${lifts}`;
  if (edge.path === "specialize") {
    return `On ${edge.mentee.name}: specialize package fit`;
  }
  if (edge.path === "balance") {
    return `On ${edge.mentee.name}: helps balance the profile`;
  }
  return `On ${edge.mentee.name}: ${edge.reasons[0] ?? edge.path}`;
}

/**
 * Prefer a few distinct mentor faces over near-duplicate top pairs that
 * reuse the same senior twice.
 */
function takeDiverseGroupSlots(
  sorted: MentoringGroupSuggestion[],
  max: number,
): MentoringGroupSuggestion[] {
  if (sorted.length <= max) return sorted;
  const picked: MentoringGroupSuggestion[] = [];
  const usedMentorIds = new Set<string>();

  for (const group of sorted) {
    if (picked.length >= max) break;
    if (group.mentors.some((m) => usedMentorIds.has(String(m.id)))) continue;
    picked.push(group);
    for (const mentor of group.mentors) usedMentorIds.add(String(mentor.id));
  }
  for (const group of sorted) {
    if (picked.length >= max) break;
    if (picked.includes(group)) continue;
    picked.push(group);
  }
  return picked;
}

function agesAllowMentoring(
  mentor: MentoringSubject,
  mentee: MentoringSubject,
): boolean {
  const mentorAge = mentor.age;
  const menteeAge = mentee.age;
  // If either age is missing, don't age-block — personality/attrs still score the edge.
  if (mentorAge === undefined || menteeAge === undefined) return true;
  if (mentorAge < MENTOR_MIN_AGE) return false;
  if (menteeAge > MENTEE_MAX_AGE) return false;
  if (menteeAge > mentorAge - AGE_GAP) return false;
  return true;
}

/** Young enough to be listed as an influence subject (under 24). */
export function isMentoringInfluenceSubject(
  player: MentoringSubject,
): boolean {
  return player.age !== undefined && player.age < YOUNG_AGE;
}

const MENTORING_TRAIT_ABBR: Record<MentoringTrait, string> = {
  determination: "Det",
  professionalism: "Pro",
  ambition: "Amb",
  loyalty: "Loy",
  sportsmanship: "Spo",
  controversy: "Con",
  pressure: "Pre",
  temperament: "Tem",
};

export type MentoringAttrReading = {
  trait: MentoringTrait;
  label: string;
  abbr: string;
  value: number | undefined;
};

export type MentoringMenteeAttrReading = MentoringAttrReading & {
  /** Mentor-group target mid used for the delta. */
  target: number | undefined;
  /**
   * Signed improvement toward the mentor target (positive = helps the mentee).
   * Controversy uses “lower is better.”
   */
  delta: number | undefined;
};

/** All eight mentoring traits with mids for UI evidence grids. */
export function mentoringAttributeValues(
  player: MentoringSubject,
): MentoringAttrReading[] {
  return MENTORING_DISPLAY_ORDER.map((trait) => ({
    trait,
    label: traitLabel(trait),
    abbr: MENTORING_TRAIT_ABBR[trait],
    value: traitValue(player, trait),
  }));
}

/**
 * Mentee attrs vs the mentoring group’s mentor target (mean of mentors with
 * a value). Delta is the lift toward that target.
 */
export function mentoringMenteeAttributeEvidence(
  mentee: MentoringSubject,
  mentors: readonly MentoringSubject[],
): MentoringMenteeAttrReading[] {
  return mentoringAttributeValues(mentee).map((row) => {
    const mentorValues = mentors
      .map((mentor) => traitValue(mentor, row.trait))
      .filter((v): v is number => v !== undefined && Number.isFinite(v));
    if (mentorValues.length === 0 || row.value === undefined) {
      return { ...row, target: undefined, delta: undefined };
    }
    const target =
      mentorValues.reduce((sum, v) => sum + v, 0) / mentorValues.length;
    const targetRounded = Math.round(target * 10) / 10;
    const raw = liftTowardBetter(row.trait, targetRounded, row.value);
    const delta = Math.round(raw);
    return {
      ...row,
      target: targetRounded,
      delta: delta === 0 ? 0 : delta,
    };
  });
}

function pathAgainstBoard(
  board: {
    lookFor: MentoringSearchProfile;
  },
  mentor: MentoringSubject,
): "specialize" | "balance" | null {
  const best = board.lookFor.bestPossible ?? [];
  const close = board.lookFor.closeMatch ?? board.lookFor.packages ?? [];
  if (best.some((pkg) => packageMatchesMentorCombo(pkg, mentor))) {
    return "specialize";
  }
  if (close.some((pkg) => packageMatchesMentorCombo(pkg, mentor))) {
    return "balance";
  }
  if (!mentor.personality?.trim()) return "balance";
  return null;
}

function aggregateGroupPath(paths: MentoringPairPath[]): MentoringPairPath {
  if (paths.includes("avoid")) return "avoid";
  if (paths.every((p) => p === "specialize")) return "specialize";
  return "balance";
}

function classifyMentorMenteeEdge(
  mentor: MentoringCandidate,
  mentee: MentoringCandidate,
  menteeBoard: { lookFor: MentoringSearchProfile } | null,
  roster: MentorRosterFilter,
  options: MenteeScoreOptions & { relaxDirection?: boolean } = {},
): MentoringSquadPair | null {
  if (mentor.id === mentee.id) return null;
  const relax = Boolean(options.relaxAge || options.relaxProfile);
  if (!relax && !agesAllowMentoring(mentor, mentee)) return null;
  if (
    !options.relaxDirection &&
    !preferredMentorWithoutAges(mentor, mentee)
  ) {
    return null;
  }

  const harm = mentorHarmReasons(mentee, mentor);
  let classified: MentoringPairPath | null = null;
  let score = 0;
  let reasons: string[] = [];
  let lifts: string[] = [];

  const path = menteeBoard
    ? pathAgainstBoard(menteeBoard, mentor)
    : menteePathUnderMentor(mentee, mentor, roster);

  const scoreOpts: MenteeScoreOptions = {
    ...(options.relaxAge ? { relaxAge: true } : {}),
    ...(options.relaxProfile ? { relaxProfile: true } : {}),
  };

  if (path === "specialize") {
    classified = "specialize";
    const basic = scoreMenteeNeedingHelp(mentee, mentor, scoreOpts);
    if (!basic) {
      // Package lane without a HAS-weighted attr win is not a recommendation.
      if (harm.length > 0 && mentor.personality?.trim()) {
        classified = "avoid";
        score = harm.length * 10;
        reasons = harm.slice(0, 4);
        lifts = [];
      } else {
        return null;
      }
    } else {
      score = basic.score;
      reasons = basic.reasons;
      lifts = basic.lifts ?? [];
    }
  } else if (path === "balance") {
    classified = "balance";
    const basic = scoreMenteeNeedingHelp(mentee, mentor, scoreOpts);
    if (!basic) {
      if (harm.length > 0 && mentor.personality?.trim()) {
        classified = "avoid";
        score = harm.length * 10;
        reasons = harm.slice(0, 4);
        lifts = [];
      } else {
        return null;
      }
    } else {
      score = basic.score;
      reasons = basic.reasons;
      lifts = basic.lifts ?? [];
    }
  } else {
    // Mentor combo isn't on the mentee's specialize/balance board, but attributes
    // can still polish them — treat as a balance edge for group composition.
    const basic = scoreMenteeNeedingHelp(mentee, mentor, scoreOpts);
    if (basic) {
      classified = "balance";
      score = basic.score;
      reasons = basic.reasons;
      lifts = basic.lifts ?? [];
    } else if (harm.length > 0 && mentor.personality?.trim()) {
      classified = "avoid";
      score = harm.length * 10;
      reasons = harm.slice(0, 4);
      lifts = [];
    }
  }

  if (!classified) return null;
  return { mentor, mentee, path: classified, score, reasons, lifts };
}

export type MentoringGroupShape = "two_mentors" | "two_mentees";

export type MentoringGroupSuggestion = {
  shape: MentoringGroupShape;
  /** Focal young player the group is built around. */
  subject: MentoringCandidate;
  mentors: MentoringCandidate[];
  /** Always includes `subject`; length 1 (2+1) or 2 (1+2). */
  mentees: MentoringCandidate[];
  path: MentoringPairPath;
  score: number;
  edges: MentoringSquadPair[];
  reasons: string[];
};

/**
 * Mentoring groups of 3 for a focal young player:
 * - two_mentors: 2 mentors → subject
 * - two_mentees: 1 mentor → subject + another young mentee
 *
 * Builds each mentee's package board once, then classifies mentors against it
 * (avoids O(n²) full-roster board rebuilds).
 */
export function findMentoringGroupsForSubject(
  subject: MentoringCandidate,
  players: MentoringCandidate[],
  roster: MentorRosterFilter = "mixed",
  options?: { maxPerShape?: number },
): MentoringGroupSuggestion[] {
  const maxPerShape = options?.maxPerShape ?? MENTORING_GROUP_SLOTS;
  const others = players.filter((p) => p.id !== subject.id);

  const subjectFocus = mentoringFocus(subject);
  const subjectBoard =
    subjectFocus.length > 0
      ? buildUnifiedMentorBoard(subject, [], subjectFocus, roster)
      : null;

  const positiveToSubject: MentoringSquadPair[] = [];
  for (const mentor of others) {
    const edge = classifyMentorMenteeEdge(
      mentor,
      subject,
      subjectBoard,
      roster,
    );
    if (!edge || edge.path === "avoid") continue;
    positiveToSubject.push(edge);
  }
  positiveToSubject.sort((a, b) => b.score - a.score);

  // Cap partner mentees — each needs an expensive package board.
  const youngOthers = others
    .filter(isMentoringInfluenceSubject)
    .sort(
      (a, b) =>
        (a.age ?? 99) - (b.age ?? 99) || a.name.localeCompare(b.name),
    )
    .slice(0, Math.max(6, maxPerShape * 3));
  const boardByMenteeId = new Map<string, { lookFor: MentoringSearchProfile } | null>();
  boardByMenteeId.set(String(subject.id), subjectBoard);
  for (const mentee of youngOthers) {
    const focus = mentoringFocus(mentee);
    boardByMenteeId.set(
      String(mentee.id),
      focus.length > 0
        ? buildUnifiedMentorBoard(mentee, [], focus, roster)
        : null,
    );
  }

  const suggestions: MentoringGroupSuggestion[] = [];

  // 2 mentors → 1 mentee (subject)
  const mentorPool = positiveToSubject.slice(0, Math.max(6, maxPerShape + 2));
  for (let i = 0; i < mentorPool.length; i++) {
    for (let j = i + 1; j < mentorPool.length; j++) {
      const a = mentorPool[i]!;
      const b = mentorPool[j]!;
      const edges = [a, b];
      const path = aggregateGroupPath(edges.map((e) => e.path));
      const score = a.score + b.score;
      suggestions.push({
        shape: "two_mentors",
        subject,
        mentors: [a.mentor, b.mentor],
        mentees: [subject],
        path,
        score,
        edges,
        reasons: [formatEdgeWhy(a, "mentor"), formatEdgeWhy(b, "mentor")],
      });
    }
  }

  // 1 mentor → 2 mentees (subject + another young)
  for (const subjectEdge of mentorPool) {
    const mentor = subjectEdge.mentor;
    const partnerEdges: MentoringSquadPair[] = [];
    for (const other of youngOthers) {
      const edge = classifyMentorMenteeEdge(
        mentor,
        other,
        boardByMenteeId.get(String(other.id)) ?? null,
        roster,
      );
      if (!edge || edge.path === "avoid") continue;
      partnerEdges.push(edge);
    }
    partnerEdges.sort((a, b) => b.score - a.score);
    for (const partner of partnerEdges.slice(0, maxPerShape)) {
      const edges = [subjectEdge, partner];
      const path = aggregateGroupPath(edges.map((e) => e.path));
      const score = subjectEdge.score + partner.score;
      suggestions.push({
        shape: "two_mentees",
        subject,
        mentors: [mentor],
        mentees: [subject, partner.mentee],
        path,
        score,
        edges,
        reasons: [
          formatEdgeWhy(subjectEdge, "mentee"),
          formatEdgeWhy(partner, "mentee"),
        ],
      });
    }
  }

  const byShape = (shape: MentoringGroupShape) =>
    takeDiverseGroupSlots(
      suggestions
        .filter((g) => g.shape === shape)
        .sort(
          (a, b) =>
            pairSortKey(a.path) - pairSortKey(b.path) ||
            b.score - a.score ||
            a.mentors[0]!.name.localeCompare(b.mentors[0]!.name),
        ),
      maxPerShape,
    );

  return [...byShape("two_mentors"), ...byShape("two_mentees")];
}

export type MentoringInfluenceLevel =
  | "none"
  | "light"
  | "average"
  | "significant";

/** Hierarchy proxy seats for a 3-player influence unit. */
export type MentoringInfluenceSeat = "high" | "mid" | "low";

export type MentoringUnitMember = {
  player: MentoringCandidate;
  role: MentoringInfluenceSeat;
};

export type MentoringDirectedEdge = {
  fromId: string;
  toId: string;
  level: MentoringInfluenceLevel;
  pair: MentoringSquadPair | null;
};

export type MentoringSafeGroupShape = "overload" | "cascade";

export type MentoringUnitShape =
  | MentoringGroupShape
  | MentoringSafeGroupShape
  | "custom"
  | "invalid";

export type MentoringUnitEvaluation = {
  members: MentoringUnitMember[];
  shape: MentoringUnitShape;
  path: MentoringPairPath | null;
  score: number;
  edges: MentoringSquadPair[];
  directed: MentoringDirectedEdge[];
  reasons: string[];
  warnings: string[];
};

export type MentoringInfluenceSafeGroup = {
  shape: MentoringSafeGroupShape;
  /** High / Mid / Low seats. */
  members: MentoringUnitMember[];
  /** Primary receiver (Low). */
  subject: MentoringCandidate;
  score: number;
  path: MentoringPairPath;
  edges: MentoringSquadPair[];
  reasons: string[];
};

/** Extra Det emphasis — squad gravitates toward mean Determination. */
const INFLUENCE_DET_WEIGHT_MULT = 2.5;

/** Map edge score / path onto FM-style influence bands. */
export function mentoringInfluenceLevel(
  pair: MentoringSquadPair | null,
): MentoringInfluenceLevel {
  if (!pair || pair.path === "avoid") return "none";
  if (pair.score >= 50) return "significant";
  if (pair.score >= 30) return "average";
  if (pair.score >= 18 || pair.lifts.length > 0) return "light";
  return "none";
}

function influenceTraitWeight(trait: MentoringTrait): number {
  const base = mentoringTraitWeight(trait);
  return trait === "determination" ? base * INFLUENCE_DET_WEIGHT_MULT : base;
}

/** HA-weight tiers for influence-safe edges (primary harm strict, tertiary absorbable). */
type InfluenceTraitTier = "primary" | "secondary" | "tertiary";

function influenceTraitTier(trait: MentoringTrait): InfluenceTraitTier {
  switch (trait) {
    case "determination":
    case "professionalism":
    case "pressure":
    case "controversy":
      return "primary";
    case "loyalty":
    case "sportsmanship":
    case "temperament":
      return "tertiary";
    default:
      return "secondary";
  }
}

/**
 * Hierarchy proxy: Leadership, Determination, age, then HA.
 * Optional Dynamics hierarchy label (user-tagged from FM) adds a seating bias
 * when present — unset labels do not invent influence.
 */
export type MentoringHierarchyLabel =
  | "teamLeader"
  | "highlyInfluential"
  | "influential"
  | "other"
  | "na";

export function mentoringHierarchyBias(
  hierarchy: MentoringHierarchyLabel | null | undefined,
): number {
  switch (hierarchy) {
    case "teamLeader":
      return 90;
    case "highlyInfluential":
      return 60;
    case "influential":
      return 28;
    case "other":
      return 4;
    case "na":
      return 0;
    default:
      return 0;
  }
}

export function mentoringInfluenceScore(
  player: MentoringSubject,
  options?: {
    hierarchy?: MentoringHierarchyLabel | null | undefined;
    /** Seat ranking only — HA must not invert young over senior without manual hierarchy. */
    excludeHa?: boolean;
  },
): number {
  const lead = player.leadership;
  const det = traitValue(player, "determination") ?? player.determination;
  const age = player.age;
  const ha = estimateSubjectHa(player) ?? player.haScore;
  let score = 0;
  if (lead !== undefined && Number.isFinite(lead)) score += lead * 4;
  if (det !== undefined && Number.isFinite(det)) score += det * 3;
  if (age !== undefined && Number.isFinite(age)) score += Math.min(40, age);
  if (!options?.excludeHa && ha !== undefined && Number.isFinite(ha)) {
    score += ha * 2;
  }
  score += mentoringHierarchyBias(options?.hierarchy);
  return score;
}

/** Stable sorted key for a 3-player mentoring unit (persist / reject memory). */
export function mentoringGroupMemberKey(
  memberIds: readonly string[],
): string {
  return [...memberIds].map(String).sort().join("|");
}

export function mentoringInfluenceEdgeKey(
  fromId: string,
  toId: string,
): string {
  return `${fromId}>${toId}`;
}

/** FM influence bands that may paint HA matrix marks. `none` never paints. */
export type MentoringDisplayBand = Exclude<MentoringInfluenceLevel, "none">;

export type MentoringMoveTone = "good" | "bad";

export type MentoringMatrixPlusItem = {
  delta: number;
  label: string;
  band: MentoringDisplayBand;
  tone: MentoringMoveTone;
};

export type MentoringMatrixArrowItem = {
  dir: "up" | "down";
  band: MentoringDisplayBand;
  tone: MentoringMoveTone;
};

export type MentoringMatrixCellMarks =
  | { kind: "plus"; items: MentoringMatrixPlusItem[] }
  | { kind: "arrow"; items: MentoringMatrixArrowItem[] };

const MENTORING_MATRIX_GAP = 0.05;

/** Numeric influencer − mentee. CON is not inverted. Equal if abs < gap. */
export function mentoringNumericTraitDelta(
  influencerValue: number,
  menteeValue: number,
): number {
  return influencerValue - menteeValue;
}

/** Mentee number will move: lower than influencer → up; higher → down. */
function mentoringNumericMoveDir(
  menteeValue: number,
  influencerValue: number,
): "up" | "down" | null {
  const delta = mentoringNumericTraitDelta(influencerValue, menteeValue);
  if (Math.abs(delta) < MENTORING_MATRIX_GAP) return null;
  return delta > 0 ? "up" : "down";
}

/** Arrow color: green towards a better value. CON inverts (down is good). */
export function mentoringAttrMoveTone(
  trait: string,
  dir: "up" | "down",
): MentoringMoveTone {
  const improving = trait === "controversy" ? dir === "down" : dir === "up";
  return improving ? "good" : "bad";
}

/** Delta color: + green, − red. CON inverts (lower is better, so − is green). */
export function mentoringDeltaSignTone(
  trait: string,
  delta: number,
): MentoringMoveTone {
  const improving = trait === "controversy" ? delta < 0 : delta > 0;
  return improving ? "good" : "bad";
}

function readMentoringInfluenceEdge(
  fromId: string,
  toId: string,
  edges?: Readonly<Record<string, MentoringInfluenceLevel>> | null,
): MentoringInfluenceLevel | undefined {
  if (!edges) return undefined;
  return edges[mentoringInfluenceEdgeKey(String(fromId), String(toId))];
}

/**
 * Matrix display only: labeled non-none edges. Unlabeled and `none` → no marks.
 * Does not fall back to the attr-score proxy.
 */
export function mentoringLabeledDisplayInfluence(
  fromId: string | number,
  toId: string | number,
  edges?: Readonly<Record<string, MentoringInfluenceLevel>> | null,
): MentoringDisplayBand | null {
  const level = readMentoringInfluenceEdge(String(fromId), String(toId), edges);
  if (level === "light" || level === "average" || level === "significant") {
    return level;
  }
  return null;
}

/** Signed mentor-better gap. Controversy inverted. Not weighted by influence band. */
export function mentoringUnweightedTraitDelta(
  trait: string,
  mentorValue: number,
  menteeValue: number,
): number {
  return trait === "controversy"
    ? menteeValue - mentorValue
    : mentorValue - menteeValue;
}

export type MentoringMatrixPlayerValue = {
  id: string;
  name: string;
  value: number | undefined;
};

/**
 * HA matrix marks from labeled edges only. Receivers: stacked arrows in
 * numeric attr direction vs each influencer. Influencers: numeric ±
 * (influencer − mentee) vs each receiver they influence.
 */
export function planMentoringMatrixCellMarks(input: {
  role: MentoringInfluenceSeat;
  playerId: string;
  trait: string;
  value: number | undefined;
  influencers: readonly MentoringMatrixPlayerValue[];
  receivers: readonly MentoringMatrixPlayerValue[];
  edges?: Readonly<Record<string, MentoringInfluenceLevel>> | null;
}): MentoringMatrixCellMarks | undefined {
  const { role, playerId, trait, value, influencers, receivers, edges } = input;
  if (value === undefined || !Number.isFinite(value)) return undefined;

  if (role !== "low") {
    const items: MentoringMatrixPlusItem[] = [];
    for (const receiver of receivers) {
      const band = mentoringLabeledDisplayInfluence(playerId, receiver.id, edges);
      if (!band) continue;
      if (receiver.value === undefined || !Number.isFinite(receiver.value)) {
        continue;
      }
      const delta = mentoringNumericTraitDelta(value, receiver.value);
      if (Math.abs(delta) < MENTORING_MATRIX_GAP) continue;
      items.push({
        delta,
        label: receiver.name,
        band,
        tone: mentoringDeltaSignTone(trait, delta),
      });
    }
    return items.length > 0 ? { kind: "plus", items } : undefined;
  }

  const items: MentoringMatrixArrowItem[] = [];
  for (const influencer of influencers) {
    const band = mentoringLabeledDisplayInfluence(
      influencer.id,
      playerId,
      edges,
    );
    if (!band) continue;
    if (influencer.value === undefined || !Number.isFinite(influencer.value)) {
      continue;
    }
    const dir = mentoringNumericMoveDir(value, influencer.value);
    if (!dir) continue;
    items.push({ dir, band, tone: mentoringAttrMoveTone(trait, dir) });
  }
  return items.length > 0 ? { kind: "arrow", items } : undefined;
}

export function mentoringChevronCount(
  band: MentoringDisplayBand | null | undefined,
): 0 | 1 | 2 | 3 {
  if (band === "light") return 1;
  if (band === "average") return 2;
  if (band === "significant") return 3;
  return 0;
}

export type MentoringSeatPeerMark = {
  peerId: string;
  /** This seat → peer. `null` = none or unlabeled. */
  outgoing: MentoringDisplayBand | null;
};

/** Other two members: outgoing = this exerts (▲ only). Incoming is on their row. */
export function planMentoringSeatPeerMarks(input: {
  playerId: string;
  peers: readonly { id: string; role: MentoringInfluenceSeat }[];
  edges?: Readonly<Record<string, MentoringInfluenceLevel>> | null;
}): MentoringSeatPeerMark[] {
  const others = (["high", "mid", "low"] as const)
    .map((role) => input.peers.find((peer) => peer.role === role))
    .filter((peer): peer is { id: string; role: MentoringInfluenceSeat } =>
      Boolean(peer && peer.id !== input.playerId),
    )
    .slice(0, 2);

  return others.map((peer) => ({
    peerId: peer.id,
    outgoing: mentoringLabeledDisplayInfluence(
      input.playerId,
      peer.id,
      input.edges,
    ),
  }));
}

export type MentoringPairSideMarks = {
  receive?: {
    dir: "up" | "down";
    band: MentoringDisplayBand;
    count: 1 | 2 | 3;
    tone: MentoringMoveTone;
  };
  exert?: { delta: number; band: MentoringDisplayBand; tone: MentoringMoveTone };
};

/**
 * Pair hover only (this seat + one peer). Receiver → stacked arrows in
 * numeric attr direction. Exerter → numeric ±. Mutual → both.
 * Equal / unlabeled → no marks. Third member never included.
 */
export function planMentoringPairTraitMarks(input: {
  subjectId: string;
  peerId: string;
  trait: string;
  subjectValue: number | undefined;
  peerValue: number | undefined;
  edges?: Readonly<Record<string, MentoringInfluenceLevel>> | null;
}): { subject: MentoringPairSideMarks; peer: MentoringPairSideMarks } {
  const subject: MentoringPairSideMarks = {};
  const peer: MentoringPairSideMarks = {};
  const outgoing = mentoringLabeledDisplayInfluence(
    input.subjectId,
    input.peerId,
    input.edges,
  );
  const incoming = mentoringLabeledDisplayInfluence(
    input.peerId,
    input.subjectId,
    input.edges,
  );
  const subjectOk =
    input.subjectValue !== undefined && Number.isFinite(input.subjectValue);
  const peerOk =
    input.peerValue !== undefined && Number.isFinite(input.peerValue);
  const bothOk = subjectOk && peerOk;

  if (outgoing && bothOk) {
    const dir = mentoringNumericMoveDir(
      input.peerValue as number,
      input.subjectValue as number,
    );
    if (dir) {
      const delta = mentoringNumericTraitDelta(
        input.subjectValue as number,
        input.peerValue as number,
      );
      peer.receive = {
        dir,
        band: outgoing,
        count: mentoringChevronCount(outgoing) as 1 | 2 | 3,
        tone: mentoringAttrMoveTone(input.trait, dir),
      };
      subject.exert = {
        delta,
        band: outgoing,
        tone: mentoringDeltaSignTone(input.trait, delta),
      };
    }
  }
  if (incoming && bothOk) {
    const dir = mentoringNumericMoveDir(
      input.subjectValue as number,
      input.peerValue as number,
    );
    if (dir) {
      const delta = mentoringNumericTraitDelta(
        input.peerValue as number,
        input.subjectValue as number,
      );
      subject.receive = {
        dir,
        band: incoming,
        count: mentoringChevronCount(incoming) as 1 | 2 | 3,
        tone: mentoringAttrMoveTone(input.trait, dir),
      };
      peer.exert = {
        delta,
        band: incoming,
        tone: mentoringDeltaSignTone(input.trait, delta),
      };
    }
  }
  return { subject, peer };
}

function hierarchyAllowsYoungAbove(
  hierarchy: MentoringHierarchyLabel | null | undefined,
): boolean {
  return hierarchy === "teamLeader" || hierarchy === "highlyInfluential";
}

function influenceLevelRank(level: MentoringInfluenceLevel): number {
  switch (level) {
    case "significant":
      return 3;
    case "average":
      return 2;
    case "light":
      return 1;
    default:
      return 0;
  }
}

/** High-influence first; HA cannot seat a youngling above a senior without manual hierarchy. */
function compareMentoringInfluenceSeating(
  a: MentoringCandidate,
  b: MentoringCandidate,
  hierarchyById?: ReadonlyMap<
    string,
    MentoringHierarchyLabel | null | undefined
  >,
): number {
  const hierarchyOf = (player: MentoringCandidate) =>
    hierarchyById?.get(String(player.id));
  const scoreOf = (player: MentoringCandidate, excludeHa = false) =>
    mentoringInfluenceScore(player, {
      hierarchy: hierarchyOf(player) ?? null,
      excludeHa,
    });

  let scoreA = scoreOf(a);
  let scoreB = scoreOf(b);
  const youngA = isMentoringInfluenceSubject(a);
  const youngB = isMentoringInfluenceSubject(b);

  if (youngA && !youngB && !hierarchyAllowsYoungAbove(hierarchyOf(a))) {
    const noHa = scoreOf(a, true);
    if (scoreA > scoreB && noHa <= scoreB) scoreA = noHa;
  }
  if (youngB && !youngA && !hierarchyAllowsYoungAbove(hierarchyOf(b))) {
    const noHa = scoreOf(b, true);
    if (scoreB > scoreA && noHa <= scoreA) scoreB = noHa;
  }

  const diff = scoreB - scoreA;
  if (Math.abs(diff) > 1e-9) return diff;
  return a.name.localeCompare(b.name);
}

/** Rank players highest-influence first. */
export function rankMentoringInfluence<T extends MentoringCandidate>(
  players: readonly T[],
  options?: {
    hierarchyById?: ReadonlyMap<string, MentoringHierarchyLabel | null | undefined>;
  },
): T[] {
  return [...players].sort((a, b) =>
    compareMentoringInfluenceSeating(a, b, options?.hierarchyById),
  );
}

/**
 * Resolve FM-style influence on a directed pair: manual label wins, else attr score.
 */
export function resolveMentoringInfluenceLevel(
  from: MentoringCandidate,
  to: MentoringCandidate,
  manualEdges?: ReadonlyMap<string, MentoringInfluenceLevel>,
): MentoringInfluenceLevel {
  const key = mentoringInfluenceEdgeKey(String(from.id), String(to.id));
  if (manualEdges?.has(key)) return manualEdges.get(key)!;
  const safe = scoreSafeInfluence(from, to);
  if (!safe) return "none";
  return mentoringInfluenceLevel(safeEdgeToPair(safe));
}

/** Young with better HA seated above a worse-HA senior without manual hierarchy override. */
export function violatesHaInfluenceSeating(
  members: readonly MentoringUnitMember[],
  hierarchyById?: ReadonlyMap<
    string,
    MentoringHierarchyLabel | null | undefined
  >,
): boolean {
  const seatRank: Record<MentoringInfluenceSeat, number> = {
    high: 0,
    mid: 1,
    low: 2,
  };
  const ordered = [...members].sort(
    (a, b) => seatRank[a.role] - seatRank[b.role],
  );

  for (let i = 0; i < ordered.length; i++) {
    for (let j = i + 1; j < ordered.length; j++) {
      const upper = ordered[i]!.player;
      const lower = ordered[j]!.player;
      if (!isMentoringInfluenceSubject(upper)) continue;
      if (isMentoringInfluenceSubject(lower)) continue;
      if (hierarchyAllowsYoungAbove(hierarchyById?.get(String(upper.id)))) {
        continue;
      }
      const upperHa = estimateSubjectHa(upper) ?? upper.haScore;
      const lowerHa = estimateSubjectHa(lower) ?? lower.haScore;
      if (
        upperHa !== undefined &&
        lowerHa !== undefined &&
        upperHa > lowerHa + 0.5
      ) {
        return true;
      }
    }
  }
  return false;
}

function lowWouldHarmSenior(
  low: MentoringCandidate,
  senior: MentoringCandidate,
  hierarchyById?: ReadonlyMap<
    string,
    MentoringHierarchyLabel | null | undefined
  >,
): boolean {
  const lowScore = mentoringInfluenceScore(low, {
    hierarchy: hierarchyById?.get(String(low.id)) ?? null,
  });
  const seniorScore = mentoringInfluenceScore(senior, {
    hierarchy: hierarchyById?.get(String(senior.id)) ?? null,
  });
  // Weak Low seats cannot drag seniors — only check when Low is influence-competitive.
  if (lowScore + 8 < seniorScore) return false;

  const edge = scoreSafeInfluence(low, senior);
  if (edge !== null) return false;

  const reasons = mentorHarmReasons(senior, low);
  return reasons.some((reason) =>
    /lowers determination|lowers professionalism|lowers pressure|toxic/i.test(
      reason,
    ),
  );
}

/** High→Low and Mid→Low are both none (manual or attr-scored). */
export function isMentoringZeroInfluenceGroup(
  members: readonly MentoringUnitMember[],
  manualEdges?: ReadonlyMap<string, MentoringInfluenceLevel>,
): boolean {
  const high = members.find((m) => m.role === "high")?.player;
  const mid = members.find((m) => m.role === "mid")?.player;
  const low = members.find((m) => m.role === "low")?.player;
  if (!high || !mid || !low) return false;
  const highLow = resolveMentoringInfluenceLevel(high, low, manualEdges);
  const midLow = resolveMentoringInfluenceLevel(mid, low, manualEdges);
  return highLow === "none" && midLow === "none";
}

/** True when the user labeled High→Low or Mid→Low as FM `none`. */
export function mentoringRolesHaveLabeledDownwardNone(
  roles: Readonly<Record<string, MentoringInfluenceSeat>>,
  edges?: Readonly<Record<string, MentoringInfluenceLevel>>,
): boolean {
  if (!edges) return false;
  let high: string | undefined;
  let mid: string | undefined;
  let low: string | undefined;
  for (const [id, role] of Object.entries(roles)) {
    if (role === "high") high = id;
    else if (role === "mid") mid = id;
    else if (role === "low") low = id;
  }
  if (!high || !mid || !low) return false;
  return (
    edges[mentoringInfluenceEdgeKey(high, low)] === "none" ||
    edges[mentoringInfluenceEdgeKey(mid, low)] === "none"
  );
}

export function mentoringUnitHasLabeledDownwardNone(
  members: readonly MentoringUnitMember[],
  manualEdges?: ReadonlyMap<string, MentoringInfluenceLevel>,
): boolean {
  const high = members.find((m) => m.role === "high")?.player;
  const mid = members.find((m) => m.role === "mid")?.player;
  const low = members.find((m) => m.role === "low")?.player;
  if (!high || !mid || !low || !manualEdges) return false;
  return (
    manualEdges.get(mentoringInfluenceEdgeKey(String(high.id), String(low.id))) ===
      "none" ||
    manualEdges.get(mentoringInfluenceEdgeKey(String(mid.id), String(low.id))) ===
      "none"
  );
}

export type MentoringMenteeSkipReason =
  | "already elite HA"
  | "no safe senior"
  | "no unused influence path"
  | "incomplete attrs"
  | "Det above squad mean";

export type MentoringMenteeCoverageRow = {
  id: string;
  name: string;
  seated: boolean;
  skipReason?: MentoringMenteeSkipReason;
  ca?: number;
  pa?: number;
};

/** Glance state for the young-pool face strip. Skip reason → skipped, else free. */
export type MentoringMenteeFaceState = "seated" | "free" | "skipped";

export function mentoringMenteeFaceState(
  row: Pick<MentoringMenteeCoverageRow, "seated" | "skipReason">,
): MentoringMenteeFaceState {
  if (row.seated) return "seated";
  if (row.skipReason) return "skipped";
  return "free";
}

export type MentoringMenteeCoverageOptions = {
  seatedIds: ReadonlySet<string>;
  occupiedIds?: ReadonlySet<string>;
  incompleteYoung?: readonly {
    id: string;
    name: string;
    ca?: number | null;
    pa?: number | null;
  }[];
  hierarchyById?: ReadonlyMap<
    string,
    MentoringHierarchyLabel | null | undefined
  >;
  manualInfluenceEdges?: ReadonlyMap<string, MentoringInfluenceLevel>;
  rejectedGroupKeys?: ReadonlySet<string>;
};

export type MentoringReplacementResult =
  | { ok: true; group: MentoringInfluenceSafeGroup }
  | { ok: false; skipReason: MentoringMenteeSkipReason };

function mentoringLowSeatId(
  members: readonly MentoringUnitMember[],
): string | undefined {
  const low = members.find((m) => m.role === "low")?.player;
  return low ? String(low.id) : undefined;
}

/** Extract CA/PA 1–200 only. Missing / junk → undefined (do not invent). */
export function mentoringKnownAbility(value: unknown): number | undefined {
  if (typeof value !== "number" || !Number.isFinite(value)) return undefined;
  if (value < 1 || value > 200) return undefined;
  return value;
}

export function formatMentoringCaPa(
  ca?: number | null,
  pa?: number | null,
): string {
  const shown = (raw: number | null | undefined) => {
    const n = mentoringKnownAbility(raw);
    return n !== undefined ? String(Math.round(n)) : "—";
  };
  return `${shown(ca)}/${shown(pa)}`;
}

/** Low-seat face digits. Missing / junk → omit (no dash placeholders). */
export function mentoringCaPaFaceDigits(
  ca?: number | null,
  pa?: number | null,
): { ca?: number; pa?: number } | null {
  const knownCa = mentoringKnownAbility(ca);
  const knownPa = mentoringKnownAbility(pa);
  if (knownCa === undefined && knownPa === undefined) return null;
  return {
    ...(knownCa !== undefined ? { ca: knownCa } : {}),
    ...(knownPa !== undefined ? { pa: knownPa } : {}),
  };
}

function coverageAbilityFields(src: {
  ca?: number | null;
  pa?: number | null;
}): { ca?: number; pa?: number } {
  const ca = mentoringKnownAbility(src.ca);
  const pa = mentoringKnownAbility(src.pa);
  return {
    ...(ca !== undefined ? { ca } : {}),
    ...(pa !== undefined ? { pa } : {}),
  };
}

function mentoringLowSeatKnownPa(
  group: MentoringInfluenceSafeGroup,
): number | undefined {
  const low =
    group.members.find((m) => m.role === "low")?.player ?? group.subject;
  return mentoringKnownAbility(low.pa);
}

function mentoringCandidateHa(player: MentoringCandidate): number | undefined {
  return estimateSubjectHa(player) ?? player.haScore;
}

function mentoringIsEligibleSenior(
  player: MentoringCandidate,
  kidId: string,
): boolean {
  if (String(player.id) === kidId) return false;
  if (!isMentoringInfluenceSubject(player)) return true;
  return player.age !== undefined && player.age >= MENTOR_MIN_AGE;
}

function mentoringHasSafeSenior(
  kid: MentoringCandidate,
  players: readonly MentoringCandidate[],
  edges?: ReadonlyMap<string, MentoringInfluenceLevel>,
): boolean {
  const kidId = String(kid.id);
  for (const player of players) {
    if (!mentoringIsEligibleSenior(player, kidId)) continue;
    if (resolveMentoringInfluenceLevel(player, kid, edges) !== "none") {
      return true;
    }
  }
  return false;
}

function mentoringYounglingDetEligible(
  player: MentoringCandidate,
  meanDet: number | undefined,
): boolean {
  const det = traitValue(player, "determination");
  return meanDet === undefined || det === undefined || det <= meanDet + 0.5;
}

function mentoringSkipReasonForUnseated(
  kid: MentoringCandidate,
  options: {
    players: readonly MentoringCandidate[];
    unusedGroupsForKid: number;
    meanDet?: number | undefined;
    manualInfluenceEdges?:
      | ReadonlyMap<string, MentoringInfluenceLevel>
      | undefined;
  },
): MentoringMenteeSkipReason | undefined {
  const ha = mentoringCandidateHa(kid);
  if (ha !== undefined && Number.isFinite(ha) && ha > MENTEE_HA_ELITE) {
    return "already elite HA";
  }
  if (
    !mentoringHasSafeSenior(kid, options.players, options.manualInfluenceEdges)
  ) {
    return "no safe senior";
  }
  if (!mentoringYounglingDetEligible(kid, options.meanDet)) {
    return "Det above squad mean";
  }
  if (options.unusedGroupsForKid <= 0) return "no unused influence path";
  return undefined;
}

export type MentoringSuggestConstraints = {
  hierarchyById?: ReadonlyMap<
    string,
    MentoringHierarchyLabel | null | undefined
  >;
  manualInfluenceEdges?: ReadonlyMap<string, MentoringInfluenceLevel>;
  rejectedGroupKeys?: ReadonlySet<string>;
};

/** Gate for Suggest: influence shape, HA seating, zero-influence, Low harming seniors. */
export function passesMentoringSuggestGate(
  group: MentoringInfluenceSafeGroup,
  constraints?: MentoringSuggestConstraints,
): boolean {
  const memberIds = group.members.map((m) => String(m.player.id));
  const key = mentoringGroupMemberKey(memberIds);
  if (constraints?.rejectedGroupKeys?.has(key)) return false;
  if (violatesHaInfluenceSeating(group.members, constraints?.hierarchyById)) {
    return false;
  }

  const high = group.members.find((m) => m.role === "high")!.player;
  const mid = group.members.find((m) => m.role === "mid")!.player;
  const low = group.members.find((m) => m.role === "low")!.player;
  const edges = constraints?.manualInfluenceEdges;

  const highLowKey = mentoringInfluenceEdgeKey(String(high.id), String(low.id));
  const midLowKey = mentoringInfluenceEdgeKey(String(mid.id), String(low.id));
  const highLowManual = edges?.has(highLowKey) ?? false;
  const midLowManual = edges?.has(midLowKey) ?? false;

  if (edges?.get(highLowKey) === "none" || edges?.get(midLowKey) === "none") {
    return false;
  }

  const highLow = resolveMentoringInfluenceLevel(high, low, edges);
  const midLow = resolveMentoringInfluenceLevel(mid, low, edges);

  if (highLow === "none" && midLow === "none") return false;

  if (!highLowManual && influenceLevelRank(highLow) < 1) return false;
  if (!midLowManual && influenceLevelRank(midLow) < 1) return false;

  if (
    lowWouldHarmSenior(low, high, constraints?.hierarchyById) ||
    lowWouldHarmSenior(low, mid, constraints?.hierarchyById)
  ) {
    return false;
  }

  return true;
}

export type SafeInfluenceEdge = {
  influencer: MentoringCandidate;
  receiver: MentoringCandidate;
  score: number;
  lifts: string[];
  reasons: string[];
  /** True when Det would be pulled down toward the influencer. */
  detHarm: boolean;
  weightedLift: number;
  weightedHarm: number;
};

/**
 * Strict influence edge for suggestions: Det cannot fall; primary-tier harm
 * (Det/Pro/Pre/Con) must stay net-positive. Tertiary drag (Loy/Spo/Tem) may be
 * absorbed when primary lifts are strong enough.
 */
export function scoreSafeInfluence(
  influencer: MentoringCandidate,
  receiver: MentoringCandidate,
): SafeInfluenceEdge | null {
  if (influencer.id === receiver.id) return null;

  let weightedLift = 0;
  let weightedHarm = 0;
  let primaryLift = 0;
  let primaryHarm = 0;
  let secondaryLift = 0;
  let secondaryHarm = 0;
  let tertiaryLift = 0;
  let tertiaryHarm = 0;
  const lifts: MentoringTrait[] = [];
  let detHarm = false;

  for (const trait of MENTORING_TRAITS) {
    const recv = traitValue(receiver, trait);
    const infl = traitValue(influencer, trait);
    if (recv === undefined || infl === undefined) continue;

    const weight = influenceTraitWeight(trait);
    const tier = influenceTraitTier(trait);
    const lift = liftTowardBetter(trait, infl, recv);

    if (trait === "determination" && lift <= -1) {
      detHarm = true;
    }

    if (lift >= 1) {
      const tone = traitTone(trait, infl);
      if (tone === "bad") {
        weightedHarm += lift * weight;
        if (tier === "primary") primaryHarm += lift * weight;
        else if (tier === "tertiary") tertiaryHarm += lift * weight;
        else secondaryHarm += lift * weight;
      } else {
        weightedLift += lift * weight;
        if (tier === "primary") primaryLift += lift * weight;
        else if (tier === "tertiary") tertiaryLift += lift * weight;
        else secondaryLift += lift * weight;
        if (lift >= 2) lifts.push(trait);
      }
    } else if (lift <= -1) {
      const harm = -lift * weight;
      weightedHarm += harm;
      if (tier === "primary") primaryHarm += harm;
      else if (tier === "tertiary") tertiaryHarm += harm;
      else secondaryHarm += harm;
    }
  }

  if (detHarm) return null;

  const HARM_MULT = 1.35;
  const primaryNet = primaryLift - primaryHarm * HARM_MULT;
  if (primaryNet < 0) return null;
  if (primaryHarm > 0 && primaryLift === 0) return null;

  const primaryLiftTraits = lifts.filter((t) => influenceTraitTier(t) === "primary");
  let effectiveTertiaryHarm = tertiaryHarm;
  if (primaryLiftTraits.length > 0) {
    if (primaryNet >= 8) {
      effectiveTertiaryHarm = tertiaryHarm * 0.12;
    } else if (primaryNet >= 4) {
      effectiveTertiaryHarm = tertiaryHarm * 0.35;
    } else if (primaryNet >= 0) {
      effectiveTertiaryHarm = tertiaryHarm * 0.6;
    }
  }

  const secondaryNet = secondaryLift - secondaryHarm * HARM_MULT;
  const tertiaryNet = tertiaryLift - effectiveTertiaryHarm * HARM_MULT;
  const net = primaryNet + secondaryNet + tertiaryNet;

  if (net < 3 && lifts.length === 0) return null;
  if (net < -2) return null;
  if (primaryHarm > 0 && primaryNet < 3) return null;

  const score = Math.round(net * 2 + lifts.length * 3);
  if (score < 6) return null;

  return {
    influencer,
    receiver,
    score,
    lifts: labelsForDisplay(lifts),
    reasons: labelsForDisplay(lifts).map((label) => `lifts ${label}`).slice(0, 4),
    detHarm: false,
    weightedLift,
    weightedHarm,
  };
}

/** Peer edge between two seniors: cheap Det / drag checks only (no boards). */
function peerInfluenceSafe(
  a: MentoringCandidate,
  b: MentoringCandidate,
): boolean {
  const detA = traitValue(a, "determination");
  const detB = traitValue(b, "determination");
  if (detA !== undefined && detB !== undefined) {
    const scoreA = mentoringInfluenceScore(a);
    const scoreB = mentoringInfluenceScore(b);
    // Higher-influence peer must not sit meaningfully below on Det.
    if (scoreA >= scoreB && detA + 1 < detB) return false;
    if (scoreB >= scoreA && detB + 1 < detA) return false;
  }
  // Quick protected-attr drag: if either lowers 2+ good attrs on the other, reject.
  let harmAb = 0;
  let harmBa = 0;
  for (const trait of MENTORING_TRAITS) {
    const va = traitValue(a, trait);
    const vb = traitValue(b, trait);
    if (va === undefined || vb === undefined) continue;
    if (trait === "controversy") {
      if (va > vb + 1) harmAb += 1;
      if (vb > va + 1) harmBa += 1;
      continue;
    }
    if (va + 1 < vb && traitTone(trait, vb) === "good") harmAb += 1;
    if (vb + 1 < va && traitTone(trait, va) === "good") harmBa += 1;
  }
  if (harmAb >= 2 || harmBa >= 2) return false;
  return true;
}

function safeEdgeToPair(edge: SafeInfluenceEdge): MentoringSquadPair {
  return {
    mentor: edge.influencer,
    mentee: edge.receiver,
    path: "balance",
    score: edge.score,
    reasons: edge.reasons,
    lifts: edge.lifts,
  };
}

function edgeCacheKey(fromId: string, toId: string): string {
  return `${fromId}>${toId}`;
}

/**
 * Seat three players High / Mid / Low by influence rank.
 */
export function defaultMentoringUnitRoles(
  players: readonly MentoringCandidate[],
  options?: {
    hierarchyById?: ReadonlyMap<string, MentoringHierarchyLabel | null | undefined>;
  },
): MentoringUnitMember[] {
  const ranked = [...players].sort((a, b) =>
    compareMentoringInfluenceSeating(a, b, options?.hierarchyById),
  );
  if (ranked.length === 0) return [];
  if (ranked.length === 1) {
    return [{ player: ranked[0]!, role: "high" }];
  }
  if (ranked.length === 2) {
    return [
      { player: ranked[0]!, role: "high" },
      { player: ranked[1]!, role: "low" },
    ];
  }
  return [
    { player: ranked[0]!, role: "high" },
    { player: ranked[1]!, role: "mid" },
    { player: ranked[2]!, role: "low" },
  ];
}

function squadMeanDetermination(
  players: readonly MentoringCandidate[],
): number | undefined {
  const values = players
    .map((p) => traitValue(p, "determination"))
    .filter((v): v is number => v !== undefined && Number.isFinite(v));
  if (values.length === 0) return undefined;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

/**
 * Influence-safe mentoring groups only:
 * - overload: 2 strong seniors → 1 weaker youngling (peer seniors not harmful)
 * - cascade: High→Mid, High→Low, Mid→Low all safe (no mid-drags-better-kid)
 *
 * Hot path: attr edges only (memoized). No personality package boards —
 * those made Suggest unusably slow.
 */
export function findInfluenceSafeMentoringGroups(
  players: MentoringCandidate[],
  options?: {
    max?: number;
    roster?: MentorRosterFilter;
    hierarchyById?: ReadonlyMap<string, MentoringHierarchyLabel | null | undefined>;
    manualInfluenceEdges?: ReadonlyMap<string, MentoringInfluenceLevel>;
    rejectedGroupKeys?: ReadonlySet<string>;
  },
): MentoringInfluenceSafeGroup[] {
  const max = options?.max ?? 12;
  if (players.length < 3) return [];

  const hierarchyById = options?.hierarchyById;
  const suggestConstraints: MentoringSuggestConstraints = {
    ...(hierarchyById ? { hierarchyById } : {}),
    ...(options?.manualInfluenceEdges
      ? { manualInfluenceEdges: options.manualInfluenceEdges }
      : {}),
    ...(options?.rejectedGroupKeys
      ? { rejectedGroupKeys: options.rejectedGroupKeys }
      : {}),
  };
  const meanDet = squadMeanDetermination(players);
  const ranked = rankMentoringInfluence(
    players,
    hierarchyById ? { hierarchyById } : undefined,
  );
  const influenceOf = new Map(
    ranked.map((p) => [
      String(p.id),
      mentoringInfluenceScore(p, {
        hierarchy: hierarchyById?.get(String(p.id)) ?? null,
      }),
    ]),
  );

  const younglings = ranked
    .filter(
      (p) =>
        isMentoringInfluenceSubject(p) &&
        mentoringYounglingDetEligible(p, meanDet),
    )
    .slice(0, 10);

  const seniors = ranked
    .filter(
      (p) =>
        !isMentoringInfluenceSubject(p) ||
        (p.age !== undefined && p.age >= MENTOR_MIN_AGE),
    )
    .slice(0, 12);

  const edgeMemo = new Map<string, SafeInfluenceEdge | null>();
  const safeEdge = (
    from: MentoringCandidate,
    to: MentoringCandidate,
  ): SafeInfluenceEdge | null => {
    const key = edgeCacheKey(String(from.id), String(to.id));
    if (edgeMemo.has(key)) return edgeMemo.get(key)!;
    const edge = scoreSafeInfluence(from, to);
    edgeMemo.set(key, edge);
    return edge;
  };

  const seen = new Set<string>();
  const out: MentoringInfluenceSafeGroup[] = [];

  const pushGroup = (group: MentoringInfluenceSafeGroup) => {
    if (!passesMentoringSuggestGate(group, suggestConstraints)) return false;
    const key = group.members
      .map((m) => String(m.player.id))
      .sort()
      .join("|");
    if (seen.has(key)) return false;
    seen.add(key);
    out.push(group);
    return true;
  };

  const orderTrio = (
    a: MentoringCandidate,
    b: MentoringCandidate,
    c: MentoringCandidate,
  ): [MentoringCandidate, MentoringCandidate, MentoringCandidate] => {
    const trio = [a, b, c].sort((x, y) =>
      compareMentoringInfluenceSeating(x, y, hierarchyById),
    );
    return [trio[0]!, trio[1]!, trio[2]!];
  };

  const overloadShapeBonus = (
    seniorA: MentoringCandidate,
    seniorB: MentoringCandidate,
    young: MentoringCandidate,
  ): number => {
    const youngHa = estimateSubjectHa(young) ?? young.haScore ?? 0;
    const youngInf = influenceOf.get(String(young.id)) ?? 0;
    let bonus = 0;
    for (const senior of [seniorA, seniorB]) {
      const sHa = estimateSubjectHa(senior) ?? senior.haScore ?? 0;
      const sInf = influenceOf.get(String(senior.id)) ?? 0;
      if (sHa > youngHa + 0.5 && sInf > youngInf) bonus += 6;
    }
    return bonus;
  };

  // --- Overload: 2 seniors → 1 youngling ---
  for (const young of younglings) {
    if (out.length >= max) break;
    const youngScore = influenceOf.get(String(young.id)) ?? 0;
    const safeSeniors: { senior: MentoringCandidate; edge: SafeInfluenceEdge }[] =
      [];
    for (const senior of seniors) {
      if (senior.id === young.id) continue;
      if ((influenceOf.get(String(senior.id)) ?? 0) <= youngScore) continue;
      const edge = safeEdge(senior, young);
      if (!edge) continue;
      safeSeniors.push({ senior, edge });
    }
    safeSeniors.sort((a, b) => b.edge.score - a.edge.score);
    // Cap pairs: top 8 seniors → at most C(8,2)=28 pairs per kid.
    const top = safeSeniors.slice(0, 8);

    for (let i = 0; i < top.length && out.length < max; i++) {
      for (let j = i + 1; j < top.length && out.length < max; j++) {
        const a = top[i]!;
        const b = top[j]!;
        if (!peerInfluenceSafe(a.senior, b.senior)) continue;

        const [high, mid, low] = orderTrio(a.senior, b.senior, young);
        if (String(low.id) !== String(young.id)) continue;

        const edgeHigh =
          String(high.id) === String(a.senior.id) ? a.edge : b.edge;
        const edgeMid =
          String(mid.id) === String(a.senior.id) ? a.edge : b.edge;
        // Sanity: both must be edges to young (already are).
        if (
          String(edgeHigh.receiver.id) !== String(young.id) ||
          String(edgeMid.receiver.id) !== String(young.id)
        ) {
          continue;
        }

        pushGroup({
          shape: "overload",
          members: [
            { player: high, role: "high" },
            { player: mid, role: "mid" },
            { player: low, role: "low" },
          ],
          subject: young,
          score:
            edgeHigh.score +
            edgeMid.score +
            overloadShapeBonus(a.senior, b.senior, young),
          path: "balance",
          edges: [safeEdgeToPair(edgeHigh), safeEdgeToPair(edgeMid)],
          reasons: [
            `${high.name} + ${mid.name} overload ${young.name}`,
            ...edgeHigh.reasons.slice(0, 1),
            ...edgeMid.reasons.slice(0, 1),
          ].slice(0, 4),
        });
      }
    }
  }

  // --- Cascade: High→Mid, High→Low, Mid→Low ---
  // Anchor on weakest influence seats; only pair with top stronger players.
  const cascadeLows = [...ranked].reverse().slice(0, 8);
  for (const low of cascadeLows) {
    if (out.length >= max) break;
    const lowScore = influenceOf.get(String(low.id)) ?? 0;
    const stronger = ranked
      .filter(
        (p) =>
          p.id !== low.id &&
          (influenceOf.get(String(p.id)) ?? 0) > lowScore,
      )
      .slice(0, 8);

    for (let i = 0; i < stronger.length && out.length < max; i++) {
      for (let j = i + 1; j < stronger.length && out.length < max; j++) {
        const [high, mid, lowSeat] = orderTrio(
          stronger[i]!,
          stronger[j]!,
          low,
        );
        if (String(lowSeat.id) !== String(low.id)) continue;

        // Mid→Low first — cheapest reject for the Lundqvist failure mode.
        const midLow = safeEdge(mid, lowSeat);
        if (!midLow) continue;
        const highLow = safeEdge(high, lowSeat);
        if (!highLow) continue;
        const highMid = safeEdge(high, mid);
        // High→Mid may be neutral peers for overload-like cascades.
        const highMidOk = highMid !== null || peerInfluenceSafe(high, mid);
        if (!highMidOk) continue;

        const pairs = [safeEdgeToPair(highLow), safeEdgeToPair(midLow)];
        if (highMid) pairs.unshift(safeEdgeToPair(highMid));

        const isYoungLow = isMentoringInfluenceSubject(lowSeat);
        const seniorsAbove =
          (high.age === undefined || high.age >= MENTOR_MIN_AGE) &&
          (mid.age === undefined || mid.age >= MENTOR_MIN_AGE);
        const shape: MentoringSafeGroupShape =
          isYoungLow && seniorsAbove && peerInfluenceSafe(high, mid)
            ? "overload"
            : "cascade";

        pushGroup({
          shape,
          members: [
            { player: high, role: "high" },
            { player: mid, role: "mid" },
            { player: lowSeat, role: "low" },
          ],
          subject: lowSeat,
          score:
            highLow.score +
            midLow.score +
            (highMid?.score ?? 0),
          path: "balance",
          edges: pairs,
          reasons: [
            shape === "overload"
              ? `${high.name} + ${mid.name} overload ${lowSeat.name}`
              : `cascade ${high.name} → ${mid.name} → ${lowSeat.name}`,
            ...midLow.reasons.slice(0, 1),
            ...highLow.reasons.slice(0, 1),
          ].slice(0, 4),
        });
      }
    }
  }

  out.sort((a, b) => {
    const shape =
      (a.shape === "overload" ? 0 : 1) - (b.shape === "overload" ? 0 : 1);
    if (shape !== 0) return shape;
    const score = b.score - a.score;
    if (score !== 0) return score;
    if (a.shape !== "overload" || b.shape !== "overload") return 0;
    const paA = mentoringLowSeatKnownPa(a);
    const paB = mentoringLowSeatKnownPa(b);
    if (paA !== undefined && paB !== undefined) return paB - paA;
    if (paA !== undefined) return -1;
    if (paB !== undefined) return 1;
    return 0;
  });
  return out.slice(0, max);
}

/** Next unused safe trio with this Low, or why Suggest cannot replace them. */
export function mentoringReplacementForLow(
  players: MentoringCandidate[],
  lowId: string,
  options?: MentoringMenteeCoverageOptions,
): MentoringReplacementResult {
  const kid = players.find((p) => String(p.id) === lowId);
  if (!kid) return { ok: false, skipReason: "incomplete attrs" };
  if (!isMentoringInfluenceSubject(kid)) {
    return { ok: false, skipReason: "no unused influence path" };
  }

  const occupied = options?.occupiedIds ?? options?.seatedIds ?? new Set();
  const pool = players.filter(
    (p) => String(p.id) === lowId || !occupied.has(String(p.id)),
  );
  const groups = findInfluenceSafeMentoringGroups(pool, {
    max: 32,
    ...(options?.hierarchyById ? { hierarchyById: options.hierarchyById } : {}),
    ...(options?.manualInfluenceEdges
      ? { manualInfluenceEdges: options.manualInfluenceEdges }
      : {}),
    ...(options?.rejectedGroupKeys
      ? { rejectedGroupKeys: options.rejectedGroupKeys }
      : {}),
  }).filter((group) => mentoringLowSeatId(group.members) === lowId);

  if (groups[0]) return { ok: true, group: groups[0] };

  const skipReason =
    mentoringSkipReasonForUnseated(kid, {
      players,
      unusedGroupsForKid: 0,
      meanDet: squadMeanDetermination(players),
      manualInfluenceEdges: options?.manualInfluenceEdges,
    }) ?? "no unused influence path";
  return { ok: false, skipReason };
}

/** Young FT pool: seated vs skipped with a one-line reason. */
export function mentoringMenteeCoverage(
  players: MentoringCandidate[],
  options: MentoringMenteeCoverageOptions,
): MentoringMenteeCoverageRow[] {
  const seatedIds = options.seatedIds;
  const occupied = options.occupiedIds ?? seatedIds;
  const meanDet = squadMeanDetermination(players);
  const pool = players.filter((p) => !occupied.has(String(p.id)));
  const unused = findInfluenceSafeMentoringGroups(pool, {
    max: 32,
    ...(options.hierarchyById ? { hierarchyById: options.hierarchyById } : {}),
    ...(options.manualInfluenceEdges
      ? { manualInfluenceEdges: options.manualInfluenceEdges }
      : {}),
    ...(options.rejectedGroupKeys
      ? { rejectedGroupKeys: options.rejectedGroupKeys }
      : {}),
  });
  const unusedCountByLow = new Map<string, number>();
  for (const group of unused) {
    const lowId = mentoringLowSeatId(group.members);
    if (!lowId) continue;
    unusedCountByLow.set(lowId, (unusedCountByLow.get(lowId) ?? 0) + 1);
  }

  const rows: MentoringMenteeCoverageRow[] = [];
  const seen = new Set<string>();

  for (const kid of players) {
    if (!isMentoringInfluenceSubject(kid)) continue;
    const id = String(kid.id);
    seen.add(id);
    if (seatedIds.has(id)) {
      rows.push({ id, name: kid.name, seated: true, ...coverageAbilityFields(kid) });
      continue;
    }
    const skipReason = mentoringSkipReasonForUnseated(kid, {
      players,
      unusedGroupsForKid: unusedCountByLow.get(id) ?? 0,
      meanDet,
      manualInfluenceEdges: options.manualInfluenceEdges,
    });
    rows.push({
      id,
      name: kid.name,
      seated: false,
      ...(skipReason ? { skipReason } : {}),
      ...coverageAbilityFields(kid),
    });
  }

  for (const young of options.incompleteYoung ?? []) {
    const id = String(young.id);
    if (seen.has(id)) continue;
    seen.add(id);
    if (seatedIds.has(id)) {
      rows.push({
        id,
        name: young.name,
        seated: true,
        ...coverageAbilityFields(young),
      });
      continue;
    }
    rows.push({
      id,
      name: young.name,
      seated: false,
      skipReason: "incomplete attrs",
      ...coverageAbilityFields(young),
    });
  }

  rows.sort((a, b) => {
    if (a.seated !== b.seated) return a.seated ? 1 : -1;
    if (!a.seated && !b.seated) {
      const paA = mentoringKnownAbility(a.pa);
      const paB = mentoringKnownAbility(b.pa);
      if (paA !== undefined && paB !== undefined && paA !== paB) return paB - paA;
      if (paA !== undefined && paB === undefined) return -1;
      if (paA === undefined && paB !== undefined) return 1;
    }
    return a.name.localeCompare(b.name);
  });
  return rows;
}

/**
 * Score a user-built 3-player unit with High / Mid / Low seats.
 * Required edges: High→Mid, High→Low, Mid→Low. Soft age warnings only.
 */
export function evaluateMentoringUnit(
  members: MentoringUnitMember[],
  _roster: MentorRosterFilter = "mixed",
): MentoringUnitEvaluation {
  const warnings: string[] = [];
  if (members.length !== 3) {
    return {
      members,
      shape: "invalid",
      path: null,
      score: 0,
      edges: [],
      directed: [],
      reasons: ["A mentoring unit needs exactly three players."],
      warnings,
    };
  }

  const ids = new Set(members.map((m) => String(m.player.id)));
  if (ids.size !== 3) {
    return {
      members,
      shape: "invalid",
      path: null,
      score: 0,
      edges: [],
      directed: [],
      reasons: ["Pick three different players."],
      warnings,
    };
  }

  const bySeat = {
    high: members.find((m) => m.role === "high")?.player,
    mid: members.find((m) => m.role === "mid")?.player,
    low: members.find((m) => m.role === "low")?.player,
  };
  if (!bySeat.high || !bySeat.mid || !bySeat.low) {
    return {
      members,
      shape: "invalid",
      path: null,
      score: 0,
      edges: [],
      directed: [],
      reasons: ["Assign High, Mid, and Low influence seats."],
      warnings,
    };
  }

  const high = bySeat.high;
  const mid = bySeat.mid;
  const low = bySeat.low;

  const required: {
    from: MentoringCandidate;
    to: MentoringCandidate;
    label: string;
    peerOk: boolean;
  }[] = [
    { from: high, to: mid, label: "High→Mid", peerOk: true },
    { from: high, to: low, label: "High→Low", peerOk: false },
    { from: mid, to: low, label: "Mid→Low", peerOk: false },
  ];

  const edges: MentoringSquadPair[] = [];
  const directed: MentoringDirectedEdge[] = [];
  const seatPlayers = [high, mid, low];
  let highMidOk = false;
  let highLowOk = false;
  let midLowOk = false;

  for (const req of required) {
    const safe = scoreSafeInfluence(req.from, req.to);
    if (safe) {
      const pair = safeEdgeToPair(safe);
      edges.push(pair);
      directed.push({
        fromId: String(req.from.id),
        toId: String(req.to.id),
        level: mentoringInfluenceLevel(pair),
        pair,
      });
      if (req.label === "High→Mid") highMidOk = true;
      if (req.label === "High→Low") highLowOk = true;
      if (req.label === "Mid→Low") midLowOk = true;
      continue;
    }

    // Seniors may be neutral peers — allow High→Mid when neither Det-drags.
    if (req.peerOk && peerInfluenceSafe(req.from, req.to)) {
      highMidOk = true;
      directed.push({
        fromId: String(req.from.id),
        toId: String(req.to.id),
        level: "none",
        pair: null,
      });
      continue;
    }

    const harm = mentorHarmReasons(req.to, req.from);
    const detFrom = traitValue(req.from, "determination");
    const detTo = traitValue(req.to, "determination");
    if (
      detFrom !== undefined &&
      detTo !== undefined &&
      detFrom + 1 < detTo
    ) {
      warnings.push(`${req.label}: lowers Determination`);
    } else if (harm.length > 0) {
      warnings.push(`${req.label}: ${harm[0]}`);
    } else {
      warnings.push(`${req.label}: weak / unsafe influence`);
    }
    directed.push({
      fromId: String(req.from.id),
      toId: String(req.to.id),
      level: "none",
      pair: null,
    });
  }

  // Fill remaining directed slots as none (for completeness).
  for (let i = 0; i < seatPlayers.length; i++) {
    for (let j = 0; j < seatPlayers.length; j++) {
      if (i === j) continue;
      const fromId = String(seatPlayers[i]!.id);
      const toId = String(seatPlayers[j]!.id);
      if (directed.some((d) => d.fromId === fromId && d.toId === toId)) {
        continue;
      }
      directed.push({ fromId, toId, level: "none", pair: null });
    }
  }

  let shape: MentoringUnitShape = "custom";
  if (highMidOk && highLowOk && midLowOk) {
    const youngLow = isMentoringInfluenceSubject(low);
    const seniorsAbove =
      (high.age === undefined || high.age >= MENTOR_MIN_AGE) &&
      (mid.age === undefined || mid.age >= MENTOR_MIN_AGE);
    shape =
      youngLow && seniorsAbove && peerInfluenceSafe(high, mid)
        ? "overload"
        : "cascade";
  } else if (!midLowOk && warnings.some((w) => w.startsWith("Mid→Low"))) {
    shape = "invalid";
  }

  const path =
    edges.length === 0 ? null : aggregateGroupPath(edges.map((e) => e.path));
  const score = edges.reduce((sum, e) => sum + e.score, 0);
  const reasons =
    edges.length > 0
      ? edges.map(
          (e) =>
            `${e.mentor.name} → ${e.mentee.name}: ${e.lifts.slice(0, 2).join(", ") || e.path}`,
        )
      : ["No safe High→Low / Mid→Low edges yet."];

  return {
    members,
    shape,
    path,
    score,
    edges,
    directed,
    reasons,
    warnings,
  };
}

/**
 * Soft direction when ages are missing: prefer the stronger (HAS / teachable)
 * player as mentor so we don't list A→B and B→A for the same duo.
 */
function preferredMentorWithoutAges(
  mentor: MentoringCandidate,
  mentee: MentoringCandidate,
): boolean {
  if (mentor.age !== undefined && mentee.age !== undefined) return true;
  const mentorHa = mentor.haScore;
  const menteeHa = mentee.haScore;
  if (
    mentorHa !== undefined &&
    menteeHa !== undefined &&
    Number.isFinite(mentorHa) &&
    Number.isFinite(menteeHa) &&
    Math.abs(mentorHa - menteeHa) > 1e-9
  ) {
    return mentorHa >= menteeHa;
  }
  const mentorTeach = teachableTraits(mentor).length;
  const menteeTeach = teachableTraits(mentee).length;
  if (mentorTeach !== menteeTeach) return mentorTeach > menteeTeach;
  return mentor.name.localeCompare(mentee.name) <= 0;
}

/** Ways this mentor personality / attrs can drag a mentee down. */
function mentorHarmReasons(
  mentee: MentoringSubject,
  mentor: MentoringSubject,
): string[] {
  const reasons: string[] = [];
  const protectedList = protectedTraits(mentee);

  for (const trait of MENTORING_TRAITS) {
    const menteeValue = traitValue(mentee, trait);
    const mentorValue = traitValue(mentor, trait);
    if (menteeValue === undefined || mentorValue === undefined) continue;

    if (trait === "controversy") {
      if (mentorValue > menteeValue + 1) {
        reasons.push(`raises ${traitLabel(trait)}`);
      }
      continue;
    }

    const menteeTone = traitTone(trait, menteeValue);
    const mentorTone = traitTone(trait, mentorValue);
    if (
      mentorValue + 1 < menteeValue &&
      (protectedList.includes(trait) || menteeTone === "good")
    ) {
      reasons.push(`lowers ${traitLabel(trait)}`);
    } else if (mentorTone === "bad" && menteeTone !== "bad") {
      reasons.push(`toxic ${traitLabel(trait)}`);
    }
  }

  if (mentor.personality?.trim()) {
    try {
      const personality = findPersonality(
        mentoringCatalog(),
        mentor.personality,
      );
      const media =
        mentor.mediaHandling?.trim()
          ? resolveMedia(mentor.mediaHandling)
          : undefined;
      if (
        personality &&
        media &&
        !isSafeMentorPackage(personality, media, mentee)
      ) {
        reasons.push("package below mentee floors");
      }
    } catch {
      // Unknown catalog labels — skip package floor check.
    }
  }

  return reasons;
}

function pairSortKey(path: MentoringPairPath): number {
  if (path === "specialize") return 0;
  if (path === "balance") return 1;
  return 2;
}
