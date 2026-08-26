/** Wide leftover plates (after trim) fill the square via cover. */
export const BADGE_WIDE_ASPECT = 1.25;

export function badgeObjectFit(naturalWidth: number, naturalHeight: number): "cover" | "contain" {
  if (!naturalWidth || !naturalHeight) return "contain";
  return naturalWidth / naturalHeight >= BADGE_WIDE_ASPECT ? "cover" : "contain";
}
