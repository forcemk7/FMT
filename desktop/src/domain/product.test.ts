import { describe, expect, it } from "vitest";
import { groupPlayerPosition, formatPlayerPositions, playerPositionParts, resolveFavorites, toggleFavorite, updateFavoriteNote } from "./live-data";
import type { LivePlayer } from "./adapters";

const livePlayer: LivePlayer = {
  id: "1",
  name: "Player One",
  age: 21,
  nationality: "France",
  positions: ["CB"],
  bestRole: null,
  currentAbility: null,
  potentialAbility: null,
  form: null,
  averageRating: null,
  minutesPlayed: null,
  goals: null,
  assists: null,
  contractStatus: null,
  value: null,
  wage: null,
  squadImportance: null,
  developmentTrend: null,
  tacticalFit: null,
  roleFit: 78,
  transferInterest: "Somewhat interested",
  loanInterest: "Unknown",
  transferAvailable: true,
  loanAvailable: false,
  strengths: [],
  weaknesses: [],
  clubId: "club-1",
};

describe("live squad grouping", () => {
  it("groups extracted players by their live position data", () => {
    expect(groupPlayerPosition(livePlayer)).toBe("Centre-backs");
    expect(groupPlayerPosition({ ...livePlayer, positions: ["DM", "CM"] })).toBe("Defensive midfielders");
  });

  it("groups by best position only, ignoring secondaries", () => {
    expect(
      groupPlayerPosition({
        ...livePlayer,
        positions: ["ST"],
        secondaryPositions: ["AMC", "MC"],
      }),
    ).toBe("Strikers");
  });
});

describe("player position labels", () => {
  it("formats best slots with secondaries in parentheses", () => {
    expect(
      formatPlayerPositions({
        positions: ["DC"],
        secondaryPositions: ["DM", "MC"],
      }),
    ).toBe("DC (DM / MC)");
    expect(formatPlayerPositions({ positions: ["DL", "DR"], secondaryPositions: ["MC"] })).toBe(
      "DL / DR (MC)",
    );
    expect(formatPlayerPositions({ positions: ["GK"], secondaryPositions: [] })).toBe("GK");
    expect(formatPlayerPositions({ positions: [], secondaryPositions: ["MC"] })).toBe("—");
  });

  it("splits primary and secondary for stacked facts display", () => {
    expect(
      playerPositionParts({
        positions: ["DR", "WBR"],
        secondaryPositions: ["DC", "MC"],
      }),
    ).toEqual({ primary: "DR / WBR", secondary: "DC / MC" });
    expect(playerPositionParts({ positions: ["GK"], secondaryPositions: [] })).toEqual({
      primary: "GK",
      secondary: null,
    });
    expect(playerPositionParts({ positions: [], secondaryPositions: ["MC"] })).toEqual({
      primary: "—",
      secondary: null,
    });
  });
});

describe("favorites", () => {
  it("adds, annotates and removes a live player reference", () => {
    const added = toggleFavorite([], livePlayer.id);
    expect(added).toEqual([{ playerId: "1", note: "" }]);
    const noted = updateFavoriteNote(added, livePlayer.id, "Watch role fit");
    expect(resolveFavorites(noted, [livePlayer])).toEqual([{ player: livePlayer, note: "Watch role fit" }]);
    expect(toggleFavorite(noted, livePlayer.id)).toEqual([]);
  });

  it("does not preserve stale player payloads when a live entity disappears", () => {
    expect(resolveFavorites([{ playerId: "missing", note: "Old target" }], [livePlayer])).toEqual([]);
  });
});
