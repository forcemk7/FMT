import { describe, expect, it } from "vitest";
import {
  normalizeRosterPlayer,
  rosterHasPersonalityData,
  rosterPersonalitySignals,
  type RosterPlayer,
} from "../web/roster-data.ts";

function player(partial: Partial<RosterPlayer> & Pick<RosterPlayer, "uid" | "name">): RosterPlayer {
  return {
    jobId: 1,
    dateOfBirth: null,
    nation: null,
    secondNation: null,
    positions: null,
    dynamics: { captaincy: null, hierarchy: null, socialGroup: null },
    training: { unit: null },
    attributes: null,
    attributeHistory: null,
    ...partial,
  };
}

describe("rosterPersonalitySignals", () => {
  it("prefers attributeHistory tip Det/Lea over divergent live attributes", () => {
    const signals = rosterPersonalitySignals(
      player({
        uid: 2002282661,
        name: "Jordan Dobler",
        attributes: {
          mental: { determination: 20, leadership: 2 },
          general: { ambition: 14, pressure: 12 },
        },
        attributeHistory: [
          {
            index: 0,
            mental: { determination: 14, leadership: 6, composure: 13 },
            technical: { penaltyTaking: 11 },
          },
        ],
      }),
    );
    expect(signals?.determination).toBe(14);
    expect(signals?.leadership).toBe(6);
    expect(signals?.ambition).toBe(14);
    expect(signals?.pressure).toBe(12);
  });

  it("falls back to live Det when history tip has no mental", () => {
    const signals = rosterPersonalitySignals(
      player({
        uid: 1,
        name: "Solo",
        attributes: {
          mental: { determination: 15, leadership: 10 },
          general: { professionalism: 14 },
        },
        attributeHistory: [{ index: 0, technical: { penaltyTaking: 8 } }],
      }),
    );
    expect(signals?.determination).toBe(15);
    expect(signals?.leadership).toBe(10);
  });

  it("lifts slim subunit determination/leadership into mental", () => {
    const normalized = normalizeRosterPlayer({
      uid: 42,
      name: "Reserve Kid",
      jobId: 1,
      kind: "UNKNOWN",
      source: "save",
      determination: 12,
      leadership: 8,
      attributes: null,
      attributeHistory: null,
      dateOfBirth: null,
      nation: null,
      secondNation: null,
      positions: null,
      dynamics: { captaincy: null, hierarchy: null, socialGroup: null },
      training: { unit: null },
    });
    expect(normalized.attributes?.mental?.determination).toBe(12);
    expect(normalized.attributes?.mental?.leadership).toBe(8);
    expect(rosterHasPersonalityData(normalized)).toBe(true);
  });
});
