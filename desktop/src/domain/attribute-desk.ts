/**
 * FM-style attribute desk groups (outfield vs GK) and Goalkeeper Rating /10.
 *
 * Native FM outfield desk shows Goalkeeper Rating from GK position familiarity
 * (0–20 blob → capped 0–10). Prefer {@link nativeGoalkeeperRating}; the mean
 * fallback is only for incomplete payloads.
 */

export const TECHNICAL_ATTRIBUTES = [
  "Crossing",
  "Dribbling",
  "Finishing",
  "First Touch",
  "Heading",
  "Long Shots",
  "Marking",
  "Passing",
  "Tackling",
  "Technique",
] as const;

/** GK profile shows only these under Technical (rest live in the header tooltip). */
export const GK_TECHNICAL_ATTRIBUTES = [
  "Free Kick Taking",
  "Penalty Taking",
  "Technique",
] as const;

export const MENTAL_ATTRIBUTES = [
  "Aggression",
  "Anticipation",
  "Bravery",
  "Composure",
  "Concentration",
  "Decisions",
  "Determination",
  "Flair",
  "Leadership",
  "Off the Ball",
  "Positioning",
  "Teamwork",
  "Vision",
  "Work Rate",
] as const;

export const PHYSICAL_ATTRIBUTES = [
  "Acceleration",
  "Agility",
  "Balance",
  "Jumping Reach",
  "Natural Fitness",
  "Pace",
  "Stamina",
  "Strength",
] as const;

export const SET_PIECE_ATTRIBUTES = [
  "Corners",
  "Free Kick Taking",
  "Penalty Taking",
  "Long Throws",
] as const;

export const GOALKEEPING_ATTRIBUTES = [
  "Aerial Reach",
  "Command of Area",
  "Communication",
  "Eccentricity",
  "Handling",
  "Kicking",
  "One on Ones",
  "Punching",
  "Reflexes",
  "Rushing Out",
  "Throwing",
] as const;

/** Folded into GK Goalkeeping column (from Technical), then alpha-sorted with GK attrs. */
export const GK_GOALKEEPING_FROM_TECHNICAL = ["First Touch", "Passing"] as const;

export const HIDDEN_ATTRIBUTES = [
  "Consistency",
  "Dirtiness",
  "Important Matches",
  "Injury Proneness",
  "Versatility",
] as const;

export const PERSONALITY_ATTRIBUTES = [
  "Adaptability",
  "Ambition",
  "Controversy",
  "Loyalty",
  "Pressure",
  "Professionalism",
  "Sportsmanship",
  "Temperament",
] as const;

export function isGoalkeeperPosition(positions: string[] | undefined | null): boolean {
  return (positions ?? []).some((position) => /\bGK\b/i.test(position));
}

/** GK Technical header tooltip: full technical set + the three shown attrs, A–Z. */
export function gkTechnicalTooltipNames(): string[] {
  return [...new Set([...TECHNICAL_ATTRIBUTES, ...GK_TECHNICAL_ATTRIBUTES])].sort((a, b) =>
    a.localeCompare(b),
  );
}

/** GK Goalkeeping column: core GK attrs + First Touch + Passing, A–Z. */
export function gkGoalkeepingAttributeNames(): string[] {
  return [...GOALKEEPING_ATTRIBUTES, ...GK_GOALKEEPING_FROM_TECHNICAL].sort((a, b) =>
    a.localeCompare(b),
  );
}

export function sortedAttributeEntries(
  names: readonly string[],
  values: Record<string, number | null> | undefined,
): { name: string; value: number | null }[] {
  return [...names]
    .sort((a, b) => a.localeCompare(b))
    .map((name) => {
      const raw = values?.[name];
      return { name, value: typeof raw === "number" ? raw : null };
    });
}

/**
 * Prefer live GK position familiarity (`player.goalkeeperRating`).
 * Falls back to round(mean(column attrs)/2) only when the native field is missing.
 */
export function nativeGoalkeeperRating(rating: number | null | undefined): number | null {
  if (typeof rating !== "number" || !Number.isFinite(rating)) return null;
  return Math.max(0, Math.min(10, Math.round(rating)));
}

/**
 * Legacy mean fallback — prefer {@link nativeGoalkeeperRating} when the live field exists.
 */
export function goalkeeperRating(
  values: Record<string, number | null> | undefined,
  names: readonly string[] = gkGoalkeepingAttributeNames(),
): number | null {
  const nums = names
    .map((name) => values?.[name])
    .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  if (!nums.length) return null;
  const mean = nums.reduce((sum, value) => sum + value, 0) / nums.length;
  return Math.max(0, Math.min(10, Math.round(mean / 2)));
}

export function resolveGoalkeeperRating(
  native: number | null | undefined,
  values: Record<string, number | null> | undefined,
): number | null {
  return nativeGoalkeeperRating(native) ?? goalkeeperRating(values);
}
