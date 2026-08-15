/**
 * FMT-side hidden-attribute development history (pack + Det/Lea).
 *
 * FM overwrites live HA in-place — there is no CA-style strip in the save.
 * We snapshot pack + Det/Lea on each Career Save upload, keyed by club + gameDate.
 */

import type { GeneralAttributes, GeneralKey } from "../shared/save/types.ts";
import {
  rosterPersonalitySignals,
  type RosterPlayer,
} from "./roster-data.ts";
import type { RosterStore, StoredRoster } from "./roster-store.ts";

const STORAGE_KEY = "fmt.ha-history.v1";

/** Pack fields we extract today (mental-trait pack near person double). */
export const HA_PACK_KEYS = [
  "adaptability",
  "ambition",
  "loyalty",
  "pressure",
  "professionalism",
  "sportsmanship",
  "temperament",
  "controversy",
] as const satisfies ReadonlyArray<GeneralKey>;

export type HaPackKey = (typeof HA_PACK_KEYS)[number];

/** Mentoring HA that live under mental (not the pack). */
export const HA_MENTAL_KEYS = ["determination", "leadership"] as const;
export type HaMentalKey = (typeof HA_MENTAL_KEYS)[number];

export type HaPackSnapshot = {
  /** In-game date (ISO YYYY-MM-DD). */
  gameDate: string;
  /** Wall-clock upload time. */
  extractedAt: string;
  /** Save filename that contributed this point (debug / provenance). */
  saveName?: string | null;
  values: Partial<Record<HaPackKey, number>>;
  /** Det/Lea at this extract (same date as pack). */
  mental?: Partial<Record<HaMentalKey, number>>;
};

export type HaCareerHistory = {
  clubId: number;
  clubName?: string | null;
  /** uid string → snapshots oldest → newest by gameDate */
  players: Record<string, HaPackSnapshot[]>;
};

export type HaHistoryStore = {
  careers: Record<string, HaCareerHistory>;
};

function emptyStore(): HaHistoryStore {
  return { careers: {} };
}

function careerKey(clubId: number): string {
  return String(clubId);
}

function isFiniteAttr(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

export function packValuesFromGeneral(
  general: GeneralAttributes | null | undefined,
): Partial<Record<HaPackKey, number>> | null {
  if (!general) return null;
  const values: Partial<Record<HaPackKey, number>> = {};
  let n = 0;
  for (const key of HA_PACK_KEYS) {
    const raw = general[key];
    if (!isFiniteAttr(raw)) continue;
    values[key] = raw;
    n += 1;
  }
  return n > 0 ? values : null;
}

/** Det/Lea as the HA table shows them (tip over live). */
export function mentalHaFromPlayer(
  player: RosterPlayer,
): Partial<Record<HaMentalKey, number>> | null {
  const signals = rosterPersonalitySignals(player);
  if (!signals) return null;
  const mental: Partial<Record<HaMentalKey, number>> = {};
  let n = 0;
  for (const key of HA_MENTAL_KEYS) {
    const raw = signals[key];
    if (!isFiniteAttr(raw)) continue;
    mental[key] = raw;
    n += 1;
  }
  return n > 0 ? mental : null;
}

export function packSignature(
  values: Partial<Record<HaPackKey, number>>,
): string {
  return HA_PACK_KEYS.map((k) => {
    const v = values[k];
    return v == null ? "-" : String(v);
  }).join(",");
}

function sortSnapshots(points: HaPackSnapshot[]): HaPackSnapshot[] {
  return [...points].sort(
    (a, b) =>
      a.gameDate.localeCompare(b.gameDate) ||
      a.extractedAt.localeCompare(b.extractedAt),
  );
}

/** Upsert one snapshot; same gameDate keeps the newer extractedAt. */
export function upsertHaSnapshot(
  points: HaPackSnapshot[],
  snap: HaPackSnapshot,
): HaPackSnapshot[] {
  const next = points.filter((p) => p.gameDate !== snap.gameDate);
  const prior = points.find((p) => p.gameDate === snap.gameDate);
  if (prior && prior.extractedAt > snap.extractedAt) {
    return sortSnapshots(points);
  }
  next.push(snap);
  return sortSnapshots(next);
}

export function loadHaHistoryStore(): HaHistoryStore {
  try {
    if (typeof localStorage === "undefined") return emptyStore();
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyStore();
    const parsed = JSON.parse(raw) as HaHistoryStore;
    if (!parsed || typeof parsed !== "object" || !parsed.careers) {
      return emptyStore();
    }
    return parsed;
  } catch (err) {
    console.error("Failed to load HA history store", err);
    return emptyStore();
  }
}

export function saveHaHistoryStore(store: HaHistoryStore): void {
  try {
    if (typeof localStorage === "undefined") return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch (err) {
    console.error("Failed to save HA history store", err);
  }
}

export function getHaCareerHistory(
  store: HaHistoryStore,
  clubId: number | null | undefined,
): HaCareerHistory | null {
  if (clubId == null || !Number.isFinite(clubId)) return null;
  return store.careers[careerKey(clubId)] ?? null;
}

export function getPlayerHaHistory(
  store: HaHistoryStore,
  clubId: number | null | undefined,
  uid: number,
): HaPackSnapshot[] {
  const career = getHaCareerHistory(store, clubId);
  if (!career) return [];
  return career.players[String(uid)] ?? [];
}

/**
 * Merge pack snapshots from one Career Save extract into the HA history store.
 */
export function mergeHaHistoryFromRoster(
  store: HaHistoryStore,
  entry: Pick<
    StoredRoster,
    | "clubId"
    | "clubName"
    | "gameDate"
    | "extractedAt"
    | "saveName"
    | "players"
    | "reserves"
    | "u19"
  >,
): HaHistoryStore {
  const clubId = entry.clubId;
  const gameDate = entry.gameDate?.trim() || null;
  if (clubId == null || !Number.isFinite(clubId) || !gameDate) {
    return store;
  }

  const key = careerKey(clubId);
  const career: HaCareerHistory = {
    clubId,
    clubName: entry.clubName ?? store.careers[key]?.clubName ?? null,
    players: { ...(store.careers[key]?.players ?? {}) },
  };

  const pool: RosterPlayer[] = [
    ...entry.players,
    ...(entry.reserves?.players ?? []),
    ...(entry.u19?.players ?? []),
  ];

  let merged = 0;
  for (const player of pool) {
    const values = packValuesFromGeneral(player.attributes?.general);
    const mental = mentalHaFromPlayer(player);
    if (!values && !mental) continue;
    const uid = String(player.uid);
    career.players[uid] = upsertHaSnapshot(career.players[uid] ?? [], {
      gameDate,
      extractedAt: entry.extractedAt,
      saveName: entry.saveName,
      values: values ?? {},
      ...(mental ? { mental } : {}),
    });
    merged += 1;
  }

  if (merged === 0 && !entry.clubName) {
    return store;
  }

  const nextStore: HaHistoryStore = {
    careers: { ...store.careers, [key]: career },
  };
  saveHaHistoryStore(nextStore);
  return nextStore;
}

/** Backfill HA history from every stored Career Save extract (one-shot / on load). */
export function backfillHaHistoryFromRosterStore(
  haStore: HaHistoryStore,
  rosterStore: RosterStore,
): HaHistoryStore {
  let next = haStore;
  for (const entry of Object.values(rosterStore.saves)) {
    next = mergeHaHistoryFromRoster(next, entry);
  }
  return next;
}

/** Map snapshots → AttributeHistoryPoint-shaped series (pack general + Det/Lea mental). */
export function haSnapshotsToHistoryPoints(
  snapshots: HaPackSnapshot[],
): Array<{
  index: number;
  date: string;
  general: Partial<Record<HaPackKey, number>>;
  mental?: Partial<Record<HaMentalKey, number>>;
}> {
  return snapshots.map((snap, index) => ({
    index,
    date: snap.gameDate,
    general: { ...snap.values },
    ...(snap.mental && Object.keys(snap.mental).length > 0
      ? { mental: { ...snap.mental } }
      : {}),
  }));
}

/** Convenience: pack from a roster player at current extract. */
export function playerHaPackValues(
  player: RosterPlayer,
): Partial<Record<HaPackKey, number>> | null {
  return packValuesFromGeneral(player.attributes?.general);
}
