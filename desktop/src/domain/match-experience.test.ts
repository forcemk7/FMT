import { describe, expect, it } from "vitest";
import type { LiveClubTeam, LivePlayer } from "./adapters";
import {
  buildMatchExperienceCards,
  matchExperiencePosition,
  matchExperienceTeamBand,
  matchExperienceWindowStart,
  sortClubTeamsForMatchExperience,
} from "./match-experience";

function player(
  partial: Partial<LivePlayer> & Pick<LivePlayer, "id" | "name">,
): LivePlayer {
  return {
    age: null,
    nationality: null,
    positions: [],
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
    roleFit: null,
    strengths: [],
    weaknesses: [],
    clubId: null,
    transferInterest: null,
    loanInterest: null,
    transferAvailable: null,
    loanAvailable: null,
    ...partial,
  };
}

function team(
  partial: Partial<LiveClubTeam> & Pick<LiveClubTeam, "teamUid" | "name" | "squadUnit">,
): LiveClubTeam {
  return {
    rosterLen: 0,
    isManagerTeam: false,
    ...partial,
  };
}

describe("matchExperiencePosition", () => {
  it("prefers bestCalculatedPosition over primary list", () => {
    expect(
      matchExperiencePosition(
        player({
          id: "1",
          name: "A",
          bestCalculatedPosition: "AMC",
          positions: ["ST", "AMC"],
        }),
      ),
    ).toBe("AMC");
  });

  it("falls back to first primary", () => {
    expect(
      matchExperiencePosition(
        player({ id: "1", name: "A", positions: ["DR", "MR"] }),
      ),
    ).toBe("DR");
  });
});

describe("sortClubTeamsForMatchExperience", () => {
  it("orders Senior → Under N → 2nd/II → Aff Senior → Aff Under N", () => {
    const sorted = sortClubTeamsForMatchExperience([
      team({
        teamUid: "aff-u",
        name: "Feeder U19",
        squadUnit: "under19s",
        affiliationType: 0x01,
        rosterLen: 10,
      }),
      team({
        teamUid: "aff-1",
        name: "Feeder",
        squadUnit: "firstTeam",
        affiliationType: 0x01,
        teamType: 0,
        rosterLen: 20,
      }),
      team({
        teamUid: "ii",
        name: "II",
        squadUnit: "reserves",
        affiliationType: 0x08,
        rosterLen: 21,
      }),
      team({
        teamUid: "u19",
        name: "U19",
        squadUnit: "under19s",
        teamType: 11,
        rosterLen: 22,
      }),
      team({
        teamUid: "ft",
        name: "First",
        squadUnit: "firstTeam",
        teamType: 0,
        rosterLen: 28,
        isManagerTeam: true,
      }),
    ]);
    expect(sorted.map((item) => item.teamUid)).toEqual([
      "ft",
      "u19",
      "ii",
      "aff-1",
      "aff-u",
    ]);
    expect(matchExperienceTeamBand(sorted[2]!)).toBe(2);
    expect(matchExperienceTeamBand(sorted[3]!)).toBe(3);
  });
});

describe("buildMatchExperienceCards", () => {
  const first = team({
    teamUid: "t-first",
    name: "First Team",
    squadUnit: "firstTeam",
    teamType: 0,
    rosterLen: 2,
    isManagerTeam: true,
  });
  const u19 = team({
    teamUid: "t-u19",
    name: "U19",
    squadUnit: "under19s",
    teamType: 2,
    rosterLen: 2,
  });

  const youth = player({
    id: "youth",
    name: "Youth",
    positions: ["ST", "MC"],
    bestCalculatedPosition: "ST",
    currentAbility: 110,
    squadTeamUid: "t-u19",
  });
  const seniorSt = player({
    id: "senior",
    name: "Senior ST",
    positions: ["ST"],
    currentAbility: 140,
    squadTeamUid: "t-first",
  });
  const otherSt = player({
    id: "other",
    name: "Other ST",
    positions: ["ST"],
    currentAbility: 100,
    squadTeamUid: "t-u19",
  });
  const mid = player({
    id: "mid",
    name: "Mid",
    positions: ["MC"],
    currentAbility: 150,
    squadTeamUid: "t-first",
  });

  it("builds per-team same-primary CA ranks and injects focus off-roster", () => {
    const cards = buildMatchExperienceCards(
      youth,
      [youth, seniorSt, otherSt, mid],
      [u19, first],
    );
    expect(cards.map((card) => card.teamUid)).toEqual(["t-first", "t-u19"]);

    const firstCard = cards[0]!;
    expect(firstCard.position).toBe("ST");
    expect(firstCard.rows.map((row) => row.playerId)).toEqual(["senior", "youth"]);
    expect(firstCard.focusRank).toBe(2);
    expect(firstCard.rows[1]).toMatchObject({
      isFocus: true,
      isOnRoster: false,
    });

    const u19Card = cards[1]!;
    expect(u19Card.rows.map((row) => row.playerId)).toEqual(["youth", "other"]);
    expect(u19Card.focusRank).toBe(1);
  });

  it("hides teams with no same-pos roster peers", () => {
    const emptySide = team({
      teamUid: "t-empty",
      name: "Empty",
      squadUnit: "reserves",
      rosterLen: 5,
    });
    const cards = buildMatchExperienceCards(
      youth,
      [youth, seniorSt, otherSt],
      [first, u19, emptySide],
    );
    expect(cards.map((card) => card.teamUid)).toEqual(["t-first", "t-u19"]);
  });

  it("allows per-team position overrides", () => {
    const cards = buildMatchExperienceCards(
      youth,
      [youth, seniorSt, otherSt, mid],
      [first, u19],
      null,
      { "t-first": "MC", "t-u19": "ST" },
    );
    expect(cards.find((card) => card.teamUid === "t-first")?.position).toBe("MC");
    expect(cards.find((card) => card.teamUid === "t-first")?.rows.map((r) => r.playerId)).toEqual([
      "mid",
      "youth",
    ]);
    expect(cards.find((card) => card.teamUid === "t-u19")?.position).toBe("ST");
  });

  it("returns empty when focus has no position", () => {
    expect(
      buildMatchExperienceCards(
        player({ id: "x", name: "X", positions: [] }),
        [],
        [first],
      ),
    ).toEqual([]);
  });
});

describe("matchExperienceWindowStart", () => {
  it("keeps start at 0 when list fits the page", () => {
    expect(matchExperienceWindowStart(4, 3, 5)).toBe(0);
  });

  it("centers focus when possible", () => {
    expect(matchExperienceWindowStart(10, 8, 5)).toBe(5);
  });
});
