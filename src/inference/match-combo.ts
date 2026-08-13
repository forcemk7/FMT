/**
 * Point-classify a player into a personality × media combo.
 *
 * Ranking uses union-projected case bands (possibility ranges). Matching a
 * known attr point must instead require that the point is feasible under the
 * media's OR cases — otherwise looser styles (Media-friendly, Unflappable+MF)
 * absorb players that belong to stricter ones (Level-Headed, Unflappable).
 */

import type { Catalog } from "../catalog/types.js";
import {
  findMediaHandling,
  findPersonality,
  parseMediaHandlingInput,
} from "../catalog/lookup.js";
import {
  FULL_RANGE,
  TRACKED_ATTRIBUTES,
  type TrackedAttribute,
} from "../domain/attributes.js";
import {
  caseFlagsFor,
  PERSONALITY_OTHER_CASES,
} from "../data/personality-cases.js";
import { applyBands, applyPersonalityConditionals, emptyBandMap } from "./bands.js";
import { applyCases } from "./cases.js";
import type { PlayerSignals } from "../domain/observations.js";

export type MatchableAttrs = Partial<
  Record<TrackedAttribute, number | null | undefined>
> & {
  isRegen?: boolean;
  age?: number;
};

function catalogBandsToMap(
  bands: Catalog["personalities"][number]["bands"],
): ReturnType<typeof emptyBandMap> {
  const map = emptyBandMap();
  for (const attribute of TRACKED_ATTRIBUTES) {
    const band = bands[attribute];
    if (band) map[attribute] = { min: band.min, max: band.max };
  }
  return map;
}

function pinKnownAttrs(
  bands: ReturnType<typeof emptyBandMap>,
  attrs: MatchableAttrs,
): { bands: ReturnType<typeof emptyBandMap>; ok: boolean } {
  let next = { ...bands };
  for (const attribute of TRACKED_ATTRIBUTES) {
    const raw = attrs[attribute];
    if (raw == null || !Number.isFinite(raw)) continue;
    const value = raw as number;
    const existing = next[attribute] ?? { ...FULL_RANGE };
    if (value < existing.min || value > existing.max) {
      return { bands: next, ok: false };
    }
    next[attribute] = { min: value, max: value };
  }
  return { bands: next, ok: true };
}

/**
 * True when the player's known attrs can sit inside personality × media,
 * including media (and personality) case OR rules — not merely their
 * union-projected mid bands.
 */
export function comboFeasibleForAttrs(
  catalog: Catalog,
  personalityId: string,
  mediaHandling: string,
  attrs: MatchableAttrs,
): boolean {
  const personality = findPersonality(catalog, personalityId);
  const styles = parseMediaHandlingInput(mediaHandling);
  const media = findMediaHandling(catalog, styles);
  if (!personality || !media) return false;

  const isRegen = Boolean(attrs.isRegen);
  if (
    !isRegen &&
    personality.conditionals.some((rule) => rule.kind === "regen_only")
  ) {
    return false;
  }

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
    if (applied.contradictions.length > 0) return false;
    bands = applied.bands;
  }
  bands = applyPersonalityConditionals(personality, signals, bands);

  {
    const applied = applyBands(bands, catalogBandsToMap(media.bands));
    if (applied.contradictions.length > 0) return false;
    bands = applied.bands;
  }

  const pinned = pinKnownAttrs(bands, attrs);
  if (!pinned.ok) return false;
  bands = pinned.bands;

  // Non-full bands need known point attrs. Skipping unknowns lets Born Leader
  // (Det=20/Lea=20) stay "feasible" when Det/Lea are missing from extract, then
  // win on tightest-band ties over Light Hearted and similar.
  for (const attribute of TRACKED_ATTRIBUTES) {
    const band = bands[attribute];
    if (!band) continue;
    if (band.min === FULL_RANGE.min && band.max === FULL_RANGE.max) continue;
    const raw = attrs[attribute];
    if (raw == null || !Number.isFinite(raw)) return false;
  }

  const mediaCaseDefs = catalog.cases.filter((c) => media.cases.includes(c.id));
  if (mediaCaseDefs.length > 0) {
    const caseResult = applyCases(bands, mediaCaseDefs, "union_feasible");
    if (caseResult.unsatisfiable.length > 0) return false;
    bands = caseResult.bands;
  }

  const flags = caseFlagsFor(personality.id, isRegen);
  const otherCaseDefs = PERSONALITY_OTHER_CASES.filter((c) =>
    flags.other.includes(c.id),
  );
  if (otherCaseDefs.length > 0) {
    const caseResult = applyCases(bands, otherCaseDefs, "union_feasible");
    if (caseResult.unsatisfiable.length > 0) return false;
  }

  return true;
}
