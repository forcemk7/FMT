/**
 * Append-only attribute history (visible / hidden / personality / CA / PA).
 * Never overwrites prior change-points — spreadsheet replacement with ups and downs.
 */

import type { LivePlayer } from "@/domain/adapters";

const STORAGE_KEY = "fmt.attr-history.v1";

export type AttrHistoryPoint = {
  /** Wall-clock observation time (ISO). */
  at: string;
  /** In-game date when known. */
  gameDate?: string | null;
  values: Record<string, number>;
};

export type AttrHistoryStore = {
  version: 1;
  players: Record<string, AttrHistoryPoint[]>;
};

function emptyStore(): AttrHistoryStore {
  return { version: 1, players: {} };
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

export function loadAttrHistoryStore(): AttrHistoryStore {
  try {
    if (typeof window === "undefined") return emptyStore();
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyStore();
    const parsed = JSON.parse(raw) as AttrHistoryStore;
    if (!parsed || parsed.version !== 1 || typeof parsed.players !== "object") return emptyStore();
    return parsed;
  } catch {
    return emptyStore();
  }
}

export function saveAttrHistoryStore(store: AttrHistoryStore): void {
  try {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
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

export function getPlayerAttrHistory(playerId: string): AttrHistoryPoint[] {
  if (!playerId) return [];
  return loadAttrHistoryStore().players[playerId] ?? [];
}

export function fieldDeltas(
  points: AttrHistoryPoint[],
  field: string,
): { recent: number | null; allTime: number | null; latest: number | null } {
  const series = points
    .map((point) => point.values[field])
    .filter((value): value is number => isFiniteNumber(value));
  if (!series.length) return { recent: null, allTime: null, latest: null };
  const latest = series[series.length - 1]!;
  const recent = series.length >= 2 ? latest - series[series.length - 2]! : null;
  const allTime = series.length >= 2 ? latest - series[0]! : null;
  return { recent, allTime, latest };
}

export function formatDelta(value: number | null): string {
  if (value == null) return "—";
  if (value > 0) return `+${value}`;
  return String(value);
}

const PLOT_COLORS = [
  "#5b8def", "#3ecf8e", "#f0b429", "#e85d75", "#a78bfa",
  "#2dd4bf", "#fb923c", "#38bdf8", "#c084fc", "#86efac",
  "#f472b6", "#facc15", "#22d3ee", "#f87171", "#a3e635",
];

export function colorForSeries(index: number): string {
  return PLOT_COLORS[index % PLOT_COLORS.length]!;
}
