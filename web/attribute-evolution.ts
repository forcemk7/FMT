/**
 * Squad attribute-evolution chart (CA history).
 * X-axis is unlabeled (change-point order only; calendar dating not locked).
 */

import type {
  AttributeHistoryPoint,
  GeneralKey,
  MentalKey,
  PhysicalKey,
  TechnicalKey,
  GoalkeepingKey,
} from "../shared/save/types.ts";
import {
  MENTAL_KEYS,
  PHYSICAL_KEYS,
  TECHNICAL_KEYS,
} from "../shared/save/types.ts";
import type { RosterPlayer } from "./roster-data.ts";
import { HA_PACK_KEYS, type HaPackKey } from "./ha-history-store.ts";
import {
  attributeTone,
  CHECKER_TABLE_ATTRIBUTES,
  TRACKED_ATTRIBUTES,
  type TrackedAttribute,
} from "../src/index.ts";

/** Catmull–Rom → cubic Bézier path through plotted points. */
function smoothLinePath(pts: Array<{ x: number; y: number }>): string {
  if (pts.length === 0) return "";
  if (pts.length === 1) return `M ${pts[0]!.x} ${pts[0]!.y}`;
  if (pts.length === 2) {
    return `M ${pts[0]!.x} ${pts[0]!.y} L ${pts[1]!.x} ${pts[1]!.y}`;
  }
  let d = `M ${pts[0]!.x} ${pts[0]!.y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i]!;
    const p1 = pts[i]!;
    const p2 = pts[i + 1]!;
    const p3 = pts[i + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${c1x} ${c1y} ${c2x} ${c2y} ${p2.x} ${p2.y}`;
  }
  return d;
}

export type EvolutionAttrId =
  | `mental.${MentalKey}`
  | `physical.${PhysicalKey}`
  | `technical.${TechnicalKey}`
  | `goalkeeping.${GoalkeepingKey}`
  | `general.${GeneralKey}`;

export type EvolutionSeries = {
  id: EvolutionAttrId;
  label: string;
  color: string;
  values: Array<number | null>;
};

export type EvolutionCategoryId =
  | "technical"
  | "setPieces"
  | "goalkeeping"
  | "goalkeepingTechnical"
  | "mental"
  | "physical"
  | "general"
  | "generalExtra"
  | "performance";

export type EvolutionCategory = {
  id: EvolutionCategoryId;
  label: string;
  ids: EvolutionAttrId[];
};

/** Unique plot colors — assigned by activation order (1st on → [0], etc.). */
const COLORS = [
  "#5b8def",
  "#3ecf8e",
  "#f0b429",
  "#e85d75",
  "#a78bfa",
  "#2dd4bf",
  "#fb923c",
  "#38bdf8",
  "#c084fc",
  "#86efac",
  "#f472b6",
  "#facc15",
  "#22d3ee",
  "#f87171",
  "#a3e635",
  "#e879f9",
  "#60a5fa",
  "#fbbf24",
  "#34d399",
  "#fb7185",
  "#818cf8",
  "#4ade80",
  "#f59e0b",
  "#06b6d4",
  "#d946ef",
  "#84cc16",
  "#ef4444",
  "#14b8a6",
  "#8b5cf6",
  "#eab308",
  "#0ea5e9",
  "#ec4899",
  "#65a30d",
  "#f97316",
  "#6366f1",
  "#10b981",
  "#dc2626",
  "#0891b2",
  "#7c3aed",
  "#ca8a04",
];

if (new Set(COLORS).size !== COLORS.length) {
  throw new Error("Evolution COLORS pool must not contain duplicates");
}

/** FM Set Pieces column (subset of technical). */
export const SET_PIECE_KEYS = [
  "corners",
  "freeKickTaking",
  "longThrows",
  "penaltyTaking",
] as const satisfies readonly TechnicalKey[];

const SET_PIECE_KEY_SET = new Set<string>(SET_PIECE_KEYS);

/** Outfield Technical column order (excludes set pieces). */
const OUTFIELD_TECHNICAL_KEYS = [
  "crossing",
  "dribbling",
  "finishing",
  "firstTouch",
  "heading",
  "longShots",
  "marking",
  "passing",
  "tackling",
  "technique",
] as const satisfies readonly TechnicalKey[];

/**
 * GK Goalkeeping column: core GK attrs plus First Touch / Passing
 * (stored under technical in the extract — single source, shown here like FM).
 */
const GK_GOALKEEPING_COLUMN: EvolutionAttrId[] = [
  "goalkeeping.aerialReach",
  "goalkeeping.commandOfArea",
  "goalkeeping.communication",
  "goalkeeping.eccentricity",
  "technical.firstTouch",
  "goalkeeping.handling",
  "goalkeeping.kicking",
  "goalkeeping.oneOnOnes",
  "technical.passing",
  "goalkeeping.punchingTendency",
  "goalkeeping.reflexes",
  "goalkeeping.rushingOutTendency",
  "goalkeeping.throwing",
];

/** FM Goalkeeping - Technical column. */
const GK_TECHNICAL_COLUMN: EvolutionAttrId[] = [
  "technical.freeKickTaking",
  "technical.penaltyTaking",
  "technical.technique",
];

const LABEL: Record<string, string> = {
  corners: "Corners",
  crossing: "Crossing",
  dribbling: "Dribbling",
  finishing: "Finishing",
  firstTouch: "First Touch",
  freeKickTaking: "Free Kick Taking",
  heading: "Heading",
  longShots: "Long Shots",
  longThrows: "Long Throws",
  marking: "Marking",
  passing: "Passing",
  penaltyTaking: "Penalty Taking",
  tackling: "Tackling",
  technique: "Technique",
  aerialReach: "Aerial Reach",
  commandOfArea: "Command Of Area",
  communication: "Communication",
  eccentricity: "Eccentricity",
  handling: "Handling",
  kicking: "Kicking",
  oneOnOnes: "One On Ones",
  punchingTendency: "Punching (Tendency)",
  reflexes: "Reflexes",
  rushingOutTendency: "Rushing Out (Tendency)",
  throwing: "Throwing",
  aggression: "Aggression",
  anticipation: "Anticipation",
  bravery: "Bravery",
  composure: "Composure",
  concentration: "Concentration",
  decisions: "Decisions",
  determination: "Determination",
  flair: "Flair",
  leadership: "Leadership",
  offTheBall: "Off The Ball",
  positioning: "Positioning",
  teamwork: "Teamwork",
  vision: "Vision",
  workRate: "Work Rate",
  acceleration: "Acceleration",
  agility: "Agility",
  balance: "Balance",
  jumpingReach: "Jumping Reach",
  naturalFitness: "Natural Fitness",
  pace: "Pace",
  stamina: "Stamina",
  strength: "Strength",
  adaptability: "Adaptability",
  ambition: "Ambition",
  consistency: "Consistency",
  controversy: "Controversy",
  dirtiness: "Dirtiness",
  importantMatches: "Important Matches",
  injuryProneness: "Injury Proneness",
  loyalty: "Loyalty",
  pressure: "Pressure",
  professionalism: "Professionalism",
  sportsmanship: "Sportsmanship",
  temperament: "Temperament",
  versatility: "Versatility",
};

export function labelForEvolutionAttr(id: EvolutionAttrId): string {
  const key = id.split(".")[1] ?? id;
  return (
    LABEL[key] ??
    key.replace(/([A-Z])/g, " $1").replace(/^./, (c) => c.toUpperCase())
  );
}

/**
 * Layout role from attr-card kind (positions not extracted yet).
 * Prefer history kind, then `_extract.kind`.
 */
export function evolutionPlayerIsGk(player: RosterPlayer): boolean {
  const history = player.attributeHistory ?? [];
  const latest = history[history.length - 1];
  return latest?.kind === "gk" || player._extract?.kind === "gk";
}

export function historyPointValue(
  point: AttributeHistoryPoint,
  id: EvolutionAttrId,
): number | null {
  const [nest, key] = id.split(".") as [keyof AttributeHistoryPoint, string];
  const block = point[nest];
  if (!block || typeof block !== "object") return null;
  const raw = (block as Record<string, unknown>)[key];
  return typeof raw === "number" && Number.isFinite(raw) ? raw : null;
}

/** Pack HA uses extract snapshots. Det/Lea stay on the CA strip (same as Strength). */
export function isHaProgressAttrId(id: EvolutionAttrId): boolean {
  return id.startsWith("general.");
}

export function haTableEvolutionAttrId(
  key: (typeof CHECKER_TABLE_ATTRIBUTES)[number],
): EvolutionAttrId {
  if (key === "determination") return "mental.determination";
  if (key === "leadership") return "mental.leadership";
  return `general.${key}`;
}

/** Default Progress chips = pack keys with snapshot points (not Det/Lea). */
export function defaultHaEvolutionAttrIds(
  history: AttributeHistoryPoint[],
): EvolutionAttrId[] {
  return CHECKER_TABLE_ATTRIBUTES.map(haTableEvolutionAttrId).filter(
    (id) =>
      isHaProgressAttrId(id) &&
      history.some((p) => historyPointValue(p, id) != null),
  );
}

/** CA attrs vs HA snapshot attrs. Any CA selection keeps the chart on the tip strip. */
export function splitEvolutionChartSelection(selected: EvolutionAttrId[]): {
  caIds: EvolutionAttrId[];
  haIds: EvolutionAttrId[];
} {
  return {
    caIds: selected.filter((id) => !isHaProgressAttrId(id)),
    haIds: selected.filter(isHaProgressAttrId),
  };
}

export function defaultEvolutionAttrIds(
  player: RosterPlayer,
): EvolutionAttrId[] {
  if (evolutionPlayerIsGk(player)) {
    return [
      "mental.determination",
      "mental.leadership",
      "mental.decisions",
      "mental.concentration",
      "goalkeeping.reflexes",
      "goalkeeping.handling",
      "goalkeeping.aerialReach",
      "physical.agility",
    ];
  }
  return [
    "mental.determination",
    "mental.leadership",
    "mental.decisions",
    "mental.anticipation",
    "technical.firstTouch",
    "technical.technique",
    "physical.acceleration",
    "physical.pace",
  ];
}

/** FM-style category columns for chart attribute pills (outfield vs GK). */
export function evolutionCategories(player: RosterPlayer): EvolutionCategory[] {
  const mental = MENTAL_KEYS.map((k) => `mental.${k}` as EvolutionAttrId);
  const physical = PHYSICAL_KEYS.map((k) => `physical.${k}` as EvolutionAttrId);

  if (evolutionPlayerIsGk(player)) {
    return [
      {
        id: "goalkeeping",
        label: "Goalkeeping",
        ids: [...GK_GOALKEEPING_COLUMN],
      },
      {
        id: "goalkeepingTechnical",
        label: "Goalkeeping - Technical",
        ids: [...GK_TECHNICAL_COLUMN],
      },
      { id: "mental", label: "Mental", ids: mental },
      { id: "physical", label: "Physical", ids: physical },
    ];
  }

  const technical = OUTFIELD_TECHNICAL_KEYS.map(
    (k) => `technical.${k}` as EvolutionAttrId,
  );
  const setPieces = SET_PIECE_KEYS.map(
    (k) => `technical.${k}` as EvolutionAttrId,
  );

  // Keep any remaining technical keys (future-proof) under Technical.
  for (const k of TECHNICAL_KEYS) {
    if (SET_PIECE_KEY_SET.has(k)) continue;
    if ((OUTFIELD_TECHNICAL_KEYS as readonly string[]).includes(k)) continue;
    technical.push(`technical.${k}`);
  }

  return [
    { id: "technical", label: "Technical", ids: technical },
    { id: "setPieces", label: "Set Pieces", ids: setPieces },
    { id: "mental", label: "Mental", ids: mental },
    { id: "physical", label: "Physical", ids: physical },
  ];
}

export function buildEvolutionSeries(
  history: AttributeHistoryPoint[],
  ids: EvolutionAttrId[],
): EvolutionSeries[] {
  return ids.map((id, i) => ({
    id,
    label: labelForEvolutionAttr(id),
    color: COLORS[i % COLORS.length]!,
    values: history.map((p) => historyPointValue(p, id)),
  }));
}

/**
 * Color for an active attribute by position in the activation list
 * (index 0 → pool[0], …). Returns null when not active.
 */
export function colorForActiveEvolutionAttr(
  id: EvolutionAttrId,
  activeOrder: EvolutionAttrId[],
): string | null {
  const i = activeOrder.indexOf(id);
  if (i < 0) return null;
  return COLORS[i % COLORS.length]!;
}

/** CA categories plus a Personality (hidden HA) column at the end. */
export function evolutionCategoriesWithPersonality(
  player: RosterPlayer,
): EvolutionCategory[] {
  const packIds = HA_PACK_KEYS.map((k) => `general.${k}` as EvolutionAttrId);
  return [
    ...evolutionCategories(player),
    { id: "general", label: "Personality", ids: packIds },
  ];
}

export function allSelectableEvolutionIds(
  player: RosterPlayer,
): EvolutionAttrId[] {
  return evolutionCategoriesWithPersonality(player).flatMap((c) => c.ids);
}

export type AttrDeltaWindow = "recent" | "allTime";

function finiteHistoryValues(
  history: AttributeHistoryPoint[],
  id: EvolutionAttrId,
): number[] {
  const out: number[] = [];
  for (const point of history) {
    const v = historyPointValue(point, id);
    if (v != null) out.push(v);
  }
  return out;
}

/**
 * Latest value + change vs a history window (0 / missing → null delta).
 * `recent` = last two finite points. `allTime` = first finite vs latest
 * (progress 0, or 1 if 0 is empty).
 */
export function attrValueAndDelta(
  history: AttributeHistoryPoint[],
  id: EvolutionAttrId,
  liveFallback: number | null = null,
  window: AttrDeltaWindow = "recent",
): { value: number | null; delta: number | null } {
  const finite = finiteHistoryValues(history, id);
  let last: number | null =
    finite.length > 0 ? finite[finite.length - 1]! : null;
  if (last == null) last = liveFallback;
  if (last == null) return { value: null, delta: null };

  let prev: number | null = null;
  if (window === "allTime") {
    if (finite.length >= 2) prev = finite[0]!;
  } else if (finite.length >= 2) {
    prev = finite[finite.length - 2]!;
  }

  if (prev == null) return { value: last, delta: null };
  const delta = last - prev;
  return { value: last, delta: delta === 0 ? null : delta };
}

export function formatAttrDelta(delta: number | null): string {
  if (delta == null || delta === 0) return "";
  return delta > 0 ? `+${delta}` : String(delta);
}

const TRACKED_ATTR_SET = new Set<string>(TRACKED_ATTRIBUTES);

/** HA-table `good` / `bad` on chip values. CON inverted; other 1–20 use the same floors. */
export function evoChipValueTone(
  id: EvolutionAttrId,
  value: number | null,
): "good" | "bad" | "" {
  if (value == null || !Number.isFinite(value)) return "";
  const key = id.slice(id.indexOf(".") + 1);
  if (TRACKED_ATTR_SET.has(key)) {
    const tone = attributeTone(key as TrackedAttribute, value);
    return tone === "neutral" ? "" : tone;
  }
  if (value > 14) return "good";
  if (value > 0 && value < 6) return "bad";
  return "";
}

/** Visibility `<select>`: `-` = role-default / mixed. */
export function evoVisibilitySelectValue(
  override: "default" | "all" | "none",
): "default" | "all" | "none" {
  return override;
}

export function evoVisibilityOverrideFromSelect(
  value: string,
): "default" | "all" | "none" {
  if (value === "none") return "none";
  if (value === "all") return "all";
  return "default";
}

export type EvolutionHoverPoint = {
  index: number;
  attrId: EvolutionAttrId;
  label: string;
  value: number;
  color: string;
  snapshotU16?: number | null;
  gap?: number | null;
  date?: string | null;
};

/** In-game axis label: `Jul 39`. */
export function formatMonYY(isoDate: string | null | undefined): string | null {
  if (!isoDate) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(isoDate);
  if (!m) return null;
  const year = Number(m[1]);
  const month = Number(m[2]);
  if (!Number.isFinite(year) || month < 1 || month > 12) return null;
  const mon = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ][month - 1]!;
  return `${mon} ${String(year).slice(-2)}`;
}

function parseIsoDate(iso: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return null;
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  return Number.isNaN(d.getTime()) ? null : d;
}

function toIsoDate(d: Date): string {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addUtcMonths(d: Date, months: number): Date {
  const out = new Date(d.getTime());
  const day = out.getUTCDate();
  out.setUTCDate(1);
  out.setUTCMonth(out.getUTCMonth() + months);
  const dim = new Date(Date.UTC(out.getUTCFullYear(), out.getUTCMonth() + 1, 0)).getUTCDate();
  out.setUTCDate(Math.min(day, dim));
  return out;
}

function monthsBetween(start: Date, end: Date): number {
  return (
    (end.getUTCFullYear() - start.getUTCFullYear()) * 12 +
    (end.getUTCMonth() - start.getUTCMonth())
  );
}

/**
 * Stamp ISO dates onto CA change-points.
 * Prefer monthly ticks from PRS when point count matches the month span;
 * otherwise linear interpolate PRS → PRE. Last point always PRE.
 */
export function assignProgressReportDates(
  history: AttributeHistoryPoint[],
  prsIso: string,
  preIso: string,
): AttributeHistoryPoint[] {
  const prs = parseIsoDate(prsIso);
  const pre = parseIsoDate(preIso);
  if (!prs || !pre || history.length === 0) {
    return history.map((p, i) => ({ ...p, index: i }));
  }
  const n = history.length;
  if (n === 1) {
    return [{ ...history[0]!, index: 0, date: toIsoDate(pre) }];
  }

  const monthSpan = monthsBetween(prs, pre);
  const useMonthly = monthSpan > 0 && n - 1 === monthSpan;
  const spanMs = pre.getTime() - prs.getTime();

  return history.map((p, i) => {
    let date: string;
    if (i === n - 1) {
      date = toIsoDate(pre);
    } else if (i === 0) {
      date = toIsoDate(prs);
    } else if (useMonthly) {
      date = toIsoDate(addUtcMonths(prs, i));
    } else {
      const t = i / (n - 1);
      date = toIsoDate(new Date(prs.getTime() + Math.round(t * spanMs)));
    }
    return { ...p, index: i, date };
  });
}

/** Drop wiped Technique-0 outfield cards and keep the newest contiguous strip (mirrors extract). */
export function filterAttributeHistory(
  history: AttributeHistoryPoint[],
): AttributeHistoryPoint[] {
  const cleaned = history.filter((p) => {
    if (p.kind === "gk") return true;
    const tech = p.technical;
    if (!tech) return true;
    // False-positive outfield cards often decode with Technique 0 (FT 0 or 1).
    return tech.technique !== 0;
  });
  if (cleaned.length <= 1) {
    return cleaned.map((p, i) => (p.index === i ? p : { ...p, index: i }));
  }

  const maxGapDrop = 2000;
  const maxL1 = 80;
  const l1 = (a: AttributeHistoryPoint, b: AttributeHistoryPoint) => {
    const va = new Map<string, number>();
    const vb = new Map<string, number>();
    for (const nest of ["mental", "physical", "technical", "goalkeeping"] as const) {
      const ba = a[nest];
      const bb = b[nest];
      if (ba) {
        for (const [k, v] of Object.entries(ba)) {
          if (typeof v === "number") va.set(`${nest}.${k}`, v);
        }
      }
      if (bb) {
        for (const [k, v] of Object.entries(bb)) {
          if (typeof v === "number") vb.set(`${nest}.${k}`, v);
        }
      }
    }
    const keys = new Set([...va.keys(), ...vb.keys()]);
    let sum = 0;
    for (const k of keys) sum += Math.abs((va.get(k) ?? 0) - (vb.get(k) ?? 0));
    return sum;
  };

  let start = 0;
  for (let i = 1; i < cleaned.length; i++) {
    const prev = cleaned[i - 1]!;
    const cur = cleaned[i]!;
    const gapDrop = (prev.gap ?? 0) - (cur.gap ?? 0);
    if (gapDrop < 0 || gapDrop > maxGapDrop || l1(prev, cur) > maxL1) {
      start = i;
    }
  }
  return cleaned.slice(start).map((p, i) => ({ ...p, index: i }));
}

export function renderEvolutionChartSvg(
  series: EvolutionSeries[],
  opts: {
    width?: number;
    height?: number;
    hover?: EvolutionHoverPoint | null;
    /** Parallel ISO dates for x labels (same length as series values). */
    dates?: Array<string | null | undefined>;
  } = {},
): SVGSVGElement {
  const width = opts.width ?? 720;
  const height = opts.height ?? 260;
  const pad = { top: 14, right: 28, bottom: 10, left: 32 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  /** Keep attr=0 above the axis so hover near the edge still works. */
  const yZero = innerH - 6;
  const n = Math.max(1, series[0]?.values.length ?? 1);

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", String(height));
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Attribute evolution");
  svg.classList.add("squad-evo-chart");

  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  g.setAttribute("transform", `translate(${pad.left},${pad.top})`);

  for (const yVal of [0, 5, 10, 15, 20]) {
    const y = yZero - (yVal / 20) * yZero;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", "0");
    line.setAttribute("x2", String(innerW));
    line.setAttribute("y1", String(y));
    line.setAttribute("y2", String(y));
    line.setAttribute("class", "squad-evo-grid");
    g.append(line);
    const lab = document.createElementNS("http://www.w3.org/2000/svg", "text");
    lab.setAttribute("x", "-8");
    lab.setAttribute("y", String(y + 3));
    lab.setAttribute("text-anchor", "end");
    lab.setAttribute("class", "squad-evo-axis");
    lab.textContent = String(yVal);
    g.append(lab);
  }

  const xAt = (i: number) => (n <= 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const yAt = (v: number) => yZero - (v / 20) * yZero;

  for (const s of series) {
    const pts: Array<{ x: number; y: number }> = [];
    s.values.forEach((v, i) => {
      if (v == null) return;
      pts.push({ x: xAt(i), y: yAt(v) });
    });
    if (pts.length >= 2) {
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", smoothLinePath(pts));
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", s.color);
      path.setAttribute("stroke-width", "2");
      path.setAttribute("stroke-linejoin", "round");
      path.setAttribute("stroke-linecap", "round");
      path.setAttribute("class", "squad-evo-line");
      path.dataset.attrId = s.id;
      g.append(path);
    } else if (pts.length === 1) {
      const only = pts[0]!;
      const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      c.setAttribute("cx", String(only.x));
      c.setAttribute("cy", String(only.y));
      c.setAttribute("r", "3.5");
      c.setAttribute("fill", s.color);
      c.setAttribute("class", "squad-evo-point");
      g.append(c);
    }
  }

  if (opts.hover) {
    const { index, value, label, color } = opts.hover;
    const cx = xAt(index);
    const cy = yAt(value);

    const point = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    point.setAttribute("cx", String(cx));
    point.setAttribute("cy", String(cy));
    point.setAttribute("r", "5");
    point.setAttribute("fill", color);
    point.setAttribute("class", "squad-evo-point is-active");
    g.append(point);

    const tipText = `${label}: ${value}`;
    const tipW = Math.max(88, Math.min(innerW, 7.2 * tipText.length + 22));
    const tipH = 24;
    let tipX = cx - tipW / 2;
    tipX = Math.max(0, Math.min(innerW - tipW, tipX));
    let tipY = cy - tipH - 14;
    if (tipY < 0) tipY = cy + 14;

    const tip = document.createElementNS("http://www.w3.org/2000/svg", "g");
    tip.setAttribute("class", "squad-evo-tooltip");
    tip.setAttribute("pointer-events", "none");

    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", String(tipX));
    rect.setAttribute("y", String(tipY));
    rect.setAttribute("width", String(tipW));
    rect.setAttribute("height", String(tipH));
    rect.setAttribute("rx", "5");
    rect.setAttribute("class", "squad-evo-tooltip-bg");
    tip.append(rect);

    const accent = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    accent.setAttribute("x", String(tipX));
    accent.setAttribute("y", String(tipY));
    accent.setAttribute("width", "3");
    accent.setAttribute("height", String(tipH));
    accent.setAttribute("rx", "1.5");
    accent.setAttribute("fill", color);
    tip.append(accent);

    const t1 = document.createElementNS("http://www.w3.org/2000/svg", "text");
    t1.setAttribute("x", String(tipX + tipW / 2 + 1));
    t1.setAttribute("y", String(tipY + 16));
    t1.setAttribute("text-anchor", "middle");
    t1.setAttribute("class", "squad-evo-tooltip-text");
    t1.textContent = tipText;
    tip.append(t1);

    const stem = document.createElementNS("http://www.w3.org/2000/svg", "line");
    stem.setAttribute("x1", String(cx));
    stem.setAttribute("x2", String(cx));
    stem.setAttribute("y1", String(tipY < cy ? tipY + tipH : tipY));
    stem.setAttribute("y2", String(cy));
    stem.setAttribute("class", "squad-evo-tooltip-stem");
    tip.append(stem);

    g.append(tip);
  }

  svg.append(g);
  return svg;
}

/** Nearest data point to the cursor in SVG user space (pure Euclidean). */
export function hitTestEvolutionPoint(
  series: EvolutionSeries[],
  opts: {
    plotX: number;
    plotY: number;
    width: number;
    height: number;
    history?: AttributeHistoryPoint[];
    maxDist?: number;
  },
): EvolutionHoverPoint | null {
  const pad = { top: 14, right: 28, bottom: 10, left: 32 };
  const innerW = opts.width - pad.left - pad.right;
  const innerH = opts.height - pad.top - pad.bottom;
  const yZero = innerH - 6;
  const n = Math.max(1, series[0]?.values.length ?? 1);
  const xAt = (i: number) => (n <= 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const yAt = (v: number) => yZero - (v / 20) * yZero;
  const lx = opts.plotX - pad.left;
  const ly = opts.plotY - pad.top;
  const maxDist = opts.maxDist ?? 22;

  if (n <= 0 || series.length === 0) return null;

  let best: EvolutionHoverPoint | null = null;
  let bestDist = maxDist;

  for (const s of series) {
    s.values.forEach((v, i) => {
      if (v == null) return;
      const d = Math.hypot(xAt(i) - lx, yAt(v) - ly);
      if (d <= bestDist) {
        bestDist = d;
        const meta = opts.history?.[i];
        best = {
          index: i,
          attrId: s.id,
          label: s.label,
          value: v,
          color: s.color,
          snapshotU16: meta?.snapshotU16,
          gap: meta?.gap,
          date: meta?.date,
        };
      }
    });
  }
  return best;
}

/** Extracted HA pack attrs (FMT snapshots). Det/Lea stay on the CA mental column. */
export function personalityEvolutionCategories(): EvolutionCategory[] {
  const packIds = HA_PACK_KEYS.map((k) => `general.${k}` as EvolutionAttrId);
  const stubGeneral: EvolutionAttrId[] = [
    "general.consistency",
    "general.versatility",
  ];
  const stubPerformance: EvolutionAttrId[] = [
    "general.dirtiness",
    "general.importantMatches",
    "general.injuryProneness",
  ];
  return [
    { id: "general", label: "Hidden", ids: packIds },
    { id: "generalExtra", label: "General", ids: stubGeneral },
    { id: "performance", label: "Performance", ids: stubPerformance },
  ];
}

export function liveAttrValue(
  player: RosterPlayer,
  id: EvolutionAttrId,
): number | null {
  const [nest, key] = id.split(".") as [string, string];
  const attrs = player.attributes as Record<string, unknown> | null | undefined;
  if (!attrs) return null;
  const block = attrs[nest];
  if (!block || typeof block !== "object") return null;
  const raw = (block as Record<string, unknown>)[key];
  return typeof raw === "number" && Number.isFinite(raw) ? raw : null;
}

export function defaultPersonalityEvolutionAttrIds(
  history: AttributeHistoryPoint[],
): EvolutionAttrId[] {
  const available = HA_PACK_KEYS.map((k) => `general.${k}` as EvolutionAttrId).filter(
    (id) => history.some((p) => historyPointValue(p, id) != null),
  );
  const preferred: HaPackKey[] = [
    "professionalism",
    "ambition",
    "loyalty",
    "pressure",
    "temperament",
    "sportsmanship",
    "controversy",
    "adaptability",
  ];
  const ordered = preferred
    .map((k) => `general.${k}` as EvolutionAttrId)
    .filter((id) => available.includes(id));
  return (ordered.length > 0 ? ordered : available).slice(0, 6);
}

/** @deprecated stub labels — prefer personalityEvolutionCategories */
export type PersonalityStubCategory = {
  id: "mental" | "general" | "performance";
  label: string;
  labels: string[];
};

/** Placeholder HA / personality categories (no history locus yet). */
export function personalityStubCategories(): PersonalityStubCategory[] {
  return [
    {
      id: "mental",
      label: "Mental",
      labels: ["Determination", "Leadership"],
    },
    {
      id: "general",
      label: "General",
      labels: [
        "Adaptability",
        "Ambition",
        "Consistency",
        "Controversy",
        "Loyalty",
        "Pressure",
        "Professionalism",
        "Sportsmanship",
        "Temperament",
        "Versatility",
      ],
    },
    {
      id: "performance",
      label: "Performance",
      labels: ["Dirtiness", "Important Matches", "Injury Proneness"],
    },
  ];
}
