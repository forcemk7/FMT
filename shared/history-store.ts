/** Shared history schema + safe v1→v2 migration (saves → players). */

export type HistorySignals = {
  personality: string;
  mediaHandling: string;
  determination?: number;
  leadership?: number;
  age?: number;
  isRegen: boolean;
};

export type PlayerLabels = {
  playerId?: string;
  playerName?: string;
  /** Preferred / listed position from save import (e.g. "D (L)", "GK"). */
  position?: string;
};

export type PlayerEntry = {
  id: string;
  createdAt: string;
  updatedAt: string;
  editedAt?: string;
  title: string;
  signals: HistorySignals;
  labels: PlayerLabels;
  caseMode: "union_feasible" | "naive_and";
  snapshot: Record<string, { min: number; max: number; midpoint: number }>;
  error?: string;
};

export type GameSave = {
  id: string;
  createdAt: string;
  updatedAt: string;
  editedAt?: string;
  /** Display name of the career save. */
  name: string;
  gameVersion?: string;
  database?: string;
  players: PlayerEntry[];
};

export type HistoryPanel = "saves" | "players";

export type HistoryStore = {
  version: 2;
  panel: HistoryPanel;
  activeSaveId: string | null;
  activePlayerId: string | null;
  saves: GameSave[];
};

/** Legacy flat store (pre save-grouping). */
type LegacyEntry = {
  id: string;
  createdAt: string;
  updatedAt: string;
  editedAt?: string;
  title: string;
  signals: HistorySignals;
  labels?: {
    gameVersion?: string;
    database?: string;
    gameSave?: string;
    playerId?: string;
    playerName?: string;
  };
  caseMode: "union_feasible" | "naive_and";
  snapshot: Record<string, { min: number; max: number; midpoint: number }>;
  error?: string;
};

type LegacyStore = {
  activeId?: string | null;
  entries?: LegacyEntry[];
};

export function emptyHistoryStore(): HistoryStore {
  return {
    version: 2,
    panel: "saves",
    activeSaveId: null,
    activePlayerId: null,
    saves: [],
  };
}

export function isHistoryStoreV2(value: unknown): value is HistoryStore {
  if (!value || typeof value !== "object") return false;
  const store = value as Partial<HistoryStore>;
  return store.version === 2 && Array.isArray(store.saves);
}

export function playerCount(store: HistoryStore): number {
  return store.saves.reduce((sum, save) => sum + save.players.length, 0);
}

export function findSave(
  store: HistoryStore,
  saveId: string | null | undefined,
): GameSave | undefined {
  if (!saveId) return undefined;
  return store.saves.find((save) => save.id === saveId);
}

export function findPlayer(
  store: HistoryStore,
  saveId: string | null | undefined,
  playerId: string | null | undefined,
): PlayerEntry | undefined {
  const save = findSave(store, saveId);
  if (!save || !playerId) return undefined;
  return save.players.find((player) => player.id === playerId);
}

function newId(): string {
  return crypto.randomUUID();
}

function groupKey(entry: LegacyEntry): string {
  const name = entry.labels?.gameSave?.trim() ?? "";
  if (name) return `save:${name}`;
  return `orphan:${entry.id}`;
}

/**
 * Convert flat v1 entries into grouped saves without dropping players.
 * Same gameSave name → one save; version/DB taken from first non-empty labels.
 */
export function migrateLegacyStore(legacy: LegacyStore): HistoryStore {
  const entries = legacy.entries ?? [];
  if (entries.length === 0) {
    return emptyHistoryStore();
  }

  const groups = new Map<string, LegacyEntry[]>();
  for (const entry of entries) {
    const key = groupKey(entry);
    const list = groups.get(key) ?? [];
    list.push(entry);
    groups.set(key, list);
  }

  const saves: GameSave[] = [];
  for (const [, group] of groups) {
    const sorted = [...group].sort((a, b) =>
      b.updatedAt.localeCompare(a.updatedAt),
    );
    const name =
      sorted.find((e) => e.labels?.gameSave?.trim())?.labels?.gameSave?.trim() ??
      "Untitled save";
    const gameVersion = sorted.find((e) => e.labels?.gameVersion)?.labels
      ?.gameVersion;
    const database = sorted.find((e) => e.labels?.database)?.labels?.database;
    const createdAt = [...group].sort((a, b) =>
      a.createdAt.localeCompare(b.createdAt),
    )[0]!.createdAt;
    const updatedAt = sorted[0]!.updatedAt;
    const editedAt = sorted.find((e) => e.editedAt)?.editedAt;

    const players: PlayerEntry[] = sorted.map((entry) => ({
      id: entry.id,
      createdAt: entry.createdAt,
      updatedAt: entry.updatedAt,
      ...(entry.editedAt ? { editedAt: entry.editedAt } : {}),
      title: entry.title,
      signals: entry.signals,
      labels: {
        ...(entry.labels?.playerId
          ? { playerId: entry.labels.playerId }
          : {}),
        ...(entry.labels?.playerName
          ? { playerName: entry.labels.playerName }
          : {}),
      },
      caseMode: entry.caseMode,
      snapshot: entry.snapshot ?? {},
      ...(entry.error ? { error: entry.error } : {}),
    }));

    saves.push({
      id: newId(),
      createdAt,
      updatedAt,
      ...(editedAt ? { editedAt } : {}),
      name,
      ...(gameVersion ? { gameVersion } : {}),
      ...(database ? { database } : {}),
      players,
    });
  }

  saves.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));

  let activeSaveId: string | null = saves[0]?.id ?? null;
  let activePlayerId: string | null = null;
  if (legacy.activeId) {
    for (const save of saves) {
      if (save.players.some((player) => player.id === legacy.activeId)) {
        activeSaveId = save.id;
        activePlayerId = legacy.activeId;
        break;
      }
    }
  }
  if (!activePlayerId && activeSaveId) {
    activePlayerId =
      saves.find((save) => save.id === activeSaveId)?.players[0]?.id ?? null;
  }

  return {
    version: 2,
    panel: activeSaveId ? "players" : "saves",
    activeSaveId,
    activePlayerId,
    saves,
  };
}

/** Normalize any on-disk JSON into a v2 store. Never drops players. */
export function normalizeHistoryStore(raw: unknown): {
  store: HistoryStore;
  migrated: boolean;
} {
  if (isHistoryStoreV2(raw)) {
    return {
      store: {
        version: 2,
        panel: raw.panel === "players" ? "players" : "saves",
        activeSaveId: raw.activeSaveId ?? null,
        activePlayerId: raw.activePlayerId ?? null,
        saves: (raw.saves ?? []).map((save) => ({
          ...save,
          players: (save.players ?? []).map((player) => ({
            ...player,
            labels: player.labels ?? {},
            snapshot: player.snapshot ?? {},
          })),
        })),
      },
      migrated: false,
    };
  }

  if (raw && typeof raw === "object" && Array.isArray((raw as LegacyStore).entries)) {
    return {
      store: migrateLegacyStore(raw as LegacyStore),
      migrated: true,
    };
  }

  return { store: emptyHistoryStore(), migrated: false };
}
