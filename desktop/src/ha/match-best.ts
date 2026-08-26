/**
 * Pick the best personality × media label for known HA points.
 * Ports web/main.ts `matchPersonalityComboFromAttrs` (priority + tightness).
 */

import {
  findMediaHandling,
  findPersonality,
  formatMediaHandlingLabel,
  loadCatalog,
} from "./catalog/lookup";
import type { Catalog } from "./catalog/types";
import {
  caseFlagsFor,
  PERSONALITY_OTHER_CASES,
} from "./data/personality-cases";
import { FULL_RANGE, TRACKED_ATTRIBUTES, type TrackedAttribute } from "./domain/attributes";
import type { PlayerSignals } from "./domain/observations";
import {
  applyBands,
  applyPersonalityConditionals,
  emptyBandMap,
} from "./inference/bands";
import { applyCases } from "./inference/cases";
import { comboFeasibleForAttrs, type MatchableAttrs } from "./inference/match-combo";

export type PersonalityComboLabels = {
  personality: string;
  mediaHandling: string;
};

type BandMap = Partial<Record<TrackedAttribute, { min: number; max: number }>>;

function catalogBandsToMap(
  bands: Catalog["personalities"][number]["bands"],
): BandMap {
  const map: BandMap = {};
  for (const attribute of TRACKED_ATTRIBUTES) {
    const band = bands[attribute];
    if (band) map[attribute] = { min: band.min, max: band.max };
  }
  return map;
}

function pinKnownAttrs(bands: BandMap, attrs: MatchableAttrs): BandMap | null {
  let next = { ...bands };
  for (const attribute of TRACKED_ATTRIBUTES) {
    const raw = attrs[attribute];
    if (raw == null || !Number.isFinite(raw)) continue;
    const value = raw as number;
    const existing = next[attribute] ?? { ...FULL_RANGE };
    if (value < existing.min || value > existing.max) return null;
    next[attribute] = { min: value, max: value };
  }
  return next;
}

/** Projected bands for a feasible combo (for tightness tie-break). */
function projectedBands(
  catalog: Catalog,
  personalityId: string,
  mediaHandling: string,
  attrs: MatchableAttrs,
): BandMap | null {
  const personality = findPersonality(catalog, personalityId);
  const media = findMediaHandling(catalog, mediaHandling);
  if (!personality || !media) return null;

  const isRegen = Boolean(attrs.isRegen);
  const signals: PlayerSignals = {
    personality: personality.id,
    mediaHandling: media.styles,
    ...(attrs.isRegen !== undefined ? { isRegen: attrs.isRegen } : {}),
    ...(attrs.age !== undefined ? { age: attrs.age } : {}),
    ...(attrs.determination != null && Number.isFinite(attrs.determination)
      ? { determination: attrs.determination }
      : {}),
    ...(attrs.leadership != null && Number.isFinite(attrs.leadership)
      ? { leadership: attrs.leadership }
      : {}),
  };

  let bands = emptyBandMap();
  {
    const applied = applyBands(bands, catalogBandsToMap(personality.bands));
    if (applied.contradictions.length > 0) return null;
    bands = applied.bands;
  }
  bands = applyPersonalityConditionals(personality, signals, bands);
  {
    const applied = applyBands(bands, catalogBandsToMap(media.bands));
    if (applied.contradictions.length > 0) return null;
    bands = applied.bands;
  }
  const pinned = pinKnownAttrs(bands, attrs);
  if (!pinned) return null;
  bands = pinned;

  const mediaCaseDefs = catalog.cases.filter((c) => media.cases.includes(c.id));
  if (mediaCaseDefs.length > 0) {
    const caseResult = applyCases(bands, mediaCaseDefs, "union_feasible");
    if (caseResult.unsatisfiable.length > 0) return null;
    bands = caseResult.bands;
  }

  const flags = caseFlagsFor(personality.id, isRegen);
  const otherCaseDefs = PERSONALITY_OTHER_CASES.filter((c) => flags.other.includes(c.id));
  if (otherCaseDefs.length > 0) {
    const caseResult = applyCases(bands, otherCaseDefs, "union_feasible");
    if (caseResult.unsatisfiable.length > 0) return null;
    bands = caseResult.bands;
  }

  return bands;
}

function bandTightness(bands: BandMap): number {
  let tight = 0;
  for (const key of TRACKED_ATTRIBUTES) {
    const band = bands[key];
    if (!band || (band.min === FULL_RANGE.min && band.max === FULL_RANGE.max)) continue;
    tight += band.max - band.min;
  }
  return tight;
}

/**
 * Best personality × media label for known attributes.
 * Returns null when nothing is feasible (incomplete pack / no match).
 */
export function matchBestPersonalityCombo(
  attrs: MatchableAttrs,
  catalog: Catalog = loadCatalog(),
): PersonalityComboLabels | null {
  type Hit = {
    personality: string;
    mediaHandling: string;
    catalogIndex: number;
    tightness: number;
  };

  const hits: Hit[] = [];
  let catalogIndex = 0;
  for (const personality of catalog.personalities) {
    for (const media of catalog.mediaHandling) {
      const mediaLabel = formatMediaHandlingLabel(media.styles);
      if (!comboFeasibleForAttrs(catalog, personality.id, mediaLabel, attrs)) {
        catalogIndex += 1;
        continue;
      }
      const bands = projectedBands(catalog, personality.id, mediaLabel, attrs);
      hits.push({
        personality: personality.id,
        mediaHandling: mediaLabel,
        catalogIndex,
        tightness: bands ? bandTightness(bands) : Number.POSITIVE_INFINITY,
      });
      catalogIndex += 1;
    }
  }

  if (hits.length === 0) return null;

  const personalities = new Set(hits.map((h) => h.personality));
  const winners = new Set(personalities);
  for (const id of personalities) {
    const def = findPersonality(catalog, id);
    if (!def) continue;
    for (const better of def.prioritizedBy) {
      if (personalities.has(better)) {
        winners.delete(id);
        break;
      }
    }
  }
  const priorityHits = hits.filter((h) => winners.has(h.personality));
  const pool = priorityHits.length > 0 ? priorityHits : hits;

  let best: Hit | null = null;
  for (const entry of pool) {
    if (
      !best ||
      entry.tightness < best.tightness ||
      (entry.tightness === best.tightness && entry.catalogIndex < best.catalogIndex)
    ) {
      best = entry;
    }
  }
  if (!best) return null;

  const def = findPersonality(catalog, best.personality);
  const display =
    def?.aliases.find((alias) => alias.includes("-")) ??
    def?.aliases[0] ??
    best.personality;

  return { personality: display, mediaHandling: best.mediaHandling };
}
