import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  loadRosterStore,
  saveRosterStore,
  shouldRefreshRosterFromDisk,
  upsertRoster,
  type RosterStore,
  type StoredRoster,
} from "../web/roster-store.ts";
import type { RosterPlayer } from "../web/roster-data.ts";

const STORAGE_KEY = "fmt.roster.saves.v3";

const memory = new Map<string, string>();
const localStorageMock = {
  getItem: (key: string) => memory.get(key) ?? null,
  setItem: (key: string, value: string) => {
    memory.set(key, String(value));
  },
  removeItem: (key: string) => {
    memory.delete(key);
  },
  clear: () => memory.clear(),
};

beforeEach(() => {
  memory.clear();
  Object.defineProperty(globalThis, "localStorage", {
    value: localStorageMock,
    configurable: true,
  });
});

afterEach(() => {
  memory.clear();
});

function player(uid: number, name: string, loanStatus?: "loanedOut"): RosterPlayer {
  return {
    uid,
    name,
    kind: "REAL",
    source: "save",
    ...(loanStatus
      ? {
          loan: {
            status: loanStatus,
            loanClubId: 1,
            parentClubId: null,
            loanClubName: "Loan FC",
            parentClubName: null,
          },
        }
      : { loan: null }),
  } as RosterPlayer;
}

function emptyStore(): RosterStore {
  return { activeSaveName: null, saves: {} };
}

describe("upsertRoster persist (T010)", () => {
  it("replaces players[] on re-extract — never keeps stale loan/name payload", () => {
    const stale: StoredRoster = {
      saveName: "Schalke.fm",
      clubId: 920,
      extractedAt: "2026-08-01T00:00:00.000Z",
      gameDate: "2026-08-01",
      players: [player(1, "Old Name"), player(2, "Ghost")],
      diskPath: null,
      diskMtimeMs: null,
    };
    let store = upsertRoster(emptyStore(), stale);

    const fresh: StoredRoster = {
      saveName: "Schalke.fm",
      clubId: 920,
      extractedAt: "2026-08-12T00:00:00.000Z",
      gameDate: "2026-08-12",
      players: [
        player(1, "New Name"),
        player(3, "Joiner"),
        player(2, "Ghost", "loanedOut"),
      ],
      diskPath: "/games/Schalke.fm",
      diskMtimeMs: 1_700_000_000_000,
    };
    store = upsertRoster(store, fresh);

    const entry = store.saves["Schalke.fm"]!;
    expect(entry.players.map((p) => [p.uid, p.name, p.loan?.status ?? null])).toEqual([
      [1, "New Name", null],
      [3, "Joiner", null],
      [2, "Ghost", "loanedOut"],
    ]);
    expect(entry.extractedAt).toBe("2026-08-12T00:00:00.000Z");
    expect(entry.diskMtimeMs).toBe(1_700_000_000_000);

    // Round-trip through localStorage must keep the fresh players.
    saveRosterStore(store);
    const reloaded = loadRosterStore();
    expect(reloaded.saves["Schalke.fm"]!.players.map((p) => p.name)).toEqual([
      "New Name",
      "Joiner",
      "Ghost",
    ]);
  });
});

describe("shouldRefreshRosterFromDisk (T010)", () => {
  it("refreshes when file mtime is newer than extractedAt (heals bind-only mtime stamps)", () => {
    const entry = {
      extractedAt: "2026-08-01T12:00:00.000Z",
      // Bind wrongly stamped current file mtime without extracting.
      diskMtimeMs: Date.parse("2026-08-10T12:00:00.000Z"),
    };
    const fileMtime = Date.parse("2026-08-10T12:00:00.000Z");
    expect(shouldRefreshRosterFromDisk(entry, fileMtime)).toBe(true);
  });

  it("skips when file is not newer than the last extract", () => {
    const extractedAt = "2026-08-12T15:00:00.000Z";
    const fileMtime = Date.parse("2026-08-12T14:00:00.000Z");
    expect(
      shouldRefreshRosterFromDisk(
        { extractedAt, diskMtimeMs: fileMtime },
        fileMtime,
      ),
    ).toBe(false);
  });

  it("refreshes when diskMtime advances after a committed extract", () => {
    const extractedAt = "2026-08-12T15:00:00.000Z";
    const prevMtime = Date.parse("2026-08-12T14:59:00.000Z");
    const nextMtime = prevMtime + 60_000;
    // File mtime still behind wall-clock extractedAt, but ahead of last diskMtime.
    expect(
      shouldRefreshRosterFromDisk(
        { extractedAt, diskMtimeMs: prevMtime },
        nextMtime,
      ),
    ).toBe(true);
  });
});
