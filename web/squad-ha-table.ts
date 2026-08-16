/**
 * Squad Personalities table: extract HA numbers + ranker-style filters.
 * One-click on 1–2 players writes ≥ floors (CON ≤) from this save — not HAS.
 */

import { CHECKER_TABLE_ATTRIBUTES } from "../src/index.ts";
import type { PersonalitySignals } from "../shared/save/types.ts";
import { isRosterNameResolved } from "./extract-trust.ts";

export const SQUAD_HA_ATTRS = CHECKER_TABLE_ATTRIBUTES;

export type SquadHaAttr = (typeof SQUAD_HA_ATTRS)[number];

export const SQUAD_HA_GROWTH_ATTRS = SQUAD_HA_ATTRS.filter(
  (key) => key !== "controversy",
) as Exclude<SquadHaAttr, "controversy">[];

export const SQUAD_HA_COL_META: Record<
  SquadHaAttr,
  { header: string; title: string }
> = {
  determination: { header: "DET", title: "Determination" },
  professionalism: { header: "PRO", title: "Professionalism" },
  pressure: { header: "PRE", title: "Pressure" },
  ambition: { header: "AMB", title: "Ambition" },
  temperament: { header: "TEM", title: "Temperament" },
  leadership: { header: "LEA", title: "Leadership" },
  loyalty: { header: "LOY", title: "Loyalty" },
  sportsmanship: { header: "SPO", title: "Sportsmanship" },
  controversy: { header: "CON", title: "Controversy" },
};

export type SquadHaFilterOp = "gte" | "lte" | "eq" | "neq";
export type SquadHaFilterJoin = "and" | "or";
export type SquadHaTextFilterKey = "name" | "unit" | "personality" | "mediaHandling";
export type SquadHaNumericFilterKey = SquadHaAttr | "has" | "age";
export type SquadHaFilterKey = SquadHaNumericFilterKey | SquadHaTextFilterKey;

/**
 * Table L→R and filter-key dropdown top→bottom. Checkbox / group # are not keys.
 * Copy of mentoring.ts YOUNG_AGE / AGE_GAP — heuristic floors, not SI lock.
 */
export const SQUAD_HA_YOUNG_AGE = 24;
export const SQUAD_HA_AGE_GAP = 3;

export const SQUAD_HA_FILTER_KEYS = [
  "name",
  "unit",
  "age",
  "personality",
  "mediaHandling",
  ...SQUAD_HA_ATTRS,
  "has",
] as const satisfies readonly SquadHaFilterKey[];

export type SquadHaFilter = {
  id: string;
  key: SquadHaFilterKey;
  op: SquadHaFilterOp;
  value: number | string;
};

/** Squad unit label shown on the club-wide HA table. */
export type SquadHaUnit = "FT" | "II" | "U19";

export const SQUAD_HA_UNIT_ORDER: readonly SquadHaUnit[] = ["FT", "II", "U19"];

export type SquadHaRow = {
  uid: number;
  name: string;
  unit: SquadHaUnit;
  age: number | null;
  personality: string | null;
  mediaHandling: string | null;
  attrs: Record<SquadHaAttr, number | null>;
  has: number | null;
};

export type SquadHaSortKey = (typeof SQUAD_HA_FILTER_KEYS)[number];

/** At-club FT + II + U19, first-seen wins, loaned-out and nameless excluded. */
export function mergeClubWideAtClubPlayers<
  T extends {
    uid?: number | null;
    name?: string | null;
    loan?: { status?: string | null } | null;
  },
>(lists: {
  firstTeam: readonly T[];
  reserves: readonly T[];
  under19s: readonly T[];
}): Array<{ player: T; unit: SquadHaUnit }> {
  return mergeClubWideEmployedPlayers(lists, { includeLoanedOut: false });
}

/** Employed FT + II + U19 (at-club + outgoing). Progress picker; Group checks stay at-club. */
export function mergeClubWideEmployedPlayers<
  T extends {
    uid?: number | null;
    name?: string | null;
    loan?: { status?: string | null } | null;
  },
>(
  lists: {
    firstTeam: readonly T[];
    reserves: readonly T[];
    under19s: readonly T[];
  },
  opts?: { includeLoanedOut?: boolean },
): Array<{ player: T; unit: SquadHaUnit }> {
  const includeLoanedOut = opts?.includeLoanedOut !== false;
  const byUid = new Map<number, { player: T; unit: SquadHaUnit }>();
  const push = (players: readonly T[], unit: SquadHaUnit) => {
    for (const player of players) {
      if (player.uid == null || !Number.isFinite(player.uid)) continue;
      if (!isRosterNameResolved(player.name)) continue;
      if (!includeLoanedOut && player.loan?.status === "loanedOut") continue;
      if (byUid.has(player.uid)) continue;
      byUid.set(player.uid, { player, unit });
    }
  };
  push(lists.firstTeam, "FT");
  push(lists.reserves, "II");
  push(lists.under19s, "U19");
  return [...byUid.values()];
}

export function finiteHaNumber(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return value;
}

export function squadHaAttrsFromSignals(
  pa: PersonalitySignals | null | undefined,
): Record<SquadHaAttr, number | null> {
  const attrs = {} as Record<SquadHaAttr, number | null>;
  for (const key of SQUAD_HA_ATTRS) {
    attrs[key] = finiteHaNumber(pa?.[key]);
  }
  return attrs;
}

export function formatSquadHaCell(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return Number.isInteger(value) ? String(value) : String(value);
}

/** HA text columns that ellipsis — Name, Personality, Media. Not Unit. */
export const SQUAD_HA_ELLIPSIS_KEYS = [
  "name",
  "personality",
  "mediaHandling",
] as const;

export type SquadHaEllipsisKey = (typeof SQUAD_HA_ELLIPSIS_KEYS)[number];

export function isSquadHaEllipsisKey(
  key: SquadHaFilterKey,
): key is SquadHaEllipsisKey {
  return (
    key === "name" || key === "personality" || key === "mediaHandling"
  );
}

export function squadHaEllipsisCellText(
  row: SquadHaRow,
  key: SquadHaEllipsisKey,
): string | null {
  if (key === "name") return row.name || null;
  return row[key];
}

/**
 * Full string for an HA ellipsis cell tooltip.
 * Empty and em-dash → no tooltip.
 */
export function squadHaEllipsisCellTitle(
  value: string | null | undefined,
): string {
  if (typeof value !== "string") return "";
  const text = value.trim();
  if (!text || text === "—") return "";
  return value;
}

/** True when the painted label is clipped (ellipsis). */
export function squadHaTextOverflows(el: {
  scrollWidth: number;
  clientWidth: number;
}): boolean {
  return el.scrollWidth - el.clientWidth > 1;
}

/** Click 1 player, or a second; a third click starts a new 1-player preset. */
export function toggleSquadHaSelection(
  selectedUids: readonly number[],
  uid: number,
): number[] {
  const id = Number(uid);
  const selected = selectedUids.map(Number);
  const at = selected.indexOf(id);
  if (at >= 0) {
    return selected.filter((x) => x !== id);
  }
  if (selected.length >= 2) return [id];
  return [...selected, id];
}

/** Mentoring unit size — same as Mentoring stack create (exactly 3). */
export const SQUAD_HA_MENTORING_UNIT_SIZE = 3;

export const SQUAD_HA_GROUP_HEADER = "Group";
export const SQUAD_HA_GROUP_HEADER_TIP = "Mentoring group";

/**
 * Checkbox selection for a mentoring unit (separate from ≥ filter selection).
 * Caps at unit size; does not invent seats. The third check assigns the group.
 */
export function toggleSquadHaUnitCheck(
  checkedUids: readonly number[],
  uid: number,
  maxSize: number = SQUAD_HA_MENTORING_UNIT_SIZE,
): number[] {
  const id = Number(uid);
  const checked = checkedUids.map(Number);
  const at = checked.indexOf(id);
  if (at >= 0) return checked.filter((x) => x !== id);
  if (checked.length >= maxSize) return checked;
  return [...checked, id];
}

/** True only when a new check just filled the unit (1–2 and uncheck do not). */
export function squadHaCheckCompletesUnit(
  previousChecked: readonly number[],
  nextChecked: readonly number[],
  unitSize: number = SQUAD_HA_MENTORING_UNIT_SIZE,
): boolean {
  return (
    nextChecked.length === unitSize &&
    previousChecked.length === unitSize - 1
  );
}

/** 1-based mentoring group number per assigned uid (first group wins). */
export function mentoringGroupNumberByUid(
  groups: readonly { memberIds: readonly string[] }[],
): Map<number, number> {
  const out = new Map<number, number>();
  for (let i = 0; i < groups.length; i += 1) {
    const n = i + 1;
    for (const id of groups[i]!.memberIds) {
      const uid = Number(id);
      if (!Number.isFinite(uid) || out.has(uid)) continue;
      out.set(uid, n);
    }
  }
  return out;
}

export type SquadHaAddMentoringUnitGate = {
  ok: boolean;
  reason: string;
};

/**
 * Gate for HA-table unit create — mirrors Mentoring create size/slot rules.
 * `canCreateSlot` is the existing canCreateMentoringGroup result.
 */
export function squadHaAddMentoringUnitGate(options: {
  checkedUids: readonly number[];
  assignedUids: ReadonlySet<number>;
  eligibleUids: ReadonlySet<number>;
  canCreateSlot: boolean;
  maxGroupsReached: boolean;
  unitSize?: number;
}): SquadHaAddMentoringUnitGate {
  const size = options.unitSize ?? SQUAD_HA_MENTORING_UNIT_SIZE;
  const checked = options.checkedUids.map(Number);
  if (checked.length === 0) {
    return { ok: false, reason: `Check ${size} players` };
  }
  if (checked.length !== size) {
    return { ok: false, reason: `Need ${size} players (${checked.length}/${size})` };
  }
  if (checked.some((uid) => options.assignedUids.has(uid))) {
    return { ok: false, reason: "Player already in a group" };
  }
  if (checked.some((uid) => !options.eligibleUids.has(uid))) {
    return { ok: false, reason: "Need Mentoring-eligible players" };
  }
  if (!options.canCreateSlot) {
    return {
      ok: false,
      reason: options.maxGroupsReached
        ? "Max groups for this squad"
        : "Need 3 unassigned players",
    };
  }
  return { ok: true, reason: "" };
}

function maxFinite(values: readonly (number | null)[]): number | null {
  let best: number | null = null;
  for (const value of values) {
    if (value == null || !Number.isFinite(value)) continue;
    if (best == null || value > best) best = value;
  }
  return best;
}

function minFinite(values: readonly (number | null)[]): number | null {
  let best: number | null = null;
  for (const value of values) {
    if (value == null || !Number.isFinite(value)) continue;
    if (best == null || value < best) best = value;
  }
  return best;
}

/**
 * Ranker-language preset from selected extract rows.
 * DET/PRO/PRE/AMB/TEM/LEA/LOY/SPO ≥ max(selected); CON ≤ min(selected).
 * Skips an attr when every selected row is missing it. Never writes HAS.
 */
export function squadHaNotWorsePreset(
  selected: readonly SquadHaRow[],
  nextId: () => string,
): { filters: SquadHaFilter[]; joins: SquadHaFilterJoin[] } {
  const filters: SquadHaFilter[] = [];
  for (const key of SQUAD_HA_GROWTH_ATTRS) {
    const floor = maxFinite(selected.map((row) => row.attrs[key]));
    if (floor == null) continue;
    filters.push({
      id: nextId(),
      key,
      op: "gte",
      value: floor,
    });
  }
  const ceiling = minFinite(selected.map((row) => row.attrs.controversy));
  if (ceiling != null) {
    filters.push({
      id: nextId(),
      key: "controversy",
      op: "lte",
      value: ceiling,
    });
  }
  const joins: SquadHaFilterJoin[] = filters.slice(1).map(() => "and");
  return { filters, joins };
}

/**
 * Inverted T033 floors: growth ≤ min(selected); CON ≥ max(selected).
 * Used when clicking a senior (≥ 24) so kids are not trapped by ≥ floors.
 */
export function squadHaNotBetterPreset(
  selected: readonly SquadHaRow[],
  nextId: () => string,
): { filters: SquadHaFilter[]; joins: SquadHaFilterJoin[] } {
  const filters: SquadHaFilter[] = [];
  for (const key of SQUAD_HA_GROWTH_ATTRS) {
    const ceiling = minFinite(selected.map((row) => row.attrs[key]));
    if (ceiling == null) continue;
    filters.push({
      id: nextId(),
      key,
      op: "lte",
      value: ceiling,
    });
  }
  const floor = maxFinite(selected.map((row) => row.attrs.controversy));
  if (floor != null) {
    filters.push({
      id: nextId(),
      key: "controversy",
      op: "gte",
      value: floor,
    });
  }
  const joins: SquadHaFilterJoin[] = filters.slice(1).map(() => "and");
  return { filters, joins };
}

/**
 * One-click preset. Pair stays T033 HA-only.
 * Exactly one player with known age also writes an Age row:
 *   < 24 → find mentor (Age ≥ age+3, T033 HA ≥)
 *   ≥ 24 → find mentee (Age ≤ age−3, inverted HA)
 * Missing age → no Age filter; HA preset still runs.
 */
export function squadHaClickPreset(
  selected: readonly SquadHaRow[],
  nextId: () => string,
): { filters: SquadHaFilter[]; joins: SquadHaFilterJoin[] } {
  if (selected.length === 0) return { filters: [], joins: [] };
  const single = selected.length === 1 ? selected[0] : null;
  const age = single != null ? finiteHaNumber(single.age) : null;
  const invertHa =
    single != null && age != null && age >= SQUAD_HA_YOUNG_AGE;
  const ha = invertHa
    ? squadHaNotBetterPreset(selected, nextId)
    : squadHaNotWorsePreset(selected, nextId);
  const filters: SquadHaFilter[] = [];
  if (single != null && age != null) {
    const findMentor = age < SQUAD_HA_YOUNG_AGE;
    filters.push({
      id: nextId(),
      key: "age",
      op: findMentor ? "gte" : "lte",
      value: findMentor ? age + SQUAD_HA_AGE_GAP : age - SQUAD_HA_AGE_GAP,
    });
  }
  filters.push(...ha.filters);
  const joins: SquadHaFilterJoin[] = filters.slice(1).map(() => "and");
  return { filters, joins };
}

/** + Add filter default. One-click presets must not use this. */
export function newSquadHaManualFilter(id: string): SquadHaFilter {
  return { id, key: "unit", op: "eq", value: "FT" };
}

export function isSquadHaTextFilterKey(
  key: SquadHaFilterKey,
): key is SquadHaTextFilterKey {
  return (
    key === "name" ||
    key === "unit" ||
    key === "personality" ||
    key === "mediaHandling"
  );
}

export function isSquadHaNumericFilterKey(
  key: SquadHaFilterKey,
): key is SquadHaNumericFilterKey {
  return !isSquadHaTextFilterKey(key);
}

/** Filter dropdown labels — full names. Table headers stay short. */
export function squadHaFilterKeyLabel(key: SquadHaFilterKey): string {
  if (key === "has") return "HAS";
  if (key === "name") return "Name";
  if (key === "unit") return "Squad";
  if (key === "age") return "Age";
  if (key === "personality") return "Personality";
  if (key === "mediaHandling") return "Media Handling";
  return SQUAD_HA_COL_META[key]?.title ?? key;
}

/** HA table column headers — abbreviations stay on the grid. */
export function squadHaTableHeaderLabel(key: SquadHaFilterKey): string {
  if (key === "has") return "HAS";
  if (key === "name") return "Name";
  if (key === "unit") return "Unit";
  if (key === "age") return "Age";
  if (key === "personality") return "Personality";
  if (key === "mediaHandling") return "Media";
  return SQUAD_HA_COL_META[key]?.header ?? key;
}

export const SQUAD_HA_ATTR_FILTER_MIN = 1;
export const SQUAD_HA_ATTR_FILTER_MAX = 20;
export const SQUAD_HA_AGE_FILTER_MIN = 0;
export const SQUAD_HA_AGE_FILTER_MAX = 50;

export function squadHaNumericFilterBounds(
  key: SquadHaNumericFilterKey,
): { min: number; max: number } {
  if (key === "age") {
    return { min: SQUAD_HA_AGE_FILTER_MIN, max: SQUAD_HA_AGE_FILTER_MAX };
  }
  return { min: SQUAD_HA_ATTR_FILTER_MIN, max: SQUAD_HA_ATTR_FILTER_MAX };
}

/** Inclusive min–max options for a numeric HA filter dropdown. */
export function squadHaNumericFilterValueOptions(
  key: SquadHaNumericFilterKey,
): { value: string; label: string }[] {
  const { min, max } = squadHaNumericFilterBounds(key);
  const options: { value: string; label: string }[] = [];
  for (let n = min; n <= max; n += 1) {
    options.push({ value: String(n), label: String(n) });
  }
  return options;
}

export function clampSquadHaFilterNumber(
  key: SquadHaNumericFilterKey,
  value: number,
): number {
  const n = Math.round(value);
  if (!Number.isFinite(n)) {
    return key === "age" ? SQUAD_HA_AGE_FILTER_MIN : SQUAD_HA_ATTR_FILTER_MIN;
  }
  const { min, max } = squadHaNumericFilterBounds(key);
  return Math.min(max, Math.max(min, n));
}

/** Per-row −/+: change that row’s number by `delta`. Text rows unchanged. */
export function nudgeSquadHaFilterBy(
  filter: SquadHaFilter,
  delta: number,
): SquadHaFilter {
  if (!isSquadHaNumericFilterKey(filter.key) || !Number.isFinite(delta)) {
    return filter;
  }
  const current =
    typeof filter.value === "number" ? filter.value : Number(filter.value);
  if (!Number.isFinite(current)) return filter;
  return {
    ...filter,
    value: clampSquadHaFilterNumber(filter.key, current + delta),
  };
}

/**
 * Footer −1 / +1: same number delta on HA numeric rows except Controversy
 * (lower-is-better — invert so footer +1 loosens CON ≤ with DET ≥).
 * Age is the T039 mentor/mentee floor — leave value and op unchanged.
 * Skip text.
 */
export function nudgeSquadHaFiltersBy(
  filters: readonly SquadHaFilter[],
  delta: number,
): SquadHaFilter[] {
  return filters.map((filter) => {
    if (filter.key === "age") return filter;
    return nudgeSquadHaFilterBy(
      filter,
      filter.key === "controversy" ? -delta : delta,
    );
  });
}

export function matchSquadHaNumeric(
  actual: number | null,
  op: SquadHaFilterOp,
  target: number,
): boolean {
  if (actual == null || !Number.isFinite(actual) || !Number.isFinite(target)) {
    return false;
  }
  switch (op) {
    case "gte":
      return actual >= target;
    case "lte":
      return actual <= target;
    case "eq":
      return Math.abs(actual - target) < 0.05;
    case "neq":
      return Math.abs(actual - target) >= 0.05;
  }
}

export function matchSquadHaText(
  actual: string | null,
  op: SquadHaFilterOp,
  target: string,
): boolean {
  if (!actual) return false;
  const equal =
    actual.localeCompare(target, undefined, { sensitivity: "accent" }) === 0;
  return op === "neq" ? !equal : equal;
}

export function matchSquadHaFilter(
  row: SquadHaRow,
  filter: SquadHaFilter,
): boolean {
  if (isSquadHaTextFilterKey(filter.key)) {
    const actual =
      filter.key === "name"
        ? row.name || null
        : filter.key === "unit"
          ? row.unit
          : filter.key === "personality"
            ? row.personality
            : row.mediaHandling;
    return matchSquadHaText(actual, filter.op, String(filter.value));
  }
  const target =
    typeof filter.value === "number" ? filter.value : Number(filter.value);
  if (!Number.isFinite(target)) return false;
  const actual =
    filter.key === "has"
      ? row.has
      : filter.key === "age"
        ? row.age
        : row.attrs[filter.key];
  return matchSquadHaNumeric(actual, filter.op, target);
}

export function squadHaRowPassesFilters(
  row: SquadHaRow,
  filters: readonly SquadHaFilter[],
  joins: readonly SquadHaFilterJoin[],
): boolean {
  if (filters.length === 0) return true;
  let acc = matchSquadHaFilter(row, filters[0]!);
  for (let i = 1; i < filters.length; i += 1) {
    const next = matchSquadHaFilter(row, filters[i]!);
    const join = joins[i - 1] ?? "and";
    acc = join === "and" ? acc && next : acc || next;
  }
  return acc;
}

/** Selected rows stay visible even when they fail a pair floor. */
export function squadHaRowVisible(
  row: SquadHaRow,
  filters: readonly SquadHaFilter[],
  joins: readonly SquadHaFilterJoin[],
  selectedUids: readonly number[],
): boolean {
  if (selectedUids.some((id) => Number(id) === Number(row.uid))) return true;
  return squadHaRowPassesFilters(row, filters, joins);
}

function compareNullableNumber(
  a: number | null,
  b: number | null,
  asc: boolean,
): number {
  const aNull = a == null || !Number.isFinite(a);
  const bNull = b == null || !Number.isFinite(b);
  if (aNull && bNull) return 0;
  if (aNull) return 1;
  if (bNull) return -1;
  const dir = asc ? 1 : -1;
  if (a! < b!) return -1 * dir;
  if (a! > b!) return 1 * dir;
  return 0;
}

function unitRank(unit: SquadHaUnit): number {
  const at = SQUAD_HA_UNIT_ORDER.indexOf(unit);
  return at >= 0 ? at : SQUAD_HA_UNIT_ORDER.length;
}

export function sortSquadHaRows(
  rows: readonly SquadHaRow[],
  key: SquadHaSortKey,
  asc: boolean,
): SquadHaRow[] {
  return [...rows].sort((a, b) => {
    let cmp = 0;
    if (key === "unit") {
      cmp = unitRank(a.unit) - unitRank(b.unit);
      if (!asc) cmp = -cmp;
    } else if (key === "name" || key === "personality" || key === "mediaHandling") {
      const av = (key === "name" ? a.name : a[key]) ?? "";
      const bv = (key === "name" ? b.name : b[key]) ?? "";
      const aEmpty = !av;
      const bEmpty = !bv;
      if (aEmpty && bEmpty) cmp = 0;
      else if (aEmpty) cmp = 1;
      else if (bEmpty) cmp = -1;
      else {
        cmp = av.localeCompare(bv, undefined, { sensitivity: "base" });
        if (!asc) cmp = -cmp;
      }
    } else if (key === "has" || key === "age") {
      cmp = compareNullableNumber(a[key], b[key], asc);
    } else {
      cmp = compareNullableNumber(a.attrs[key], b.attrs[key], asc);
    }
    if (cmp !== 0) return cmp;
    const hasCmp = compareNullableNumber(a.has, b.has, false);
    if (hasCmp !== 0) return hasCmp;
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  });
}

function isSquadHaTextSortKey(
  key: SquadHaSortKey,
): key is "name" | "unit" | "personality" | "mediaHandling" {
  return (
    key === "name" ||
    key === "unit" ||
    key === "personality" ||
    key === "mediaHandling"
  );
}

export function cycleSquadHaSort(
  currentKey: SquadHaSortKey,
  currentAsc: boolean,
  nextKey: SquadHaSortKey,
): { key: SquadHaSortKey; asc: boolean } {
  if (currentKey !== nextKey) {
    return { key: nextKey, asc: isSquadHaTextSortKey(nextKey) };
  }
  if (isSquadHaTextSortKey(nextKey)) {
    if (currentAsc) return { key: nextKey, asc: false };
    return { key: "has", asc: false };
  }
  if (!currentAsc) return { key: nextKey, asc: true };
  return { key: "has", asc: false };
}
