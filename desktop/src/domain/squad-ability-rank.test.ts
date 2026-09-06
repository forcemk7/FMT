import { describe, expect, it } from "vitest";
import type { LivePlayer } from "./adapters";
import {
  dashClubTeamChrome,
  isOwnedManagedPlayer,
  rankBestPlayers,
  rankBestTalent,
} from "./squad-ability-rank";
import type { LiveClubTeam } from "./adapters";

function player(partial: Partial<LivePlayer> & { id: string; name: string }): LivePlayer {
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
    clubId: "920",
    transferInterest: null,
    loanInterest: null,
    transferAvailable: null,
    loanAvailable: null,
    ...partial,
  };
}

describe("isOwnedManagedPlayer", () => {
  it("includes loaned-out owned players", () => {
    expect(isOwnedManagedPlayer({ clubId: "920" }, "920")).toBe(true);
    expect(isOwnedManagedPlayer({ clubId: "912" }, "920")).toBe(false);
  });
});

describe("rankBestPlayers", () => {
  it("ranks by CA desc and keeps loaned-out", () => {
    const squad = [
      player({ id: "a", name: "A", currentAbility: 140, potentialAbility: 150 }),
      player({
        id: "loan",
        name: "Loan",
        currentAbility: 155,
        potentialAbility: 160,
        loanedOut: true,
      }),
      player({ id: "b", name: "B", currentAbility: 130, potentialAbility: 145 }),
      player({ id: "other", name: "Other", clubId: "1", currentAbility: 200 }),
    ];
    const ranked = rankBestPlayers(squad, "920", 3);
    expect(ranked.map((row) => row.player.id)).toEqual(["loan", "a", "b"]);
    expect(ranked[0]!.ca).toBe(155);
  });
});

describe("rankBestTalent", () => {
  it("ranks by PA desc for age ≤ 20, includes FT and loans", () => {
    const squad = [
      player({
        id: "ft-kid",
        name: "FT Kid",
        age: 18,
        currentAbility: 100,
        potentialAbility: 170,
        squadUnit: "firstTeam",
      }),
      player({
        id: "loan-kid",
        name: "Loan Kid",
        age: 19,
        currentAbility: 90,
        potentialAbility: 165,
        loanedOut: true,
        squadUnit: "under19s",
      }),
      player({
        id: "old",
        name: "Old High PA",
        age: 21,
        currentAbility: 120,
        potentialAbility: 180,
        squadUnit: "under19s",
      }),
      player({
        id: "u19",
        name: "U19",
        age: 17,
        currentAbility: 80,
        potentialAbility: 160,
        squadUnit: "under19s",
      }),
    ];
    const ranked = rankBestTalent(squad, "920", 5);
    expect(ranked.map((row) => row.player.id)).toEqual(["ft-kid", "loan-kid", "u19"]);
    expect(ranked[0]!.pa).toBe(170);
  });
});

describe("dashClubTeamChrome", () => {
  const teams: LiveClubTeam[] = [
    {
      teamUid: "t-u19",
      name: "U19",
      clubName: "Schalke",
      clubId: "920",
      squadUnit: "under19s",
      teamType: 11,
      rosterLen: 2,
      isManagerTeam: false,
    },
    {
      teamUid: "t-legia",
      name: "First Team",
      clubName: "Legia",
      clubId: "9001",
      squadUnit: "firstTeam",
      teamType: 0,
      rosterLen: 20,
      isManagerTeam: false,
      affiliationType: 0x03,
    },
  ];

  it("returns clubId + teamType for managed clubTeam", () => {
    const kid = player({
      id: "1",
      name: "Kid",
      squadTeamUid: "t-u19",
      clubId: "920",
    });
    expect(dashClubTeamChrome(kid, teams, [{ id: "920", name: "Schalke" }])).toEqual({
      clubId: "920",
      clubName: "Schalke",
      teamType: "Under 19s",
    });
  });

  it("returns loan destination First Team chrome", () => {
    const loan = player({
      id: "2",
      name: "Loan",
      squadTeamUid: "t-u19",
      clubId: "920",
      loanedOut: true,
      loanClubId: "9001",
      loanClubName: "Legia",
    });
    expect(dashClubTeamChrome(loan, teams)).toEqual({
      clubId: "9001",
      clubName: "Legia",
      teamType: "First Team",
    });
  });
});
