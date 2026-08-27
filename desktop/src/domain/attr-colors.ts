/**
 * App-wide attribute / score tone palette — FMT design scheme.
 * Hex defaults are owner preference inherited by FMT (not SI / FM in-game chrome).
 * Band cutoffs live in `attribute-tone.ts`; call `toneCssVar` / `toneClassName` / `toneHex` anywhere.
 */

import type { AttributeTone } from "./attribute-tone";

export type AttrColorBand = AttributeTone;

/** Attr bands + HAS elite overflow (gold). */
export type AppTone = AttrColorBand | "super";

export type AttrColorPalette = Record<AttrColorBand, string>;

/** FMT default tone hexes (design scheme, not FM in-game). */
export const FMT_ATTR_TONE_COLORS: AttrColorPalette = {
  high: "#65e53a", // 16–20  R101 G229 B58
  upper: "#3a8acf", // 11–15  R58 G138 B207
  mid: "#e6e6fa", // 6–10   R230 G230 B250
  low: "#bd4e4e", // 1–5    R189 G78 B78
};

/** HAS-only elite above practical ceiling. */
export const APP_TONE_SUPER = "#d4b45a";

export const ATTR_COLOR_BANDS: Array<{ key: AttrColorBand; label: string; range: string }> = [
  { key: "high", label: "High", range: "16–20" },
  { key: "upper", label: "Upper", range: "11–15" },
  { key: "mid", label: "Mid", range: "6–10" },
  { key: "low", label: "Low", range: "1–5" },
];

const STORAGE_KEY = "fmt.attr-color-palette.v1";

const CSS_VARS: Record<AttrColorBand, string> = {
  high: "--attr-tone-high",
  upper: "--attr-tone-upper",
  mid: "--attr-tone-mid",
  low: "--attr-tone-low",
};

const SUPER_CSS_VAR = "--attr-tone-super";

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
  root.style.setProperty(SUPER_CSS_VAR, APP_TONE_SUPER);
}

/** CSS custom property name for a tone (`--attr-tone-mid`, …). */
export function toneCssVar(tone: AppTone): string {
  if (tone === "super") return SUPER_CSS_VAR;
  return CSS_VARS[tone];
}

/** Utility class for a tone (`attr-tone-mid`, …). */
export function toneClassName(tone: AppTone): string {
  return `attr-tone-${tone}`;
}

/** Default hex for a tone (ignores user Settings overrides). */
export function toneDefaultHex(tone: AppTone): string {
  if (tone === "super") return APP_TONE_SUPER;
  return FMT_ATTR_TONE_COLORS[tone];
}

/** Resolve hex from palette (or default), including super. */
export function toneHex(tone: AppTone, palette: AttrColorPalette = FMT_ATTR_TONE_COLORS): string {
  if (tone === "super") return APP_TONE_SUPER;
  return palette[tone] ?? FMT_ATTR_TONE_COLORS[tone];
}
