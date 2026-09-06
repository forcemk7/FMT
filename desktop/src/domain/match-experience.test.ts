import { describe, expect, it } from "vitest";
import type { LiveClubTeam, LivePlayer } from "./adapters";
import {
  buildMatchExperienceCards,
  matchExperiencePlayerCompetesOnTeam,
  matchExperiencePosition,
  matchExperiencePositionOptions,
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
});

describe("matchExperiencePositionOptions", () => {
  it("unions best, primary, and secondary", () => {
    expect(
      matchExperiencePositionOptions(
        player({
          id: "1",
          name: "A",
          bestCalculatedPosition: "ST",
          positions: ["ST"],
          secondaryPositions: ["AMC", "MC"],
        }),
      ),
    ).toEqual(["ST", "AMC", "MC"]);
  });
});

describe("sortClubTeamsForMatchExperience", () => {
  it("orders First → Res/II → Under N → Normal First → Normal Under N", () => {
    const sorted = sortClubTeamsForMatchExperience([
      team({
        teamUid: "aff-1",
        name: "Feeder",
        squadUnit: "firstTeam",
        affiliationType: 0x03,
        teamType: 0,
        rosterLen: 20,
      }),
      team({
        teamUid: "aff-u",
        name: "Feeder U19",
        squadUnit: "under19s",
        affiliationType: 0x03,
        teamType: 11,
        rosterLen: 10,
      }),
      team({
        teamUid: "u18",
        name: "U18",
        squadUnit: "under19s",
        teamType: 12,
        rosterLen: 18,
      }),
      team({
        teamUid: "u19",
        name: "U19",
        squadUnit: "under19s",
        teamType: 11,
        rosterLen: 22,
      }),
      team({
        teamUid: "ii",
        name: "II",
        squadUnit: "reserves",
        affiliationType: 0x08,
        rosterLen: 21,
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
      "ii",
      "u19",
      "u18",
      "aff-1",
      "aff-u",
    ]);
    expect(matchExperienceTeamBand(sorted[1]!)).toBe(1);
    expect(matchExperienceTeamBand(sorted[2]!)).toBe(2);
    expect(matchExperienceTeamBand(sorted[4]!)).toBe(3);
  });
});

describe("matchExperiencePlayerCompetesOnTeam", () => {
  it("excludes loaned-out from parent team and includes loan club", () => {
    const loaned = player({
      id: "y",
      name: "Youth",
      squadTeamUid: "t-u19",
      loanedOut: true,
      loanClubId: "9001",
    });
    expect(matchExperiencePlayerCompetesOnTeam(loaned, "t-u19", "920")).toBe(false);
    expect(matchExperiencePlayerCompetesOnTeam(loaned, "t-feed", "9001")).toBe(true);
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
    teamType: 11,
    rosterLen: 2,
  });
  const feeder = team({
    teamUid: "t-feed",
    name: "Feeder",
    squadUnit: "firstTeam",
    affiliationType: 0x03,
    teamType: 0,
    rosterLen: 12,
  });

  const youth = player({
    id: "youth",
    name: "Youth",
    positions: ["ST"],
    bestCalculatedPosition: "ST",
    currentAbility: 110,
    squadTeamUid: "t-u19",
    clubId: "920",
  });
  const seniorSt = player({
    id: "senior",
    name: "Senior ST",
    positions: ["ST"],
    currentAbility: 140,
    squadTeamUid: "t-first",
    clubId: "920",
  });
  const otherSt = player({
    id: "other",
    name: "Other ST",
    positions: ["ST"],
    currentAbility: 100,
    squadTeamUid: "t-u19",
    clubId: "920",
  });
  const loanedSt = player({
    id: "loan",
    name: "Loaned ST",
    positions: ["ST"],
    currentAbility: 105,
    squadTeamUid: "t-u19",
    clubId: "920",
    loanedOut: true,
    loanClubId: "9001",
  });
  const feederSt = player({
    id: "fs",
    name: "Feeder ST",
    positions: ["ST"],
    currentAbility: 95,
    squadTeamUid: "t-feed",
    clubId: "9001",
  });

  it("orders First before Under N and omits loaned-out from parent card", () => {
    const cards = buildMatchExperienceCards(
      youth,
      [youth, seniorSt, otherSt, loanedSt, feederSt],
      [u19, first, feeder],
    );
    expect(cards.map((card) => card.teamUid)).toEqual(["t-first", "t-u19", "t-feed"]);
    expect(cards[1]!.rows.map((row) => row.playerId)).toEqual(["youth", "other"]);
    expect(cards[1]!.rows.some((row) => row.playerId === "loan")).toBe(false);
  });

  it("places loaned focus on affiliate card as current", () => {
    const loanedYouth = player({
      id: "youth",
      name: "Youth",
      positions: ["ST"],
      currentAbility: 110,
      squadTeamUid: "t-u19",
      clubId: "920",
      loanedOut: true,
      loanClubId: "9001",
    });
    const cards = buildMatchExperienceCards(
      loanedYouth,
      [loanedYouth, otherSt, feederSt],
      [u19, feeder],
    );
    const u19Card = cards.find((card) => card.teamUid === "t-u19")!;
    expect(u19Card.rows.map((row) => row.playerId)).toEqual(["youth", "other"]);
    expect(u19Card.rows.find((row) => row.isFocus)?.isOnRoster).toBe(false);

    const feedCard = cards.find((card) => card.teamUid === "t-feed")!;
    expect(feedCard.rows.find((row) => row.isFocus)?.isOnRoster).toBe(true);
  });

  it("hides teams with zero resolved players", () => {
    const empty = team({
      teamUid: "t-empty",
      name: "Empty",
      squadUnit: "reserves",
      rosterLen: 9,
    });
    const cards = buildMatchExperienceCards(youth, [youth, seniorSt], [first, empty, u19]);
    expect(cards.map((card) => card.teamUid)).toEqual(["t-first", "t-u19"]);
    expect(cards.some((card) => card.teamUid === "t-empty")).toBe(false);
  });

  it("windows long lists around focus", () => {
    const many = Array.from({ length: 8 }, (_, index) =>
      player({
        id: `s${index}`,
        name: `Senior ${index}`,
        positions: ["ST"],
        currentAbility: 160 - index,
        squadTeamUid: "t-first",
        clubId: "920",
      }),
    );
    const cards = buildMatchExperienceCards(youth, [youth, ...many], [first]);
    expect(cards[0]!.totalRows).toBe(9);
    expect(cards[0]!.rows).toHaveLength(5);
    expect(cards[0]!.rows.some((row) => row.isFocus)).toBe(true);
  });
});

describe("matchExperienceWindowStart", () => {
  it("centers focus when possible", () => {
    expect(matchExperienceWindowStart(10, 8, 5)).toBe(5);
  });
});
