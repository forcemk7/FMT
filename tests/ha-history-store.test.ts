import { describe, expect, it } from "vitest";
import {
  HA_PACK_KEYS,
  mergeHaHistoryFromRoster,
  packSignature,
  packValuesFromGeneral,
  upsertHaSnapshot,
  type HaHistoryStore,
  type HaPackSnapshot,
} from "../web/ha-history-store.ts";
import type { RosterPlayer } from "../web/roster-data.ts";

function player(
  uid: number,
  general: Record<string, number>,
): RosterPlayer {
  return {
    jobId: uid,
    uid,
    name: `P${uid}`,
    dateOfBirth: null,
    nation: null,
    secondNation: null,
    positions: null,
    dynamics: { captaincy: null, hierarchy: null, socialGroup: null },
    training: { unit: null },
    attributes: { general },
    attributeHistory: null,
  };
}

describe("ha-history-store", () => {
  it("packValuesFromGeneral keeps only HA pack keys", () => {
    const values = packValuesFromGeneral({
      adaptability: 18,
      ambition: 14,
      loyalty: 12,
      pressure: 9,
      professionalism: 16,
      sportsmanship: 12,
      temperament: 16,
      controversy: 7,
      consistency: 11,
      dirtiness: 5,
    });
    expect(values).toEqual({
      adaptability: 18,
      ambition: 14,
      loyalty: 12,
      pressure: 9,
      professionalism: 16,
      sportsmanship: 12,
      temperament: 16,
      controversy: 7,
    });
    expect(HA_PACK_KEYS.every((k) => values?.[k] != null)).toBe(true);
  });

  it("upsertHaSnapshot replaces same gameDate with newer extract", () => {
    const a: HaPackSnapshot = {
      gameDate: "2039-11-07",
      extractedAt: "2026-08-11T01:00:00.000Z",
      values: { professionalism: 16 },
    };
    const b: HaPackSnapshot = {
      gameDate: "2039-11-07",
      extractedAt: "2026-08-11T08:00:00.000Z",
      values: { professionalism: 15 },
    };
    const out = upsertHaSnapshot([a], b);
    expect(out).toHaveLength(1);
    expect(out[0]!.values.professionalism).toBe(15);
  });

  it("mergeHaHistoryFromRoster accumulates by club + gameDate", () => {
    const empty: HaHistoryStore = { careers: {} };
    const once = mergeHaHistoryFromRoster(empty, {
      clubId: 42,
      clubName: "Schalke",
      gameDate: "2039-11-07",
      extractedAt: "2026-08-11T01:00:00.000Z",
      saveName: "a.fm",
      players: [
        player(1, {
          adaptability: 6,
          ambition: 10,
          loyalty: 12,
          pressure: 14,
          professionalism: 16,
          sportsmanship: 11,
          temperament: 17,
          controversy: 8,
        }),
      ],
    });
    const twice = mergeHaHistoryFromRoster(once, {
      clubId: 42,
      clubName: "Schalke",
      gameDate: "2039-12-01",
      extractedAt: "2026-08-11T08:00:00.000Z",
      saveName: "b.fm",
      players: [
        player(1, {
          adaptability: 7,
          ambition: 10,
          loyalty: 12,
          pressure: 14,
          professionalism: 15,
          sportsmanship: 11,
          temperament: 16,
          controversy: 8,
        }),
      ],
    });
    const snaps = twice.careers["42"]!.players["1"]!;
    expect(snaps).toHaveLength(2);
    expect(snaps[0]!.gameDate).toBe("2039-11-07");
    expect(snaps[0]!.values.professionalism).toBe(16);
    expect(snaps[1]!.gameDate).toBe("2039-12-01");
    expect(snaps[1]!.values.professionalism).toBe(15);
  });

  it("keeps distinct gameDates even when pack values are identical", () => {
    const values = {
      adaptability: 6,
      ambition: 10,
      loyalty: 12,
      pressure: 14,
      professionalism: 16,
      sportsmanship: 11,
      temperament: 17,
      controversy: 8,
    };
    const empty: HaHistoryStore = { careers: {} };
    const once = mergeHaHistoryFromRoster(empty, {
      clubId: 42,
      clubName: "Schalke",
      gameDate: "2039-11-07",
      extractedAt: "2026-08-11T01:00:00.000Z",
      saveName: "a.fm",
      players: [player(1, values)],
    });
    const twice = mergeHaHistoryFromRoster(once, {
      clubId: 42,
      clubName: "Schalke",
      gameDate: "2039-11-19",
      extractedAt: "2026-08-11T12:00:00.000Z",
      saveName: "b.fm",
      players: [player(1, values)],
    });
    const snaps = twice.careers["42"]!.players["1"]!;
    expect(snaps).toHaveLength(2);
    expect(snaps.map((s) => s.gameDate)).toEqual([
      "2039-11-07",
      "2039-11-19",
    ]);
    expect(packSignature(snaps[0]!.values)).toBe(
      packSignature(snaps[1]!.values),
    );
  });
});
