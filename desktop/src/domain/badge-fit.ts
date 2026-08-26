/**
 * Wide leftover plates (after trim) may use cover outside the fact row.
 * Tall crests must stay on contain — cover makes them overflow the frame.
 */
export const BADGE_WIDE_ASPECT = 1.25;

export function badgeObjectFit(naturalWidth: number, naturalHeight: number): "cover" | "contain" {
  if (!naturalWidth || !naturalHeight) return "contain";
  const aspect = naturalWidth / naturalHeight;
  if (aspect >= BADGE_WIDE_ASPECT) return "cover";
  return "contain";
}
