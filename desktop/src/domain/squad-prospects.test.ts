import { describe, expect, it } from "vitest";
import type { LivePlayer } from "./adapters";
import {
  median,
  rankSquadProspects,
  squadMedianCa,
  youngProspectCandidates,
} from "./squad-prospects";

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
    clubId: "1",
    transferInterest: null,
    loanInterest: null,
    transferAvailable: null,
    loanAvailable: null,
    ...partial,
  };
}

describe("median", () => {
  it("handles odd and even lengths", () => {
    expect(median([3, 1, 2])).toBe(2);
    expect(median([4, 1, 2, 3])).toBe(2.5);
    expect(median([])).toBeNull();
  });
});

describe("youngProspectCandidates", () => {
  it("prefers age ≤ 21 when the pool is large enough", () => {
    const squad = [
      player({ id: "1", name: "A", age: 18 }),
      player({ id: "2", name: "B", age: 20 }),
      player({ id: "3", name: "C", age: 21 }),
      player({ id: "4", name: "D", age: 24 }),
    ];
    expect(youngProspectCandidates(squad).map((p) => p.id)).toEqual(["1", "2", "3"]);
  });

  it("falls back to youngest third capped at 23 when ≤21 pool is thin", () => {
    const squad = [
      player({ id: "1", name: "A", age: 19 }),
      player({ id: "2", name: "B", age: 22 }),
      player({ id: "3", name: "C", age: 23 }),
      player({ id: "4", name: "D", age: 28 }),
      player({ id: "5", name: "E", age: 30 }),
      player({ id: "6", name: "F", age: 32 }),
    ];
    const ids = youngProspectCandidates(squad).map((p) => p.id);
    expect(ids).toContain("1");
    expect(ids).toContain("2");
    expect(ids).not.toContain("4");
  });
});

describe("rankSquadProspects", () => {
  it("keeps young high-PA players with a Pro mentor gap ≥ 2", () => {
    const squad = [
      player({
        id: "kid",
        name: "Kid",
        age: 18,
        currentAbility: 90,
        potentialAbility: 150,
        squadUnit: "under19s",
        personalityAttributes: { Professionalism: 10 },
      }),
      player({
        id: "mentor",
        name: "Mentor",
        age: 30,
        currentAbility: 140,
        potentialAbility: 145,
        squadUnit: "firstTeam",
        personalityAttributes: { Professionalism: 15 },
      }),
      player({
        id: "peer",
        name: "Peer",
        age: 27,
        currentAbility: 130,
        potentialAbility: 135,
        squadUnit: "firstTeam",
        personalityAttributes: { Professionalism: 11 },
      }),
      player({
        id: "ft-kid",
        name: "First Team Kid",
        age: 19,
        currentAbility: 95,
        potentialAbility: 155,
        squadUnit: "firstTeam",
        personalityAttributes: { Professionalism: 9 },
      }),
    ];
    expect(squadMedianCa(squad)).toBe(112.5);
    const ranked = rankSquadProspects(squad);
    expect(ranked).toHaveLength(1);
    expect(ranked[0]!.player.id).toBe("kid");
    expect(ranked[0]!.mentor.id).toBe("mentor");
    expect(ranked[0]!.proGap).toBe(5);
  });

  it("excludes First Team squadUnit even with mentor room", () => {
    const squad = [
      player({
        id: "ft",
        name: "FT Prospect",
        age: 18,
        currentAbility: 90,
        potentialAbility: 160,
        squadUnit: "firstTeam",
        personalityAttributes: { Professionalism: 10 },
      }),
      player({
        id: "mentor",
        name: "Mentor",
        age: 30,
        currentAbility: 140,
        potentialAbility: 145,
        squadUnit: "firstTeam",
        personalityAttributes: { Professionalism: 18 },
      }),
    ];
    expect(rankSquadProspects(squad)).toEqual([]);
  });

  it("drops players without Pro room or below median CA PA", () => {
    const squad = [
      player({
        id: "low-pa",
        name: "Low",
        age: 18,
        currentAbility: 80,
        potentialAbility: 99,
        personalityAttributes: { Professionalism: 8 },
      }),
      player({
        id: "no-mentor",
        name: "Alone",
        age: 19,
        currentAbility: 100,
        potentialAbility: 160,
        personalityAttributes: { Professionalism: 18 },
      }),
      player({
        id: "vet",
        name: "Vet",
        age: 32,
        currentAbility: 150,
        potentialAbility: 155,
        personalityAttributes: { Professionalism: 17 },
      }),
    ];
    expect(rankSquadProspects(squad)).toEqual([]);
  });
});
