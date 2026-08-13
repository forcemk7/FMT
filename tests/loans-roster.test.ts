import { describe, expect, it } from "vitest";
import {
  loanCrestClubId,
  loanedOutPlayers,
  loansByUnit,
} from "../web/loans-roster.ts";
import type { RosterPlayer } from "../web/roster-data.ts";
import type { PlayerLoan } from "../shared/save/types.ts";

function player(
  partial: Partial<RosterPlayer> & Pick<RosterPlayer, "uid" | "name">,
  loan?: PlayerLoan | null,
): RosterPlayer {
  return {
    jobId: 1,
    dateOfBirth: null,
    nation: null,
    secondNation: null,
    positions: null,
    dynamics: { captaincy: null, hierarchy: null, socialGroup: null },
    training: { unit: null },
    attributes: null,
    attributeHistory: null,
    loan: loan ?? null,
    ...partial,
  };
}

describe("loanedOutPlayers", () => {
  it("returns empty for empty input", () => {
    expect(loanedOutPlayers([])).toEqual([]);
  });

  it("keeps loanedOut only and ignores loanedIn / atClub / missing", () => {
    const out = loanedOutPlayers([
      player({ uid: 1, name: "At Club" }, { status: "atClub" }),
      player({ uid: 2, name: "Vlad" }, { status: "loanedOut", loanClubId: 912 }),
      player(
        { uid: 3, name: "Loaned In" },
        { status: "loanedIn", parentClubId: 100 },
      ),
      player({ uid: 4, name: "No Loan" }),
      player(
        { uid: 5, name: "Sipho" },
        { status: "loanedOut", loanClubId: 1456 },
      ),
    ]);
    expect(out.map((p) => p.uid)).toEqual([5, 2]); // Sipho, Vlad — name sort
  });

  it("sorts by name (base localeCompare)", () => {
    const out = loanedOutPlayers([
      player({ uid: 1, name: "Zebra" }, { status: "loanedOut" }),
      player({ uid: 2, name: "alpha" }, { status: "loanedOut" }),
      player({ uid: 3, name: "Beta" }, { status: "loanedOut" }),
    ]);
    expect(out.map((p) => p.name)).toEqual(["alpha", "Beta", "Zebra"]);
  });
});

describe("loansByUnit", () => {
  it("buckets empty units", () => {
    expect(
      loansByUnit({ firstTeam: [], reserves: [], under19s: [] }),
    ).toEqual({ firstTeam: [], reserves: [], under19s: [] });
  });

  it("FT-only loans stay in firstTeam", () => {
    const ft = player(
      { uid: 10, name: "Vlad" },
      { status: "loanedOut", loanClubId: 912 },
    );
    const result = loansByUnit({
      firstTeam: [ft, player({ uid: 11, name: "Paco" }, { status: "atClub" })],
      reserves: [player({ uid: 20, name: "II kid" }, { status: "atClub" })],
      under19s: [],
    });
    expect(result.firstTeam.map((p) => p.uid)).toEqual([10]);
    expect(result.reserves).toEqual([]);
    expect(result.under19s).toEqual([]);
  });

  it("multi-unit bucketing ignores loanedIn", () => {
    const result = loansByUnit({
      firstTeam: [
        player({ uid: 1, name: "Vlad" }, { status: "loanedOut", loanClubId: 1 }),
        player(
          { uid: 2, name: "Inbound" },
          { status: "loanedIn", parentClubId: 99 },
        ),
      ],
      reserves: [
        player(
          { uid: 3, name: "Manole" },
          { status: "loanedOut", loanClubId: 2 },
        ),
      ],
      under19s: [
        player(
          { uid: 4, name: "Braescu" },
          { status: "loanedOut", loanClubId: 3 },
        ),
        player({ uid: 5, name: "Home U19" }, { status: "atClub" }),
      ],
    });
    expect(result.firstTeam.map((p) => p.uid)).toEqual([1]);
    expect(result.reserves.map((p) => p.uid)).toEqual([3]);
    expect(result.under19s.map((p) => p.uid)).toEqual([4]);
  });
});

describe("loanCrestClubId", () => {
  it("returns loanClubId for loanedOut when finite", () => {
    expect(
      loanCrestClubId(
        player(
          { uid: 1, name: "Vlad" },
          { status: "loanedOut", loanClubId: 912 },
        ),
      ),
    ).toBe(912);
  });

  it("returns null when loanedOut lacks club id", () => {
    expect(
      loanCrestClubId(player({ uid: 1, name: "X" }, { status: "loanedOut" })),
    ).toBeNull();
  });

  it("returns null for loanedIn / atClub / missing", () => {
    expect(
      loanCrestClubId(
        player(
          { uid: 1, name: "In" },
          { status: "loanedIn", parentClubId: 100, loanClubId: 50 },
        ),
      ),
    ).toBeNull();
    expect(
      loanCrestClubId(player({ uid: 2, name: "Home" }, { status: "atClub" })),
    ).toBeNull();
    expect(loanCrestClubId(player({ uid: 3, name: "Bare" }))).toBeNull();
  });
});
