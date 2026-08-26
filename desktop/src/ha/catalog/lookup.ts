import {
  MEDIA_STYLE_ABBREVIATIONS,
  MEDIA_STYLE_TAGS,
  type MediaStyleTag,
} from "../domain/observations";
import { MEDIA_CASES } from "../data/cases";
import { MEDIA_HANDLING } from "../data/media-handling";
import { PERSONALITIES } from "../data/personalities";
import type {
  Catalog,
  MediaHandlingDefinition,
  PersonalityDefinition,
} from "./types";

export function loadCatalog(): Catalog {
  return {
    personalities: PERSONALITIES,
    mediaHandling: MEDIA_HANDLING,
    cases: MEDIA_CASES,
  };
}

function normalizeKey(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[_/]+/g, " ")
    .replace(/-/g, " ")
    .replace(/\s+/g, " ");
}

export function findPersonality(
  catalog: Catalog,
  name: string,
): PersonalityDefinition | undefined {
  const key = normalizeKey(name);
  return catalog.personalities.find(
    (p) =>
      normalizeKey(p.id) === key ||
      p.aliases.some((alias) => normalizeKey(alias) === key),
  );
}

function canonicalTag(raw: string): MediaStyleTag | undefined {
  const trimmed = raw.trim();
  if (!trimmed) return undefined;

  const asAbbrev = MEDIA_STYLE_ABBREVIATIONS[trimmed];
  if (asAbbrev) return asAbbrev;

  const key = normalizeKey(trimmed);
  return MEDIA_STYLE_TAGS.find((tag) => normalizeKey(tag) === key);
}

/**
 * Parse spreadsheet abbreviations ("MF, Unf") or full names
 * ("Unflappable, Media-friendly") into ordered style tags.
 * Display order lives on the catalog row; matching ignores order.
 */
export function parseMediaHandlingInput(
  input: string | readonly MediaStyleTag[],
): MediaStyleTag[] {
  if (typeof input !== "string") {
    return [...input];
  }

  const parts = input.split(",").map((part) => part.trim()).filter(Boolean);
  const styles: MediaStyleTag[] = [];

  for (const part of parts) {
    const tag = canonicalTag(part);
    if (!tag) {
      throw new Error(`Unknown media handling style fragment: "${part}"`);
    }
    styles.push(tag);
  }

  if (styles.length === 0) {
    throw new Error(`Empty media handling style: "${input}"`);
  }

  return styles;
}

/** Order-insensitive identity for matching catalog rows. */
function stylesMatchKey(styles: readonly MediaStyleTag[]): string {
  return [...styles].map((tag) => normalizeKey(tag)).sort().join("|");
}

export function findMediaHandling(
  catalog: Catalog,
  input: string | readonly MediaStyleTag[],
): MediaHandlingDefinition | undefined {
  const styles = parseMediaHandlingInput(input);
  const key = stylesMatchKey(styles);
  return catalog.mediaHandling.find(
    (row) => stylesMatchKey(row.styles) === key,
  );
}

/** In-game presentation order from the catalog row when known. */
export function formatMediaHandlingLabel(
  styles: readonly MediaStyleTag[],
): string {
  return styles.join(", ");
}
