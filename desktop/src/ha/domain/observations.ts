import type { TrackedAttribute } from "./attributes";

/**
 * Atomic media-handling style tags.
 * Combinations are ordered lists of these (e.g. Outspoken + Unflappable).
 */
export const MEDIA_STYLE_TAGS = [
  "Outspoken",
  "Unflappable",
  "Short-tempered",
  "Confrontational",
  "Volatile",
  "Evasive",
  "Reserved",
  "Level-Headed",
  "Media-friendly",
] as const;

export type MediaStyleTag = (typeof MEDIA_STYLE_TAGS)[number];

/** Abbreviation → full tag (spreadsheet / in-game shorthand). */
export const MEDIA_STYLE_ABBREVIATIONS: Record<string, MediaStyleTag> = {
  Out: "Outspoken",
  Unf: "Unflappable",
  ST: "Short-tempered",
  St: "Short-tempered",
  Con: "Confrontational",
  Vol: "Volatile",
  Eva: "Evasive",
  Res: "Reserved",
  LH: "Level-Headed",
  MF: "Media-friendly",
};

export type PlayerSignals = {
  /** Empty / omitted until chosen — estimate runs on whatever is known so far. */
  personality?: string;
  mediaHandling?: string | readonly MediaStyleTag[];
  /** Known visible Determination (1–20). */
  determination?: number;
  /** Known visible Leadership (1–20). */
  leadership?: number;
  /** True when the player is a regen / newgen. */
  isRegen?: boolean;
  /** Player age in years; used by age-gated personalities. */
  age?: number;
};

export type ConstraintSource =
  | "personality"
  | "mediaHandling"
  | "determination"
  | "leadership"
  | "case"
  | "conditional";

export type AppliedConstraint = {
  source: ConstraintSource;
  attribute: TrackedAttribute;
  detail: string;
};
