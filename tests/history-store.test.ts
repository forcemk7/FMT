import { describe, expect, it } from "vitest";
import { normalizeHistoryStore } from "../shared/history-store.ts";

describe("history store migration", () => {
  it("groups legacy players under their game save without changing player ids", () => {
    const legacy = {
      activeId: "player-2",
      entries: [
        {
          id: "player-1",
          createdAt: "2026-01-01T10:00:00.000Z",
          updatedAt: "2026-01-01T10:01:00.000Z",
          title: "Driven / Evasive",
          signals: {
            personality: "Driven",
            mediaHandling: "Evasive",
            isRegen: false,
          },
          labels: {
            gameSave: "Journeyman",
            gameVersion: "FM26 26.3.2",
            playerName: "Alex One",
          },
          caseMode: "union_feasible",
          snapshot: {},
        },
        {
          id: "player-2",
          createdAt: "2026-01-02T10:00:00.000Z",
          updatedAt: "2026-01-02T10:01:00.000Z",
          title: "Resolute / Reserved",
          signals: {
            personality: "Resolute",
            mediaHandling: "Reserved",
            isRegen: true,
          },
          labels: {
            gameSave: "Journeyman",
            database: "26.2.0",
            playerId: "9876",
          },
          caseMode: "union_feasible",
          snapshot: {},
        },
      ],
    };

    const { store, migrated } = normalizeHistoryStore(legacy);

    expect(migrated).toBe(true);
    expect(store.saves).toHaveLength(1);
    expect(store.saves[0]?.name).toBe("Journeyman");
    expect(store.saves[0]?.players.map((player) => player.id).sort()).toEqual([
      "player-1",
      "player-2",
    ]);
    expect(store.saves[0]?.players[0]?.labels).not.toHaveProperty("gameSave");
    expect(store.activePlayerId).toBe("player-2");
  });
});
