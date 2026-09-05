import { describe, expect, it } from "vitest";
import {
  GOALKEEPING_ATTRIBUTES,
  gkGoalkeepingAttributeNames,
  goalkeeperRating,
  nativeGoalkeeperRating,
  resolveGoalkeeperRating,
  sortedAttributeEntries,
} from "./attribute-desk";

describe("gkGoalkeepingAttributeNames", () => {
  it("merges First Touch and Passing then sorts A–Z", () => {
    const names = gkGoalkeepingAttributeNames();
    expect(names[0]).toBe("Aerial Reach");
    expect(names).toContain("First Touch");
    expect(names).toContain("Passing");
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
  });
});

describe("nativeGoalkeeperRating", () => {
  it("clamps the live GK familiarity field to 0–10", () => {
    expect(nativeGoalkeeperRating(3)).toBe(3);
    expect(nativeGoalkeeperRating(15)).toBe(10);
    expect(nativeGoalkeeperRating(null)).toBeNull();
    expect(nativeGoalkeeperRating(undefined)).toBeNull();
  });
});

describe("resolveGoalkeeperRating", () => {
  it("prefers the native field over the mean fallback", () => {
    const attrs = Object.fromEntries(GOALKEEPING_ATTRIBUTES.map((name) => [name, 2]));
    expect(resolveGoalkeeperRating(4, attrs)).toBe(4);
    expect(resolveGoalkeeperRating(null, attrs)).toBe(1);
  });
});

describe("goalkeeperRating", () => {
  it("returns null when no GK attrs are mapped", () => {
    expect(goalkeeperRating({})).toBeNull();
    expect(goalkeeperRating(undefined)).toBeNull();
  });

  it("maps mean(1–20) onto 0–10 via round(mean / 2) as fallback", () => {
    const names = gkGoalkeepingAttributeNames();
    const all = Object.fromEntries(names.map((name) => [name, 6]));
    expect(goalkeeperRating(all)).toBe(3);

    const high = Object.fromEntries(names.map((name) => [name, 8]));
    expect(goalkeeperRating(high)).toBe(4);

    const low = Object.fromEntries(names.map((name) => [name, 4]));
    expect(goalkeeperRating(low)).toBe(2);
  });

  it("ignores unmapped names in the mean", () => {
    expect(
      goalkeeperRating({
        Handling: 10,
        Reflexes: 6,
        "Aerial Reach": null,
      }),
    ).toBe(4);
  });
});

describe("sortedAttributeEntries", () => {
  it("sorts names alphabetically and preserves values", () => {
    expect(
      sortedAttributeEntries(["Technique", "Crossing", "Passing"], {
        Crossing: 1,
        Passing: 15,
        Technique: 13,
      }),
    ).toEqual([
      { name: "Crossing", value: 1 },
      { name: "Passing", value: 15 },
      { name: "Technique", value: 13 },
    ]);
  });
});
