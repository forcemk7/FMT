/**
 * Squad penalty-taker ranking from Penalty Taking, Composure, and Pressure.
 *
 * Important Matches is reserved for a later extract lock and is omitted from
 * the score until then. Weights are equal across the three available attrs.
 */

export const PENALTY_TAKER_ATTRS = [
  "penaltyTaking",
  "composure",
  "pressure",
] as const;

export type PenaltyTakerAttr = (typeof PENALTY_TAKER_ATTRS)[number];

/** Equal weight per available attribute (Important Matches not scored yet). */
export const PENALTY_TAKER_WEIGHTS: Record<PenaltyTakerAttr, number> = {
  penaltyTaking: 1,
  composure: 1,
  pressure: 1,
};

export const PENALTY_TAKER_WEIGHT_SUM = PENALTY_TAKER_ATTRS.reduce(
  (sum, key) => sum + PENALTY_TAKER_WEIGHTS[key],
  0,
);

export type PenaltyTakerCandidate = {
  id: string;
  name: string;
  penaltyTaking: number;
  composure: number;
  pressure: number;
  /** Reserved — ignored in scoring until modeled. */
  importantMatches?: number | null;
};

export type PenaltyTakerRankEntry = PenaltyTakerCandidate & {
  score: number;
  rank: number;
};

function finiteAttr(value: number | null | undefined): number | null {
  return value != null && Number.isFinite(value) ? value : null;
}

/** Weighted mean of Pen / Composure / Pressure (equal weights). */
export function penaltyTakerScore(
  input: Pick<
    PenaltyTakerCandidate,
    "penaltyTaking" | "composure" | "pressure"
  >,
): number {
  const pen = finiteAttr(input.penaltyTaking);
  const composure = finiteAttr(input.composure);
  const pressure = finiteAttr(input.pressure);
  if (pen == null || composure == null || pressure == null) {
    return Number.NaN;
  }
  return (
    (PENALTY_TAKER_WEIGHTS.penaltyTaking * pen +
      PENALTY_TAKER_WEIGHTS.composure * composure +
      PENALTY_TAKER_WEIGHTS.pressure * pressure) /
    PENALTY_TAKER_WEIGHT_SUM
  );
}

/**
 * Rank candidates by penalty-taker score (DESC). Ties break on name.
 * Returns at most `limit` rows (default 5). Candidates missing any of the
 * three scored attrs are skipped.
 */
export function rankPenaltyTakers(
  candidates: readonly PenaltyTakerCandidate[],
  limit = 5,
): PenaltyTakerRankEntry[] {
  const scored: PenaltyTakerRankEntry[] = [];
  for (const candidate of candidates) {
    const score = penaltyTakerScore(candidate);
    if (!Number.isFinite(score)) continue;
    scored.push({ ...candidate, score, rank: 0 });
  }
  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  });
  const top = scored.slice(0, Math.max(0, limit));
  return top.map((entry, i) => ({ ...entry, rank: i + 1 }));
}
