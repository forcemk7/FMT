/**
 * Append-only attribute history (visible / hidden / personality / CA / PA).
 * Never overwrites prior change-points — spreadsheet replacement with ups and downs.
 *
 * Store v2: T132 fixed FM attr rounding `(raw+2)/5`. v1 points were often +1 high;
 * keeping them made Development “all-time” look like blanket −1 after the fix.
 */

import type { LivePlayer } from "@/domain/adapters";

const STORE_VERSION = 2 as const;
const STORAGE_KEY = "fmt.attr-history.v2";
/** Pre-T132 rounding poison — ignore and drop if still present. */
const LEGACY_STORAGE_KEY = "fmt.attr-history.v1";

export type AttrHistoryPoint = {
  /** Wall-clock observation time (ISO). */
  at: string;
  /** In-game date when known. */
  gameDate?: string | null;
  values: Record<string, number>;
};

export type AttrHistoryStore = {
  version: typeof STORE_VERSION;
  players: Record<string, AttrHistoryPoint[]>;
};

function emptyStore(): AttrHistoryStore {
  return { version: STORE_VERSION, players: {} };
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function valuesFromPlayer(player: LivePlayer): Record<string, number> {
  const values: Record<string, number> = {};
  if (isFiniteNumber(player.currentAbility)) values.CA = player.currentAbility;
  if (isFiniteNumber(player.potentialAbility)) values.PA = player.potentialAbility;
  for (const [key, value] of Object.entries(player.attributes ?? {})) {
    if (isFiniteNumber(value)) values[key] = value;
  }
  for (const [key, value] of Object.entries(player.hiddenAttributes ?? {})) {
    if (isFiniteNumber(value)) values[key] = value;
  }
  for (const [key, value] of Object.entries(player.personalityAttributes ?? {})) {
    if (isFiniteNumber(value)) values[key] = value;
  }
  return values;
}

function signaturesEqual(a: Record<string, number>, b: Record<string, number>): boolean {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  for (const key of keys) {
    if (a[key] !== b[key]) return false;
  }
  return true;
}

/** Parse persisted JSON; any non-v2 payload is treated as empty (drops rounding-poisoned v1). */
export function parseAttrHistoryStore(raw: string | null | undefined): AttrHistoryStore {
  if (!raw) return emptyStore();
  try {
    const parsed = JSON.parse(raw) as { version?: unknown; players?: unknown };
    if (
      !parsed ||
      parsed.version !== STORE_VERSION ||
      typeof parsed.players !== "object" ||
      parsed.players == null ||
      Array.isArray(parsed.players)
    ) {
      return emptyStore();
    }
    return { version: STORE_VERSION, players: parsed.players as Record<string, AttrHistoryPoint[]> };
  } catch {
    return emptyStore();
  }
}

export function loadAttrHistoryStore(): AttrHistoryStore {
  try {
    if (typeof window === "undefined") return emptyStore();
    // Drop legacy v1 so Development cannot read poisoned baselines.
    if (window.localStorage.getItem(LEGACY_STORAGE_KEY) != null) {
      window.localStorage.removeItem(LEGACY_STORAGE_KEY);
    }
    return parseAttrHistoryStore(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    return emptyStore();
  }
}

export function saveAttrHistoryStore(store: AttrHistoryStore): void {
  try {
    if (typeof window === "undefined") return;
    const payload: AttrHistoryStore = { version: STORE_VERSION, players: store.players };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Quota / private mode — history is best-effort.
  }
}

/** Append a point only when at least one tracked value changed (or first sighting). */
export function appendPlayerSnapshot(
  store: AttrHistoryStore,
  playerId: string,
  values: Record<string, number>,
  gameDate?: string | null,
  at = new Date().toISOString(),
): AttrHistoryStore {
  if (!playerId || Object.keys(values).length === 0) return store;
  const prior = store.players[playerId] ?? [];
  const last = prior[prior.length - 1];
  if (last && signaturesEqual(last.values, values)) return store;
  return {
    ...store,
    players: {
      ...store.players,
      [playerId]: [...prior, { at, gameDate: gameDate ?? null, values }],
    },
  };
}

export function recordPlayersFromSnapshot(
  players: LivePlayer[],
  gameDate?: string | null,
): AttrHistoryStore {
  let store = loadAttrHistoryStore();
  const at = new Date().toISOString();
  for (const player of players) {
    store = appendPlayerSnapshot(store, player.id, valuesFromPlayer(player), gameDate, at);
  }
  saveAttrHistoryStore(store);
  return store;
}

/** Attach recent + all-time delta maps from a history store onto each player. */
export function attachAttrDeltas(
  players: LivePlayer[],
  store: AttrHistoryStore = loadAttrHistoryStore(),
): LivePlayer[] {
  return players.map((player) => {
    if (!player.id) {
      return {
        ...player,
        recentAttrDeltas: {},
        allTimeAttrDeltas: {},
      };
    }
    const points = store.players[player.id] ?? [];
    return {
      ...player,
      recentAttrDeltas: recentDeltasFromPoints(points),
      allTimeAttrDeltas: allTimeDeltasFromPoints(points),
    };
  });
}

/**
 * Load pipeline: append change-points, then stamp recent/all-time Δ on players
 * for Attributes / Development desks.
 */
export function ingestSnapshotPlayers(
  players: LivePlayer[],
  gameDate?: string | null,
): LivePlayer[] {
  const store = recordPlayersFromSnapshot(players, gameDate);
  return attachAttrDeltas(players, store);
}

export function getPlayerAttrHistory(playerId: string): AttrHistoryPoint[] {
  if (!playerId) return [];
  return loadAttrHistoryStore().players[playerId] ?? [];
}

export function fieldDeltas(
  points: AttrHistoryPoint[],
  field: string,
): { recent: number | null; allTime: number | null; latest: number | null } {
  if (!points.length) return { recent: null, allTime: null, latest: null };

  // All-time = last observation − first observation for this field.
  // Do not skip early points that lack the field (that invents a false baseline).
  const firstRaw = points[0]!.values[field];
  const lastRaw = points[points.length - 1]!.values[field];
  const latest = isFiniteNumber(lastRaw) ? lastRaw : null;
  const allTime =
    points.length >= 2 && isFiniteNumber(firstRaw) && isFiniteNumber(lastRaw)
      ? lastRaw - firstRaw
      : null;

  let recent: number | null = null;
  if (points.length >= 2) {
    const prevRaw = points[points.length - 2]!.values[field];
    if (isFiniteNumber(prevRaw) && isFiniteNumber(lastRaw)) recent = lastRaw - prevRaw;
  }

  return { recent, allTime, latest };
}

/** Recent (vs previous change-point) delta for every field in a history series. */
export function recentDeltasFromPoints(points: AttrHistoryPoint[]): Record<string, number | null> {
  if (!points.length) return {};
  const fields = new Set<string>();
  for (const point of points) {
    for (const key of Object.keys(point.values)) fields.add(key);
  }
  const deltas: Record<string, number | null> = {};
  for (const field of fields) {
    deltas[field] = fieldDeltas(points, field).recent;
  }
  return deltas;
}

/** All-time (vs first change-point) delta for every field in a history series. */
export function allTimeDeltasFromPoints(points: AttrHistoryPoint[]): Record<string, number | null> {
  if (!points.length) return {};
  const fields = new Set<string>();
  for (const point of points) {
    for (const key of Object.keys(point.values)) fields.add(key);
  }
  const deltas: Record<string, number | null> = {};
  for (const field of fields) {
    deltas[field] = fieldDeltas(points, field).allTime;
  }
  return deltas;
}

/** Recent (vs previous change-point) delta for every field seen in this player's history. */
export function recentDeltasForPlayer(playerId: string): Record<string, number | null> {
  return recentDeltasFromPoints(getPlayerAttrHistory(playerId));
}

/** All-time (vs first change-point) delta for every field seen in this player's history. */
export function allTimeDeltasForPlayer(playerId: string): Record<string, number | null> {
  return allTimeDeltasFromPoints(getPlayerAttrHistory(playerId));
}

export type SquadMoverChange = { field: string; delta: number };

export type SquadMover<T extends { id: string } = { id: string }> = {
  player: T;
  changes: SquadMoverChange[];
  /** Sum of |delta| — primary sort key. */
  magnitude: number;
};

const MOVER_FIELD_PRIORITY = ["CA", "PA", "Determination", "Professionalism"];

function sortMoverChanges(changes: SquadMoverChange[]): SquadMoverChange[] {
  return [...changes].sort((a, b) => {
    const ai = MOVER_FIELD_PRIORITY.indexOf(a.field);
    const bi = MOVER_FIELD_PRIORITY.indexOf(b.field);
    const aPri = ai === -1 ? 99 : ai;
    const bPri = bi === -1 ? 99 : bi;
    if (aPri !== bPri) return aPri - bPri;
    if (Math.abs(b.delta) !== Math.abs(a.delta)) return Math.abs(b.delta) - Math.abs(a.delta);
    return a.field.localeCompare(b.field);
  });
}

/**
 * Managed-squad players with any non-zero recent history delta (vs prior change-point).
 * Empty when history has fewer than two points or nothing moved.
 */
export function rankSquadMovers<T extends { id: string }>(
  players: T[],
  getHistory: (playerId: string) => AttrHistoryPoint[] = getPlayerAttrHistory,
  limit = 12,
): SquadMover<T>[] {
  const movers: SquadMover<T>[] = [];
  for (const player of players) {
    if (!player.id) continue;
    const deltas = recentDeltasFromPoints(getHistory(player.id));
    const changes: SquadMoverChange[] = [];
    let magnitude = 0;
    for (const [field, delta] of Object.entries(deltas)) {
      if (delta == null || delta === 0) continue;
      changes.push({ field, delta });
      magnitude += Math.abs(delta);
    }
    if (!changes.length) continue;
    movers.push({ player, changes: sortMoverChanges(changes), magnitude });
  }
  movers.sort((a, b) => {
    if (b.magnitude !== a.magnitude) return b.magnitude - a.magnitude;
    if (b.changes.length !== a.changes.length) return b.changes.length - a.changes.length;
    return a.player.id.localeCompare(b.player.id);
  });
  return movers.slice(0, Math.max(0, limit));
}

export function formatDelta(value: number | null): string {
  if (value == null) return "—";
  if (value > 0) return `+${value}`;
  return String(value);
}

export type AttrFieldMove = { field: string; from: number | null; to: number; delta: number };

/** Fields that differ between two consecutive observations (appear / change / leave counted as move). */
export function movedFieldsBetween(
  previous: Record<string, number> | null | undefined,
  next: Record<string, number>,
): AttrFieldMove[] {
  const prev = previous ?? {};
  const keys = new Set([...Object.keys(prev), ...Object.keys(next)]);
  const moves: AttrFieldMove[] = [];
  for (const field of keys) {
    const from = isFiniteNumber(prev[field]) ? prev[field]! : null;
    const to = isFiniteNumber(next[field]) ? next[field]! : null;
    if (to == null) continue;
    if (from === to) continue;
    const delta = from == null ? to : to - from;
    if (delta === 0) continue;
    moves.push({ field, from, to, delta });
  }
  return moves.sort((a, b) => {
    if (Math.abs(b.delta) !== Math.abs(a.delta)) return Math.abs(b.delta) - Math.abs(a.delta);
    return a.field.localeCompare(b.field);
  });
}

export type AttrTimelineRow = {
  /** Index in chronological store (0 = first observation). */
  index: number;
  at: string;
  gameDate: string | null;
  /** Prefer in-game date; fall back to wall-clock observation time. */
  label: string;
  isFirst: boolean;
  moves: AttrFieldMove[];
  values: Record<string, number>;
};

function formatWallClock(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Newest-first evidence rows for the Development desk. */
export function buildAttrTimeline(points: AttrHistoryPoint[]): AttrTimelineRow[] {
  const rows: AttrTimelineRow[] = [];
  for (let index = points.length - 1; index >= 0; index--) {
    const point = points[index]!;
    const previous = index > 0 ? points[index - 1]!.values : null;
    const gameDate = point.gameDate?.trim() ? point.gameDate.trim() : null;
    rows.push({
      index,
      at: point.at,
      gameDate,
      label: gameDate ?? formatWallClock(point.at),
      isFirst: index === 0,
      // First point is baseline — no prior to diff against.
      moves: previous ? movedFieldsBetween(previous, point.values) : [],
      values: point.values,
    });
  }
  return rows;
}

/** Factual one-liner — counts and CA span only; no mentoring doctrine. */
export function factualHistorySummary(points: AttrHistoryPoint[]): string | null {
  if (points.length === 0) return null;
  if (points.length === 1) {
    return "1 observation on record. Reload after in-game days; a new point appends when tracked values change.";
  }
  const ca = fieldDeltas(points, "CA");
  const lastMoves = movedFieldsBetween(
    points[points.length - 2]!.values,
    points[points.length - 1]!.values,
  );
  const parts = [
    `${points.length} observations`,
    ca.allTime != null ? `CA ${formatDelta(ca.allTime)} vs first` : null,
    lastMoves.length
      ? `${lastMoves.length} field${lastMoves.length === 1 ? "" : "s"} moved last load`
      : "no field moves last load",
  ];
  return parts.filter(Boolean).join(" · ") + ".";
}

const PLOT_COLORS = [
  "#5b8def", "#3ecf8e", "#f0b429", "#e85d75", "#a78bfa",
  "#2dd4bf", "#fb923c", "#38bdf8", "#c084fc", "#86efac",
  "#f472b6", "#facc15", "#22d3ee", "#f87171", "#a3e635",
];

export function colorForSeries(index: number): string {
  return PLOT_COLORS[index % PLOT_COLORS.length]!;
}

/** Stable plot color for a field in the current selection order; null if not selected. */
export function colorForPlotField(field: string, selectedFields: readonly string[]): string | null {
  const index = selectedFields.indexOf(field);
  if (index < 0) return null;
  return colorForSeries(index);
}

