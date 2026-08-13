/**
 * Rank valid personality × media handling combos by HA index.
 * Impossible (empty-intersect) pairs are excluded.
 */

import type { Catalog, PersonalityDefinition } from "../catalog/types.js";
import { formatMediaHandlingLabel } from "../catalog/lookup.js";
import {
  formatHaQualityWeightsTip,
  hiddenQualityFloorScore,
  hiddenQualityScore,
  resolveEliteHasFloor,
  resolvePoorHasCeiling,
  type AttributeTone,
  type HaVisibleKnown,
  type HasAttribute,
  hiddenQualityTone,
} from "../domain/attributes.js";
import { isPersonalityMediaCompatible } from "./bands.js";
import { estimatePlayer } from "./estimate.js";

/** Population chip when REAL / NEWGEN HA diverge (or combo exists in only one). */
export type ComboPopulationLabel = "REAL" | "NEWGEN";

/** Midpoints shown in the expanded ranker table (null = not modeled / unconstrained). */
export type ComboRankMids = {
  professionalism: number;
  pressure: number;
  ambition: number;
  /** Placeholder — not modeled yet; kept for future HAS work. */
  importantMatches: number | null;
  sportsmanship: number;
  temperament: number;
  loyalty: number;
  controversy: number;
  determination: number | null;
  leadership: number | null;
};

export type ComboRankBand = { min: number; max: number };

/** Min–max bands for Mid/Band value mode (null = not modeled / unconstrained). */
export type ComboRankBands = {
  [K in keyof ComboRankMids]: ComboRankBand | null;
};

export type ComboRankEntry = {
  rank: number;
  personality: string;
  mediaHandling: string;
  haScore: number;
  /** Pessimistic HAS (same weights on mins / Con max). */
  floorScore: number;
  tone: AttributeTone;
  mids: ComboRankMids;
  bands: ComboRankBands;
  /**
   * REAL / NEWGEN when scores differ (or combo is population-only).
   * Omitted / null when HA matches for both populations.
   */
  label?: ComboPopulationLabel | null;
};

export type ComboRanking = {
  entries: ComboRankEntry[];
  isRegen: boolean;
  generatedAt: string;
  /** HAS ≥ this is painted elite (top 25% of unique scores in this ranking). */
  eliteHasFloor: number;
  /** HAS ≤ this is painted poor (bottom 25% of unique scores in this ranking). */
  poorHasCeiling: number;
};

export type RankCombosOptions = {
  /** When false, skip regen-only personalities and apply non-newgen cases. */
  isRegen?: boolean;
};

export type RankPopulationMode = "mixed" | "real" | "newgen";

export type RankCombosUnifiedOptions = {
  /** mixed = both populations merged; real / newgen filter the labeled split. */
  population?: RankPopulationMode;
};

type ScoredCombo = Omit<ComboRankEntry, "rank">;

/** Native `title` / tooltip copy for the ranker sort order. */
export const COMBO_RANK_SORT_HINT =
  `Sort: weighted HAS (${formatHaQualityWeightsTip()}). Same HAS → floor HAS (mins / Con max, same weights). Then name.`;

function isRegenOnly(personality: PersonalityDefinition): boolean {
  return personality.conditionals.some((rule) => rule.kind === "regen_only");
}

function midFromBand(band: { min: number; max: number } | undefined): number | null {
  if (!band) return null;
  return (band.min + band.max) / 2;
}

function copyBand(
  band: { min: number; max: number } | undefined,
): ComboRankBand | null {
  if (!band) return null;
  return { min: band.min, max: band.max };
}

function hiddenBand(
  attributes: Record<HasAttribute, { min: number; max: number }>,
  attribute: HasAttribute,
): ComboRankBand {
  const range = attributes[attribute];
  return { min: range.min, max: range.max };
}

function hiddenMid(
  attributes: Record<HasAttribute, { midpoint: number }>,
  attribute: HasAttribute,
): number {
  return attributes[attribute].midpoint;
}

function buildMids(
  attributes: Record<HasAttribute, { midpoint: number }>,
  impliedVisible: {
    determination?: { min: number; max: number };
    leadership?: { min: number; max: number };
  },
): ComboRankMids {
  return {
    professionalism: hiddenMid(attributes, "professionalism"),
    pressure: hiddenMid(attributes, "pressure"),
    ambition: hiddenMid(attributes, "ambition"),
    importantMatches: null,
    sportsmanship: hiddenMid(attributes, "sportsmanship"),
    temperament: hiddenMid(attributes, "temperament"),
    loyalty: hiddenMid(attributes, "loyalty"),
    controversy: hiddenMid(attributes, "controversy"),
    determination: midFromBand(impliedVisible.determination),
    leadership: midFromBand(impliedVisible.leadership),
  };
}

function buildBands(
  attributes: Record<HasAttribute, { min: number; max: number }>,
  impliedVisible: {
    determination?: { min: number; max: number };
    leadership?: { min: number; max: number };
  },
): ComboRankBands {
  return {
    professionalism: hiddenBand(attributes, "professionalism"),
    pressure: hiddenBand(attributes, "pressure"),
    ambition: hiddenBand(attributes, "ambition"),
    importantMatches: null,
    sportsmanship: hiddenBand(attributes, "sportsmanship"),
    temperament: hiddenBand(attributes, "temperament"),
    loyalty: hiddenBand(attributes, "loyalty"),
    controversy: hiddenBand(attributes, "controversy"),
    determination: copyBand(impliedVisible.determination),
    leadership: copyBand(impliedVisible.leadership),
  };
}

function comboKey(personality: string, mediaHandling: string): string {
  return `${personality}\0${mediaHandling}`;
}

function visibleKnownFromImplied(
  impliedVisible: {
    determination?: { min: number; max: number };
    leadership?: { min: number; max: number };
  },
  mode: "mid" | "floor",
): HaVisibleKnown | undefined {
  const visible: HaVisibleKnown = {};
  if (impliedVisible.determination) {
    const band = impliedVisible.determination;
    visible.determination =
      mode === "floor" ? band.min : (band.min + band.max) / 2;
  }
  if (impliedVisible.leadership) {
    const band = impliedVisible.leadership;
    visible.leadership =
      mode === "floor" ? band.min : (band.min + band.max) / 2;
  }
  if (
    visible.determination === undefined &&
    visible.leadership === undefined
  ) {
    return undefined;
  }
  return visible;
}

function scoreCompatibleCombos(
  catalog: Catalog,
  isRegen: boolean,
): ScoredCombo[] {
  const scored: ScoredCombo[] = [];

  for (const personality of catalog.personalities) {
    if (!isRegen && isRegenOnly(personality)) continue;

    for (const media of catalog.mediaHandling) {
      if (!isPersonalityMediaCompatible(personality, media)) continue;

      const mediaHandling = formatMediaHandlingLabel(media.styles);
      try {
        const result = estimatePlayer(catalog, {
          personality: personality.id,
          mediaHandling,
          isRegen,
        });
        if (result.impossibleCombo) continue;
        const visibleMid = visibleKnownFromImplied(
          result.impliedVisible,
          "mid",
        );
        const visibleFloor = visibleKnownFromImplied(
          result.impliedVisible,
          "floor",
        );
        const haScore = hiddenQualityScore(result.attributes, visibleMid);
        const floorScore = hiddenQualityFloorScore(
          result.attributes,
          visibleFloor,
        );
        if (!Number.isFinite(haScore) || !Number.isFinite(floorScore)) {
          continue;
        }
        scored.push({
          personality: personality.id,
          mediaHandling,
          haScore,
          floorScore,
          tone: "neutral",
          mids: buildMids(result.attributes, result.impliedVisible),
          bands: buildBands(result.attributes, result.impliedVisible),
        });
      } catch {
        // Skip combos the estimator cannot resolve (unknown case edge, etc.).
      }
    }
  }

  return scored;
}

function sortScoredCombos(scored: ScoredCombo[]): ScoredCombo[] {
  return [...scored].sort(
    (a, b) =>
      b.haScore - a.haScore ||
      b.floorScore - a.floorScore ||
      a.personality.localeCompare(b.personality) ||
      a.mediaHandling.localeCompare(b.mediaHandling) ||
      String(a.label ?? "").localeCompare(String(b.label ?? "")),
  );
}

function sameHaScore(a: number, b: number): boolean {
  return Math.abs(a - b) < 1e-9;
}

/**
 * Merge REAL + NEWGEN rankings into one list.
 * Same HA → one unlabeled row. Different HA (or population-only) → labeled rows.
 */
export function mergePopulationCombos(
  real: ScoredCombo[],
  newgen: ScoredCombo[],
): ScoredCombo[] {
  const realByKey = new Map(
    real.map((e) => [comboKey(e.personality, e.mediaHandling), e]),
  );
  const newgenByKey = new Map(
    newgen.map((e) => [comboKey(e.personality, e.mediaHandling), e]),
  );
  const keys = new Set([...realByKey.keys(), ...newgenByKey.keys()]);
  const merged: ScoredCombo[] = [];

  for (const key of keys) {
    const realEntry = realByKey.get(key);
    const newgenEntry = newgenByKey.get(key);

    if (realEntry && newgenEntry) {
      if (sameHaScore(realEntry.haScore, newgenEntry.haScore)) {
        merged.push({ ...realEntry, label: null });
      } else {
        merged.push({ ...realEntry, label: "REAL" });
        merged.push({ ...newgenEntry, label: "NEWGEN" });
      }
      continue;
    }

    if (realEntry) {
      merged.push({ ...realEntry, label: "REAL" });
      continue;
    }

    if (newgenEntry) {
      merged.push({ ...newgenEntry, label: "NEWGEN" });
    }
  }

  return merged;
}

function filterByPopulation(
  entries: ScoredCombo[],
  population: RankPopulationMode,
): ScoredCombo[] {
  if (population === "mixed") return entries;
  if (population === "real") {
    return entries.filter((e) => e.label !== "NEWGEN");
  }
  return entries.filter((e) => e.label !== "REAL");
}

function toRanking(scored: ScoredCombo[], isRegen: boolean): ComboRanking {
  const scores = scored.map((s) => s.haScore);
  const eliteHasFloor = resolveEliteHasFloor(scores);
  const poorHasCeiling = resolvePoorHasCeiling(scores);
  const sorted = sortScoredCombos(scored);
  return {
    isRegen,
    generatedAt: new Date().toISOString(),
    eliteHasFloor,
    poorHasCeiling,
    entries: sorted.map((entry, index) => ({
      ...entry,
      tone: hiddenQualityTone(entry.haScore, eliteHasFloor, poorHasCeiling),
      rank: index + 1,
    })),
  };
}

export function rankPersonalityMediaCombos(
  catalog: Catalog,
  options: RankCombosOptions = {},
): ComboRanking {
  const isRegen = options.isRegen ?? false;
  return toRanking(scoreCompatibleCombos(catalog, isRegen), isRegen);
}

/**
 * Single list of personality × media combos with REAL/NEWGEN labels when HA differs.
 */
export function rankPersonalityMediaCombosUnified(
  catalog: Catalog,
  options: RankCombosUnifiedOptions = {},
): ComboRanking {
  const population = options.population ?? "mixed";
  const real = scoreCompatibleCombos(catalog, false);
  const newgen = scoreCompatibleCombos(catalog, true);
  const merged = filterByPopulation(
    mergePopulationCombos(real, newgen),
    population,
  );
  return toRanking(merged, population === "newgen");
}
