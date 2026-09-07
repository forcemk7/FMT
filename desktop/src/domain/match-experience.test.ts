import { describe, expect, it } from "vitest";
import type { LiveClubTeam, LivePlayer } from "./adapters";
import {
  buildMatchExperienceCards,
  matchExperiencePlayerCompetesOnTeam,
  matchExperiencePosition,
  matchExperiencePositionOptions,
  matchExperienceTeamBand,
  matchExperienceTeamLabel,
  matchExperienceWindowStart,
  pickBestMatchExperienceCard,
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
  it("orders all First Teams before Under Ns, then by club name", () => {
    const sorted = sortClubTeamsForMatchExperience([
      team({
        teamUid: "aff-u",
        name: "Feeder U19",
        clubName: "Feeder",
        squadUnit: "under19s",
        affiliationType: 0x03,
        teamType: 11,
        rosterLen: 10,
      }),
      team({
        teamUid: "aff-1",
        name: "Feeder",
        clubName: "Feeder",
        squadUnit: "firstTeam",
        affiliationType: 0x03,
        teamType: 0,
        rosterLen: 20,
      }),
      team({
        teamUid: "u18",
        name: "U18",
        clubName: "Schalke",
        squadUnit: "under19s",
        teamType: 12,
        rosterLen: 18,
      }),
      team({
        teamUid: "u19",
        name: "U19",
        clubName: "Schalke",
        squadUnit: "under19s",
        teamType: 11,
        rosterLen: 22,
      }),
      team({
        teamUid: "ii",
        name: "First Team",
        clubName: "FC Schalke 04 II",
        squadUnit: "reserves",
        affiliationType: 0x08,
        teamType: 0,
        rosterLen: 21,
      }),
      team({
        teamUid: "ft",
        name: "First Team",
        clubName: "FC Schalke 04",
        squadUnit: "firstTeam",
        teamType: 0,
        rosterLen: 28,
        isManagerTeam: true,
      }),
    ]);
    expect(sorted.map((item) => item.teamUid)).toEqual([
      "ft",
      "ii",
      "aff-1",
      "aff-u",
      "u19",
      "u18",
    ]);
  });
});

describe("matchExperienceTeamLabel", () => {
  it("uses TeamType only (crest carries club identity)", () => {
    expect(
      matchExperienceTeamLabel({
        squadUnit: "firstTeam",
        teamType: 0,
      }),
    ).toBe("First Team");
    expect(
      matchExperienceTeamLabel({
        squadUnit: "under19s",
        teamType: 11,
      }),
    ).toBe("Under 19s");
  });
});

describe("matchExperiencePlayerCompetesOnTeam", () => {
  it("excludes loaned-out from parent and non-First loan teams; includes loan First", () => {
    const loaned = player({
      id: "y",
      name: "Youth",
      squadTeamUid: "t-u19",
      loanedOut: true,
      loanClubId: "9001",
    });
    expect(matchExperiencePlayerCompetesOnTeam(loaned, "t-u19", "920", 2)).toBe(false);
    expect(matchExperiencePlayerCompetesOnTeam(loaned, "t-feed", "9001", 0)).toBe(true);
    expect(matchExperiencePlayerCompetesOnTeam(loaned, "t-legia-u19", "9001", 2)).toBe(
      false,
    );
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
    clubId: "9001",
    clubName: "Feeder FC",
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
      "920",
      undefined,
      undefined,
      [
        { id: "920", name: "Schalke" },
        { id: "9001", name: "Feeder FC" },
      ],
    );
    expect(cards.map((card) => card.teamUid)).toEqual(["t-first", "t-feed", "t-u19"]);
    const firstCard = cards.find((card) => card.teamUid === "t-first")!;
    const feedCard = cards.find((card) => card.teamUid === "t-feed")!;
    const u19Card = cards.find((card) => card.teamUid === "t-u19")!;
    expect(firstCard.teamLabel).toBe("First Team");
    expect(firstCard.clubId).toBe("920");
    expect(firstCard.clubName).toBe("Schalke");
    expect(firstCard.maxSamePosCa).toBe(140);
    expect(firstCard.isFocusCurrentTeam).toBe(false);
    expect(feedCard.teamLabel).toBe("First Team");
    expect(feedCard.clubId).toBe("9001");
    expect(feedCard.clubName).toBe("Feeder FC");
    expect(feedCard.maxSamePosCa).toBe(105);
    expect(feedCard.rows.some((row) => row.playerId === "loan")).toBe(true);
    expect(u19Card.rows.map((row) => row.playerId)).toEqual(["youth", "other"]);
    expect(u19Card.rows.some((row) => row.playerId === "loan")).toBe(false);
    expect(u19Card.isFocusCurrentTeam).toBe(true);
  });

  it("counts loaned-out same-pos CA on destination First Team ranks", () => {
    const florin = player({
      id: "florin",
      name: "Florin",
      positions: ["GK"],
      bestCalculatedPosition: "GK",
      currentAbility: 100,
      squadTeamUid: "t-u19",
      clubId: "920",
    });
    const joao = player({
      id: "joao",
      name: "Joao",
      positions: ["GK"],
      bestCalculatedPosition: "GK",
      currentAbility: 140,
      squadTeamUid: "t-u19",
      clubId: "920",
      loanedOut: true,
      loanClubId: "9001",
    });
    const weakGk = player({
      id: "weak",
      name: "Weak GK",
      positions: ["GK"],
      currentAbility: 80,
      squadTeamUid: "t-feed",
      clubId: "9001",
    });
    const cards = buildMatchExperienceCards(
      florin,
      [florin, joao, weakGk],
      [u19, feeder],
      "920",
      undefined,
      "GK",
      [
        { id: "920", name: "Schalke" },
        { id: "9001", name: "Feeder FC" },
      ],
    );
    const feedCard = cards.find((card) => card.teamUid === "t-feed")!;
    expect(feedCard.maxSamePosCa).toBe(140);
    expect(feedCard.focusRank).toBe(2);
    expect(feedCard.rows.map((row) => row.playerId)).toEqual(["joao", "florin", "weak"]);
  });

  it("prefers clubTeam owner club over player clubId for II", () => {
    const ii = team({
      teamUid: "t-ii",
      name: "First Team",
      squadUnit: "reserves",
      affiliationType: 0x08,
      teamType: 0,
      rosterLen: 20,
      clubId: "921",
      clubName: "FC Schalke 04 II",
    });
    const iiPlayer = player({
      id: "ii1",
      name: "II DC",
      positions: ["ST"],
      currentAbility: 100,
      squadTeamUid: "t-ii",
      clubId: "920", // managed stamp — Squad structure
    });
    const cards = buildMatchExperienceCards(
      youth,
      [youth, iiPlayer],
      [ii],
      "920",
      undefined,
      undefined,
      [{ id: "920", name: "FC Schalke 04" }],
    );
    expect(cards).toHaveLength(1);
    expect(cards[0]!.clubId).toBe("921");
    expect(cards[0]!.clubName).toBe("FC Schalke 04 II");
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
    expect(feedCard.isFocusCurrentTeam).toBe(true);
    expect(u19Card.isFocusCurrentTeam).toBe(false);
  });

  it("within First band sorts stronger same-pos max CA left", () => {
    const weakFirst = team({
      teamUid: "t-weak",
      name: "Weak First",
      clubName: "AAA Weak",
      squadUnit: "firstTeam",
      teamType: 0,
      rosterLen: 10,
      clubId: "1",
    });
    const strongFirst = team({
      teamUid: "t-strong",
      name: "Strong First",
      clubName: "ZZZ Strong",
      squadUnit: "firstTeam",
      teamType: 0,
      rosterLen: 10,
      clubId: "2",
    });
    const weakSt = player({
      id: "w",
      name: "Weak ST",
      positions: ["ST"],
      currentAbility: 90,
      squadTeamUid: "t-weak",
      clubId: "1",
    });
    const strongSt = player({
      id: "s",
      name: "Strong ST",
      positions: ["ST"],
      currentAbility: 150,
      squadTeamUid: "t-strong",
      clubId: "2",
    });
    const cards = buildMatchExperienceCards(
      youth,
      [youth, weakSt, strongSt],
      [weakFirst, strongFirst],
    );
    expect(cards.map((card) => card.teamUid)).toEqual(["t-strong", "t-weak"]);
    expect(cards[0]!.maxSamePosCa).toBe(150);
    expect(cards[1]!.maxSamePosCa).toBe(90);
  });

  it("elite focus CA does not flatten First card order", () => {
    const weakFirst = team({
      teamUid: "t-weak",
      name: "Weak First",
      clubName: "AAA Weak",
      squadUnit: "firstTeam",
      teamType: 0,
      rosterLen: 10,
      clubId: "1",
    });
    const strongFirst = team({
      teamUid: "t-strong",
      name: "Strong First",
      clubName: "ZZZ Strong",
      squadUnit: "firstTeam",
      teamType: 0,
      rosterLen: 10,
      clubId: "2",
    });
    const weakGk = player({
      id: "w",
      name: "Weak GK",
      positions: ["GK"],
      currentAbility: 90,
      squadTeamUid: "t-weak",
      clubId: "1",
    });
    const strongGk = player({
      id: "s",
      name: "Strong GK",
      positions: ["GK"],
      currentAbility: 150,
      squadTeamUid: "t-strong",
      clubId: "2",
    });
    const elite = player({
      id: "elite",
      name: "Elite GK",
      positions: ["GK"],
      currentAbility: 180,
      squadTeamUid: "t-strong",
      clubId: "2",
    });
    const cards = buildMatchExperienceCards(
      elite,
      [elite, weakGk, strongGk],
      [weakFirst, strongFirst],
    );
    expect(cards.map((card) => card.teamUid)).toEqual(["t-strong", "t-weak"]);
    expect(cards[0]!.maxSamePosCa).toBe(150);
    expect(cards[1]!.maxSamePosCa).toBe(90);
  });

  it("pickBest keeps Current when already top-2 with no better move", () => {
    const homeFirst = team({
      teamUid: "t-home",
      name: "Home First",
      clubName: "Home",
      squadUnit: "firstTeam",
      teamType: 0,
      rosterLen: 10,
      clubId: "home",
    });
    const otherFirst = team({
      teamUid: "t-other",
      name: "Other First",
      clubName: "Other",
      squadUnit: "firstTeam",
      teamType: 0,
      rosterLen: 10,
      clubId: "other",
    });
    const focus = player({
      id: "f",
      name: "Focus",
      positions: ["ST"],
      currentAbility: 120,
      squadTeamUid: "t-home",
      clubId: "home",
    });
    const homeMate = player({
      id: "hm",
      name: "Home Mate",
      positions: ["ST"],
      currentAbility: 100,
      squadTeamUid: "t-home",
      clubId: "home",
    });
    const otherMate = player({
      id: "om",
      name: "Other Mate",
      positions: ["ST"],
      currentAbility: 50,
      squadTeamUid: "t-other",
      clubId: "other",
    });
    const cards = buildMatchExperienceCards(
      focus,
      [focus, homeMate, otherMate],
      [homeFirst, otherFirst],
      "home",
    );
    const best = pickBestMatchExperienceCard(cards, "home");
    expect(best?.teamUid).toBe("t-home");
    expect(best?.focusRank).toBe(1);
  });

  it("pickBest moves youth up when First projects top-2", () => {
    const u19Team = team({
      teamUid: "t-u19",
      name: "U19",
      clubName: "Home",
      squadUnit: "under19s",
      teamType: 11,
      rosterLen: 10,
      clubId: "home",
    });
    const firstTeam = team({
      teamUid: "t-first",
      name: "First",
      clubName: "Home",
      squadUnit: "firstTeam",
      teamType: 0,
      rosterLen: 10,
      clubId: "home",
    });
    const focus = player({
      id: "y",
      name: "Youth",
      positions: ["ST"],
      currentAbility: 130,
      squadTeamUid: "t-u19",
      clubId: "home",
    });
    const u19Mate = player({
      id: "um",
      name: "U19 Mate",
      positions: ["ST"],
      currentAbility: 100,
      squadTeamUid: "t-u19",
      clubId: "home",
    });
    const firstMate = player({
      id: "fm",
      name: "First Mate",
      positions: ["ST"],
      currentAbility: 125,
      squadTeamUid: "t-first",
      clubId: "home",
    });
    const cards = buildMatchExperienceCards(
      focus,
      [focus, u19Mate, firstMate],
      [u19Team, firstTeam],
      "home",
    );
    expect(cards.find((c) => c.teamUid === "t-u19")?.focusRank).toBe(1);
    expect(cards.find((c) => c.teamUid === "t-first")?.focusRank).toBe(1);
    const best = pickBestMatchExperienceCard(cards, "home");
    expect(best?.teamUid).toBe("t-first");
  });

  it("pickBest stays on youth when First would bury them", () => {
    const u19Team = team({
      teamUid: "t-u19",
      name: "U19",
      clubName: "Home",
      squadUnit: "under19s",
      teamType: 11,
      rosterLen: 10,
      clubId: "home",
    });
    const firstTeam = team({
      teamUid: "t-first",
      name: "First",
      clubName: "Home",
      squadUnit: "firstTeam",
      teamType: 0,
      rosterLen: 10,
      clubId: "home",
    });
    const focus = player({
      id: "y",
      name: "Youth",
      positions: ["ST"],
      currentAbility: 110,
      squadTeamUid: "t-u19",
      clubId: "home",
    });
    const u19Mate = player({
      id: "um",
      name: "U19 Mate",
      positions: ["ST"],
      currentAbility: 100,
      squadTeamUid: "t-u19",
      clubId: "home",
    });
    const firstPack = Array.from({ length: 4 }, (_, i) =>
      player({
        id: `f${i}`,
        name: `First ${i}`,
        positions: ["ST"],
        currentAbility: 140 - i,
        squadTeamUid: "t-first",
        clubId: "home",
      }),
    );
    const cards = buildMatchExperienceCards(
      focus,
      [focus, u19Mate, ...firstPack],
      [u19Team, firstTeam],
      "home",
    );
    expect(cards.find((c) => c.teamUid === "t-first")?.focusRank).toBeGreaterThan(2);
    const best = pickBestMatchExperienceCard(cards, "home");
    expect(best?.teamUid).toBe("t-u19");
  });

  it("pickBest does not hop equal-rung First (II vs Europa First)", () => {
    const legiaFirst = team({
      teamUid: "t-legia",
      name: "First Team",
      clubName: "Legia Warszawa",
      squadUnit: "firstTeam",
      teamType: 0,
      rosterLen: 20,
      clubId: "legia",
    });
    const schalkeIi = team({
      teamUid: "t-s04ii",
      name: "First Team",
      clubName: "FC Schalke 04 II",
      squadUnit: "firstTeam",
      teamType: 0,
      rosterLen: 20,
      clubId: "s04ii",
    });
    const focus = player({
      id: "eze",
      name: "Eze",
      positions: ["ST"],
      currentAbility: 120,
      squadTeamUid: "t-legia",
      clubId: "legia",
    });
    const legiaMate = player({
      id: "lm",
      name: "Legia Mate",
      positions: ["ST"],
      currentAbility: 115,
      squadTeamUid: "t-legia",
      clubId: "legia",
    });
    const iiMate = player({
      id: "im",
      name: "II Mate",
      positions: ["ST"],
      currentAbility: 80,
      squadTeamUid: "t-s04ii",
      clubId: "s04ii",
    });
    const cards = buildMatchExperienceCards(
      focus,
      [focus, legiaMate, iiMate],
      [legiaFirst, schalkeIi],
      "legia",
    );
    expect(cards.find((c) => c.teamUid === "t-legia")?.focusRank).toBe(1);
    expect(cards.find((c) => c.teamUid === "t-s04ii")?.focusRank).toBe(1);
    const best = pickBestMatchExperienceCard(cards, "legia");
    expect(best?.teamUid).toBe("t-legia");
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
