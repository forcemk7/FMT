import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  destMatchesLastPersist,
  loadRosterStore,
  saveRosterStore,
  setActiveRoster,
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

  it("does not steal Active when upserting another save (T088)", () => {
    const alpha: StoredRoster = {
      saveName: "A.fm",
      clubId: 1,
      extractedAt: "2026-08-01T00:00:00.000Z",
      players: [player(1, "Alpha")],
    };
    const beta: StoredRoster = {
      saveName: "B.fm",
      clubId: 2,
      extractedAt: "2026-08-01T00:00:00.000Z",
      players: [player(2, "Beta")],
    };
    let store = upsertRoster(emptyStore(), alpha);
    expect(store.activeSaveName).toBe("A.fm");
    store = setActiveRoster(store, "A.fm");
    store = upsertRoster(store, beta);
    expect(store.activeSaveName).toBe("A.fm");
    expect(store.saves["B.fm"]?.players[0]?.name).toBe("Beta");

    const betaFresh: StoredRoster = {
      ...beta,
      extractedAt: "2026-08-16T00:00:00.000Z",
      players: [player(2, "Beta Updated")],
    };
    store = upsertRoster(store, betaFresh);
    expect(store.activeSaveName).toBe("A.fm");
    expect(store.saves["B.fm"]?.players[0]?.name).toBe("Beta Updated");
  });

  it("sets Active to the upserted save when setActive (T100)", () => {
    const alpha: StoredRoster = {
      saveName: "A.fm",
      clubId: 1,
      extractedAt: "2026-08-01T00:00:00.000Z",
      players: [player(1, "Alpha")],
    };
    const beta: StoredRoster = {
      saveName: "B.fm",
      clubId: 2,
      extractedAt: "2026-08-16T00:00:00.000Z",
      players: [player(2, "Beta")],
    };
    let store = upsertRoster(emptyStore(), alpha);
    expect(store.activeSaveName).toBe("A.fm");
    store = upsertRoster(store, beta, { setActive: true });
    expect(store.activeSaveName).toBe("B.fm");
    expect(store.saves["A.fm"]?.players[0]?.name).toBe("Alpha");
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

  it("skips when dest already matches the last persist (T067)", () => {
    const extractedAt = "2026-08-15T00:10:00.000Z";
    const destMtime = Date.parse("2026-08-15T00:05:00.000Z");
    const destSize = 688_314_098;
    expect(
      destMatchesLastPersist(
        { mtimeMs: destMtime, size: destSize },
        { extractedAt, diskMtimeMs: destMtime, diskSize: destSize },
      ),
    ).toBe(true);
    expect(
      shouldRefreshRosterFromDisk(
        { extractedAt, diskMtimeMs: destMtime, diskSize: destSize },
        destMtime,
        destSize,
      ),
    ).toBe(false);
    // Filesystem mtime jitter on the same snapshot must not re-extract.
    expect(
      shouldRefreshRosterFromDisk(
        { extractedAt, diskMtimeMs: destMtime, diskSize: destSize },
        destMtime + 5,
        destSize,
      ),
    ).toBe(false);
  });

  it("refreshes when dest mtime advances after persist (new copy)", () => {
    const extractedAt = "2026-08-15T00:10:00.000Z";
    const destMtime = Date.parse("2026-08-15T00:05:00.000Z");
    const destSize = 688_314_098;
    expect(
      shouldRefreshRosterFromDisk(
        { extractedAt, diskMtimeMs: destMtime, diskSize: destSize },
        destMtime + 60_000,
        destSize,
      ),
    ).toBe(true);
  });
});

describe("saveRosterStore quota (T068 / T079)", () => {
  function ftPlayerWithStrip(points: number): RosterPlayer {
    return {
      ...player(1, "Jan Lundqvist"),
      attributeHistory: Array.from({ length: points }, (_, i) => ({
        index: i,
        mental: { determination: 6 + i },
      })),
    } as RosterPlayer;
  }

  function iiPlayerWithStrip(points = 8): RosterPlayer {
    return {
      ...player(2, "II Kid"),
      attributeHistory: Array.from({ length: points }, (_, i) => ({
        index: i,
        mental: { determination: 10 },
      })),
    } as RosterPlayer;
  }

  function storeWithStrips(): RosterStore {
    const entry: StoredRoster = {
      saveName: "Schalke.fm",
      clubId: 920,
      extractedAt: "2026-08-15T00:00:00.000Z",
      gameDate: "2040-01-13",
      players: [ftPlayerWithStrip(12)],
      reserves: {
        iiName: "II",
        players: [iiPlayerWithStrip()],
      },
      u19: {
        u19Name: "Schalke 04 U19",
        players: [iiPlayerWithStrip()],
      },
      diskPath: null,
      diskMtimeMs: null,
    };
    return {
      activeSaveName: "Schalke.fm",
      saves: { "Schalke.fm": entry },
    };
  }

  it("upsert keeps II/U19 CA strips (not tip-only)", () => {
    saveRosterStore(storeWithStrips());
    const reloaded = loadRosterStore();
    expect(
      reloaded.saves["Schalke.fm"]!.reserves?.players[0]?.attributeHistory?.length,
    ).toBe(8);
    expect(reloaded.saves["Schalke.fm"]!.u19?.players[0]?.attributeHistory?.length).toBe(
      8,
    );
    expect(reloaded.saves["Schalke.fm"]!.players[0]?.attributeHistory?.length).toBe(12);
  });

  it("quota compact trims; II/U19 stay more than one point when 8 fit", () => {
    let writes = 0;
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: {
        getItem: (key: string) => memory.get(key) ?? null,
        setItem: (key: string, value: string) => {
          writes += 1;
          if (writes === 1) {
            const err = new Error("quota") as Error & { name: string };
            err.name = "QuotaExceededError";
            throw err;
          }
          memory.set(key, String(value));
        },
        removeItem: (key: string) => {
          memory.delete(key);
        },
        clear: () => memory.clear(),
      },
    });

    saveRosterStore(storeWithStrips());
    const reloaded = loadRosterStore();
    const ft = reloaded.saves["Schalke.fm"]!.players[0]!;
    expect(ft.attributeHistory?.length).toBe(12);
    expect(ft.attributeHistory?.at(-1)?.mental?.determination).toBe(17);
    expect(
      reloaded.saves["Schalke.fm"]!.reserves?.players[0]?.attributeHistory?.length,
    ).toBe(8);
    expect(reloaded.saves["Schalke.fm"]!.u19?.players[0]?.attributeHistory?.length).toBe(
      8,
    );
  });

  it("quota last resort tip-onlys II/U19 if trim still overflows", () => {
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: {
        getItem: (key: string) => memory.get(key) ?? null,
        setItem: (key: string, value: string) => {
          const parsed = JSON.parse(String(value)) as RosterStore;
          const iiLen =
            parsed.saves["Schalke.fm"]?.reserves?.players[0]?.attributeHistory
              ?.length ?? 0;
          if (iiLen > 1) {
            const err = new Error("quota") as Error & { name: string };
            err.name = "QuotaExceededError";
            throw err;
          }
          memory.set(key, String(value));
        },
        removeItem: (key: string) => {
          memory.delete(key);
        },
        clear: () => memory.clear(),
      },
    });

    saveRosterStore(storeWithStrips());
    const reloaded = loadRosterStore();
    expect(
      reloaded.saves["Schalke.fm"]!.reserves?.players[0]?.attributeHistory?.length,
    ).toBe(1);
    expect(reloaded.saves["Schalke.fm"]!.u19?.players[0]?.attributeHistory?.length).toBe(
      1,
    );
    expect(reloaded.saves["Schalke.fm"]!.players[0]?.attributeHistory?.length).toBe(8);
  });
});
