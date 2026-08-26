import type { LivePlayer } from "./adapters";
import { attributeTone } from "./attribute-tone";

/**
 * HAS weights — development + squad-impact hierarchy (FM Dossier / FM Stats).
 * Pro: linear primary driver. Pre: big-game/trophy weight. Det/Amb: floor to ~10, flat tail above.
 * Profile screens keep FM alphabetical order; only HAS views use {@link HAS_INPUTS} order.
 */
export type HasInputMode = "linear" | "diminishing" | "inverted";

type HasInputDef = {
  abbr: string;
  label: string;
  weight: number;
  mode: HasInputMode;
  toneKey: string;
  /** Required for HAS score, or optional bonus when mapped (Det/Lea). */
  required: boolean;
  read: (player: LivePlayer) => number | null;
};

const HAS_KNEE = 10;
const HAS_TAIL_FACTOR = 0.25;
export const HAS_DASHBOARD_LEADERBOARD_SIZE = 10;

const HAS_INPUTS: HasInputDef[] = [
  {
    abbr: "Pro",
    label: "Professionalism",
    weight: 7,
    mode: "linear",
    toneKey: "professionalism",
    required: true,
    read: (p) => readAttr(p.personalityAttributes?.Professionalism),
  },
  {
    abbr: "Pre",
    label: "Pressure",
    weight: 5,
    mode: "linear",
    toneKey: "pressure",
    required: true,
    read: (p) => readAttr(p.personalityAttributes?.Pressure),
  },
  {
    abbr: "Det",
    label: "Determination",
    weight: 3,
    mode: "diminishing",
    toneKey: "determination",
    required: false,
    read: (p) => readAttr(p.attributes?.Determination),
  },
  {
    abbr: "Amb",
    label: "Ambition",
    weight: 3,
    mode: "diminishing",
    toneKey: "ambition",
    required: true,
    read: (p) => readAttr(p.personalityAttributes?.Ambition),
  },
  {
    abbr: "Lea",
    label: "Leadership",
    weight: 3,
    mode: "linear",
    toneKey: "leadership",
    required: false,
    read: (p) => readAttr(p.attributes?.Leadership),
  },
  {
    abbr: "Loy",
    label: "Loyalty",
    weight: 2,
    mode: "linear",
    toneKey: "loyalty",
    required: true,
    read: (p) => readAttr(p.personalityAttributes?.Loyalty),
  },
  {
    abbr: "Tem",
    label: "Temperament",
    weight: 1,
    mode: "linear",
    toneKey: "temperament",
    required: true,
    read: (p) => readAttr(p.personalityAttributes?.Temperament),
  },
  {
    abbr: "Spo",
    label: "Sportsmanship",
    weight: 1,
    mode: "linear",
    toneKey: "sportsmanship",
    required: true,
    read: (p) => readAttr(p.personalityAttributes?.Sportsmanship),
  },
  {
    abbr: "Con",
    label: "Controversy",
    weight: 2,
    mode: "inverted",
    toneKey: "controversy",
    required: true,
    read: (p) => readAttr(p.personalityAttributes?.Controversy),
  },
];

export type HasCalculationSpec = {
  abbr: string;
  label: string;
  weight: number;
  mode: HasInputMode;
  rationale: string;
};

/** Living doc for Settings → Frontend calculations (weights must match {@link HAS_INPUTS}). */
export const HAS_CALCULATION_SPECS: HasCalculationSpec[] = [
  {
    abbr: "Pro",
    label: "Professionalism",
    weight: 7,
    mode: "linear",
    rationale: "Primary development driver — linear across 1–20 (FM Stats / FM Dossier).",
  },
  {
    abbr: "Pre",
    label: "Pressure",
    weight: 5,
    mode: "linear",
    rationale: "Big-game and trophy performance; correlates with Important Matches.",
  },
  {
    abbr: "Det",
    label: "Determination",
    weight: 3,
    mode: "diminishing",
    rationale: "Floor matters (~8–10); gains above 10 flatten (diminishing returns).",
  },
  {
    abbr: "Amb",
    label: "Ambition",
    weight: 3,
    mode: "diminishing",
    rationale: "Same diminishing curve as Det — necessary, not a headline above mid-range.",
  },
  {
    abbr: "Lea",
    label: "Leadership",
    weight: 3,
    mode: "linear",
    rationale: "On-pitch influence plus mentoring / squad rub-off.",
  },
  {
    abbr: "Loy",
    label: "Loyalty",
    weight: 2,
    mode: "linear",
    rationale: "Squad retention — less rebuild churn, not raw ability.",
  },
  {
    abbr: "Tem",
    label: "Temperament",
    weight: 1,
    mode: "linear",
    rationale: "Conduct when things go wrong; discipline proxy.",
  },
  {
    abbr: "Spo",
    label: "Sportsmanship",
    weight: 1,
    mode: "linear",
    rationale: "Fair play / booking risk proxy.",
  },
  {
    abbr: "Con",
    label: "Controversy",
    weight: 2,
    mode: "inverted",
    rationale: "Scored as 21 − Con — lower is better for a quiet dressing room.",
  },
];

/** Personality / hidden attrs not in HAS weighting. */
export const HAS_EXCLUDED_ATTRIBUTES = [
  "Adaptability",
  "Consistency",
  "Dirtiness",
  "Important Matches",
  "Injury Proneness",
  "Versatility",
] as const;

export type FrontendCalculationCard = {
  key: string;
  badge: string;
  state: "passed" | "pending" | "warning";
  title: string;
  detail: string;
};

function hasCalculationDetail() {
  const weights = HAS_CALCULATION_SPECS.map((spec) => {
    if (spec.mode === "diminishing") return `${spec.abbr}×${spec.weight} dim>10`;
    if (spec.mode === "inverted") return `${spec.abbr}×${spec.weight} 21−x`;
    return `${spec.abbr}×${spec.weight}`;
  }).join(", ");
  const excluded = HAS_EXCLUDED_ATTRIBUTES.join(", ");
  return `Σ(w×eff)/Σ(w): ${weights}. Excluded: ${excluded}.`;
}

/** Settings → Frontend calculations cards (one row per FMT model). */
export const FRONTEND_CALCULATION_CARDS: FrontendCalculationCard[] = [
  {
    key: "has",
    badge: "Live",
    state: "passed",
    title: "Hidden attribute score (HAS)",
    detail: hasCalculationDetail(),
  },
  {
    key: "personality-media",
    badge: "Live",
    state: "passed",
    title: "Personality × Media Handling labels",
    detail:
      "Catalog band match on HA pack + Det/Lea (FM HA Calculator). Shown on the profile header. Incomplete pack → —.",
  },
];

export type HasTone = "high" | "upper" | "mid" | "low";

export type HasBreakdownRow = {
  abbr: string;
  label: string;
  value: number;
  tone: HasTone;
};

function readAttr(value: number | null | undefined) {
  return typeof value === "number" && value >= 1 && value <= 20 ? value : null;
}

function invertControversy(controversy: number) {
  return 21 - controversy;
}

/** Meaningful to ~10, then diminishing tail (FM Stats development research). */
export function diminishingPersonalityValue(value: number, knee = HAS_KNEE, tailFactor = HAS_TAIL_FACTOR) {
  if (value <= knee) return value;
  return knee + (value - knee) * tailFactor;
}

function effectiveHasValue(value: number, mode: HasInputMode) {
  if (mode === "inverted") return invertControversy(value);
  if (mode === "diminishing") return diminishingPersonalityValue(value);
  return value;
}

function hasContributions(player: LivePlayer) {
  const rows: Array<{ def: HasInputDef; raw: number; effective: number }> = [];
  for (const def of HAS_INPUTS) {
    const raw = def.read(player);
    if (raw == null) {
      if (def.required) return null;
      continue;
    }
    rows.push({ def, raw, effective: effectiveHasValue(raw, def.mode) });
  }
  return rows;
}

/** Presentation order for HAS widgets — importance high → low. */
export function liveHasBreakdown(player: LivePlayer): HasBreakdownRow[] {
  const contributions = hasContributions(player);
  if (!contributions) return [];
  return contributions.map(({ def, raw }) => ({
    abbr: def.abbr,
    label: def.label,
    value: raw,
    tone: attributeTone(def.toneKey, raw),
  }));
}

/** Weighted HAS from live personality (+ Det/Lea when mapped). */
export function liveHasScore(player: LivePlayer): number | null {
  const contributions = hasContributions(player);
  if (!contributions?.length) return null;

  let numerator = 0;
  let divisor = 0;
  for (const { def, effective } of contributions) {
    numerator += def.weight * effective;
    divisor += def.weight;
  }
  return numerator / divisor;
}

export function formatHasScore(score: number | null) {
  return score == null || !Number.isFinite(score) ? "—" : score.toFixed(1);
}

export function hasTone(score: number, eliteFloor = 14, poorCeiling = 6): HasTone {
  if (score >= eliteFloor) return "high";
  if (score <= poorCeiling) return "low";
  return "mid";
}

export function squadHasRankings(players: LivePlayer[]) {
  const ranked = players
    .map((player) => ({ player, score: liveHasScore(player) }))
    .filter((row): row is { player: LivePlayer; score: number } => row.score != null)
    .sort((a, b) => b.score - a.score);

  const scores = ranked.map((row) => row.score);
  const eliteFloor = uniqueTopFractionFloor(scores, 0.25);
  const poorCeiling = uniqueBottomFractionCeiling(scores, 0.25);

  return {
    ranked,
    eliteFloor,
    poorCeiling,
    top: ranked.slice(0, HAS_DASHBOARD_LEADERBOARD_SIZE),
    bottom: [...ranked].reverse().slice(0, HAS_DASHBOARD_LEADERBOARD_SIZE),
  };
}

function uniqueTopFractionFloor(scores: number[], fraction: number) {
  const unique = [...new Set(scores.map((score) => +score.toFixed(10)))].sort((a, b) => b - a);
  if (!unique.length) return 14;
  const k = Math.max(1, Math.ceil(unique.length * fraction));
  return unique[k - 1]!;
}

function uniqueBottomFractionCeiling(scores: number[], fraction: number) {
  const unique = [...new Set(scores.map((score) => +score.toFixed(10)))].sort((a, b) => a - b);
  if (!unique.length) return 6;
  const k = Math.max(1, Math.ceil(unique.length * fraction));
  return unique[k - 1]!;
}
