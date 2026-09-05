/**
 * App-wide attribute / score tone palette — FMT design scheme.
 * Hex defaults are owner preference (not SI / FM in-game chrome).
 * Band cutoffs: `attribute-tone.ts` (T208 SD + Super experiment).
 */

import type { AttributeTone } from "./attribute-tone";

export type AttrColorBand = AttributeTone;

export type AppTone = AttributeTone;

export type AttrColorPalette = Record<AttrColorBand, string>;

/** FMT default tone hexes. Super = neon eye-catcher; High = solid matte green (blue-weight). */
export const FMT_ATTR_TONE_COLORS: AttrColorPalette = {
  super: "#65e53a", // 19–20 (z≥+3) — eye-catcher
  high: "#2f9e4f", // 16–18 (z≥+2) — solid matte (match blue weight)
  upper: "#3a8acf", // 13–15 (z≥+1)
  mid: "#e6e6fa", // 8–12 (|z|<1)
  low: "#bd4e4e", // 1–7 (z≤−1)
};

/** Alias kept for call sites / tests. */
export const APP_TONE_SUPER = FMT_ATTR_TONE_COLORS.super;

export const ATTR_COLOR_BANDS: Array<{ key: AttrColorBand; label: string; range: string }> = [
  { key: "super", label: "Super", range: "19–20 · z≥+3" },
  { key: "high", label: "High", range: "16–18 · z≥+2" },
  { key: "upper", label: "Upper", range: "13–15 · z≥+1" },
  { key: "mid", label: "Mid", range: "8–12 · |z|<1" },
  { key: "low", label: "Low", range: "1–7 · z≤−1" },
];

const STORAGE_KEY = "fmt.attr-color-palette.v2";

const CSS_VARS: Record<AttrColorBand, string> = {
  super: "--attr-tone-super",
  high: "--attr-tone-high",
  upper: "--attr-tone-upper",
  mid: "--attr-tone-mid",
  low: "--attr-tone-low",
};

function normalizeHex(value: string): string | null {
  const trimmed = value.trim().toLowerCase();
  if (/^#[0-9a-f]{6}$/.test(trimmed)) return trimmed;
  if (/^#[0-9a-f]{3}$/.test(trimmed)) {
    const [, a, b, c] = trimmed;
    return `#${a}${a}${b}${b}${c}${c}`;
  }
  return null;
}

export function loadAttrColorPalette(): AttrColorPalette {
  if (typeof window === "undefined") return { ...FMT_ATTR_TONE_COLORS };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...FMT_ATTR_TONE_COLORS };
    const parsed = JSON.parse(raw) as Partial<AttrColorPalette>;
    return {
      super: normalizeHex(parsed.super ?? "") ?? FMT_ATTR_TONE_COLORS.super,
      high: normalizeHex(parsed.high ?? "") ?? FMT_ATTR_TONE_COLORS.high,
      upper: normalizeHex(parsed.upper ?? "") ?? FMT_ATTR_TONE_COLORS.upper,
      mid: normalizeHex(parsed.mid ?? "") ?? FMT_ATTR_TONE_COLORS.mid,
      low: normalizeHex(parsed.low ?? "") ?? FMT_ATTR_TONE_COLORS.low,
    };
  } catch {
    return { ...FMT_ATTR_TONE_COLORS };
  }
}

export function saveAttrColorPalette(palette: AttrColorPalette) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(palette));
}

export function applyAttrColorPalette(palette: AttrColorPalette) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  for (const band of ATTR_COLOR_BANDS) {
    root.style.setProperty(CSS_VARS[band.key], palette[band.key]);
  }
}

/** CSS custom property name for a tone (`--attr-tone-mid`, …). */
export function toneCssVar(tone: AppTone): string {
  return CSS_VARS[tone];
}

/** Utility class for a tone (`attr-tone-mid`, …). */
export function toneClassName(tone: AppTone): string {
  return `attr-tone-${tone}`;
}

/** Default hex for a tone (ignores user Settings overrides). */
export function toneDefaultHex(tone: AppTone): string {
  return FMT_ATTR_TONE_COLORS[tone];
}

/** Resolve hex from palette (or default). */
export function toneHex(tone: AppTone, palette: AttrColorPalette = FMT_ATTR_TONE_COLORS): string {
  return palette[tone] ?? FMT_ATTR_TONE_COLORS[tone];
}
