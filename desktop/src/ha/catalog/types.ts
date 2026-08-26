import type {
  AttributeRange,
  HasAttribute,
  TrackedAttribute,
} from "../domain/attributes";
import type { MediaStyleTag } from "../domain/observations";

/** A band copied from the sheet; `star` marks a footnote in Notes. */
export type CatalogBand = AttributeRange & {
  star?: boolean;
};

/** Personality / media rows may constrain HAS / visible attrs. */
export type AttributeBands = Partial<Record<TrackedAttribute, CatalogBand>>;

/**
 * Conditionals attached to a personality row.
 * Kept explicit so we can expand parsing without reshaping callers.
 */
export type PersonalityConditional =
  | {
      kind: "regen_only";
    }
  | {
      kind: "min_age";
      age: number;
    }
  | {
      kind: "regen_range";
      attribute: HasAttribute;
      range: AttributeRange;
    }
  | {
      kind: "regen_loyalty_band";
      /** e.g. Loyal: 6-7 if regen */
      range: AttributeRange;
    }
  | {
      kind: "if_ambition_not";
      value: number;
      thenAttribute: HasAttribute;
      thenRange: AttributeRange;
    }
  | {
      kind: "if_professionalism_in";
      range: AttributeRange;
      thenAttribute: HasAttribute;
      thenRange: AttributeRange;
    }
  | {
      kind: "if_over_age";
      age: number;
      attribute: HasAttribute;
      range: AttributeRange;
    }
  | {
      kind: "club_context";
      /** e.g. Devoted if at favourite club */
      note: string;
    }
  | {
      kind: "raw";
      note: string;
    };

export type PersonalityDefinition = {
  id: string;
  /** Alternate display names that share this row (e.g. Very Loyal / Devoted). */
  aliases: string[];
  bands: AttributeBands;
  notes: string | null;
  /** Personalities that take priority over this one (sheet column L). */
  prioritizedBy: string[];
  conditionals: PersonalityConditional[];
};

/** One clause inside a media-handling case ("A and/or B"). */
export type CaseClause =
  | {
      kind: "range";
      attribute: HasAttribute;
      range: AttributeRange;
    }
  | {
      kind: "all";
      clauses: CaseClause[];
    };

export type MediaCase = {
  id: number;
  /** Human-readable rule from the sheet. */
  label: string;
  /** OR of clauses — at least one must hold. */
  anyOf: CaseClause[];
};

export type MediaHandlingDefinition = {
  id: string;
  styles: MediaStyleTag[];
  bands: AttributeBands;
  /** Case ids that must all be satisfied. */
  cases: number[];
};

export type Catalog = {
  personalities: PersonalityDefinition[];
  mediaHandling: MediaHandlingDefinition[];
  cases: MediaCase[];
};
