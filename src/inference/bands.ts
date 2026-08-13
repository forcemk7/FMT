import type {
  AttributeRange,
  TrackedAttribute,
} from "../domain/attributes.js";
import { TRACKED_ATTRIBUTES, FULL_RANGE } from "../domain/attributes.js";
import { rawIntersect } from "../domain/range.js";
import type {
  MediaHandlingDefinition,
  PersonalityDefinition,
} from "../catalog/types.js";
import type { PlayerSignals } from "../domain/observations.js";

export type BandMap = Partial<Record<TrackedAttribute, AttributeRange>>;

export function emptyBandMap(): BandMap {
  return {};
}

export function fullBandMap(): BandMap {
  const map: BandMap = {};
  for (const attribute of TRACKED_ATTRIBUTES) {
    map[attribute] = { ...FULL_RANGE };
  }
  return map;
}

function catalogBandsToMap(
  bands: Partial<Record<TrackedAttribute, { min: number; max: number }>>,
): BandMap {
  const map: BandMap = {};
  for (const attribute of TRACKED_ATTRIBUTES) {
    const band = bands[attribute];
    if (band) map[attribute] = { min: band.min, max: band.max };
  }
  return map;
}

/**
 * Merge a catalog band onto an accumulating map (intersect).
 * Empty intersections keep the inverted range (e.g. 15–14) and are listed
 * in `contradictions` — matching spreadsheet cells for impossible combos.
 */
export function applyBands(
  current: BandMap,
  bands: BandMap,
): { bands: BandMap; contradictions: TrackedAttribute[] } {
  const next: BandMap = { ...current };
  const contradictions: TrackedAttribute[] = [];

  for (const attribute of TRACKED_ATTRIBUTES) {
    const incoming = bands[attribute];
    if (!incoming) continue;

    const existing = next[attribute];
    if (!existing) {
      next[attribute] = { ...incoming };
      continue;
    }

    const merged = rawIntersect(existing, incoming);
    next[attribute] = merged;
    if (merged.min > merged.max) {
      contradictions.push(attribute);
    }
  }

  return { bands: next, contradictions };
}

/**
 * Attributes where personality × media bands have no overlap.
 * Does not apply age/regen conditionals or cases — base catalog bands only.
 */
export function personalityMediaContradictions(
  personality: PersonalityDefinition,
  media: MediaHandlingDefinition,
): TrackedAttribute[] {
  const applied = applyBands(
    catalogBandsToMap(personality.bands),
    catalogBandsToMap(media.bands),
  );
  return applied.contradictions;
}

/** True when base personality × media bands all intersect cleanly. */
export function isPersonalityMediaCompatible(
  personality: PersonalityDefinition,
  media: MediaHandlingDefinition,
): boolean {
  return personalityMediaContradictions(personality, media).length === 0;
}

/**
 * Apply personality conditionals that we currently understand.
 * Unknown / TBD footnotes are left as raw notes for later parity work.
 */
export function applyPersonalityConditionals(
  personality: PersonalityDefinition,
  signals: PlayerSignals,
  bands: BandMap,
): BandMap {
  let next = { ...bands };

  for (const rule of personality.conditionals) {
    switch (rule.kind) {
      case "regen_range": {
        if (signals.isRegen) {
          next[rule.attribute] = { ...rule.range };
        }
        break;
      }
      case "if_over_age": {
        if (signals.age !== undefined && signals.age > rule.age) {
          const existing = next[rule.attribute];
          const incoming = rule.range;
          next[rule.attribute] = existing
            ? rawIntersect(existing, incoming)
            : { ...incoming };
        }
        break;
      }
      case "if_professionalism_in": {
        const professionalism = next.professionalism;
        if (
          professionalism &&
          professionalism.min >= rule.range.min &&
          professionalism.max <= rule.range.max &&
          professionalism.min <= professionalism.max
        ) {
          const existing = next[rule.thenAttribute];
          const incoming = rule.thenRange;
          next[rule.thenAttribute] = existing
            ? rawIntersect(existing, incoming)
            : { ...incoming };
        }
        break;
      }
      case "if_ambition_not": {
        const ambition = next.ambition;
        // Only apply when ambition is known exactly and ≠ value.
        if (
          ambition &&
          ambition.min === ambition.max &&
          ambition.min !== rule.value
        ) {
          const existing = next[rule.thenAttribute];
          const incoming = rule.thenRange;
          next[rule.thenAttribute] = existing
            ? rawIntersect(existing, incoming)
            : { ...incoming };
        }
        break;
      }
      case "regen_only":
      case "min_age":
      case "regen_loyalty_band":
      case "club_context":
      case "raw":
        // Eligibility / deferred rules — handled elsewhere or later.
        break;
      default: {
        const _exhaustive: never = rule;
        return _exhaustive;
      }
    }
  }

  return next;
}

export function assertPersonalityEligible(
  personality: PersonalityDefinition,
  signals: PlayerSignals,
): string[] {
  const warnings: string[] = [];

  for (const rule of personality.conditionals) {
    if (rule.kind === "regen_only" && signals.isRegen === false) {
      warnings.push(`${personality.id} is marked regen-only`);
    }
    if (
      rule.kind === "min_age" &&
      signals.age !== undefined &&
      signals.age <= rule.age
    ) {
      warnings.push(`${personality.id} requires age over ${rule.age}`);
    }
  }

  return warnings;
}
