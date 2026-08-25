/**
 * OG FMT spreadsheet tones for attribute midpoints.
 * Most attrs: >14 good, 0&lt;x&lt;6 bad; Controversy inverted.
 */

export type AttributeTone = "good" | "bad" | "neutral";

export function attributeTone(attribute: string, value: number): AttributeTone {
  if (!Number.isFinite(value)) return "neutral";
  const key = attribute.trim().toLowerCase();
  if (key === "important matches") return "neutral";
  if (key === "controversy") {
    if (value > 0 && value < 6) return "good";
    if (value > 14) return "bad";
    return "neutral";
  }
  if (value > 14) return "good";
  if (value > 0 && value < 6) return "bad";
  return "neutral";
}
