/** Filtered Dashboard views — peeks on Dashboard, full lists on dedicated screens. */

export const DASH_VIEW_IDS = ["Movers", "Prospects", "HAS Top", "HAS Bottom"] as const;

export type DashViewId = (typeof DASH_VIEW_IDS)[number];

export const DASH_PEEK_SIZE = 5;

export function isDashViewId(value: string): value is DashViewId {
  return (DASH_VIEW_IDS as readonly string[]).includes(value);
}

export function dashViewTitle(id: DashViewId): string {
  switch (id) {
    case "Movers":
      return "Movers";
    case "Prospects":
      return "Prospects";
    case "HAS Top":
      return "HAS Top";
    case "HAS Bottom":
      return "HAS Bottom";
  }
}

export function dashViewBlurb(id: DashViewId): string {
  switch (id) {
    case "Movers":
      return "Attribute changes since the last recorded change-point";
    case "Prospects":
      return "Young high-PA players with Professionalism mentor room";
    case "HAS Top":
      return "Highest hidden-attribute scores on the managed squad";
    case "HAS Bottom":
      return "Lowest hidden-attribute scores on the managed squad";
  }
}
