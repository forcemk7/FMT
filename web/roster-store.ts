/** localStorage persistence for uploaded .fm extracts, keyed by save filename. */

import {
  normalizeRosterPlayer,
  type LegacyRosterPlayer,
  type RosterPlayer,
} from "./roster-data.ts";

const STORAGE_KEY = "fmt.roster.saves.v3";
const LEGACY_STORAGE_KEY = "fmt.roster.saves.v2";

export type StoredFavouredClubPlayer = {
  uid: number;
  name?: string | null;
  affinity: number;
  ca?: number | null;
  pa?: number | null;
};

export type StoredReservesSquad = {
  iiName?: string;
  clubId?: number;
  teamId?: number | null;
  countHeader?: number;
  capaResolved?: number;
  /** Full roster-shaped players (same extract pipeline as First Team). */
  players: RosterPlayer[];
};

export type StoredU19Squad = {
  u19Name?: string;
  countHeader?: number;
  capaResolved?: number;
  /** Full roster-shaped players (same extract pipeline as First Team). */
  players: RosterPlayer[];
};

export type StoredFavouredClub = {
  clubId?: number;
  clubName?: string | null;
  clubNameShort?: string | null;
  affinity?: number;
  hitCount?: number;
  anchoredCount?: number;
  elapsedMs?: number;
  error?: string | null;
  players: StoredFavouredClubPlayer[];
};

export type StoredRoster = {
  saveName: string;
  /** Club Site UniqueID */
  clubId?: number;
  /** @deprecated alias of clubId */
  teamId?: number;
  clubName?: string;
  clubNameShort?: string;
  /** FM Date Created when extracted (ISO or display string). */
  dateCreated?: string | null;
  /** FM Last Saved when extracted. */
  lastSaved?: string | null;
  /** In-game date when extracted — used to derive age from DOB. */
  gameDate?: string | null;
  elapsedMs?: number;
  extractedAt: string;
  players: RosterPlayer[];
  /** Players who list this club as favoured (affinity 100), from the same upload. */
  favouredClub?: StoredFavouredClub | null;
  /** Reserves / II squad from the same upload. */
  reserves?: StoredReservesSquad | null;
  /** U19 squad from the same upload. */
  u19?: StoredU19Squad | null;
  /** Absolute path when bound to a disk file (dev auto-sync). */
  diskPath?: string | null;
  /** File mtimeMs at last extract — used to detect FM saves on disk. */
  diskMtimeMs?: number | null;
  /** Dest size at last extract — same snapshot as diskMtimeMs. */
  diskSize?: number | null;
};

export type RosterStore = {
  activeSaveName: string | null;
  saves: Record<string, StoredRoster>;
};

function emptyStore(): RosterStore {
  return { activeSaveName: null, saves: {} };
}

function isQuotaExceededError(err: unknown): boolean {
  if (!err || typeof err !== "object") return false;
  const e = err as { name?: string; code?: number | string };
  return (
    e.name === "QuotaExceededError" ||
    e.name === "NS_ERROR_DOM_QUOTA_REACHED" ||
    e.code === 22 ||
    e.code === 1014
  );
}

/** Keep only the live tip CA strip — last-resort quota shrink for II/U19. */
export function tipOnlyAttributeHistory(
  player: RosterPlayer,
): RosterPlayer {
  const hist = player.attributeHistory;
  if (!Array.isArray(hist) || hist.length <= 1) return player;
  const tip = { ...hist[hist.length - 1]!, index: 0 };
  return { ...player, attributeHistory: [tip] };
}

function trimPlayersAttributeHistory(
  players: RosterPlayer[],
  keep: number,
): RosterPlayer[] {
  return players.map((p) => {
    const hist = p.attributeHistory;
    if (!Array.isArray(hist) || hist.length <= keep) return p;
    const sliced = hist.slice(-keep).map((pt, i) => ({ ...pt, index: i }));
    return { ...p, attributeHistory: sliced };
  });
}

/** Trim FT + II + U19 CA strips. Never collapses to a single tip. */
function trimSquadsAttributeHistory(
  entry: StoredRoster,
  keep: number,
): StoredRoster {
  return {
    ...entry,
    players: trimPlayersAttributeHistory(entry.players, keep),
    ...(entry.reserves
      ? {
          reserves: {
            ...entry.reserves,
            players: trimPlayersAttributeHistory(entry.reserves.players, keep),
          },
        }
      : {}),
    ...(entry.u19
      ? {
          u19: {
            ...entry.u19,
            players: trimPlayersAttributeHistory(entry.u19.players, keep),
          },
        }
      : {}),
  };
}

/** II/U19 only — FT CA strip (Det/Lea Progress) must survive last-resort quota. */
function compactSubunitsForStorage(entry: StoredRoster): StoredRoster {
  return {
    ...entry,
    ...(entry.reserves
      ? {
          reserves: {
            ...entry.reserves,
            players: entry.reserves.players.map(tipOnlyAttributeHistory),
          },
        }
      : {}),
    ...(entry.u19
      ? {
          u19: {
            ...entry.u19,
            players: entry.u19.players.map(tipOnlyAttributeHistory),
          },
        }
      : {}),
  };
}

const HISTORY_TRIMS = [24, 8] as const;

function dropInactiveSaves(store: RosterStore): RosterStore {
  const active = store.activeSaveName;
  if (!active || !store.saves[active]) return store;
  if (Object.keys(store.saves).length <= 1) return store;
  return { activeSaveName: active, saves: { [active]: store.saves[active]! } };
}

function mapSaves(
  store: RosterStore,
  mapEntry: (entry: StoredRoster) => StoredRoster,
): RosterStore {
  const saves: Record<string, StoredRoster> = {};
  for (const [name, entry] of Object.entries(store.saves)) {
    saves[name] = mapEntry(entry);
  }
  return { ...store, saves };
}

function* quotaCompactCandidates(store: RosterStore): Generator<RosterStore> {
  let current = store;
  for (const keep of HISTORY_TRIMS) {
    current = mapSaves(current, (entry) =>
      trimSquadsAttributeHistory(entry, keep),
    );
    yield current;

    const dropped = dropInactiveSaves(current);
    if (dropped !== current) {
      yield dropped;
      current = dropped;
    }
  }

  yield mapSaves(current, compactSubunitsForStorage);
}

function normalizeSquadPlayers(raw: unknown[] | undefined): RosterPlayer[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((p) =>
    normalizeRosterPlayer({
      ...(p as LegacyRosterPlayer),
      uid: Number((p as LegacyRosterPlayer).uid) || 0,
      name: (p as LegacyRosterPlayer).name ?? "",
      kind: (p as LegacyRosterPlayer).kind ?? "UNKNOWN",
      source: (p as LegacyRosterPlayer).source ?? "save",
    }),
  );
}

function migrateSubunitPlayers(raw: unknown[] | undefined): RosterPlayer[] {
  return normalizeSquadPlayers(raw);
}

function migrateStoredRoster(raw: StoredRoster): StoredRoster {
  const reserves = raw.reserves
    ? {
        ...raw.reserves,
        players: migrateSubunitPlayers(raw.reserves.players as unknown[]),
      }
    : raw.reserves;
  const u19 = raw.u19
    ? {
        ...raw.u19,
        players: migrateSubunitPlayers(raw.u19.players as unknown[]),
      }
    : raw.u19;
  return {
    ...raw,
    players: (raw.players as LegacyRosterPlayer[]).map(normalizeRosterPlayer),
    ...(reserves !== undefined ? { reserves } : {}),
    ...(u19 !== undefined ? { u19 } : {}),
  };
}

function migrateStore(parsed: RosterStore): RosterStore {
  const saves: Record<string, StoredRoster> = {};
  for (const [name, entry] of Object.entries(parsed.saves ?? {})) {
    try {
      saves[name] = migrateStoredRoster(entry);
    } catch (err) {
      console.error(`Skipping corrupt Career Save extract “${name}”`, err);
    }
  }
  const active =
    typeof parsed.activeSaveName === "string" ? parsed.activeSaveName : null;
  return {
    activeSaveName: active && saves[active] ? active : (Object.keys(saves)[0] ?? null),
    saves,
  };
}

export function loadRosterStore(): RosterStore {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as RosterStore;
      if (!parsed || typeof parsed !== "object" || !parsed.saves) {
        return emptyStore();
      }
      return migrateStore(parsed);
    }
    // One-shot lift from v2 (personalityAttributes / age era).
    const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!legacy) return emptyStore();
    const parsed = JSON.parse(legacy) as RosterStore;
    if (!parsed || typeof parsed !== "object" || !parsed.saves) {
      return emptyStore();
    }
    const next = migrateStore(parsed);
    saveRosterStore(next);
    localStorage.removeItem(LEGACY_STORAGE_KEY);
    return next;
  } catch (err) {
    console.error("Failed to load Career Saves from localStorage", err);
    return emptyStore();
  }
}

export function saveRosterStore(store: RosterStore): void {
  const payload = JSON.stringify(store);
  try {
    localStorage.setItem(STORAGE_KEY, payload);
  } catch (err) {
    if (!isQuotaExceededError(err)) throw err;
    let lastErr: unknown = err;
    for (const candidate of quotaCompactCandidates(store)) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(candidate));
        return;
      } catch (inner) {
        lastErr = inner;
        if (!isQuotaExceededError(inner)) throw inner;
      }
    }
    throw lastErr instanceof Error
      ? lastErr
      : new Error("saveRosterStore quota exceeded");
  }
}

function normalizeStoredSubunit(
  squad: StoredReservesSquad | StoredU19Squad | null | undefined,
): StoredReservesSquad | StoredU19Squad | null | undefined {
  if (squad == null) return squad;
  return {
    ...squad,
    players: squad.players.map((p) =>
      normalizeRosterPlayer(p as LegacyRosterPlayer),
    ),
  };
}

/** Insert or replace an extract under its save filename (no merge across saves). */
export function upsertRoster(
  store: RosterStore,
  entry: StoredRoster,
  options?: { setActive?: boolean },
): RosterStore {
  const prev = store.saves[entry.saveName];
  // Omit reserves/u19 on the entry (e.g. disk-binding patch) → keep previous.
  // Explicit null clears. Present object replaces.
  const reserves = Object.prototype.hasOwnProperty.call(entry, "reserves")
    ? normalizeStoredSubunit(entry.reserves)
    : prev?.reserves;
  const u19 = Object.prototype.hasOwnProperty.call(entry, "u19")
    ? normalizeStoredSubunit(entry.u19)
    : prev?.u19;

  const nextEntry: StoredRoster = {
    ...entry,
    players: entry.players.map((p) =>
      normalizeRosterPlayer(p as LegacyRosterPlayer),
    ),
    ...(reserves !== undefined ? { reserves: reserves as StoredReservesSquad | null } : {}),
    ...(u19 !== undefined ? { u19: u19 as StoredU19Squad | null } : {}),
  };

  const current = store.activeSaveName;
  // T100: + / Edit persist sets Active to this save. T088: other upserts keep Active.
  const pinThisSave = options?.setActive === true;
  const keepActive =
    !pinThisSave &&
    current != null &&
    (current === entry.saveName || Boolean(store.saves[current]));
  const next: RosterStore = {
    activeSaveName: keepActive ? current : entry.saveName,
    saves: {
      ...store.saves,
      [entry.saveName]: nextEntry,
    },
  };
  saveRosterStore(next);
  return next;
}

export function setActiveRoster(
  store: RosterStore,
  saveName: string | null,
): RosterStore {
  const next: RosterStore = {
    ...store,
    activeSaveName:
      saveName && store.saves[saveName] ? saveName : null,
  };
  saveRosterStore(next);
  return next;
}

export function deleteRoster(store: RosterStore, saveName: string): RosterStore {
  const saves = { ...store.saves };
  delete saves[saveName];
  const activeSaveName =
    store.activeSaveName === saveName
      ? (Object.keys(saves)[0] ?? null)
      : store.activeSaveName;
  const next: RosterStore = { activeSaveName, saves };
  saveRosterStore(next);
  return next;
}

export function listRosterSaveNames(store: RosterStore): string[] {
  return Object.keys(store.saves).sort((a, b) =>
    a.localeCompare(b, undefined, { sensitivity: "base" }),
  );
}

/** Dest mtime jitter that must not retrigger a 690MB extract. */
export const PERSIST_MTIME_JITTER_MS = 2000;

/**
 * True when dest is the snapshot we already extracted.
 * Recopy/touch with the same size+mtime must not chain another extract.
 */
export function destMatchesLastPersist(
  dest: { mtimeMs: number; size: number },
  entry: Pick<StoredRoster, "diskMtimeMs" | "diskSize" | "extractedAt">,
): boolean {
  if (entry.diskMtimeMs == null || !Number.isFinite(entry.diskMtimeMs)) {
    return false;
  }
  if (Math.abs(dest.mtimeMs - entry.diskMtimeMs) > PERSIST_MTIME_JITTER_MS) {
    return false;
  }
  if (entry.diskSize != null && dest.size !== entry.diskSize) {
    return false;
  }
  const extractedMs = Date.parse(entry.extractedAt);
  if (!Number.isFinite(extractedMs)) return false;
  // Bind-only stamps have dest.mtime ≈ now and extractedAt in the past — not a match.
  return dest.mtimeMs <= extractedMs + PERSIST_MTIME_JITTER_MS;
}

/**
 * Whether the on-disk Career Save is newer than the last committed extract.
 *
 * `diskMtimeMs` is only trustworthy after a successful persist — never stamp it
 * from bind-alone. Prefer `extractedAt` so a bind-only mtime stamp cannot hide
 * FM writes that happened after the extract in the store.
 */
export function shouldRefreshRosterFromDisk(
  entry: Pick<StoredRoster, "diskMtimeMs" | "diskSize" | "extractedAt">,
  diskMtimeMs: number,
  diskSize?: number,
): boolean {
  if (
    diskSize != null &&
    destMatchesLastPersist({ mtimeMs: diskMtimeMs, size: diskSize }, entry)
  ) {
    return false;
  }
  const extractedMs = Date.parse(entry.extractedAt);
  if (Number.isFinite(extractedMs) && diskMtimeMs > extractedMs + 1000) {
    return true;
  }
  if (entry.diskMtimeMs != null && Number.isFinite(entry.diskMtimeMs)) {
    return diskMtimeMs > entry.diskMtimeMs + PERSIST_MTIME_JITTER_MS;
  }
  // No usable baseline — extract once to establish diskMtime/extractedAt.
  return !Number.isFinite(extractedMs);
}
