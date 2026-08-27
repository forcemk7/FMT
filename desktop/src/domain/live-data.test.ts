import { describe, expect, it } from "vitest";
import {
  gmAdvice,
  isAtClubSquadPlayer,
  isLoanedOutSquadPlayer,
  MOVE_ON_HEADROOM_MAX,
  squadAverageCA,
} from "./live-data";

describe("isAtClubSquadPlayer", () => {
  it("keeps managed at-club players", () => {
    expect(
      isAtClubSquadPlayer({ clubId: "920", loanedOut: false }, "920"),
    ).toBe(true);
    expect(isAtClubSquadPlayer({ clubId: "920", loanedOut: null }, "920")).toBe(
      true,
    );
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

describe("squadAverageCA", () => {
  it("averages finite CA only", () => {
    expect(
      squadAverageCA([
        { currentAbility: 100 },
        { currentAbility: 120 },
        { currentAbility: null },
      ]),
    ).toBe(110);
  });

  it("returns null when no finite CA", () => {
    expect(squadAverageCA([{ currentAbility: null }])).toBeNull();
    expect(squadAverageCA([])).toBeNull();
  });
});

describe("gmAdvice", () => {
  const avg = 130;

  it("sells when PA below avg and CA near PA", () => {
    expect(
      gmAdvice({ currentAbility: 118, potentialAbility: 122 }, avg),
    ).toBe("sell");
    expect(
      gmAdvice(
        {
          currentAbility: avg - 20 - MOVE_ON_HEADROOM_MAX,
          potentialAbility: avg - 20,
        },
        avg,
      ),
    ).toBe("sell");
  });

  it("loans when PA at/above avg and CA below avg", () => {
    expect(
      gmAdvice({ currentAbility: 110, potentialAbility: 140 }, avg),
    ).toBe("loan");
    expect(
      gmAdvice({ currentAbility: 129, potentialAbility: 130 }, avg),
    ).toBe("loan");
  });

  it("returns null when neither lane or missing CA/PA", () => {
    // PA below avg but too much headroom → not sell; not loan either
    expect(
      gmAdvice(
        {
          currentAbility: avg - 20 - MOVE_ON_HEADROOM_MAX - 1,
          potentialAbility: avg - 20,
        },
        avg,
      ),
    ).toBeNull();
    // already at/above avg CA
    expect(
      gmAdvice({ currentAbility: 130, potentialAbility: 140 }, avg),
    ).toBeNull();
    expect(
      gmAdvice({ currentAbility: null, potentialAbility: 120 }, avg),
    ).toBeNull();
    expect(
      gmAdvice({ currentAbility: 120, potentialAbility: null }, avg),
    ).toBeNull();
  });
});
