/** Filtered Dashboard views — peeks on Dashboard, full lists on dedicated screens. */

export const DASH_VIEW_IDS = [
  "Movers",
  "Prospects",
  "Match experience",
  "HAS Top",
  "HAS Bottom",
] as const;

export type DashViewId = (typeof DASH_VIEW_IDS)[number];

export const DASH_PEEK_SIZE = 5;

export function isDashViewId(value: string): value is DashViewId {
  return (DASH_VIEW_IDS as readonly string[]).includes(value);
}

export function dashViewTitle(id: DashViewId): string {
  switch (id) {
    case "Movers":
      return "Attribute changes";
    case "Prospects":
      return "First-team path";
    case "Match experience":
      return "Match experience";
    case "HAS Top":
      return "Top personalities";
    case "HAS Bottom":
      return "Worst personalities";
  }
}

export function dashViewBlurb(id: DashViewId): string {
  switch (id) {
    case "Movers":
      return "Attribute changes since the last recorded change-point";
    case "Prospects":
      return "Non–First Team players with First Team upside (PA + mentor room)";
    case "Match experience":
      return "Under N / Reserves players who would be #1 or #2 same-pos on a First Team";
    case "HAS Top":
      return "Highest hidden-attribute scores on the managed squad";
    case "HAS Bottom":
      return "Lowest hidden-attribute scores on the managed squad";
  }
}

/** Profile tab when opening a player from a dashboard peek / full view. */
export function dashViewProfileTab(
  id: DashViewId,
): "attributes" | "match-experience" {
  return id === "Match experience" ? "match-experience" : "attributes";
}
