import { describe, expect, it } from "vitest";
import {
  penaltyTakerScore,
  rankPenaltyTakers,
  type PenaltyTakerCandidate,
} from "../src/inference/penalty-taker.ts";

function player(
  partial: Partial<PenaltyTakerCandidate> &
    Pick<PenaltyTakerCandidate, "id" | "name">,
): PenaltyTakerCandidate {
  return {
    penaltyTaking: 10,
    composure: 10,
    pressure: 10,
    ...partial,
  };
}

describe("penaltyTakerScore", () => {
  it("averages the three attributes equally", () => {
    expect(
      penaltyTakerScore({ penaltyTaking: 18, composure: 15, pressure: 12 }),
    ).toBe(15);
  });

  it("returns NaN when any scored attr is missing", () => {
    expect(
      penaltyTakerScore({
        penaltyTaking: 18,
        composure: Number.NaN,
        pressure: 12,
      }),
    ).toBeNaN();
  });

  it("ignores importantMatches even when present on the candidate", () => {
    const base = { penaltyTaking: 14, composure: 14, pressure: 14 };
    expect(
      penaltyTakerScore({
        ...base,
      }),
    ).toBe(
      penaltyTakerScore({
        ...base,
      }),
    );
  });
});

describe("rankPenaltyTakers", () => {
  it("returns the top 5 by score, highest first", () => {
    const squad = [
      player({ id: "1", name: "Low", penaltyTaking: 8, composure: 8, pressure: 8 }),
      player({ id: "2", name: "Ace", penaltyTaking: 18, composure: 17, pressure: 16 }),
      player({ id: "3", name: "Solid", penaltyTaking: 15, composure: 14, pressure: 14 }),
      player({ id: "4", name: "Mid", penaltyTaking: 12, composure: 12, pressure: 12 }),
      player({ id: "5", name: "High", penaltyTaking: 16, composure: 16, pressure: 15 }),
      player({ id: "6", name: "Bench", penaltyTaking: 11, composure: 11, pressure: 11 }),
      player({ id: "7", name: "Rival", penaltyTaking: 16, composure: 15, pressure: 15 }),
    ];
    const ranked = rankPenaltyTakers(squad, 5);
    expect(ranked.map((r) => r.name)).toEqual([
      "Ace",
      "High",
      "Rival",
      "Solid",
      "Mid",
    ]);
    expect(ranked.map((r) => r.rank)).toEqual([1, 2, 3, 4, 5]);
    expect(ranked[0]!.score).toBeCloseTo((18 + 17 + 16) / 3);
  });

  it("skips candidates missing required attrs", () => {
    const ranked = rankPenaltyTakers(
      [
        player({ id: "ok", name: "Ok", penaltyTaking: 14, composure: 14, pressure: 14 }),
        {
          id: "bad",
          name: "Bad",
          penaltyTaking: 20,
          composure: 20,
          pressure: Number.NaN,
        },
      ],
      5,
    );
    expect(ranked).toHaveLength(1);
    expect(ranked[0]!.name).toBe("Ok");
  });

  it("breaks ties by name", () => {
    const ranked = rankPenaltyTakers(
      [
        player({ id: "b", name: "Zed", penaltyTaking: 15, composure: 15, pressure: 15 }),
        player({ id: "a", name: "Ann", penaltyTaking: 15, composure: 15, pressure: 15 }),
      ],
      5,
    );
    expect(ranked.map((r) => r.name)).toEqual(["Ann", "Zed"]);
  });
});
