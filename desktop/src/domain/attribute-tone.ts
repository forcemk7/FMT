/**
 * FMT attribute / ability tone bands on the 1–20 scale (design scheme).
 * Standard: 16–20 high, 11–15 upper, 6–10 mid, 1–5 low.
 * Inverse (low better): Controversy, Injury Proneness — mirrored bands.
 * Hex colors: see `attr-colors.ts` (FMT preference palette, not FM chrome).
 */

export type AttributeTone = "high" | "upper" | "mid" | "low";

const INVERSE_ATTRIBUTES = new Set(["controversy", "injury proneness"]);

const BAND_INVERT: Record<AttributeTone, AttributeTone> = {
  high: "low",
  upper: "mid",
  mid: "upper",
  low: "high",
};

/** Fixed FMT tone ranges — not user-editable (T153). */
export function attributeBand(value: number): AttributeTone {
  if (!Number.isFinite(value)) return "mid";
  if (value >= 16) return "high";
  if (value >= 11) return "upper";
  if (value >= 6) return "mid";
  return "low";
}

export function isInverseAttribute(attribute: string): boolean {
  return INVERSE_ATTRIBUTES.has(attribute.trim().toLowerCase());
}

export function attributeTone(attribute: string, value: number): AttributeTone {
  if (!Number.isFinite(value)) return "mid";
  const band = attributeBand(value);
  return isInverseAttribute(attribute) ? BAND_INVERT[band] : band;
}

/**
 * Binary development color for recent deltas.
 * Positive raw change is good (green) except inverse attrs
 * (Controversy, Injury Proneness), where a drop is good.
 */
export function attributeDeltaTone(
  attribute: string,
  delta: number,
): "high" | "low" | null {
  if (!Number.isFinite(delta) || delta === 0) return null;
  const improved = isInverseAttribute(attribute) ? delta < 0 : delta > 0;
  return improved ? "high" : "low";
}

/** CA/PA (1–200) use the same bands on tenths. */
export function abilityToneFromScore(value: number): AttributeTone {
  return attributeBand(value / 10);
}
