import { describe, expect, it } from "vitest";
import {
  isAtClubSquadPlayer,
  isLoanedOutSquadPlayer,
  isMoveOnCandidate,
  MOVE_ON_HEADROOM_MAX,
  PA_MOVE_ON_MAX,
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

describe("isMoveOnCandidate", () => {
  it("keeps low PA with CA near PA", () => {
    expect(
      isMoveOnCandidate({ currentAbility: 120, potentialAbility: 128 }),
    ).toBe(true);
    expect(
      isMoveOnCandidate({
        currentAbility: PA_MOVE_ON_MAX,
        potentialAbility: PA_MOVE_ON_MAX,
      }),
    ).toBe(true);
    expect(
      isMoveOnCandidate({
        currentAbility: PA_MOVE_ON_MAX - MOVE_ON_HEADROOM_MAX,
        potentialAbility: PA_MOVE_ON_MAX,
      }),
    ).toBe(true);
  });

  it("drops high PA, big headroom, or missing CA/PA", () => {
    expect(
      isMoveOnCandidate({ currentAbility: 130, potentialAbility: 141 }),
    ).toBe(false);
    expect(
      isMoveOnCandidate({
        currentAbility: PA_MOVE_ON_MAX - MOVE_ON_HEADROOM_MAX - 1,
        potentialAbility: PA_MOVE_ON_MAX,
      }),
    ).toBe(false);
    expect(
      isMoveOnCandidate({ currentAbility: null, potentialAbility: 120 }),
    ).toBe(false);
    expect(
      isMoveOnCandidate({ currentAbility: 120, potentialAbility: null }),
    ).toBe(false);
  });
});
