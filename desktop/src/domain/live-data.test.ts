import { describe, expect, it } from "vitest";
import {
  countAtClubSquadUnit,
  countClubEmployees,
  countClubEmployeesAtClub,
  countClubEmployeesOnLoan,
  countSquadTeamRoster,
  gmAdvice,
  GM_DEVELOPMENT_AGE_MAX,
  groupPlayerPosition,
  isAtClubEmployee,
  isAtClubSquadPlayer,
  isAtClubTeamPlayer,
  isHoydProspect,
  isLoanedOutSquadPlayer,
  MOVE_ON_HEADROOM_MAX,
  playerMatchesSquadRosterFilters,
  sortClubTeamsForSquadDesk,
  squadMedianCA,
  squadTeamDisplayName,
  squadTeamTabLabel,
} from "./live-data";

describe("isAtClubSquadPlayer", () => {
  it("keeps managed at-club players", () => {
    expect(
      isAtClubSquadPlayer({ clubId: "920", loanedOut: false, squadUnit: "firstTeam" }, "920"),
    ).toBe(true);
    expect(isAtClubSquadPlayer({ clubId: "920", loanedOut: null }, "920")).toBe(
      true,
    );
  });

  it("filters by squad unit", () => {
    expect(
      isAtClubSquadPlayer({ clubId: "920", loanedOut: false, squadUnit: "under19s" }, "920", "under19s"),
    ).toBe(true);
    expect(
      isAtClubSquadPlayer({ clubId: "920", loanedOut: false, squadUnit: "under19s" }, "920", "firstTeam"),
    ).toBe(false);
  });

  it("drops outgoing loans and other clubs", () => {
    expect(
      isAtClubSquadPlayer({ clubId: "920", loanedOut: true }, "920"),
    ).toBe(false);
    expect(
      isAtClubSquadPlayer({ clubId: "912", loanedOut: false }, "920"),
    ).toBe(false);
    expect(isAtClubSquadPlayer({ clubId: "920", loanedOut: false }, null)).toBe(
      false,
    );
  });

  it("keeps B-team affiliate reserves at club when loanedOut is false", () => {
    expect(
      isAtClubSquadPlayer(
        { clubId: "920", loanedOut: false, squadUnit: "reserves", squadTeamUid: "3609393" },
        "920",
        "reserves",
      ),
    ).toBe(true);
    expect(
      isAtClubTeamPlayer(
        { clubId: "920", loanedOut: false, squadTeamUid: "3609393" },
        "920",
        "3609393",
      ),
    ).toBe(true);
  });
});

describe("isAtClubEmployee", () => {
  it("keeps managed at-club players in any squad unit", () => {
    expect(
      isAtClubEmployee({ clubId: "920", loanedOut: false }, "920"),
    ).toBe(true);
    expect(
      isAtClubEmployee({ clubId: "920", loanedOut: false, squadUnit: "under19s" } as never, "920"),
    ).toBe(true);
    expect(isAtClubEmployee({ clubId: "920", loanedOut: null }, "920")).toBe(true);
  });

  it("drops outgoing loans and other clubs", () => {
    expect(isAtClubEmployee({ clubId: "920", loanedOut: true }, "920")).toBe(false);
    expect(isAtClubEmployee({ clubId: "912", loanedOut: false }, "920")).toBe(false);
    expect(isAtClubEmployee({ clubId: "920", loanedOut: false }, null)).toBe(false);
  });
});

describe("countClubEmployees", () => {
  it("counts all managed-club rows regardless of loan or unit", () => {
    const players = [
      { clubId: "920", loanedOut: false, squadUnit: "firstTeam" as const },
      { clubId: "920", loanedOut: true, squadUnit: "under19s" as const },
      { clubId: "912", loanedOut: false, squadUnit: "under19s" as const },
    ];
    expect(countClubEmployees(players, "920")).toBe(2);
  });
});

describe("groupPlayerPosition", () => {
  it("maps sweeper primary to centre-backs", () => {
    expect(groupPlayerPosition({ positions: ["SW"], secondaryPositions: [] } as never)).toBe(
      "Centre-backs",
    );
  });

  it("maps MR primary to wingers", () => {
    expect(
      groupPlayerPosition({ positions: ["MR"], secondaryPositions: ["AMR"], bestCalculatedPosition: "MR" } as never),
    ).toBe("Wingers");
  });

  it("uses secondary MR when best calculated slot is unmapped", () => {
    expect(
      groupPlayerPosition({ positions: [], secondaryPositions: ["MR"], bestCalculatedPosition: null } as never),
    ).toBe("Wingers");
  });

  it("groups by primary DM even when CB and LB are secondaries", () => {
    expect(
      groupPlayerPosition({
        positions: ["DM"],
        secondaryPositions: ["CB", "LB"],
        bestCalculatedPosition: "DM",
      } as never),
    ).toBe("Defensive midfielders");
  });
});

describe("squadTeamTabLabel", () => {
  it("uses the in-game team name only", () => {
    expect(squadTeamTabLabel({ name: "FC Schalke 04 U19", teamUid: "1" })).toBe(
      "FC Schalke 04 U19",
    );
  });

  it("falls back to team uid when FM team name is empty", () => {
    expect(squadTeamTabLabel({ name: "  ", teamUid: "2000069496" })).toBe(
      "Team 2000069496",
    );
  });
});

describe("countSquadTeamRoster", () => {
  it("counts at-club, loaned in, and loaned out on the same team roster", () => {
    const players = [
      { clubId: "920", squadTeamUid: "1", loanedOut: false, loanedIn: false },
      { clubId: "920", squadTeamUid: "1", loanedOut: true, loanedIn: false },
      { clubId: "920", squadTeamUid: "1", loanedOut: false, loanedIn: true },
      { clubId: "920", squadTeamUid: "2", loanedOut: false, loanedIn: false },
    ];
    expect(countSquadTeamRoster(players, "920", "1")).toEqual({
      atClub: 1,
      loanedIn: 1,
      loanedOut: 1,
    });
  });
});

describe("playerMatchesSquadRosterFilters", () => {
  it("keeps players whose status is enabled", () => {
    const atClub = { clubId: "920", loanedOut: false, loanedIn: false };
    const loanedIn = { clubId: "920", loanedOut: false, loanedIn: true };
    const loanedOut = { clubId: "920", loanedOut: true, loanedIn: false };
    expect(
      playerMatchesSquadRosterFilters(atClub, "920", new Set(["atClub"])),
    ).toBe(true);
    expect(
      playerMatchesSquadRosterFilters(loanedIn, "920", new Set(["atClub"])),
    ).toBe(false);
    expect(
      playerMatchesSquadRosterFilters(
        loanedOut,
        "920",
        new Set(["loanedOut", "loanedIn"]),
      ),
    ).toBe(true);
  });

  it("rejects other clubs and empty filter sets", () => {
    expect(
      playerMatchesSquadRosterFilters(
        { clubId: "912", loanedOut: false, loanedIn: false },
        "920",
        new Set(["atClub"]),
      ),
    ).toBe(false);
    expect(
      playerMatchesSquadRosterFilters(
        { clubId: "920", loanedOut: false, loanedIn: false },
        "920",
        new Set(),
      ),
    ).toBe(false);
  });
});

describe("sortClubTeamsForSquadDesk", () => {
  it("orders senior before youth before reserves", () => {
    const sorted = sortClubTeamsForSquadDesk([
      { name: "Res", squadUnit: "reserves", rosterLen: 8, teamUid: "3", isManagerTeam: false },
      { name: "U19", squadUnit: "under19s", rosterLen: 22, teamUid: "2", isManagerTeam: false },
      { name: "Senior", squadUnit: "firstTeam", rosterLen: 28, teamUid: "1", isManagerTeam: true },
    ]);
    expect(sorted.map((team) => team.squadUnit)).toEqual(["firstTeam", "under19s", "reserves"]);
  });
});

describe("squadTeamDisplayName", () => {
  it("keeps a distinct FM team string (Schalke U19)", () => {
    expect(
      squadTeamDisplayName(
        { name: "FC Schalke 04 U19", teamUid: "2", teamType: 11 },
        "FC Schalke 04",
      ),
    ).toBe("FC Schalke 04 U19");
  });

  it("disambiguates English club-name collisions via TeamType", () => {
    expect(
      squadTeamDisplayName({ name: "Liverpool", teamUid: "676", teamType: 0 }, "Liverpool"),
    ).toBe("First Team");
    expect(
      squadTeamDisplayName({ name: "Liverpool", teamUid: "2", teamType: 10 }, "Liverpool"),
    ).toBe("U21");
    expect(
      squadTeamDisplayName({ name: "liverpool", teamUid: "3", teamType: 12 }, "Liverpool"),
    ).toBe("U18");
  });

  it("uses TeamType when the FM string is empty", () => {
    expect(
      squadTeamDisplayName({ name: "", teamUid: "99", teamType: 11 }, "Leicester City"),
    ).toBe("U19");
  });

  it("falls back to Team uid when name and type are missing", () => {
    expect(squadTeamDisplayName({ name: "", teamUid: "42" })).toBe("Team 42");
  });
});

describe("countAtClubSquadUnit", () => {
  it("counts only at-club players in the requested unit", () => {
    const players = [
      { clubId: "920", loanedOut: false, squadUnit: "firstTeam" as const },
      { clubId: "920", loanedOut: false, squadUnit: "under19s" as const },
      { clubId: "920", loanedOut: true, squadUnit: "under19s" as const },
      { clubId: "912", loanedOut: false, squadUnit: "under19s" as const },
    ];
    expect(countAtClubSquadUnit(players, "920", "under19s")).toBe(1);
    expect(countAtClubSquadUnit(players, "920", "firstTeam")).toBe(1);
  });
});

describe("isLoanedOutSquadPlayer", () => {
  it("keeps only managed outgoing loans", () => {
    expect(
      isLoanedOutSquadPlayer({ clubId: "920", loanedOut: true }, "920"),
    ).toBe(true);
    expect(
      isLoanedOutSquadPlayer({ clubId: "920", loanedOut: false }, "920"),
    ).toBe(false);
    expect(
      isLoanedOutSquadPlayer({ clubId: "912", loanedOut: true }, "920"),
    ).toBe(false);
  });
});

describe("squadMedianCA", () => {
  it("returns middle CA (odd count)", () => {
    expect(
      squadMedianCA([
        { currentAbility: 100 },
        { currentAbility: 120 },
        { currentAbility: 140 },
        { currentAbility: null },
      ]),
    ).toBe(120);
  });

  it("averages two middle values when even count", () => {
    expect(
      squadMedianCA([
        { currentAbility: 100 },
        { currentAbility: 120 },
        { currentAbility: 140 },
        { currentAbility: 160 },
      ]),
    ).toBe(130);
  });

  it("ignores a star outlier vs mean", () => {
    const squad = [
      { currentAbility: 100 },
      { currentAbility: 110 },
      { currentAbility: 120 },
      { currentAbility: 130 },
      { currentAbility: 200 },
    ];
    expect(squadMedianCA(squad)).toBe(120);
  });

  it("returns null when no finite CA", () => {
    expect(squadMedianCA([{ currentAbility: null }])).toBeNull();
    expect(squadMedianCA([])).toBeNull();
  });
});

describe("gmAdvice", () => {
  const ref = 130;

  it("sells when PA below ref and CA near PA", () => {
    expect(
      gmAdvice({ currentAbility: 118, potentialAbility: 122 }, ref),
    ).toBe("sell");
    expect(
      gmAdvice(
        {
          currentAbility: ref - 20 - MOVE_ON_HEADROOM_MAX,
          potentialAbility: ref - 20,
        },
        ref,
      ),
    ).toBe("sell");
  });

  it("loans when PA at/above ref, CA below ref, and in dev range", () => {
    expect(
      gmAdvice(
        { currentAbility: 110, potentialAbility: 140, age: 20 },
        ref,
      ),
    ).toBe("loan");
    expect(
      gmAdvice(
        { currentAbility: 120, potentialAbility: 140, age: GM_DEVELOPMENT_AGE_MAX },
        ref,
      ),
    ).toBe("loan");
  });

  it("loans young low-PA players with room to grow before eventual sell", () => {
    expect(
      gmAdvice(
        { currentAbility: 95, potentialAbility: 115, age: 19 },
        ref,
      ),
    ).toBe("loan");
  });

  it("sells declining veterans instead of loaning", () => {
    expect(
      gmAdvice(
        { currentAbility: 155, potentialAbility: 175, age: 32 },
        167.5,
      ),
    ).toBe("sell");
    expect(
      gmAdvice(
        { currentAbility: 120, potentialAbility: 140, age: 28 },
        ref,
      ),
    ).toBe("sell");
  });

  it("does not loan past dev age even when CA below ref", () => {
    expect(
      gmAdvice(
        { currentAbility: 129, potentialAbility: 135, age: 30 },
        ref,
      ),
    ).toBeNull();
  });

  it("returns null when neither lane or missing CA/PA", () => {
    expect(
      gmAdvice(
        {
          currentAbility: ref - 20 - MOVE_ON_HEADROOM_MAX - 1,
          potentialAbility: ref - 20,
        },
        ref,
      ),
    ).toBeNull();
    expect(
      gmAdvice({ currentAbility: 130, potentialAbility: 140 }, ref),
    ).toBeNull();
    expect(
      gmAdvice({ currentAbility: null, potentialAbility: 120 }, ref),
    ).toBeNull();
    expect(
      gmAdvice({ currentAbility: 120, potentialAbility: null }, ref),
    ).toBeNull();
  });
});

describe("isHoydProspect", () => {
  const ref = 130;

  it("includes high PA with headroom above squad median CA", () => {
    expect(
      isHoydProspect({ currentAbility: 110, potentialAbility: 150, age: 20 }, ref),
    ).toBe(true);
    expect(
      isHoydProspect(
        {
          currentAbility: ref - MOVE_ON_HEADROOM_MAX - 1,
          potentialAbility: ref,
          age: GM_DEVELOPMENT_AGE_MAX,
        },
        ref,
      ),
    ).toBe(true);
  });

  it("excludes players past development age", () => {
    expect(
      isHoydProspect(
        { currentAbility: 110, potentialAbility: 150, age: GM_DEVELOPMENT_AGE_MAX + 1 },
        ref,
      ),
    ).toBe(false);
    expect(
      isHoydProspect({ currentAbility: 110, potentialAbility: 150, age: null }, ref),
    ).toBe(false);
  });

  it("excludes low PA, near-ceiling, or missing CA/PA", () => {
    expect(
      isHoydProspect({ currentAbility: 120, potentialAbility: 125, age: 20 }, ref),
    ).toBe(false);
    expect(
      isHoydProspect(
        {
          currentAbility: ref - MOVE_ON_HEADROOM_MAX,
          potentialAbility: ref,
          age: 20,
        },
        ref,
      ),
    ).toBe(false);
    expect(
      isHoydProspect({ currentAbility: 110, potentialAbility: 120, age: 20 }, ref),
    ).toBe(false);
    expect(
      isHoydProspect({ currentAbility: null, potentialAbility: 150, age: 20 }, ref),
    ).toBe(false);
    expect(
      isHoydProspect({ currentAbility: 110, potentialAbility: null, age: 20 }, ref),
    ).toBe(false);
  });
});
