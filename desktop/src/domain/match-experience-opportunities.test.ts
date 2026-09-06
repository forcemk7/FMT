import { describe, expect, it } from "vitest";
import type { LiveClubTeam, LiveFootballSnapshot, LivePlayer } from "./adapters";
import { rankMatchExperienceOpportunities } from "./match-experience-opportunities";

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

function snapshot(
  players: LivePlayer[],
  clubTeams: LiveClubTeam[],
): Pick<LiveFootballSnapshot, "players" | "clubTeams" | "managedClubId" | "clubs"> {
  return {
    players,
    clubTeams,
    managedClubId: "920",
    clubs: [
      { id: "920", name: "Schalke", nation: null, league: null },
      { id: "9001", name: "Feeder FC", nation: null, league: null },
    ],
  };
}

describe("rankMatchExperienceOpportunities", () => {
  const first = team({
    teamUid: "t-first",
    name: "First Team",
    clubName: "Schalke",
    squadUnit: "firstTeam",
    teamType: 0,
    rosterLen: 2,
    isManagerTeam: true,
    clubId: "920",
  });
  const u19 = team({
    teamUid: "t-u19",
    name: "U19",
    clubName: "Schalke",
    squadUnit: "under19s",
    teamType: 11,
    rosterLen: 2,
    clubId: "920",
  });
  const feeder = team({
    teamUid: "t-feed",
    name: "First Team",
    clubName: "Feeder FC",
    squadUnit: "firstTeam",
    affiliationType: 0x03,
    teamType: 0,
    rosterLen: 12,
    clubId: "9001",
  });

  it("flags Under N players who would be #1–2 on a First Team", () => {
    const youth = player({
      id: "youth",
      name: "Youth",
      positions: ["ST"],
      bestCalculatedPosition: "ST",
      currentAbility: 120,
      potentialAbility: 150,
      squadTeamUid: "t-u19",
      clubId: "920",
    });
    const seniorSt = player({
      id: "senior",
      name: "Senior ST",
      positions: ["ST"],
      currentAbility: 100,
      squadTeamUid: "t-first",
      clubId: "920",
    });
    const feederSt = player({
      id: "fs",
      name: "Feeder ST",
      positions: ["ST"],
      currentAbility: 80,
      squadTeamUid: "t-feed",
      clubId: "9001",
    });

    const rows = rankMatchExperienceOpportunities(
      snapshot([youth, seniorSt, feederSt], [first, u19, feeder]),
      8,
    );
    expect(rows).toHaveLength(1);
    expect(rows[0]!.player.id).toBe("youth");
    expect(rows[0]!.focusRank).toBe(1);
    expect(rows[0]!.toTeamLabel).toBe("First Team");
    expect(rows[0]!.toClubName).toBe("Schalke");
    expect(rows[0]!.fromTeamLabel).toBe("Under 19s");
    expect(rows[0]!.fromClubName).toBe("Schalke");
    expect(rows[0]!.fromClubId).toBe("920");
    expect(rows[0]!.toClubId).toBe("920");
  });

  it("skips First-team players and loaned-out players", () => {
    const senior = player({
      id: "senior",
      name: "Senior",
      positions: ["ST"],
      currentAbility: 140,
      squadTeamUid: "t-first",
      clubId: "920",
    });
    const mid = player({
      id: "mid",
      name: "Mid",
      positions: ["ST"],
      currentAbility: 130,
      squadTeamUid: "t-first",
      clubId: "920",
    });
    const loaned = player({
      id: "loan",
      name: "Loaned",
      positions: ["ST"],
      currentAbility: 135,
      squadTeamUid: "t-u19",
      clubId: "920",
      loanedOut: true,
      loanClubId: "9001",
    });
    const weakU19 = player({
      id: "weak",
      name: "Weak",
      positions: ["ST"],
      currentAbility: 70,
      squadTeamUid: "t-u19",
      clubId: "920",
    });
    const feederSt = player({
      id: "fs",
      name: "Feeder ST",
      positions: ["ST"],
      currentAbility: 150,
      squadTeamUid: "t-feed",
      clubId: "9001",
    });
    const feederSt2 = player({
      id: "fs2",
      name: "Feeder ST2",
      positions: ["ST"],
      currentAbility: 145,
      squadTeamUid: "t-feed",
      clubId: "9001",
    });

    const rows = rankMatchExperienceOpportunities(
      snapshot([senior, mid, loaned, weakU19, feederSt, feederSt2], [first, u19, feeder]),
      8,
    );
    expect(rows.map((row) => row.player.id)).toEqual([]);
  });
});
