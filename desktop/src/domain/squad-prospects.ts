/**
 * Dashboard prospects: young high-PA players with Professionalism mentor room on squad.
 */

import type { LivePlayer } from "./adapters";

const YOUNG_AGE_HARD = 21;
const YOUNG_AGE_CAP = 23;
const MIN_YOUNG_POOL = 3;
const PRO_GAP_MIN = 2;
const DEFAULT_LIMIT = 8;

export type SquadProspect = {
  player: LivePlayer;
  pa: number;
  caMedian: number;
  paAboveMedian: number;
  professionalism: number;
  mentor: LivePlayer;
  mentorPro: number;
  proGap: number;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function readPro(player: LivePlayer): number | null {
  const value = player.personalityAttributes?.Professionalism;
  return typeof value === "number" && value >= 1 && value <= 20 ? value : null;
}

/** Median of a non-empty sorted numeric list (average of middle pair when even). */
export function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[mid]!;
  return (sorted[mid - 1]! + sorted[mid]!) / 2;
}

export function squadMedianCa(squad: LivePlayer[]): number | null {
  const cas = squad
    .map((player) => player.currentAbility)
    .filter((value): value is number => isFiniteNumber(value));
  return median(cas);
}

/**
 * Age ≤ 21 when that pool is large enough; else youngest third of known-age
 * players, still capped at age ≤ 23.
 */
export function youngProspectCandidates(squad: LivePlayer[]): LivePlayer[] {
  const withAge = squad.filter(
    (player) => isFiniteNumber(player.age) && (player.age as number) <= YOUNG_AGE_CAP,
  );
  const hard = withAge.filter((player) => (player.age as number) <= YOUNG_AGE_HARD);
  if (hard.length >= MIN_YOUNG_POOL) return hard;

  const knownAge = squad
    .filter((player) => isFiniteNumber(player.age))
    .sort((a, b) => (a.age as number) - (b.age as number));
  if (!knownAge.length) return [];
  const take = Math.max(MIN_YOUNG_POOL, Math.ceil(knownAge.length / 3));
  return knownAge.slice(0, take).filter((player) => (player.age as number) <= YOUNG_AGE_CAP);
}

function bestProMentor(
  subject: LivePlayer,
  subjectPro: number,
  squad: LivePlayer[],
): { mentor: LivePlayer; mentorPro: number; proGap: number } | null {
  let best: { mentor: LivePlayer; mentorPro: number; proGap: number } | null = null;
  for (const candidate of squad) {
    if (candidate.id === subject.id) continue;
    const mentorPro = readPro(candidate);
    if (mentorPro == null) continue;
    const proGap = mentorPro - subjectPro;
    if (proGap < PRO_GAP_MIN) continue;
    if (
      !best ||
      proGap > best.proGap ||
      (proGap === best.proGap && candidate.name.localeCompare(best.mentor.name) < 0)
    ) {
      best = { mentor: candidate, mentorPro, proGap };
    }
  }
  return best;
}

/**
 * Young high-PA squad players who still have a clear Professionalism mentor on squad.
 * PA ≥ squad median CA; mentor Pro ≥ subject Pro + 2.
 */
export function rankSquadProspects(
  squad: LivePlayer[],
  limit = DEFAULT_LIMIT,
): SquadProspect[] {
  const caMedian = squadMedianCa(squad);
  if (caMedian == null) return [];

  const young = youngProspectCandidates(squad);
  const rows: SquadProspect[] = [];

  for (const player of young) {
    const pa = player.potentialAbility;
    if (!isFiniteNumber(pa) || pa < caMedian) continue;
    const professionalism = readPro(player);
    if (professionalism == null) continue;
    const mentorHit = bestProMentor(player, professionalism, squad);
    if (!mentorHit) continue;
    rows.push({
      player,
      pa,
      caMedian,
      paAboveMedian: pa - caMedian,
      professionalism,
      mentor: mentorHit.mentor,
      mentorPro: mentorHit.mentorPro,
      proGap: mentorHit.proGap,
    });
  }

  rows.sort((a, b) => {
    if (b.proGap !== a.proGap) return b.proGap - a.proGap;
    if (b.paAboveMedian !== a.paAboveMedian) return b.paAboveMedian - a.paAboveMedian;
    return a.player.name.localeCompare(b.player.name);
  });

  return rows.slice(0, Math.max(0, limit));
}
