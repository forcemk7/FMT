import type { AttributeTone } from "./attribute-tone";

export type AttrColorBand = AttributeTone;

export type AttrColorPalette = Record<AttrColorBand, string>;

/** FM in-game RGB → hex (user-supplied). */
export const FM_IN_GAME_ATTR_COLORS: AttrColorPalette = {
  high: "#65e53a", // 16–20  R101 G229 B58
  upper: "#3a8acf", // 11–15  R58 G138 B207
  mid: "#e6e6fa", // 6–10   R230 G230 B250
  low: "#bd4e4e", // 1–5    R189 G78 B78
};

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
  if (typeof window === "undefined") return { ...FM_IN_GAME_ATTR_COLORS };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...FM_IN_GAME_ATTR_COLORS };
    const parsed = JSON.parse(raw) as Partial<AttrColorPalette>;
    return {
      high: normalizeHex(parsed.high ?? "") ?? FM_IN_GAME_ATTR_COLORS.high,
      upper: normalizeHex(parsed.upper ?? "") ?? FM_IN_GAME_ATTR_COLORS.upper,
      mid: normalizeHex(parsed.mid ?? "") ?? FM_IN_GAME_ATTR_COLORS.mid,
      low: normalizeHex(parsed.low ?? "") ?? FM_IN_GAME_ATTR_COLORS.low,
    };
  } catch {
    return { ...FM_IN_GAME_ATTR_COLORS };
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
