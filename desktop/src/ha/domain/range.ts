import type { AttributeEstimate, AttributeRange } from "./attributes";
import { FULL_RANGE } from "./attributes";

export function isValidRange(range: AttributeRange): boolean {
  return (
    Number.isInteger(range.min) &&
    Number.isInteger(range.max) &&
    range.min >= FULL_RANGE.min &&
    range.max <= FULL_RANGE.max &&
    range.min <= range.max
  );
}

export function midpoint(range: AttributeRange): number {
  return (range.min + range.max) / 2;
}

export function toEstimate(range: AttributeRange): AttributeEstimate {
  const impossible = range.min > range.max;
  return {
    min: range.min,
    max: range.max,
    // Spreadsheet still averages inverted cells (e.g. 15-14 → 14.5).
    midpoint: midpoint(range),
    exact: !impossible && range.min === range.max,
    ...(impossible ? { impossible: true } : {}),
  };
}

/**
 * Always compute max(mins) / min(maxes), even when empty.
 * Empty intersections (min > max) match spreadsheet “15-14” cells and
 * flag personality × media combos that cannot exist in-game.
 */
export function rawIntersect(
  a: AttributeRange,
  b: AttributeRange,
): AttributeRange {
  return {
    min: Math.max(a.min, b.min),
    max: Math.min(a.max, b.max),
  };
}

/** Intersect ranges; returns null when empty (contradiction). */
export function intersect(
  a: AttributeRange,
  b: AttributeRange,
): AttributeRange | null {
  const merged = rawIntersect(a, b);
  if (merged.min > merged.max) return null;
  return merged;
}

export function intersectAll(
  ranges: readonly AttributeRange[],
): AttributeRange | null {
  if (ranges.length === 0) return { ...FULL_RANGE };
  let acc: AttributeRange = ranges[0]!;
  for (let i = 1; i < ranges.length; i++) {
    const next = intersect(acc, ranges[i]!);
    if (!next) return null;
    acc = next;
  }
  return acc;
}

/** Parse sheet cells like "15-20", "1", "01 - 20". */
export function parseRange(raw: string): AttributeRange | null {
  const text = raw.trim();
  if (!text || text === "-") return null;

  const collapsed = text.replace(/\s+/g, "");
  const span = /^(\d{1,2})-(\d{1,2})$/.exec(collapsed);
  if (span) {
    return { min: Number(span[1]), max: Number(span[2]) };
  }

  const single = /^(\d{1,2})$/.exec(collapsed);
  if (single) {
    const value = Number(single[1]);
    return { min: value, max: value };
  }

  throw new Error(`Unrecognized attribute range: "${raw}"`);
}

export function formatRange(range: AttributeRange): string {
  if (range.min === range.max) return String(range.min);
  return `${range.min}-${range.max}`;
}

export function isEmptyRange(range: AttributeRange): boolean {
  return range.min > range.max;
}
