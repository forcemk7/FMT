/**
 * FMT attribute / ability tone bands on the 1–20 scale (T208 experiment).
 *
 * Assumed normal N(μ=10, σ=3); band by z-score. Inverse attrs band on (21 − value).
 * Hex: `attr-colors.ts`. Color = zigma bands; ring fill = range % (`attrProgress` /
 * `abilityProgress` / `hasProgress`). Revert this + palette together if QA fails.
 *
 * | Band  | z        | ≈ value | Inverse |
 * |-------|----------|---------|---------|
 * | Super | ≥ +3     | 19–20   | 1–2     |
 * | High  | ≥ +2     | 16–18   | 3–5     |
 * | Upper | ≥ +1     | 13–15   | 6–8     |
 * | Mid   | > −1     | 8–12    | 9–13    |
 * | Low   | ≤ −1     | 1–7     | 14–20   |
 */

export type AttributeTone = "super" | "high" | "upper" | "mid" | "low";

/** Assumed mean on the 1–20 attr scale (SD experiment). */
export const ATTR_TONE_MEAN = 10;
/** Assumed standard deviation on the 1–20 attr scale (SD experiment). */
export const ATTR_TONE_SD = 3;

const INVERSE_ATTRIBUTES = new Set(["controversy", "injury proneness"]);

export function attributeZ(value: number): number {
  return (value - ATTR_TONE_MEAN) / ATTR_TONE_SD;
}

/** SD-based tone ranges — not user-editable. */
export function attributeBand(value: number): AttributeTone {
  if (!Number.isFinite(value)) return "mid";
  const z = attributeZ(value);
  if (z >= 3) return "super";
  if (z >= 2) return "high";
  if (z >= 1) return "upper";
  if (z > -1) return "mid";
  return "low";
}

export function isInverseAttribute(attribute: string): boolean {
  return INVERSE_ATTRIBUTES.has(attribute.trim().toLowerCase());
}

export function attributeTone(attribute: string, value: number): AttributeTone {
  if (!Number.isFinite(value)) return "mid";
  const scored = isInverseAttribute(attribute) ? 21 - value : value;
  return attributeBand(scored);
}

/**
 * Binary development color for recent deltas.
 * Gains → Super neon; drops → Low red. Inverse attrs flip which raw sign is good.
 */
export function attributeDeltaTone(
  attribute: string,
  delta: number,
): "super" | "low" | null {
  if (!Number.isFinite(delta) || delta === 0) return null;
  const improved = isInverseAttribute(attribute) ? delta < 0 : delta > 0;
  return improved ? "super" : "low";
}

/** CA/PA (1–200) use the same bands on tenths — continuous, no gaps. */
export function abilityToneFromScore(value: number): AttributeTone {
  return attributeBand(value / 10);
}

/** Clamp to [0, 1] for ring fill. Color still comes from {@link attributeBand}. */
export function unitProgress(ratio: number): number {
  if (!Number.isFinite(ratio)) return 0;
  return Math.max(0, Math.min(1, ratio));
}

/** Attr ring fill — % of 1–20 scale (19 → 0.95). */
export function attrProgress(value: number): number {
  return unitProgress(value / 20);
}

/** CA/PA ring fill — % of 0–200 scale (190 → 0.95). */
export function abilityProgress(value: number): number {
  return unitProgress(value / 200);
}
