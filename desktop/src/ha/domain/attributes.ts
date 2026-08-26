/**
 * HAS / checker estimate outputs (Beni weights). Not the SI "Hidden Attributes" group.
 * Order: weight high → low, Controversy last (inverted in HAS).
 * Important Matches remains in the set for future modeling but is omitted from
 * Personalities / Attributes / Compare HA tables until then.
 */
export const HAS_ATTRIBUTES = [
  "professionalism",
  "pressure",
  "importantMatches",
  "ambition",
  "temperament",
  "loyalty",
  "sportsmanship",
  "controversy",
] as const;

export type HasAttribute = (typeof HAS_ATTRIBUTES)[number];

/** @deprecated Prefer {@link HAS_ATTRIBUTES} — kept for checker HAS math. */
export const HIDDEN_ATTRIBUTES_HAS = HAS_ATTRIBUTES;
/** @deprecated Use {@link HasAttribute}. */
export type HiddenAttributeHas = HasAttribute;

/**
 * SI Personality Attributes (roster / extract).
 * Det + Lea are visible mentals that drive personality; the rest come from the
 * locked save pack (Ada is SI Hidden, not Personality).
 */
export const PERSONALITY_ATTRIBUTES = [
  "determination",
  "leadership",
  "ambition",
  "controversy",
  "loyalty",
  "pressure",
  "professionalism",
  "sportsmanship",
  "temperament",
] as const;

export type PersonalityAttribute = (typeof PERSONALITY_ATTRIBUTES)[number];

/**
 * SI Hidden Attributes — Adaptability + match/availability HAs.
 * Ada is extracted with the personality pack today; the other five are prepared
 * for a later layout lock.
 */
export const HIDDEN_ATTRIBUTES = [
  "adaptability",
  "consistency",
  "dirtiness",
  "importantMatches",
  "injuryProneness",
  "versatility",
] as const;

export type HiddenAttribute = (typeof HIDDEN_ATTRIBUTES)[number];

/**
 * HAS attrs reserved in catalog estimates but omitted from Personalities /
 * Attributes / Compare HA tables until modeled from personality × media bands.
 */
export const UNMODELED_HAS_ATTRIBUTES = ["importantMatches"] as const;

export type UnmodeledHasAttribute = (typeof UNMODELED_HAS_ATTRIBUTES)[number];

/** @deprecated Use {@link UNMODELED_HAS_ATTRIBUTES}. */
export const UNMODELED_HIDDEN_ATTRIBUTES = UNMODELED_HAS_ATTRIBUTES;
/** @deprecated Use {@link UnmodeledHasAttribute}. */
export type UnmodeledHiddenAttribute = UnmodeledHasAttribute;

export function isUnmodeledHiddenAttribute(
  attribute: HasAttribute | string,
): attribute is UnmodeledHasAttribute {
  return (UNMODELED_HAS_ATTRIBUTES as readonly string[]).includes(attribute);
}

/**
 * Visible in-game attributes used as checker inputs (also in Personality).
 */
export const VISIBLE_ATTRIBUTES = ["determination", "leadership"] as const;

export type VisibleAttribute = (typeof VISIBLE_ATTRIBUTES)[number];

/** Attributes that participate in HAS constraint solving. */
export const TRACKED_ATTRIBUTES = [
  ...HAS_ATTRIBUTES,
  ...VISIBLE_ATTRIBUTES,
] as const;

export type TrackedAttribute = (typeof TRACKED_ATTRIBUTES)[number];

/**
 * Checker / HAS / Compare presentation order: weight high → low
 * (Controversy last), with Det (×5) and Lea (×2) interleaved beside
 * same-weight peers. Important Matches omitted until modeled.
 */
export const CHECKER_TABLE_ATTRIBUTES = [
  "determination",
  "professionalism",
  "pressure",
  "ambition",
  "temperament",
  "leadership",
  "loyalty",
  "sportsmanship",
  "controversy",
] as const satisfies readonly TrackedAttribute[];

export type CheckerTableAttribute = (typeof CHECKER_TABLE_ATTRIBUTES)[number];

export const ATTRIBUTE_LABELS: Record<TrackedAttribute, string> = {
  professionalism: "Professionalism",
  determination: "Determination",
  ambition: "Ambition",
  loyalty: "Loyalty",
  sportsmanship: "Sportsmanship",
  pressure: "Pressure",
  temperament: "Temperament",
  leadership: "Leadership",
  controversy: "Controversy",
  importantMatches: "Important Matches",
};

export const PERSONALITY_ATTRIBUTE_LABELS: Record<PersonalityAttribute, string> =
  {
    determination: "Determination",
    leadership: "Leadership",
    ambition: "Ambition",
    controversy: "Controversy",
    loyalty: "Loyalty",
    pressure: "Pressure",
    professionalism: "Professionalism",
    sportsmanship: "Sportsmanship",
    temperament: "Temperament",
  };

export const PERSONALITY_ATTRIBUTE_ABBR: Record<PersonalityAttribute, string> = {
  determination: "Det",
  leadership: "Lea",
  ambition: "Amb",
  controversy: "Con",
  loyalty: "Loy",
  pressure: "Pre",
  professionalism: "Pro",
  sportsmanship: "Spo",
  temperament: "Tem",
};

export const HIDDEN_ATTRIBUTE_LABELS: Record<HiddenAttribute, string> = {
  adaptability: "Adaptability",
  consistency: "Consistency",
  dirtiness: "Dirtiness",
  importantMatches: "Important Matches",
  injuryProneness: "Injury Proneness",
  versatility: "Versatility",
};


/** Spreadsheet-style tooltips for tracked attributes. */
export const ATTRIBUTE_DESCRIPTIONS: Record<TrackedAttribute, string> = {
  professionalism:
    "How good a player attitude is to his match performance, training performance and career (an important attribute for young players and mentors)",
  determination:
    "How determined a player is (visible attribute; weighted heavily in HAS when known)",
  ambition:
    "How much a player wants to achieve success (an important attribute for young player and mentors)",
  pressure: "How well a player copes with demanding situations",
  importantMatches:
    "How well a player performs in big games (not yet modeled from catalog bands — reserved ★4 in HAS)",
  temperament:
    "How disciplined a player's conduct is when events go against him",
  loyalty: "How strong a player's allegiance to his current club is",
  sportsmanship: "How ethical a player is",
  leadership:
    "How well a player leads teammates (visible attribute; included in HAS when known)",
  controversy: "How outspoken a player is",
};

/**
 * Spreadsheet conditional formatting on the midpoint (checker column D):
 * most attrs green when mid > 14, red when 0 < mid < 6;
 * controversy is inverted.
 * Det / Lead use the same thresholds as the non-inverted hidden attrs.
 */
export type AttributeTone = "good" | "bad" | "neutral";

export function attributeTone(
  attribute: TrackedAttribute,
  midpoint: number,
): AttributeTone {
  if (attribute === "importantMatches") return "neutral";
  if (attribute === "controversy") {
    if (midpoint > 0 && midpoint < 6) return "good";
    if (midpoint > 14) return "bad";
    return "neutral";
  }

  if (midpoint > 14) return "good";
  if (midpoint > 0 && midpoint < 6) return "bad";
  return "neutral";
}

/** Canonical FM attribute scale. */
export const FULL_RANGE = { min: 1, max: 20 } as const;

export type AttributeRange = {
  min: number;
  max: number;
};

export type AttributeEstimate = AttributeRange & {
  /** Midpoint used by the spreadsheet UI averages. */
  midpoint: number;
  /** True when min === max (known exact value). */
  exact: boolean;
  /** True when min > max — empty intersection (combo likely impossible). */
  impossible?: boolean;
  /** True when this attr is reserved but not estimated yet. */
  unmodeled?: boolean;
};

/** Checker / HAS estimate map (not SI Hidden Attributes). */
export type AttributeEstimates = Record<HasAttribute, AttributeEstimate>;

function hasImpossibleBand(attributes: AttributeEstimates): boolean {
  for (const estimate of Object.values(attributes)) {
    if (estimate.unmodeled) continue;
    if (estimate.impossible || estimate.min > estimate.max) return true;
  }
  return false;
}

/**
 * Beni FM24 personality-guide priorities (★ → weight).
 * Controversy is ×3 (Amb/Tem) — above Beni’s ★2 so high Con is not
 * cancelled by a Pre bump, without over-taxing elite low-Con lines.
 * Importance Matches (★4) is reserved until modeled ({@link HA_IMPORTANCE_WEIGHT}).
 * Controversy is inverted via `21 − Con` so lower Con raises HAS.
 *
 * Determination / Leadership join only when known (constrained band or
 * entered value) so definite high/low Det/Lead can re-rank combos.
 */
export const HA_QUALITY_WEIGHTS = {
  professionalism: 5,
  pressure: 4,
  ambition: 3,
  temperament: 3,
  loyalty: 2,
  controversy: 3,
  sportsmanship: 1,
} as const;

/** Weights for known visible attrs (folded into HAS only when present). */
export const HA_VISIBLE_QUALITY_WEIGHTS = {
  determination: 5,
  leadership: 2,
} as const;

/** Sum of hidden {@link HA_QUALITY_WEIGHTS} (before optional Det/Lead). */
export const HA_QUALITY_WEIGHT_SUM =
  HA_QUALITY_WEIGHTS.professionalism +
  HA_QUALITY_WEIGHTS.pressure +
  HA_QUALITY_WEIGHTS.ambition +
  HA_QUALITY_WEIGHTS.temperament +
  HA_QUALITY_WEIGHTS.loyalty +
  HA_QUALITY_WEIGHTS.controversy +
  HA_QUALITY_WEIGHTS.sportsmanship; // 21

/** Known Det / Lead values to fold into HAS (omit when unconstrained). */
export type HaVisibleKnown = {
  determination?: number;
  leadership?: number;
};

/** Beni weight for Importance Matches once that hidden attr is estimated. */
export const HA_IMPORTANCE_WEIGHT = 4;

/** Invert Controversy onto the same 1–20 “higher is better” scale. */
export function invertControversy(controversy: number): number {
  return FULL_RANGE.min + FULL_RANGE.max - controversy; // 21 − Con
}

export function haQualityWeightSum(visible?: HaVisibleKnown): number {
  let sum = HA_QUALITY_WEIGHT_SUM;
  const v = HA_VISIBLE_QUALITY_WEIGHTS;
  if (visible?.determination !== undefined) sum += v.determination;
  if (visible?.leadership !== undefined) sum += v.leadership;
  return sum;
}

type ScoredHasAttribute = Exclude<
  HasAttribute,
  "controversy" | "importantMatches"
>;

function weightedHiddenQuality(
  positive: (attribute: ScoredHasAttribute) => number,
  controversyRaw: number,
  visible?: HaVisibleKnown,
): number {
  const w = HA_QUALITY_WEIGHTS;
  const vw = HA_VISIBLE_QUALITY_WEIGHTS;
  let numerator =
    w.professionalism * positive("professionalism") +
    w.pressure * positive("pressure") +
    w.ambition * positive("ambition") +
    w.temperament * positive("temperament") +
    w.loyalty * positive("loyalty") +
    w.sportsmanship * positive("sportsmanship") +
    w.controversy * invertControversy(controversyRaw);
  if (visible?.determination !== undefined) {
    numerator += vw.determination * visible.determination;
  }
  if (visible?.leadership !== undefined) {
    numerator += vw.leadership * visible.leadership;
  }
  return numerator / haQualityWeightSum(visible);
}

/**
 * Weighted HA index from midpoints (1–20 scale).
 * Base: (5×Pro + 4×Pre + 3×Amb + 3×Tem + 2×Loy + 1×Spo + 3×(21−Con)) ÷ 21
 * Plus DET×5 / LEA×2 when those known visibles are supplied (divisor grows).
 * Returns NaN when any attribute has an impossible (min > max) range.
 */
export function hiddenQualityScore(
  attributes: AttributeEstimates,
  visible?: HaVisibleKnown,
): number {
  if (hasImpossibleBand(attributes)) return Number.NaN;
  return weightedHiddenQuality(
    (attribute) => attributes[attribute].midpoint,
    attributes.controversy.midpoint,
    visible,
  );
}

/**
 * Pessimistic HA using band extremes (mins for goods, max Controversy before invert).
 * Known Det/Lead should pass their low ends when available.
 */
export function hiddenQualityFloorScore(
  attributes: AttributeEstimates,
  visible?: HaVisibleKnown,
): number {
  if (hasImpossibleBand(attributes)) return Number.NaN;
  return weightedHiddenQuality(
    (attribute) => attributes[attribute].min,
    attributes.controversy.max,
    visible,
  );
}

/** Compact weight list for tips / docs — same order as {@link CHECKER_TABLE_ATTRIBUTES}. */
export function formatHaQualityWeightsTip(visible?: HaVisibleKnown): string {
  const w = HA_QUALITY_WEIGHTS;
  const vw = HA_VISIBLE_QUALITY_WEIGHTS;
  const det =
    visible?.determination !== undefined
      ? `DET×${vw.determination}`
      : `DET×${vw.determination} if known`;
  const lea =
    visible?.leadership !== undefined
      ? `LEA×${vw.leadership}`
      : `LEA×${vw.leadership} if known`;
  return (
    `${det}` +
    ` · PRO×${w.professionalism}` +
    ` · PRE×${w.pressure}` +
    ` · AMB×${w.ambition}` +
    ` · TEM×${w.temperament}` +
    ` · ${lea}` +
    ` · LOY×${w.loyalty}` +
    ` · SPO×${w.sportsmanship}` +
    ` · CON×${w.controversy} as (21−Con)` +
    ` ÷ ${haQualityWeightSum(visible)}`
  );
}

/**
 * Elite HAS cutoff fraction: greens when score is in the top `fraction`
 * of unique mid HAS values across the ranked catalog (exceptional within set).
 * FM per-attribute elite (16+) is a different scale; HAS is relative.
 */
export const HIDDEN_QUALITY_ELITE_TOP_FRACTION = 0.25;

/**
 * Fallback elite floor when no score set is available.
 * Prefer {@link resolveEliteHasFloor} from a live ranking.
 */
export const HIDDEN_QUALITY_GOOD_FLOOR = 14;

/** Spreadsheet-style low band for the HA index. */
export const HIDDEN_QUALITY_BAD_CEILING = 6;

/** FM elite-band start on the 1–20 attribute scale (per-attribute midpoints). */
export const FM_ATTRIBUTE_ELITE_MIN = 16;

/** Theoretical HAS ceiling (all goods 20, Controversy 1). */
export const HIDDEN_QUALITY_INDEX_MAX = 20;

/**
 * Raw FM-style attribute band mapped onto a HAS ceiling:
 * (FM_ATTRIBUTE_ELITE_MIN / 20) × maxHas.
 */
export function fmEliteHasFloor(
  maxHas: number = HIDDEN_QUALITY_INDEX_MAX,
): number {
  return (FM_ATTRIBUTE_ELITE_MIN / 20) * maxHas;
}

/**
 * Lowest score still inside the top `fraction` of unique values
 * (descending). Used for catalog-relative elite HAS.
 */
export function uniqueHasTopFractionFloor(
  scores: Iterable<number>,
  fraction: number,
): number {
  const unique = [
    ...new Set(
      [...scores]
        .filter((s) => Number.isFinite(s))
        .map((s) => +s.toFixed(10)),
    ),
  ].sort((a, b) => b - a);
  if (unique.length === 0) return HIDDEN_QUALITY_GOOD_FLOOR;
  const k = Math.max(1, Math.ceil(unique.length * fraction));
  return unique[k - 1]!;
}

/**
 * Highest score still inside the bottom `fraction` of unique values
 * (ascending). Used for catalog-relative poor HAS.
 */
export function uniqueHasBottomFractionCeiling(
  scores: Iterable<number>,
  fraction: number,
): number {
  const unique = [
    ...new Set(
      [...scores]
        .filter((s) => Number.isFinite(s))
        .map((s) => +s.toFixed(10)),
    ),
  ].sort((a, b) => a - b);
  if (unique.length === 0) return HIDDEN_QUALITY_BAD_CEILING;
  const k = Math.max(1, Math.ceil(unique.length * fraction));
  return unique[k - 1]!;
}

/** Catalog-relative elite HAS floor (top {@link HIDDEN_QUALITY_ELITE_TOP_FRACTION}). */
export function resolveEliteHasFloor(scores: Iterable<number>): number {
  return uniqueHasTopFractionFloor(scores, HIDDEN_QUALITY_ELITE_TOP_FRACTION);
}

/**
 * Catalog-relative poor HAS ceiling (bottom {@link HIDDEN_QUALITY_ELITE_TOP_FRACTION}).
 * Mirrors elite so ~the same share of unique HAS values paint red as green.
 */
export function resolvePoorHasCeiling(scores: Iterable<number>): number {
  return uniqueHasBottomFractionCeiling(
    scores,
    HIDDEN_QUALITY_ELITE_TOP_FRACTION,
  );
}

/**
 * Tone for the HA index.
 * Pass floors from {@link resolveEliteHasFloor} / {@link resolvePoorHasCeiling}.
 */
export function hiddenQualityTone(
  score: number,
  eliteFloor: number = HIDDEN_QUALITY_GOOD_FLOOR,
  poorCeiling: number = HIDDEN_QUALITY_BAD_CEILING,
): AttributeTone {
  if (score >= eliteFloor) return "good";
  if (score <= poorCeiling) return "bad";
  return "neutral";
}
