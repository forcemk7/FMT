import { describe, expect, it } from "vitest";
import type { LiveClubTeam, LivePlayer } from "./adapters";
import {
  buildMatchExperienceCards,
  matchExperiencePosition,
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
    positions: ["ST"],
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
    expect(u19Card.rows[0]).toMatchObject({
      isFocus: true,
      isOnRoster: true,
    });
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
