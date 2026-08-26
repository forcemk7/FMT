/**
 * FM in-game attribute color bands on the 1–20 scale.
 * Standard: 16–20 high, 11–15 upper, 6–10 mid, 1–5 low.
 * Inverse (low better): Controversy, Injury Proneness — mirrored bands.
 */

export type AttributeTone = "high" | "upper" | "mid" | "low";

const INVERSE_ATTRIBUTES = new Set(["controversy", "injury proneness"]);

const BAND_INVERT: Record<AttributeTone, AttributeTone> = {
  high: "low",
  upper: "mid",
  mid: "upper",
  low: "high",
};

/** Fixed FM ranges — not user-editable (T153). */
export function attributeBand(value: number): AttributeTone {
  if (!Number.isFinite(value)) return "mid";
  if (value >= 16) return "high";
  if (value >= 11) return "upper";
  if (value >= 6) return "mid";
  return "low";
}

export function attributeTone(attribute: string, value: number): AttributeTone {
  if (!Number.isFinite(value)) return "mid";
  const band = attributeBand(value);
  const key = attribute.trim().toLowerCase();
  return INVERSE_ATTRIBUTES.has(key) ? BAND_INVERT[band] : band;
}

/** CA/PA (1–200) use the same bands on tenths. */
export function abilityToneFromScore(value: number): AttributeTone {
  return attributeBand(value / 10);
}
