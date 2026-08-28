import { describe, expect, it } from "vitest";
import {
  countAtClubSquadUnit,
  gmAdvice,
  GM_DEVELOPMENT_AGE_MAX,
  isAtClubSquadPlayer,
  isHoydProspect,
  isLoanedOutSquadPlayer,
  MOVE_ON_HEADROOM_MAX,
  squadMedianCA,
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
