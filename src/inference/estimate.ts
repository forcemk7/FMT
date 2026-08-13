import type { Catalog } from "../catalog/types.js";
import {
  findMediaHandling,
  findPersonality,
  formatMediaHandlingLabel,
  parseMediaHandlingInput,
} from "../catalog/lookup.js";
import type { AppliedConstraint, PlayerSignals } from "../domain/observations.js";
import { intersect, toEstimate } from "../domain/range.js";
import {
  ATTRIBUTE_LABELS,
  FULL_RANGE,
  HAS_ATTRIBUTES,
  TRACKED_ATTRIBUTES,
  isUnmodeledHiddenAttribute,
  type AttributeEstimates,
  type TrackedAttribute,
  type VisibleAttribute,
} from "../domain/attributes.js";
import {
  caseFlagsFor,
  DET_CASE_SPORTSMANSHIP,
  PERSONALITY_OTHER_CASES,
} from "../data/personality-cases.js";
import {
  applyBands,
  applyPersonalityConditionals,
  assertPersonalityEligible,
  emptyBandMap,
  type BandMap,
} from "./bands.js";
import { applyCases, type CaseMode } from "./cases.js";

export type EstimateOptions = {
  /** @deprecated Spreadsheet has no mode toggle; always union_feasible. */
  caseMode?: CaseMode;
};

export type FieldViolation = {
  field:
    | "personality"
    | "mediaHandling"
    | "age"
    | "determination"
    | "leadership"
    | "isRegen";
  message: string;
};

export type EstimateResult = {
  player: {
    personality?: string;
    mediaHandling?: string;
    determination?: number;
    leadership?: number;
    isRegen?: boolean;
    age?: number;
  };
  /** Estimated hidden-attribute ranges only. */
  attributes: AttributeEstimates;
  /** Allowed Det/Lead bands before pinning known values. */
  impliedVisible: {
    determination?: { min: number; max: number };
    leadership?: { min: number; max: number };
  };
  /** Attributes whose bands inverted (min > max) after intersecting sources. */
  contradictions: TrackedAttribute[];
  /**
   * True when personality × media base bands conflict on at least one attribute.
   * Strong signal the in-game combo does not exist (spreadsheet shows e.g. 15–14).
   */
  impossibleCombo: boolean;
  warnings: string[];
  violations: FieldViolation[];
  constraints: AppliedConstraint[];
  /** Case ids that could not be satisfied under the chosen mode. */
  unsatisfiableCases: number[];
  /** True when some signals are still missing (progressive / partial estimate). */
  partial: boolean;
};

function catalogBandsToMap(
  bands: Catalog["personalities"][number]["bands"],
): BandMap {
  const map: BandMap = {};
  for (const attribute of TRACKED_ATTRIBUTES) {
    const band = bands[attribute];
    if (band) {
      map[attribute] = { min: band.min, max: band.max };
    }
  }
  return map;
}

function pinVisibleInput(
  bands: BandMap,
  attribute: VisibleAttribute,
  value: number,
  constraints: AppliedConstraint[],
  contradictions: TrackedAttribute[],
  warnings: string[],
  violations: FieldViolation[],
): BandMap {
  const expected = bands[attribute];
  if (
    expected &&
    (value < expected.min || value > expected.max)
  ) {
    const message = `Known ${ATTRIBUTE_LABELS[attribute]} ${value} is outside ${ATTRIBUTE_LABELS[attribute]} ${expected.min}-${expected.max} implied by this combo`;
    warnings.push(message);
    violations.push({
      field: attribute === "determination" ? "determination" : "leadership",
      message,
    });
  }

  const applied = applyBands(bands, {
    [attribute]: { min: value, max: value },
  });
  contradictions.push(...applied.contradictions);
  constraints.push({
    source: attribute,
    attribute,
    detail: `known ${value}`,
  });
  return applied.bands;
}

function recordBandChanges(
  before: BandMap,
  after: BandMap,
  source: AppliedConstraint["source"],
  detail: string,
  constraints: AppliedConstraint[],
) {
  for (const attribute of HAS_ATTRIBUTES) {
    if (isUnmodeledHiddenAttribute(attribute)) continue;
    const prev = before[attribute] ?? { ...FULL_RANGE };
    const next = after[attribute] ?? { ...FULL_RANGE };
    if (prev.min !== next.min || prev.max !== next.max) {
      constraints.push({ source, attribute, detail });
    }
  }
}

/**
 * Per-player hidden-attribute estimate.
 * Applies whatever signals are known so far (personality and/or media, then
 * optional Det/Lead pins) so the UI can show progressive interim bands.
 */
export function estimatePlayer(
  catalog: Catalog,
  signals: PlayerSignals,
  options: EstimateOptions = {},
): EstimateResult {
  const caseMode: CaseMode = options.caseMode ?? "union_feasible";
  const warnings: string[] = [];
  const violations: FieldViolation[] = [];
  const constraints: AppliedConstraint[] = [];
  const contradictions: TrackedAttribute[] = [];
  const unsatisfiableCases: number[] = [];

  const personalityRaw = signals.personality?.trim() ?? "";
  const personality = personalityRaw
    ? findPersonality(catalog, personalityRaw)
    : undefined;
  if (personalityRaw && !personality) {
    throw new Error(`Unknown personality: "${signals.personality}"`);
  }

  const mediaRaw = signals.mediaHandling;
  const mediaProvided =
    mediaRaw !== undefined &&
    !(typeof mediaRaw === "string" && mediaRaw.trim() === "") &&
    !(Array.isArray(mediaRaw) && mediaRaw.length === 0);

  let styles: ReturnType<typeof parseMediaHandlingInput> = [];
  let media: ReturnType<typeof findMediaHandling> | undefined;
  if (mediaProvided) {
    styles = parseMediaHandlingInput(mediaRaw);
    media = findMediaHandling(catalog, styles);
    if (!media) {
      throw new Error(
        `Unknown media handling combination: "${formatMediaHandlingLabel(styles)}"`,
      );
    }
  }

  if (!personality && !media) {
    throw new Error("Select a personality or media handling to estimate");
  }

  if (personality) {
    for (const message of assertPersonalityEligible(personality, signals)) {
      warnings.push(message);
      if (message.includes("regen-only")) {
        violations.push({ field: "isRegen", message });
      } else if (message.includes("requires age")) {
        violations.push({ field: "age", message });
      } else {
        violations.push({ field: "personality", message });
      }
    }
  }

  const isRegen = Boolean(signals.isRegen);
  const flags = personality
    ? caseFlagsFor(personality.id, isRegen)
    : { det: [] as number[], other: [] as number[] };

  let bands = emptyBandMap();

  if (personality) {
    const personalityBands = catalogBandsToMap(personality.bands);
    {
      const applied = applyBands(bands, personalityBands);
      bands = applied.bands;
      contradictions.push(...applied.contradictions);
      for (const attribute of Object.keys(personalityBands) as TrackedAttribute[]) {
        constraints.push({
          source: "personality",
          attribute,
          detail: personality.id,
        });
      }
    }

    bands = applyPersonalityConditionals(personality, signals, bands);

    // Cases (det) — only case 5 is applied as a forward Spo floor in the sheet.
    if (flags.det.includes(DET_CASE_SPORTSMANSHIP.id)) {
      const before = { ...bands };
      const existing = bands.sportsmanship ?? { ...FULL_RANGE };
      const merged = intersect(existing, DET_CASE_SPORTSMANSHIP.range);
      if (merged) {
        bands = { ...bands, sportsmanship: merged };
        recordBandChanges(
          before,
          bands,
          "case",
          `personality det case ${DET_CASE_SPORTSMANSHIP.id}`,
          constraints,
        );
      }
    }
  }

  if (media) {
    const mediaBands = catalogBandsToMap(media.bands);
    {
      const applied = applyBands(bands, mediaBands);
      bands = applied.bands;
      contradictions.push(...applied.contradictions);
      for (const attribute of Object.keys(mediaBands) as TrackedAttribute[]) {
        constraints.push({
          source: "mediaHandling",
          attribute,
          detail: media.id,
        });
      }
      // Personality × media empty intersects → likely non-existent in-game combo.
      if (personality && applied.contradictions.length > 0) {
        const labels = [...new Set(applied.contradictions)]
          .map((attribute) => ATTRIBUTE_LABELS[attribute])
          .join(", ");
        const message = `Impossible personality / media combo — conflicting ${labels} (empty intersection; may not exist in-game)`;
        warnings.push(message);
        violations.push({ field: "personality", message });
        violations.push({ field: "mediaHandling", message });
      }
    }
  }

  const impliedVisible = {
    ...(bands.determination
      ? { determination: { ...bands.determination } }
      : {}),
    ...(bands.leadership ? { leadership: { ...bands.leadership } } : {}),
  };

  if (signals.determination !== undefined) {
    bands = pinVisibleInput(
      bands,
      "determination",
      signals.determination,
      constraints,
      contradictions,
      warnings,
      violations,
    );
  }

  if (signals.leadership !== undefined) {
    bands = pinVisibleInput(
      bands,
      "leadership",
      signals.leadership,
      constraints,
      contradictions,
      warnings,
      violations,
    );
  }

  if (media) {
    const mediaCaseDefs = catalog.cases.filter((c) => media.cases.includes(c.id));
    if (mediaCaseDefs.length > 0) {
      const before = { ...bands };
      const caseResult = applyCases(bands, mediaCaseDefs, caseMode);
      unsatisfiableCases.push(...caseResult.unsatisfiable);
      bands =
        caseMode === "union_feasible"
          ? caseResult.bands
          : applyBands(before, caseResult.bands).bands;
      recordBandChanges(
        before,
        bands,
        "case",
        `media cases [${mediaCaseDefs.map((c) => c.id).join(", ")}]`,
        constraints,
      );
    }
  }

  if (personality) {
    const otherCaseDefs = PERSONALITY_OTHER_CASES.filter((c) =>
      flags.other.includes(c.id),
    );
    if (otherCaseDefs.length > 0) {
      const before = { ...bands };
      const caseResult = applyCases(bands, otherCaseDefs, "union_feasible");
      unsatisfiableCases.push(...caseResult.unsatisfiable);
      bands = caseResult.bands;
      recordBandChanges(
        before,
        bands,
        "case",
        `personality other cases [${otherCaseDefs.map((c) => c.id).join(", ")}]`,
        constraints,
      );
    }
  }

  const attributes = {} as AttributeEstimates;
  for (const attribute of HAS_ATTRIBUTES) {
    if (isUnmodeledHiddenAttribute(attribute)) {
      attributes[attribute] = {
        min: FULL_RANGE.min,
        max: FULL_RANGE.max,
        midpoint: Number.NaN,
        exact: false,
        unmodeled: true,
      };
      continue;
    }
    const range = bands[attribute] ?? { ...FULL_RANGE };
    attributes[attribute] = toEstimate(range);
  }

  const uniqueContradictions = [...new Set(contradictions)];
  const uniqueUnsatisfiable = [...new Set(unsatisfiableCases)];
  const bandContradiction = uniqueContradictions.some((attribute) =>
    HAS_ATTRIBUTES.includes(attribute as (typeof HAS_ATTRIBUTES)[number]) &&
    !isUnmodeledHiddenAttribute(attribute as (typeof HAS_ATTRIBUTES)[number]),
  );
  // Unsatisfiable media/personality cases (e.g. case 2 vs Model Citizen · MF Unf)
  // match spreadsheet empty cells like Pro 15-12 — treat as impossible combos.
  const caseContradiction =
    Boolean(personality && media) && uniqueUnsatisfiable.length > 0;
  const impossibleCombo = Boolean(personality && media) &&
    (bandContradiction || caseContradiction);

  if (caseContradiction) {
    const message =
      `Impossible personality / media combo — unsatisfiable media case(s) [${uniqueUnsatisfiable.join(", ")}]`;
    if (!warnings.includes(message)) warnings.push(message);
    violations.push({ field: "personality", message });
    violations.push({ field: "mediaHandling", message });
  }

  return {
    player: {
      ...(personality ? { personality: personality.id } : {}),
      ...(media ? { mediaHandling: formatMediaHandlingLabel(media.styles) } : {}),
      ...(signals.determination !== undefined
        ? { determination: signals.determination }
        : {}),
      ...(signals.leadership !== undefined
        ? { leadership: signals.leadership }
        : {}),
      ...(signals.isRegen !== undefined ? { isRegen: signals.isRegen } : {}),
      ...(signals.age !== undefined ? { age: signals.age } : {}),
    },
    attributes,
    impliedVisible,
    contradictions: uniqueContradictions,
    impossibleCombo,
    warnings,
    violations,
    constraints,
    unsatisfiableCases: uniqueUnsatisfiable,
    partial: !personality || !media,
  };
}
